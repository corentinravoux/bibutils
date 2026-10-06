#!/usr/bin/env bash
# Superseded by bibutils (~/Documents/Python/Packages/bibutils): this now runs
#   bib-hdr [--push] [--no-export] [--no-<step> ...]
# so there is one pipeline and one citation-key registry
# (~/Documents/Biblio/bibli_hdr.citekeys.json). The previous script is kept in
# Sauvegardes/bib_update.legacy.sh.
args=()
for a in "$@"; do [[ "$a" == "--quiet" ]] || args+=("$a"); done
exec bib-hdr ${args[@]+"${args[@]}"}
