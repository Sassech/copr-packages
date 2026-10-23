# shellcheck shell=bash
# Shared upstream resolution for make-srpm.sh and check-upstream.sh.
# Source it; it defines functions only and has no side effects.
#
# Both scripts must agree on which tag/commit a spec builds, so this is the
# single place where that is decided.

# Print the value of a `%global <name> <value>` line from the spec.
spec_global() {
    awk -v n="$2" '$1 == "%global" && $2 == n { print $3; exit }' "$1"
}

# Latest stable tag (vX.Y.Z or X.Y.Z, pre-releases excluded), highest by version sort.
latest_tag() {
    git ls-remote --tags --refs "$1" \
        | awk '{ sub("refs/tags/", "", $2); print $2 }' \
        | { grep -E '^v?[0-9]+(\.[0-9]+)*$' || true; } \
        | sort -V | tail -n 1
}

# Commit a tag points to (peels annotated tags).
tag_commit() {
    local url="$1" tag="$2" out
    out="$(git ls-remote "$url" "refs/tags/${tag}^{}" "refs/tags/${tag}")"
    awk -v t="refs/tags/${tag}^{}" '$2 == t { print $1; found = 1; exit } END { exit !found }' <<<"$out" \
        || awk 'NR == 1 { print $1 }' <<<"$out"
}

# Commit of the default branch HEAD.
head_commit() {
    git ls-remote "$1" HEAD | awk 'NR == 1 { print $1 }'
}

# resolve_upstream <forgeurl> <release|git>
# Sets UPSTREAM_TAG, UPSTREAM_BASE (tag without leading "v") and
# UPSTREAM_COMMIT (40-char sha). Returns non-zero with a message on stderr
# when the tag or commit cannot be resolved.
# shellcheck disable=SC2034  # UPSTREAM_* are outputs read by the sourcing script
resolve_upstream() {
    local url="$1" track="$2"
    UPSTREAM_TAG="$(latest_tag "$url")"
    if [[ -z $UPSTREAM_TAG ]]; then
        printf 'no stable tag found in %s\n' "$url" >&2
        return 1
    fi
    UPSTREAM_BASE="${UPSTREAM_TAG#v}"
    case $track in
        release) UPSTREAM_COMMIT="$(tag_commit "$url" "$UPSTREAM_TAG")" ;;
        git) UPSTREAM_COMMIT="$(head_commit "$url")" ;;
        *)
            printf 'srpm_track must be release|git, got %s\n' "$track" >&2
            return 1
            ;;
    esac
    if [[ ! $UPSTREAM_COMMIT =~ ^[0-9a-f]{40}$ ]]; then
        printf 'cannot resolve commit for %s (%s)\n' "$url" "$track" >&2
        return 1
    fi
}
