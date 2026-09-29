# bibutils

Zotero → BibTeX → Overleaf, in one command:

```bash
bibutils run <profile> --push      # export Zotero, build the .bib, push it to Overleaf
```

Checks are optional (`--verify`, `bibutils verify`), never in the way.

- **export**: reads `zotero.sqlite` directly (no GUI, no plugin), one `.bib` per
  collection, citation keys identical to Zotero's own BibTeX export.
- **build**: merges them into the bibliography of a project, with optional
  cleaning steps (below).
- **verify** (optional): compares every field of every entry with Zotero, and
  can check every arXiv id and DOI online (does the link exist, and does it
  point to *this* paper?).
- **push**: publishes to an Overleaf git clone (fetch, merge, commit, push).
- **publist**: compares a LaTeX publication list with an INSPIRE-HEP author record.

Pure standard library (Python ≥ 3.9; `tomli` below 3.11).

## Install

```bash
uv tool install --editable .      # puts `bibutils` and `bib-hdr` on PATH
# or: pip install -e .
```

## Configure

Copy `config.example.toml` to `~/.config/bibutils/config.toml` and add one
`[profile.<name>]` per project. A new Overleaf project is a new profile, not
new code:

```bash
bibutils run <name>            # export + build + integrity check
bibutils run <name> --push     # ... and publish to the Overleaf clone
bib-hdr --push                 # shortcut for the "hdr" profile
```

Overleaf authentication uses git's credential helper, scoped to Overleaf; no
token is ever read or stored by bibutils:

```bash
git config --global credential.https://git.overleaf.com.helper \
    "store --file ~/.config/git/credentials-overleaf"   # file mode 600
```

## Citation keys: add, replace, edit — citations keep working

`bibutils run` keeps a key registry (`keys_file` in the profile), one entry per
Zotero item, so keys are unique across the whole library and never move:

- a new entry gets the Zotero-pattern key, or the first free `-1`, `-2`, … if
  that key is, or ever was, used by another paper — it is never dropped;
- a re-imported paper (same DOI or arXiv id) replacing a record you removed
  inherits the old key, so `\cite{...}` keeps working;
- editing an item's date or title does not rename its key;
- a key pinned in Zotero (Citation Key field) always wins.
- when you merge duplicates, the key of the record that disappears is dropped
  (no alias is written); the run lists it with the key to cite instead.

Each run lists the keys given to new entries. To start a registry
from an existing setup without moving any key:

```bash
bibutils keys-seed REGISTRY zotero.sqlite --status active      # today's keys
bibutils keys-seed REGISTRY old-backup.sqlite --status retired # optional history
```

## Cleaning steps

All on by default; each can be switched off with `--no-<step>` (on `run`,
`export` or `build`) or listed in the profile's `disable`.

| step | where | what it does |
|---|---|---|
| `escape` | export | Zotero's special-character escaping (`&`, `%`, `_`, …) |
| `protect-caps` | export | brace capitalised words so the style keeps them |
| `keep-latex` | export | titles typed as LaTeX in Zotero (`$z_{\rm eff}$`, `$\Lambda$CDM`, `\textit{Planck}`) stay LaTeX instead of being escaped to literal text |
| `fix-allcaps` | export | titles stored in capitals → title case, keeping acronyms learned from the library |
| `eprint` | export | `eprint`/`archivePrefix` from the item's own arXiv id (only when all its sources agree) |
| `arxiv-journal` | export | drop a journal field that is only that same arXiv id |
| `legacy-greek` | build | `$\alpha$` → `\ensuremath{\alpha}` in older exports |
| `collaboration` | build | `collaboration` field for `*_collaboration` keys |
| `drop-fields` | build | remove fields no style uses (file paths, abstracts, …) |
| `repeated-keys` / `repeated-fields` | build | keep the first copy (BibTeX errors otherwise) |
| `latexify` | build | Unicode pdflatex cannot typeset → LaTeX |
| `math-cleanup` | build | `\ensuremath{X}` inside `$…$` → `X` |
| `ascii-names` | build | accented author letters → LaTeX accents (BibTeX initials) |

## Verification (optional)

```bash
bibutils run <profile> --verify [--push]                  # + the two checks below;
                                                          #   a failure blocks the push
bibutils verify out/bibli_hdr_0.bib                       # offline, against Zotero
bibutils verify out/bibli_hdr_0.bib --online --cache ~/.cache/bibutils \
                --cited path/to/latex/project             # + every link, cited flagged
```

The offline check compares authors, title, journal, volume, number, pages,
year, DOI, URL, publisher, … after normalising away LaTeX, accents, case and
punctuation, plus a strict pass on numbers and relation signs (`z=2.3` must
not become `z=23`). `run --verify` also lists the keys the LaTeX project
cites that the bibliography lacks. Set `verify = true` in a profile to make
it the default for that project.

The online check reports links that do not resolve, links that resolve to a
different paper (title/author/year, errata, book reviews), entries with no
link at all, and preprints that arXiv lists as published.

## Tests

```bash
uvx --with-editable . pytest -q
```
