#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge per-collection Zotero exports into the bibliography of one project.

Author: Corentin Ravoux

Description:
    Merge the per-topic Zotero exports of a directory into the
    <prefix>_*.bib files used by a LaTeX project (bibli_hdr_*.bib for the
    HDR manuscript).

    In addition to the math-notation fixes and the automatic
    "collaboration" field, entries are trimmed of the fields that Zotero
    exports but that no bibliography style uses. This removes the local
    absolute paths of the "file" fields (which otherwise leak the local
    directory tree into the manuscript repository) and divides the size
    of the output by roughly three.

    Duplicate entries are reported but never merged, since the citation
    keys are already in use in the manuscript.

    Every cleaning step is optional:
        bibutils build SOURCE_DIR OUT_DIR [--prefix P] [--no-<step> ...]
    with <step> one of the keys of CLEANING below (--help lists them).
"""

########################## MODULE IMPORTATION ###############################


import argparse
import glob
import os
import sys
import tempfile
import re
import unicodedata

################################ OPTIONS ####################################

# Cleaning steps, all on by default; each is switched off with --no-<step>.
CLEANING = {
    "legacy-greek": "rewrite $\\alpha$, $\\Lambda$, $\\Omega$ (escaped or not) "
                    "as \\ensuremath{...}",
    "collaboration": "add a collaboration field to *_collaboration entries",
    "drop-fields": "remove the fields listed in DROP_FIELDS",
    "repeated-keys": "keep only the first entry of a key exported twice",
    "repeated-fields": "keep only the first copy of a field repeated in an entry",
    "latexify": "rewrite characters pdflatex cannot typeset (UNICODE_MAP)",
    "math-cleanup": "inside $...$, turn \\ensuremath{X} into X",
    "ascii-names": "rewrite accented letters of author/editor as LaTeX accents",
}

# Fields removed from every entry. Everything here is either unused by the
# bibliography style, or local to the machine that produced the export.
DROP_FIELDS = {
    "file",  # absolute paths to the local Zotero storage
    "abstract",
    "urldate",
    "keywords",
    "annote",
    "shorttitle",
    "copyright",
    "langid",
    "pmid",
    "pmcid",
}

# Entries sharing one of these fields are reported as possible duplicates.
DUPLICATE_KEYS = ("doi", "eprint")

# Characters that pdflatex cannot typeset with inputenc/utf8 + fontenc/T1.
#
#   - Greek letters raise "Unicode character ... not set up for use with LaTeX".
#   - Everything in the Mathematical Alphanumeric Symbols block (U+1D400 and
#     above) is encoded on four bytes, which inputenc's utf8 option cannot
#     decode at all: that is the "Invalid UTF-8 byte sequence" error.
#   - The f-ligatures and the private-use characters come from text extracted
#     out of PDFs.
#
# Accented Latin letters are deliberately absent: T1 handles them, and
# rewriting them would only make the entries harder to read.
UNICODE_MAP = {
    # Greek, lower case
    "α": r"\ensuremath{\alpha}", "β": r"\ensuremath{\beta}",
    "γ": r"\ensuremath{\gamma}", "δ": r"\ensuremath{\delta}",
    "η": r"\ensuremath{\eta}", "θ": r"\ensuremath{\theta}",
    "μ": r"\ensuremath{\mu}", "ν": r"\ensuremath{\nu}",
    "ξ": r"\ensuremath{\xi}", "π": r"\ensuremath{\pi}",
    "σ": r"\ensuremath{\sigma}", "τ": r"\ensuremath{\tau}",
    "χ": r"\ensuremath{\chi}",
    # Greek, upper case
    "Γ": r"\ensuremath{\Gamma}", "Δ": r"\ensuremath{\Delta}",
    "Λ": r"\ensuremath{\Lambda}", "Ξ": r"\ensuremath{\Xi}",
    "Σ": r"\ensuremath{\Sigma}", "Ω": r"\ensuremath{\Omega}",
    # Mathematical Alphanumeric Symbols, four bytes, always fatal
    "\U0001d6fc": r"\ensuremath{\alpha}", "\U0001d70e": r"\ensuremath{\sigma}",
    "\U0001d44e": r"\ensuremath{a}", "\U0001d44f": r"\ensuremath{b}",
    "\U0001d458": r"\ensuremath{k}", "\U0001d45a": r"\ensuremath{m}",
    "\U0001d460": r"\ensuremath{s}", "\U0001d464": r"\ensuremath{w}",
    "\U0001d467": r"\ensuremath{z}",
    # Mathematical operators and relations
    "−": r"\ensuremath{-}", "∼": r"\ensuremath{\sim}",
    "±": r"\ensuremath{\pm}", "≤": r"\ensuremath{\leq}",
    "×": r"\ensuremath{\times}", "≈": r"\ensuremath{\approx}",
    "≳": r"\ensuremath{\gtrsim}", "≲": r"\ensuremath{\lesssim}",
    "⊙": r"\ensuremath{\odot}", "≃": r"\ensuremath{\simeq}",
    "∈": r"\ensuremath{\in}", "≥": r"\ensuremath{\geq}",
    "∗": r"\ensuremath{*}", "≡": r"\ensuremath{\equiv}",
    "⩽": r"\ensuremath{\leq}", "⩾": r"\ensuremath{\geq}",
    "∑": r"\ensuremath{\sum}", "≺": r"\ensuremath{\prec}",
    "≾": r"\ensuremath{\prec}", "★": r"\ensuremath{\star}",
    "↔": r"\ensuremath{\leftrightarrow}", "◦": r"\ensuremath{\circ}",
    "⟨": r"\ensuremath{\langle}", "⟩": r"\ensuremath{\rangle}",
    "⊥": r"\ensuremath{\perp}", "∆": r"\ensuremath{\Delta}",
    "°": r"\ensuremath{^\circ}", "′": r"\ensuremath{'}",
    "¾": r"\ensuremath{3/4}",
    # Super- and subscripts
    "¹": r"\ensuremath{^1}", "²": r"\ensuremath{^2}",
    "³": r"\ensuremath{^3}", "⁻": r"\ensuremath{^-}",
    "₈": r"\ensuremath{_8}",
    # f-ligatures, from text extracted out of PDFs
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl",
    # Spaces, dashes and quotation marks
    " ": " ", " ": " ", "‑": "-",
    "–": "--", "—": "---",
    "‘": "`", "’": "'", "“": "``", "”": "''",
    "»": r"\guillemotright{}", "´": "'", "©": r"\copyright{}",
    # Corruption: removed, and reported entry by entry
    "": "", "℡": "", "舁": "", "̄": "", "⁢": "",
}

# Removed rather than translated: these are extraction artefacts with no
# meaning, so their entries are listed in the report for a manual check.
SUSPICIOUS = {"", "℡", "舁", "̄", "⁢"}

# Left untouched: T1 covers Latin-1 Supplement and Latin Extended-A/B.
SAFE_RANGES = ((0x00C0, 0x024F), (0x1E00, 0x1EFF))

# url and doi are not translated: a \ensuremath inside a link breaks it.
NO_TRANSLATION_FIELDS = {"url", "doi"}

# Fields BibTeX requires per entry type. Entries missing one of them produce a
# "Warning--empty <field>" at compilation. They are reported, never invented:
# the fix belongs in Zotero.
REQUIRED_FIELDS = {
    "article": ("author", "title", "journal", "year"),
    "book": ("title", "publisher", "year"),
    "inbook": ("title", "publisher", "year"),
    "incollection": ("author", "title", "booktitle", "publisher", "year"),
    "inproceedings": ("author", "title", "booktitle", "year"),
    "conference": ("author", "title", "booktitle", "year"),
    "techreport": ("author", "title", "institution", "year"),
    "phdthesis": ("author", "title", "school", "year"),
    "mastersthesis": ("author", "title", "school", "year"),
    "unpublished": ("author", "title", "note"),
}

################################# FILE ######################################

# Number of bibli_hdr_*.bib files written into out/. This is FIXED, not
# derived from the number of topic exports: the manuscript hard-codes
#     \bibliography{bibli_hdr_0,bibli_hdr_1,bibli_hdr_2}
# in every chapter, so a chunk count that drifted with the size of the Zotero
# library would either leave a file uncited (citations silently rendered as
# "?") or point at a file that does not exist.
#
# The topic files are spread as evenly as possible over the N_CHUNKS outputs,
# so all three stay roughly the same size whatever the collection count is.
N_CHUNKS = 1

# Single whole-library export produced by zotero_export_bib.js. When it is
# present it is the only source: one Zotero translator call instead of one per
# collection, and the build no longer depends on how the collections are
# arranged. The per-collection exports are still accepted as a fallback.
LIBRARY_EXPORT = "zotero_library.bib"

# Cleaning steps in force; build() sets them for one run.
DO = {step: True for step in CLEANING}


def label(key, source, title="", extra=""):
    """One aligned report line: key, where it comes from, what is wrong."""
    short = re.sub(r"[{}]", "", title).strip()
    if len(short) > 58:
        short = short[:55] + "..."
    where = source if len(source) <= 30 else source[:27] + "..."
    line = f"{key:<34} {where:<30} {extra}"
    return line + (f'\n{" " * 4}"{short}"' if short else "")


def split_chunks(seq, n):
    """Split seq into exactly n groups of near-equal length."""
    q, r = divmod(len(seq), n)
    out, start = [], 0
    for i in range(n):
        stop = start + q + (1 if i < r else 0)
        out.append(seq[start:stop])
        start = stop
    return out


def library_sources(path, n):
    """Cut the whole-library export into n pieces, on entry boundaries.

    Returns [(label, path)], the pieces written to a temporary directory so
    that no intermediate file is left next to the real exports.
    """
    text = open(path, "r", encoding="utf-8").read()
    entries = [e for e in re.split(r"\n(?=@)", text) if e.strip()]
    tmp = tempfile.mkdtemp(prefix="bibli_hdr_")
    out = []
    for i, group in enumerate(split_chunks(entries, n)):
        part = os.path.join(tmp, f"part{i}.bib")
        with open(part, "w", encoding="utf-8") as fh:
            fh.write("\n".join(group) + "\n")
        out.append((f"Zotero library, part {i + 1}/{n} ({len(group)} entries)", part))
    return out


def collection_sources(source_dir, n):
    """Fallback: the per-collection .bib exports, grouped into n chunks."""
    paths = sorted(p for p in glob.glob(os.path.join(source_dir, "*.bib"))
                   if os.path.basename(p) != LIBRARY_EXPORT)
    names = [(os.path.basename(p)[:-4], p) for p in paths]
    return split_chunks(names, n)


############################ TRIMMING HELPERS ###############################


def split_entries(text):
    """Split a bib file into (before, header, body, raw) chunks.

    An entry is returned as its "@type{" header, the content between the
    outermost braces, and the raw text. Anything that is not an entry is
    returned unchanged so that comments and blank lines survive.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            out.append((text[i:], None, None, None))
            break
        brace = text.find("{", at)
        if brace == -1:
            out.append((text[i:], None, None, None))
            break
        depth, j = 0, brace
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:  # unbalanced braces, keep the rest verbatim
            out.append((text[i:], None, None, None))
            break
        out.append((text[i:at], text[at:brace + 1], text[brace + 1:j], text[at:j + 1]))
        i = j + 1
    return out


