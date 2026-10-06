#!/usr/bin/env bash
#
# Publish the generated bibliography to the HDR Overleaf project.
#
# Copies out/bibli_hdr_*.bib into the Overleaf git clone, updates the clone
# from Overleaf first, commits only if the files actually changed, and pushes.
#
# Authentication uses git's credential store, scoped to git.overleaf.com in
# the global git config (token in ~/.config/git/credentials-overleaf, mode 600):
#   git config --global credential.https://git.overleaf.com.helper \
#       "store --file ~/.config/git/credentials-overleaf"
# This script never reads or prints the token.
#
# Usage:
#   ./push_bib_to_overleaf.sh            # update, copy, commit, push
#   ./push_bib_to_overleaf.sh --dry-run  # do everything except commit and push
#
# Author: Corentin Ravoux

set -euo pipefail

################################ CONFIG #####################################

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bib_files/out"
REPO="$HOME/Software/overleaf/6a43ba00166d744d7802db95"
OVERLEAF_URL="https://git.overleaf.com"
# Discovered from SRC_DIR rather than hardcoded, so that a new chunk
# (bibli_hdr_2.bib, ...) is picked up automatically when the number of Zotero
# topic files grows past a multiple of 20.
FILES=()
while IFS= read -r _f; do FILES+=("$(basename "$_f")"); done \
    < <(find "$SRC_DIR" -maxdepth 1 -name 'bibli_hdr_*.bib' | sort)

BRANCH="main"
COMMIT_MSG="Update bibliography from Zotero export"

#############################################################################

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

die() { echo "error: $*" >&2; exit 1; }
say() { echo "==> $*"; }

# ---------------------------------------------------------------- preflight

[[ -d "$REPO/.git" ]] || die "$REPO is not a git repository"
git config --get-urlmatch credential.helper "$OVERLEAF_URL" >/dev/null \
    || die "no git credential helper for $OVERLEAF_URL -- see the header of this script"

[[ ${#FILES[@]} -gt 0 ]] || die "no bibli_hdr_*.bib in $SRC_DIR -- run create_bib_hdr.py first"
for f in "${FILES[@]}"; do
    [[ -s "$SRC_DIR/$f" ]] || die "missing or empty source file: $SRC_DIR/$f"
done
say "publishing ${#FILES[@]} file(s): ${FILES[*]}"

# Refuse to run on a dirty tree, except for the bibliography files themselves.
# This is what stops a stray chapter edit from being swept into the commit.
dirty=$(cd "$REPO" && git status --porcelain | awk '{print $2}' \
        | grep -vxF "$(printf '%s\n' "${FILES[@]}")" || true)
if [[ -n "$dirty" ]]; then
    echo "error: uncommitted changes in $REPO:" >&2
    echo "$dirty" | sed 's/^/  /' >&2
    die "commit or stash them first"
fi

# Never fall back to an interactive password prompt: fail instead.
git_auth() {
    GIT_TERMINAL_PROMPT=0 git -C "$REPO" "$@"
}

# ------------------------------------------------------- update before push

say "fetching $BRANCH from Overleaf"
git_auth fetch origin "$BRANCH"

behind=$(git -C "$REPO" rev-list --count "HEAD..origin/$BRANCH")
ahead=$(git -C "$REPO" rev-list --count "origin/$BRANCH..HEAD")
say "local is $ahead ahead, $behind behind origin/$BRANCH"

if [[ "$behind" -gt 0 ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
        say "dry run: would merge origin/$BRANCH ($behind commit(s))"
    else
        say "merging origin/$BRANCH"
        # pull.rebase is forced here so the script does not depend on local config
        if ! git_auth -c pull.rebase=false merge --no-edit "origin/$BRANCH"; then
            git -C "$REPO" merge --abort 2>/dev/null || true
            die "merge conflict with Overleaf. Resolve it by hand in $REPO, then rerun."
        fi
    fi
fi

# -------------------------------------------------------------------- copy

changed=0
for f in "${FILES[@]}"; do
    if ! cmp -s "$SRC_DIR/$f" "$REPO/$f"; then
        say "updating $f"
        [[ "$DRY_RUN" -eq 1 ]] || cp "$SRC_DIR/$f" "$REPO/$f"
        changed=1
    else
        say "$f unchanged"
    fi
done

if [[ "$changed" -eq 0 && "$ahead" -eq 0 ]]; then
    say "nothing to do"
    exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    say "dry run: stopping before commit and push"
    exit 0
fi

# --------------------------------------------------------- commit and push

if [[ "$changed" -eq 1 ]]; then
    git -C "$REPO" add -- "${FILES[@]}"
    if git -C "$REPO" diff --cached --quiet; then
        say "no staged change after copy"
    else
        say "committing"
        git -C "$REPO" commit -m "$COMMIT_MSG"
    fi
fi

say "pushing to Overleaf"
git_auth push origin "$BRANCH"
say "done"
