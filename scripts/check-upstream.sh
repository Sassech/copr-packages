#!/usr/bin/env bash
# Rebuild COPR packages whose upstream moved on.
#
# Usage:
#   check-upstream.sh [<pkg>...]        check the given packages (default: all)
#   check-upstream.sh --changed-files   read changed repo paths on stdin and
#                                       print the packages they affect
#
# For every package (<pkg>/<pkg>.spec) it resolves the upstream tag/commit the
# same way make-srpm.sh does (scripts/upstream-lib.sh), reads the latest COPR
# build from the public API and triggers the COPR custom webhook when needed:
#
#   release track  rebuild if the upstream version differs from the COPR version
#   git track      rebuild if the COPR version is not <base>^...git<sha7> of HEAD
#   no build yet, or latest build has no version (SRPM failure)  -> rebuild
#   same version, latest build failed/canceled  -> skip with a warning
#   build still in progress                     -> skip
#
# Environment:
#   COPR_WEBHOOK_URL  custom webhook base URL ending in /<ID>/<UUID>/ (secret;
#                     required unless DRY_RUN=1)
#   COPR_OWNER        default: sassech
#   COPR_PROJECT      default: packages
#   COPR_URL          default: https://copr.fedorainfracloud.org
#   FORCE=1           rebuild regardless of versions
#   DRY_RUN=1         print decisions, never call the webhook
set -euo pipefail

TOPDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TOPDIR
readonly COPR_OWNER="${COPR_OWNER:-sassech}"
readonly COPR_PROJECT="${COPR_PROJECT:-packages}"
readonly COPR_URL="${COPR_URL:-https://copr.fedorainfracloud.org}"
readonly FORCE="${FORCE:-0}"
readonly DRY_RUN="${DRY_RUN:-0}"

# shellcheck source=scripts/upstream-lib.sh
source "${TOPDIR}/scripts/upstream-lib.sh"

die() { printf 'check-upstream: error: %s\n' "$*" >&2; exit 1; }
warn() {
    printf 'check-upstream: warning: %s\n' "$*" >&2
    [[ -z ${GITHUB_ACTIONS:-} ]] || printf '::warning::%s\n' "$*"
}