def split_fields(body):
    """Split an entry body into its citation key and [(name, value), ...]."""
    comma = body.find(",")
    if comma == -1:
        return body.strip(), []
    key = body[:comma].strip()
    rest = body[comma + 1:]
    fields, i, n = [], 0, len(rest)
    field_start = re.compile(r"\s*([A-Za-z][A-Za-z0-9_+:-]*)\s*=\s*")
    while i < n:
        m = field_start.match(rest, i)
        if m is None:
            break
        name, i = m.group(1), m.end()
        if i < n and rest[i] == "{":  # brace-delimited value, possibly nested
            depth, j = 0, i
            while j < n:
                if rest[j] == "{":
                    depth += 1
                elif rest[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            value, i = rest[i:j + 1], j + 1
        elif i < n and rest[i] == '"':  # quote-delimited value
            j = rest.find('"', i + 1)
            value, i = rest[i:j + 1], j + 1
        else:  # bare value, ends at the next comma or newline
            j = i
            while j < n and rest[j] not in ",\n":
                j += 1
            value, i = rest[i:j].strip(), j
        while i < n and rest[i] in " \t\r\n,":
            i += 1
        fields.append((name, value))
    return key, fields


def is_safe_character(char):
    """True if pdflatex can typeset the character with inputenc/utf8 + T1."""
    code = ord(char)
    if code < 128:
        return True
    return any(low <= code <= high for low, high in SAFE_RANGES)


def latexify(value, key, field, state):
    """Replace the characters pdflatex cannot typeset by their LaTeX form."""
    if field.lower() in NO_TRANSLATION_FIELDS:
        for char in value:
            if not is_safe_character(char):
                state["unmapped"].add(
                    f"U+{ord(char):04X} {char!r} in {key} ({field}, left as is)"
                )
        return value
    out = []
    for char in value:
        if char in UNICODE_MAP:
            if char in SUSPICIOUS:
                state["suspicious"].append(f"{key}: removed U+{ord(char):04X}")
            out.append(UNICODE_MAP[char])
            state["converted"] += 1
        elif is_safe_character(char):
            out.append(char)
        else:
            # Unknown and unsafe: kept so that nothing is silently lost, and
            # reported so that it can be added to UNICODE_MAP.
            state["unmapped"].add(f"U+{ord(char):04X} {char!r} in {key} ({field})")
            out.append(char)
    return "".join(out)


_MATH_RE = re.compile(r"(?<!\\)\$(.*?)(?<!\\)\$", re.S)
_ENSUREMATH_RE = re.compile(r"\\ensuremath\{((?:[^{}]|\{[^{}]*\})*)\}")


def math_cleanup(value):
    """Inside $...$, \\ensuremath{X} is just X: drop the wrapper.

    latexify writes "\\ensuremath{\\alpha}" for a Unicode alpha, which is right
    in text but noise inside math such as "Ly$\u03b1$".
    """
    if "$" not in value or "ensuremath" not in value:
        return value
    return _MATH_RE.sub(
        lambda m: "$" + _ENSUREMATH_RE.sub(r"\1", m.group(1)) + "$", value)


def normalise_title(title):
    """Comparable form of a title, for duplicate detection."""
    title = re.sub(r"[{}\\$]", "", title or "").lower()
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", title)


def trim_entries(text, source, state):
    """Rewrite every entry of one topic file.

    Removes DROP_FIELDS, drops repeated citation keys and repeated fields
    (both are BibTeX errors or warnings), and records duplicate candidates
    and missing required fields.

    "state" is accumulated across all output files so that a key exported
    into two topic files is still caught.
    """
    out, n_entries, n_dropped = [], 0, 0
    for before, header, body, raw in split_entries(text):
        if header is None:
            out.append(before)
            continue
        out.append(before)
        entry_type = header[1:-1].strip().lower()
        if entry_type in {"comment", "preamble", "string"}:
            out.append(raw)
            continue
        key, fields = split_fields(body)

        # A key exported into two topic files is a "Repeated entry" error and
        # BibTeX keeps only one of them. Keep the first and skip the rest.
        if DO["repeated-keys"] and key in state["keys"]:
            first_source, first_n = state["keys"][key]
            # the same item filed in two collections: identical entry, not a clash
            if state["contents"].get(key) == fields:
                state["same_item"] = state.get("same_item", 0) + 1
                continue
            note = f"{key}: kept from {first_source}, skipped in {source}"
            if first_n != len(fields):
                note += f" (differing content: {first_n} vs {len(fields)} fields)"
            state["repeated_keys"].append(note)
            continue
        state["keys"][key] = (source, len(fields))
        state["contents"][key] = fields

        n_entries += 1
        kept, seen_names = [], set()
        for name, value in fields:
            lname = name.lower()
            if DO["drop-fields"] and lname in DROP_FIELDS:
                n_dropped += 1
                continue
            # A field repeated inside one entry makes BibTeX ignore the extra
            # one; drop it here so the warning never reaches the log.
            if DO["repeated-fields"] and lname in seen_names:
                state["repeated_fields"].append(
                    label(key, source, extra=f'second "{lname}" field removed'))
                continue
            seen_names.add(lname)
            if DO["latexify"]:
                value = latexify(value, key, lname, state)
            if DO["math-cleanup"]:
                value = math_cleanup(value)
            if DO["ascii-names"] and lname in NAME_FIELDS:
                value = asciify_name(value)
            kept.append((name, value))

        flat = {name.lower(): value.strip('{}" ') for name, value in kept}
        title = flat.get("title", "")

        missing = [
            field for field in REQUIRED_FIELDS.get(entry_type, ())
            if field not in seen_names
            # an arXiv-only article has its reference in eprint, not journal
            and not (field == "journal" and "eprint" in seen_names)
        ]
        if missing:
            state["missing_fields"].append(
                label(key, source, title,
                      f"@{entry_type}, missing {', '.join(missing)}")
            )

        seen, duplicates = state["fingerprints"], state["duplicates"]
        pairs = state.setdefault("dup_pairs", set())
        ids = state.setdefault("ids", {})
        ids[key] = {f: flat.get(f, "").lower() for f in DUPLICATE_KEYS}
        for field in DUPLICATE_KEYS:
            value = flat.get(field, "").lower()
            if len(value) > 3:
                if seen.setdefault((field, value), key) != key:
                    first = seen[(field, value)]
                    if frozenset((first, key)) not in pairs:
                        pairs.add(frozenset((first, key)))
                        duplicates.add(
                            label(key, source, title,
                                  f"same {field} as {first}  ({value})")
                        )
        norm = normalise_title(title)
        if len(norm) > 3:
            first = seen.setdefault(("title", norm), key)
            # two papers may share a title (a code paper and its software
            # release): not duplicates when their DOI or arXiv id differ
            differ = first != key and any(
                ids[first][f] and ids[key][f] and ids[first][f] != ids[key][f]
                for f in DUPLICATE_KEYS)
            # Reported once per pair: a duplicate usually shares doi AND title,
            # and listing it twice only makes the report longer to read.
            if first != key and not differ and frozenset((first, key)) not in pairs:
                pairs.add(frozenset((first, key)))
                duplicates.add(
                    label(key, source, title, f"same title as {first}")
                )

        lines = [f"@{entry_type}{{{key},"]
        for name, value in kept:
            lines.append(f"\t{name} = {value},")
        if len(lines) > 1:
            lines[-1] = lines[-1].rstrip(",")
        lines.append("}")
        out.append("\n".join(lines))
    return "".join(out), n_entries, n_dropped


#############################################################################


def create_bib_file(file_out_name, list_sub, state):

    os.makedirs(os.path.dirname(file_out_name), exist_ok=True)
    file_out = open(file_out_name, "w", encoding="utf-8")
    total_entries, total_dropped = 0, 0

    for i in range(len(list_sub)):
        list_index_collab, list_collab = [], []
        label, source_path = list_sub[i]
        file_in = open(source_path, "r", encoding="utf-8")
        f = file_in.readlines()
        for j in range(len(f)):
            if not DO["legacy-greek"]:
                break
            f[j] = f[j].replace("$\\alpha$", "\\ensuremath{\\alpha}")
            f[j] = f[j].replace("$\\Lambda$", "\\ensuremath{\\Lambda}")
            f[j] = f[j].replace("$\\Omega$", "\\ensuremath{\\Omega}")
            f[j] = f[j].replace("\\${\\textbackslash}alpha\\$", "\\ensuremath{\\alpha}")
            f[j] = f[j].replace(
                "\\${\\textbackslash}Lambda\\$", "\\ensuremath{\\Lambda}"
            )
            f[j] = f[j].replace("\\${\\textbackslash}Omega\\$", "\\ensuremath{\\Omega}")
            f[j] = f[j].replace(
                "\\${\\textbackslash}{alpha}\\$", "\\ensuremath{\\alpha}"
            )
            f[j] = f[j].replace(
                "\\${\\textbackslash}{Lambda}\\$", "\\ensuremath{\\Lambda}"
            )
            f[j] = f[j].replace(
                "\\${\\textbackslash}{Omega}\\$", "\\ensuremath{\\Omega}"
            )
        for j in range(len(f)):
            if not DO["collaboration"]:
                break
            if ("_collaboration" in f[j]) & ("@article{" in f[j]):
                list_index_collab.append(j)
                list_collab.append(
                    f[j]
                    .split("@article{")[-1]
                    .split("_collaboration")[0]
                    .replace("_", " ")
                )
        if len(list_index_collab) != 0:
            for j in range(len(list_index_collab[::-1])):

                f = (
                    f[: list_index_collab[::-1][j] + 1]
                    + ["	collaboration = {" + list_collab[::-1][j] + "},\n"]
                    + f[list_index_collab[::-1][j] + 1 :]
                )
        file_in.close()

        # Remove the unused Zotero fields. Done after the substitutions above
        # so that the line indices used for the collaboration field stay valid.
        content, n_entries, n_dropped = trim_entries(
            "".join(f), label, state
        )
        total_entries += n_entries
        total_dropped += n_dropped

        file_out.write("#######################################\n")
        file_out.write("#######################################\n")
        file_out.write(f"##############  {label}  ##############" + "\n")
        file_out.write("#######################################\n")
        file_out.write("#######################################\n")
        file_out.write("\n")
        file_out.write(content)
        file_out.write("\n")
        file_out.write("\n")
        file_out.write("\n")
    file_out.close()

    size = os.path.getsize(file_out_name) / 1024
    print(
        f"  {os.path.basename(file_out_name)}: {total_entries} entries, "
        f"{total_dropped} fields dropped, {size:.0f} KB"
    )
    return total_entries, total_dropped


# BibTeX abbreviates first names to initials by taking the first *byte* of the
# name. For a name beginning with a non-ASCII letter that byte is half of a
# UTF-8 sequence, and the .bbl it writes is no longer valid UTF-8 -- which is
# where "LaTeX Error: Invalid UTF-8 byte sequence" in the compiled document
# comes from. E.Aubourg, J.Guy and five others were being cut in half.
#
# The cure is to keep author and editor fields pure ASCII: every accented
# letter becomes a braced LaTeX accent, which BibTeX counts as one character.
# Titles are left alone -- they are never abbreviated, and stay readable.
COMBINING_TEX = {
    "̀": "`", "́": "'", "̂": "^", "̃": "~",
    "̄": "=", "̆": "u", "̇": ".", "̈": '"',
    "̊": "r", "̋": "H", "̌": "v", "̧": "c",
    "̨": "k", "̣": "d", "̱": "b",
}
STANDALONE_TEX = {
    "ø": r"\o", "Ø": r"\O", "ß": r"\ss", "æ": r"\ae", "Æ": r"\AE",
    "œ": r"\oe", "Œ": r"\OE", "å": r"\aa", "Å": r"\AA",
    "ł": r"\l", "Ł": r"\L", "đ": r"\dj", "Đ": r"\DJ",
    "ı": r"\i", "İ": r"\.I", "þ": r"\th", "Þ": r"\TH",
    "ð": r"\dh", "Ð": r"\DH", "'": "'", "-": "-",
}
NAME_FIELDS = {"author", "editor"}


def asciify_name(value):
    """Rewrite a name field so that it contains no byte above 127."""
    out = []
    for ch in value:
        if ord(ch) < 128:
            out.append(ch)
            continue
        if ch in STANDALONE_TEX:
            out.append("{%s}" % STANDALONE_TEX[ch])
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        base = decomposed[0]
        marks = [COMBINING_TEX.get(c) for c in decomposed[1:]]
        if ord(base) < 128 and marks and all(marks):
            for mark in marks:
                base = "\\%s{%s}" % (mark, base)
            out.append("{%s}" % base)
        else:
            # Unknown: drop the accent rather than emit a broken initial.
            stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
            out.append(stripped if stripped.isascii() else "?")
    return "".join(out)


def report(title, items, comment=""):
    """Print one warning group in full, sorted by citation key."""
    if not items:
        return
    print(f"\n{len(items)} {title}{comment}:")
    for item in sorted(items):
        print(f"  {item}")


def build(source_dir, out_dir, prefix="bibli_hdr", n_chunks=N_CHUNKS, disable=()):
    """Write <out_dir>/<prefix>_<i>.bib from the Zotero exports in source_dir.

    disable: names of CLEANING steps to skip. Returns the run state (counts
    and every reported problem), which the caller may inspect.
    """
    unknown = set(disable) - set(CLEANING)
    if unknown:
        raise ValueError(f"unknown cleaning step(s): {', '.join(sorted(unknown))}")
    for step in CLEANING:
        DO[step] = step not in disable

    _library = os.path.join(source_dir, LIBRARY_EXPORT)
    if os.path.exists(_library):
        SOURCES = [[s] for s in library_sources(_library, n_chunks)]
        ORIGIN = f"whole-library export {_library}"
    else:
        SOURCES = collection_sources(source_dir, n_chunks)
        ORIGIN = (f"{sum(len(c) for c in SOURCES)} per-collection exports in "
                  f"{source_dir}/")

    # Abort rather than truncate: writing empty <prefix>_*.bib files over
    # good ones would break every citation in the manuscript, and the failure
    # would only show up at the next compilation.
    if not any(SOURCES):
        sys.exit(
            f"error: no Zotero export found in {os.path.abspath(source_dir)}\n"
            f"       expected {LIBRARY_EXPORT} (whole-library export) or per-collection\n"
            f"       *.bib files. {prefix}_*.bib left untouched."
        )

    print(f"source: {ORIGIN} -> {n_chunks} bibliography files")
    _off = [step for step, on in DO.items() if not on]
    if _off:
        print("cleaning steps switched off: " + ", ".join(_off))
    for i, group in enumerate(SOURCES):
        print(f"  {prefix}_{i}.bib  <- " + ", ".join(lbl for lbl, _ in group))

    state = {
        "keys": {},            # citation key -> (topic file, number of fields)
        "contents": {},        # citation key -> its fields, to tell a copy from a clash
        "fingerprints": {},    # (field, value) -> citation key
        "repeated_keys": [],   # same key exported into two topic files
        "repeated_fields": [], # same field twice inside one entry
        "missing_fields": [],  # entry lacking a field its type requires
        "duplicates": set(),   # distinct keys pointing at the same paper
        "converted": 0,        # characters rewritten into their LaTeX form
        "unmapped": set(),     # non-ASCII pdflatex cannot typeset, not in the table
        "suspicious": [],      # extraction artefacts removed
    }
    all_entries, all_dropped = 0, 0
    for i, group in enumerate(SOURCES):
        n_entries, n_dropped = create_bib_file(
            os.path.join(out_dir, f"{prefix}_{i}.bib"), group, state)
        all_entries += n_entries
        all_dropped += n_dropped

    # A {prefix}_*.bib left over from a run with a larger n_chunks is still
    # listed in the manuscript and still full of entries, so BibTeX would read it
    # and report every key in it as a repeated entry. Remove the extras, and say
    # what the \bibliography line has to look like now.
    stale = sorted(glob.glob(os.path.join(out_dir, f"{prefix}_*.bib")))
    for path in stale:
        n = re.search(re.escape(prefix) + r"_(\d+)\.bib$", path)
        if n and int(n.group(1)) >= n_chunks:
            os.remove(path)
            print(f"  removed stale {os.path.basename(path)}")

    print(
        f"\n{all_entries} entries written, {all_dropped} unused fields removed, "
        f"{state['converted']} characters converted to LaTeX"
    )

    # Fixed automatically: these would be BibTeX errors or warnings.
    report("repeated keys skipped", state["repeated_keys"],
           " (BibTeX 'Repeated entry' errors; clean them up in Zotero)")
    report("repeated fields removed", state["repeated_fields"])
    report("extraction artefacts removed", state["suspicious"], " (check these titles)")

    # Reported only: unknown characters pdflatex cannot typeset. Each one will
    # still break the compilation, so add it to UNICODE_MAP.
    report("characters still unsupported", state["unmapped"],
           " -- add them to UNICODE_MAP")

    # Reported only: the data is missing, and this script will not invent it.
    report("entries missing a required field", state["missing_fields"],
           " (BibTeX 'empty <field>' warnings; fix in Zotero)")
    report("possible duplicates", state["duplicates"],
           " (distinct keys, not merged, both may be cited)")
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="bibutils build",
        description="Merge the Zotero exports into <out_dir>/<prefix>_*.bib.")
    parser.add_argument("source_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--prefix", default="bibli_hdr")
    parser.add_argument("--chunks", type=int, default=N_CHUNKS)
    for step, text in CLEANING.items():
        parser.add_argument(f"--no-{step}", dest=step, action="store_false",
                            help=f"skip: {text}")
    args = parser.parse_args(argv)
    build(args.source_dir, args.out_dir, args.prefix, args.chunks,
          [s for s in CLEANING if not getattr(args, s)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
