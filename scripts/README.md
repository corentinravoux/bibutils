# scripts

Scripts that preceded the package or run outside it. They were moved here from
`~/Documents/Biblio` on 2026-10-06, so that directory holds only the library
data: the per-collection exports, the built bibliography, the citation-key
registry and Zotero backups.

## zotero/ — run inside Zotero

Paste into Zotero: *Tools > Developer > Run JavaScript*, tick *Run as async
function*. Each script starts in dry-run mode and prints what it would change.

| script | what |
|---|---|
| `zotero_reorganise.js` | one-off reorganisation of the library into the `Probes/`, `Surveys/`, `Methods/`… collection tree (2026-08-04) |
| `zotero_cleanup.js` | follow-up: file stray items, trash unfiled duplicates, delete the empty legacy collections |
| `zotero_export_bib.js` | whole-library BibTeX export through Zotero's translator; replaced by `bibutils export`, which reads `zotero.sqlite` directly |
| `zotero_fix_collaborations.js` | rejoin collaboration names that Zotero split like a person's name; generated for this library on 2026-09-30, not a general tool |

## legacy/ — the pipeline before bibutils

Superseded by `bibutils` (`bib-hdr`, `bibutils run <profile>`), whose output is
byte-identical. They are kept for reference only, and they still hard-code
paths under `~/Documents/Biblio`, so they will not run from here.

| script | replaced by |
|---|---|
| `zotero_to_bib.py` | `bibutils.zotero` / `bibutils export` |
| `create_bib_hdr.py` | `bibutils.build` / `bibutils build` |
| `push_bib_to_overleaf.sh` | `bibutils.overleaf` / `bibutils push` |
| `bib_update.legacy.sh` | `bibutils run hdr` |
| `bib_update.sh` | the shim that forwarded to `bib-hdr`: call `bib-hdr` directly |