# All packages of the repo: directories holding <dir>/<dir>.spec.
all_packages() {
    local spec pkg
    for spec in "$TOPDIR"/*/*.spec; do
        pkg="$(basename "$(dirname "$spec")")"
        [[ $spec == "$TOPDIR/$pkg/$pkg.spec" ]] && printf '%s\n' "$pkg"
    done
}

# Map changed paths (stdin, repo-relative) to packages to force-rebuild:
#   <pkg>/**              -> that package
#   scripts/**, .copr/**  -> every package
#   anything else         -> nothing
changed_packages() {
    local path top all=0
    local -A hit=()
    while IFS= read -r path; do
        [[ -n $path ]] || continue
        top="${path%%/*}"
        [[ $top != "$path" ]] || continue # top-level file
        case $top in
            scripts | .copr) all=1 ;;
            *) [[ -f "$TOPDIR/$top/$top.spec" ]] && hit[$top]=1 ;;
        esac
    done
    if ((all)); then
        all_packages
    elif ((${#hit[@]})); then
        printf '%s\n' "${!hit[@]}" | sort
    fi
}

# Print "<state>\t<version>" of the latest COPR build ("none\t" if no build).
copr_latest() {
    local json
    json="$(curl -fsS --retry 3 -G "${COPR_URL}/api_3/package" \
        --data-urlencode "ownername=${COPR_OWNER}" \
        --data-urlencode "projectname=${COPR_PROJECT}" \
        --data-urlencode "packagename=$1" \
        --data-urlencode "with_latest_build=true")" || return 1
    jq -r '.builds.latest // {} | [(.state // "none"), (.source_package.version // "")] | @tsv' <<<"$json"
}

# Trigger the custom webhook for one package and print the build id.
trigger() {
    local pkg="$1" id
    id="$(curl -fsS --retry 2 -X POST "${COPR_WEBHOOK_URL%/}/${pkg}/")" || return 1
    printf '%s: triggered build %s (%s/coprs/%s/%s/build/%s/)\n' \
        "$pkg" "$id" "$COPR_URL" "$COPR_OWNER" "$COPR_PROJECT" "$id"
}

# Decide for one package. Prints a status line; returns 0 = rebuild,
# 1 = no rebuild, 2 = error.
decide() {
    local pkg="$1" spec forgeurl track state version want
    spec="$TOPDIR/$pkg/$pkg.spec"
    forgeurl="$(spec_global "$spec" forgeurl)"
    track="$(spec_global "$spec" srpm_track)"
    [[ -n $forgeurl ]] || { warn "$pkg: missing '%global forgeurl'"; return 2; }
    resolve_upstream "$forgeurl" "$track" || { warn "$pkg: upstream resolution failed"; return 2; }

    local tsv
    tsv="$(copr_latest "$pkg")" || { warn "$pkg: COPR API request failed"; return 2; }
    IFS=$'\t' read -r state version <<<"$tsv"
    version="${version%-*}" # drop -<release>
    version="${version#*:}" # drop epoch, if any

    if [[ $track == release ]]; then
        want="$UPSTREAM_BASE"
    else
        want="${UPSTREAM_BASE}^*git${UPSTREAM_COMMIT:0:7}"
    fi
    local info="$pkg: $track upstream=${UPSTREAM_TAG}@${UPSTREAM_COMMIT:0:7} copr=${version:-<none>} ($state)"

    if [[ $FORCE == 1 ]]; then
        printf '%s -> rebuild (forced)\n' "$info"
        return 0
    fi
    case $state in
        pending | importing | starting | running | waiting)
            printf '%s -> skip (build in progress)\n' "$info"
            return 1
            ;;
    esac
    if [[ $state == none || -z $version ]]; then
        printf '%s -> rebuild (no previous build with a version)\n' "$info"
        return 0
    fi
    # shellcheck disable=SC2053  # $want is a glob pattern for the git track
    if [[ $version != $want ]]; then
        printf '%s -> rebuild (upstream changed)\n' "$info"
        return 0
    fi
    if [[ $state != succeeded ]]; then
        printf '%s -> skip (same version already %s)\n' "$info" "$state"
        warn "$pkg: latest build of ${version} is ${state}; not retrying (run with FORCE=1 to retry)"
        return 1
    fi
    printf '%s -> up to date\n' "$info"
    return 1
}

main() {
    if [[ ${1:-} == --changed-files ]]; then
        (($# == 1)) || die "--changed-files takes no arguments (paths go on stdin)"
        changed_packages
        return 0
    fi

    command -v jq >/dev/null || die "jq is required"
    if [[ $DRY_RUN != 1 && -z ${COPR_WEBHOOK_URL:-} ]]; then
        die "COPR_WEBHOOK_URL is not set (export it, or use DRY_RUN=1)"
    fi

    local -a pkgs=("$@")
    if ((${#pkgs[@]} == 0)) || [[ ${pkgs[*]} == all ]]; then
        mapfile -t pkgs < <(all_packages)
    fi
    local pkg
    for pkg in "${pkgs[@]}"; do
        [[ -f "$TOPDIR/$pkg/$pkg.spec" ]] || die "unknown package: $pkg"
    done

    local failed=0 rc
    for pkg in "${pkgs[@]}"; do
        rc=0
        decide "$pkg" || rc=$?
        case $rc in
            0)
                if [[ $DRY_RUN == 1 ]]; then
                    printf '%s: dry run, webhook not called\n' "$pkg"
                else
                    trigger "$pkg" || { warn "$pkg: webhook call failed"; failed=1; }
                fi
                ;;
            1) ;;
            *) failed=1 ;;
        esac
    done
    return "$failed"
}

main "$@"
