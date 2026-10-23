#!/usr/bin/env bash
# Build an SRPM for one package of this repo with the latest upstream sources.
#
# Usage: make-srpm.sh <spec> <outdir>
#
# The spec declares, as plain %global lines:
#   forgeurl            GitHub repository URL (https://github.com/<owner>/<repo>)
#   srpm_track          "release" (latest stable vX.Y.Z tag) or "git" (default branch HEAD)
#   cargo_manifest_dir  directory holding Cargo.toml/Cargo.lock ("." or e.g. "src-tauri")
#
# This script resolves the upstream tag/commit at SRPM time (nothing is
# hardcoded), downloads the GitHub archive (Source0), vendors all crates with
# `cargo vendor` (Source1) so rpmbuild runs offline, and writes a spec copy with
# injected %global defines (commit, upstream_version, snapdate) and a changelog
# entry.
#
# Environment overrides:
#   PACKAGER  changelog identity (default: "Sassech <lainstroop@gmail.com>")
set -euo pipefail

die() { printf 'make-srpm: error: %s\n' "$*" >&2; exit 1; }
log() { printf 'make-srpm: %s\n' "$*" >&2; }

TOPDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TOPDIR
readonly PACKAGER="${PACKAGER:-Sassech <lainstroop@gmail.com>}"

ensure_tools() {
    local -a missing=()
    command -v git >/dev/null || missing+=(git-core)
    command -v curl >/dev/null || missing+=(curl)
    command -v tar >/dev/null || missing+=(tar)
    command -v xz >/dev/null || missing+=(xz)
    command -v cargo >/dev/null || missing+=(cargo)
    command -v rpmbuild >/dev/null || missing+=(rpm-build)
    ((${#missing[@]} == 0)) && return 0
    [[ $(id -u) -eq 0 ]] || die "missing tools (${missing[*]}); install them or run as root"
    log "installing ${missing[*]}"
    dnf -y install "${missing[@]}"
}

# Print the value of a `%global <name> <value>` line from the spec.
spec_global() {
    awk -v n="$2" '$1 == "%global" && $2 == n { print $3; exit }' "$1"
}

# Latest stable tag (vX.Y.Z or X.Y.Z, pre-releases excluded), highest by version sort.
latest_tag() {
    git ls-remote --tags --refs "$1" \
        | awk '{ sub("refs/tags/", "", $2); print $2 }' \
        | grep -E '^v?[0-9]+(\.[0-9]+)*$' \
        | sort -V | tail -n 1
}

# Commit a tag points to (peels annotated tags).
tag_commit() {
    local url="$1" tag="$2" out
    out="$(git ls-remote "$url" "refs/tags/${tag}^{}" "refs/tags/${tag}")"
    awk -v t="refs/tags/${tag}^{}" '$2 == t { print $1; found = 1; exit } END { exit !found }' <<<"$out" \
        || awk 'NR == 1 { print $1 }' <<<"$out"
}

main() {
    (($# == 2)) || die "usage: make-srpm.sh <spec> <outdir>"
    local spec="$1" outdir="$2"
    [[ -n $spec ]] || die "no spec given (pass spec=<pkg>/<pkg>.spec)"
    [[ -f $spec ]] || spec="${TOPDIR}/${spec}"
    [[ -f $spec ]] || die "spec not found: $1"
    spec="$(cd "$(dirname "$spec")" && pwd)/$(basename "$spec")"

    ensure_tools

    local name forgeurl track manifest_dir
    name="$(basename "$spec" .spec)"
    forgeurl="$(spec_global "$spec" forgeurl)"
    track="$(spec_global "$spec" srpm_track)"
    manifest_dir="$(spec_global "$spec" cargo_manifest_dir)"
    [[ -n $forgeurl ]] || die "$spec: missing '%global forgeurl'"
    [[ $track == release || $track == git ]] || die "$spec: srpm_track must be release|git"
    manifest_dir="${manifest_dir:-.}"

    local tag base_version commit snapdate="" version
    tag="$(latest_tag "$forgeurl")"
    [[ -n $tag ]] || die "no stable tag found in $forgeurl"
    base_version="${tag#v}"
    if [[ $track == release ]]; then
        commit="$(tag_commit "$forgeurl" "$tag")"
        version="$base_version"
    else
        commit="$(git ls-remote "$forgeurl" HEAD | awk 'NR == 1 { print $1 }')"
    fi
    [[ $commit =~ ^[0-9a-f]{40}$ ]] || die "cannot resolve commit for $forgeurl ($track)"

    local work
    work="$(mktemp -d)"
    # shellcheck disable=SC2064  # expand now: $work is local
    trap "rm -rf '$work'" EXIT

    if [[ $track == git ]]; then
        # Blob-less shallow fetch: only needed for the commit date.
        git -C "$work" init -q meta
        git -C "$work/meta" fetch -q --depth 1 --filter=blob:none "$forgeurl" "$commit"
        snapdate="$(TZ=UTC git -C "$work/meta" log -1 --format=%cd --date=format-local:%Y%m%d FETCH_HEAD)"
        version="${base_version}^${snapdate}git${commit:0:7}"
    fi
    log "$name: track=$track tag=$tag commit=$commit version=$version"

    local repo="${forgeurl##*/}"
    local src0="${repo}-${commit}.tar.gz"
    local src1="${name}-vendor-${commit:0:7}.tar.xz"
    mkdir -p "$work/sources" "$work/tree"
    curl -fsSL --retry 3 -o "$work/sources/$src0" "${forgeurl}/archive/${commit}/${src0}"
    tar -xzf "$work/sources/$src0" -C "$work/tree"

    local crate_dir="$work/tree/${repo}-${commit}/${manifest_dir}"
    [[ -f "$crate_dir/Cargo.lock" ]] || die "no Cargo.lock in ${manifest_dir}"
    log "vendoring crates in ${manifest_dir}"
    # The printed source config is kept so %prep can wire up git dependencies too.
    (cd "$crate_dir" && cargo vendor --locked --versioned-dirs vendor >vendor-config.toml)
    mv "$crate_dir/vendor-config.toml" "$crate_dir/vendor/"
    tar -C "$crate_dir" -cJf "$work/sources/$src1" vendor

    local gen="$work/${name}.spec"
    {
        printf '%%global commit %s\n' "$commit"
        printf '%%global upstream_version %s\n' "$base_version"
        [[ -z $snapdate ]] || printf '%%global snapdate %s\n' "$snapdate"
        cat "$spec"
        printf '* %s %s - %s-1\n' "$(LC_ALL=C date -u '+%a %b %d %Y')" "$PACKAGER" "$version"
        printf -- '- Automated build of %s %s (%s)\n' "$repo" "$([[ $track == release ]] && echo "$tag" || echo "snapshot")" "${commit:0:12}"
    } >"$gen"

    mkdir -p "$outdir"
    rpmbuild -bs "$gen" \
        --define "_sourcedir $work/sources" \
        --define "_srcrpmdir $outdir"
}

main "$@"
