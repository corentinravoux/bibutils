#!/usr/bin/env bash
#
# Zotero -> bibli_hdr_*.bib -> Overleaf, in one command, with no GUI step.
#
#   zotero_to_bib.py    reads zotero.sqlite and writes one .bib per collection
#   create_bib_hdr.py   merges them into the three out/bibli_hdr_*.bib
#   push_bib_to_overleaf.sh   copies those into the Overleaf clone and pushes
#
# Safe to run while Zotero is open: the database is copied before being read.
# Safe to run from cron for the same reason.
#
# Usage:
#   ./bib_update.sh                 # export + build
#   ./bib_update.sh --push          # export + build + push to Overleaf
#   ./bib_update.sh --no-export     # rebuild from the .bib already on disk
#   ./bib_update.sh --quiet         # counts only, no per-entry list
#
# Every cleaning step is on by default and can be switched off:
#   export (zotero_to_bib.py):  --no-escape --no-protect-caps --no-keep-latex
#                               --no-fix-allcaps --no-eprint --no-arxiv-journal
#   build (create_bib_hdr.py):  --no-legacy-greek --no-collaboration
#                               --no-drop-fields --no-repeated-keys
#                               --no-repeated-fields --no-latexify
#                               --no-math-cleanup --no-ascii-names
#   e.g.  ./bib_update.sh --no-fix-allcaps --no-math-cleanup
#
# Author: Corentin Ravoux

set -euo pipefail

# All scripts live next to this one; only the .bib files live below.
BIBLIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIBDIR="$BIBLIO/bib_files"
EXPORT="$BIBLIO/zotero_to_bib.py"
BUILD="$BIBLIO/create_bib_hdr.py"
PUSH="$BIBLIO/push_bib_to_overleaf.sh"

PUSH_AFTER=0; DO_EXPORT=1; QUIET=0
EXPORT_OPTS=(); BUILD_OPTS=()
for a in "$@"; do
    case "$a" in
        --push)       PUSH_AFTER=1 ;;
        --no-export)  DO_EXPORT=0 ;;
        --quiet)      QUIET=1 ;;
        --no-escape|--no-protect-caps|--no-keep-latex|--no-fix-allcaps|--no-eprint|--no-arxiv-journal)
                      EXPORT_OPTS+=("$a") ;;
        --no-legacy-greek|--no-collaboration|--no-drop-fields|--no-repeated-keys|\
        --no-repeated-fields|--no-latexify|--no-math-cleanup|--no-ascii-names)
                      BUILD_OPTS+=("$a") ;;
        -h|--help)    sed -n '3,28p' "$0"; exit 0 ;;
        *) echo "unknown option: $a" >&2; exit 2 ;;
    esac
done

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }

# ------------------------------------------------------------------ export
if [[ "$DO_EXPORT" -eq 1 ]]; then
    say "exporting Zotero"
    python3 "$EXPORT" -o "$BIBDIR" ${EXPORT_OPTS[@]+"${EXPORT_OPTS[@]}"} > /tmp/bib_export.log 2>&1 \
        || { cat /tmp/bib_export.log >&2; exit 1; }
    # summary, plus the titles rewritten from all capitals (worth fixing in Zotero)
    sed -n '/all-capitals title/,$p' /tmp/bib_export.log | sed 's/^/    /'
    grep -qF 'all-capitals title' /tmp/bib_export.log || tail -3 /tmp/bib_export.log
fi

# ------------------------------------------------------------------- build
say "building"
python3 "$BUILD" ${BUILD_OPTS[@]+"${BUILD_OPTS[@]}"} > /tmp/bib_build.log 2>&1 || { cat /tmp/bib_build.log >&2; exit 1; }
grep -E 'bibli_hdr_[0-9]\.bib:|entries written' /tmp/bib_build.log | sed 's/^/    /'

# Duplicates and entries with missing BibTeX fields, in full. These are the
# two things worth acting on in Zotero; everything else the build fixes by
# itself. --quiet keeps the counts and sends the lists to the log only.
if grep -qE '^[0-9]+ .*:$' /tmp/bib_build.log; then
    echo
    say "library problems to fix in Zotero"
    if [[ "$QUIET" -eq 1 ]]; then
        grep -E '^[0-9]+ .*:$' /tmp/bib_build.log | sed 's/^/    /'
        echo "    lists in /tmp/bib_build.log"
    else
        sed -n '/^[0-9]* .*:$/,$p' /tmp/bib_build.log | sed 's/^/    /'
    fi
fi

# -------------------------------------------------------------------- push
if [[ "$PUSH_AFTER" -eq 1 ]]; then
    echo; say "pushing to Overleaf"; "$PUSH"
else
    echo; say "not pushed -- rerun with --push"
fi
