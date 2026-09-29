#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export a Zotero library to per-collection BibTeX files, without Zotero.

Author: Corentin Ravoux

Description:
    Reads zotero.sqlite directly and writes one .bib per collection, so the
    export can run from a terminal, a Makefile or cron -- no GUI, no plugin,
    no clicking inside Zotero.

    The citation keys reproduce Zotero's own BibTeX translator exactly
    (translators/BibTeX.js, citeKeyFormat "%a_%t_%y", banned-word list,
    accent folding, "-1" disambiguation). That is the load-bearing part:
    every \\cite in the manuscript depends on those keys. Run with --check to
    diff the generated keys against a directory of real Zotero exports.

    Zotero must not be writing while this runs; the database is copied to a
    temporary file first, so a running Zotero is harmless.

Usage:
    bibutils export -o DIR                      # one .bib per collection
    bibutils export -o DIR --flat               # one library-wide .bib
    bibutils export --check DIR                 # compare keys with real exports
    bibutils export -o DIR --no-keep-latex      # switch a cleaning step off
                                                # (see OPTIONS; --help lists them)
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile

# Default locations of zotero.sqlite, tried in order (Zotero's own default,
# then the snap package). Override with -d or the [zotero] database setting.
DB_CANDIDATES = ("~/Zotero/zotero.sqlite", "~/snap/zotero-snap/common/Zotero/zotero.sqlite")
DB = next((os.path.expanduser(p) for p in DB_CANDIDATES
           if os.path.exists(os.path.expanduser(p))), os.path.expanduser(DB_CANDIDATES[0]))

SKIP_TYPES = ("attachment", "note", "annotation")

# translators/BibTeX.js, zotero2bibtexTypeMap. Types absent from the map are
# exported as @misc, which is what the translator's fallback does.
TYPE_MAP = {
    "book": "book", "bookSection": "incollection", "journalArticle": "article",
    "magazineArticle": "article", "newspaperArticle": "article",
    "thesis": "phdthesis", "letter": "misc", "manuscript": "unpublished",
    "patent": "patent", "interview": "misc", "film": "misc", "artwork": "misc",
    "webpage": "misc", "conferencePaper": "inproceedings", "report": "techreport",
}

# Zotero field -> BibTeX field, for the fields that survive create_bib_hdr.py.
FIELD_MAP = {
    "place": "address", "section": "chapter", "edition": "edition",
    "series": "series", "title": "title", "volume": "volume",
    "ISBN": "isbn", "ISSN": "issn", "url": "url", "DOI": "doi",
    "language": "language", "pages": "pages", "numPages": "pages",
}

# translators/BibTeX.js, citeKeyTitleBannedRe
BANNED = re.compile(
    r"\b(a|an|the|some|from|on|in|to|of|do|with|der|die|das|ein|eine|einer|"
    r"eines|einem|einen|un|une|la|le|l'|les|el|las|los|al|uno|una|unos|unas|"
    r"de|des|del|d')(\s+|\b)|(</?(i|b|sup|sub|sc|span style=\"small-caps\"|span)>)"
)
CLEAN_MODERN = re.compile(r"[^a-z0-9_-]")
CLEAN_LEGACY = re.compile(r"[^a-z0-9!$&*+\-./:;<>?\[\]^_`|]+")
AND = re.compile(r"\band\b")


# translators BibTeX.js -> tidyAccents -> Zotero.Utilities.removeDiacritics(s, true).
# Verbatim from the lowercase half of _diacriticsRemovalMap in Zotero's
# utilities.js (440 characters). Unicode NFD normalisation is NOT a
# substitute: it leaves dotless i and the f-ligatures alone, which changes
# the key of every Karacayli and every ligature-carrying title.
_FOLD_SOURCE = {
    'a': 'aàáâãäåāăąǎǟǡǻȁȃȧɐḁẚạảấầẩẫậắằẳẵặⓐⱥａ',
    'aa': 'ꜳ',
    'ae': 'æǣǽ',
    'ao': 'ꜵ',
    'au': 'ꜷ',
    'av': 'ꜹꜻ',
    'ay': 'ꜽ',
    'b': 'bƀƃɓḃḅḇⓑｂ',
    'c': 'cçćĉċčƈȼḉↄⓒꜿｃ',
    'd': 'dďđƌɖɗḋḍḏḑḓⓓꝺｄ',
    'dz': 'ǆǳ',
    'e': 'eèéêëēĕėęěǝȅȇȩɇɛḕḗḙḛḝẹẻẽếềểễệⓔｅ',
    'f': 'fƒḟⓕꝼｆ',
    'g': 'gĝğġģǥǧǵɠᵹḡⓖꝿꞡｇ',
    'h': 'hĥħȟɥḣḥḧḩḫẖⓗⱨⱶｈ',
    'hv': 'ƕ',
    'i': 'iìíîïĩīĭįıǐȉȋɨḭḯỉịⓘｉ',
    'j': 'jĵǰɉⓙｊ',
    'k': 'kķƙǩḱḳḵⓚⱪꝁꝃꝅꞣｋ',
    'l': 'lĺļľŀłſƚɫḷḹḻḽⓛⱡꝇꝉꞁｌ',
    'lj': 'ǉ',
    'm': 'mɯɱḿṁṃⓜｍ',
    'n': 'nñńņňŉƞǹɲṅṇṉṋⓝꞑꞥｎ',
    'nj': 'ǌ',
    'o': 'oòóôõöøōŏőơǒǫǭǿȍȏȫȭȯȱɔɵṍṏṑṓọỏốồổỗộớờởỡợⓞꝋꝍｏ',
    'oe': 'œ',
    'oi': 'ƣ',
    'oo': 'ꝏ',
    'ou': 'ȣ',
    'p': 'pƥᵽṕṗⓟꝑꝓꝕｐ',
    'q': 'qɋⓠꝗꝙｑ',
    'r': 'rŕŗřȑȓɍɽṙṛṝṟⓡꝛꞃꞧｒ',
    's': 'sßśŝşšșȿṡṣṥṧṩẛⓢꞅꞩｓ',
    't': 'tţťŧƭțʈṫṭṯṱẗⓣⱦꞇｔ',
    'tz': 'ꜩ',
    'u': 'uùúûüũūŭůűųưǔǖǘǚǜȕȗʉṳṵṷṹṻụủứừửữựⓤｕ',
    'v': 'vʋʌṽṿⓥꝟｖ',
    'vy': 'ꝡ',
    'w': 'wŵẁẃẅẇẉẘⓦⱳｗ',
    'x': 'xẋẍⓧｘ',
    'y': 'yýÿŷƴȳɏẏẙỳỵỷỹỿⓨｙ',
    'z': 'zźżžƶȥɀẑẓẕⓩⱬꝣｚ',
}
FOLD = {c: b for b, chars in _FOLD_SOURCE.items() for c in chars}


def fold(s):
    """Zotero's tidyAccents: lowercase, then removeDiacritics(lowercaseOnly)."""
    return "".join(FOLD.get(ch, ch) for ch in s.lower())


def cite_key(author, title, date, date_added, used):
    a = author.lower().replace(" ", "_").replace(",", "") if author else "noauthor"
    if title:
        t = BANNED.sub("", title.lower()).split()
        t = t[0] if t else "notitle"
    else:
        t = "notitle"
    m = re.search(r"\b(\d{4})\b", date or "")
    y = m.group(1) if m else "nodate"

    base = fold(f"{a}_{t}_{y}")
    # Items added from 2020 on use the strict pattern; older ones the legacy one.
    modern = bool(date_added) and date_added[:4] >= "2020"
    base = (CLEAN_MODERN if modern else CLEAN_LEGACY).sub("", base)

    key, i = base, 0
    while key in used:
        i += 1
        key = f"{base}-{i}"
    used.add(key)
    return key


def item_key(flds, author, date_added, used):
    """translators/BibTeX.js buildCiteKey: a pinned key wins.

    A "Citation Key: ..." line in Extra, then the citationKey field, is used
    verbatim -- and, as in Zotero, is not registered in `used`. Otherwise the
    key is generated from the pattern.
    """
    for line in (flds.get("extra") or "").split("\n"):
        m = re.match(r"\s*citation key\s*:\s*(\S.*?)\s*$", line, re.I)
        if m:
            return m.group(1)
    if flds.get("citationKey"):
        return flds["citationKey"]
    return cite_key(author, flds.get("title", ""), flds.get("date", ""), date_added, used)


# translators/BibTeX.js, alwaysMap + escapeSpecialCharacters. Without this the
# .bib carries raw "&", "%", "_" and "$" straight into BibTeX, which is what
# produces "Misplaced alignment tab character &", a "%" that comments out the
# rest of an entry, and the "Runaway argument?" that follows from it.
ALWAYS_MAP = {
    "|": r"{\textbar}",
    "<": r"{\textless}",
    ">": r"{\textgreater}",
    "~": r"{\textasciitilde}",
    "^": r"{\textasciicircum}",
    "\\": r"{\textbackslash}",
    "{": r"\{\vphantom{\}}",
    "}": r"\vphantom{\{}\}",
}
ALWAYS_RE = re.compile(r"[|<>~^\\{}]")
SIMPLE_RE = re.compile(r"([#$%&_])")
VPHANTOM_RE = re.compile(r"\\vphantom\{\\\}\}((?:.(?!\\vphantom\{\\\}\}))*)\\vphantom\{\\\{\}", re.S)

# Fields written verbatim: escaping a URL or a DOI would break the link.
RAW_FIELDS = {"url", "doi", "file", "lccn"}

# Fields whose capitals are brace-protected, so a bibliography style cannot
# lowercase "DESI" or "SDSS-IV".
CASE_PROTECTED = {"title", "booktitle", "series", "type"}


def escape(value):
    """Zotero's escapeSpecialCharacters, including the \\vphantom collapsing."""
    out = ALWAYS_RE.sub(lambda m: ALWAYS_MAP[m.group(0)], value)
    out = SIMPLE_RE.sub(r"\\\1", out)
    # Braces are escaped one by one above, which double-protects a pair that
    # was already balanced; Zotero undoes that, and so do we.
    if "\\vphantom" in out:
        while True:
            m = VPHANTOM_RE.search(out)
            if not m:
                break
            out = out[:m.start()] + m.group(1) + out[m.end():]
    return out


# translators/BibTeX.js, protectCapsRE (the default, initial case unprotected)
# [^\W_] is "letter or digit": Python's \w would also match the underscore of
# an already-escaped "\_", and brace across it.
_LD = r"[^\W_]"
PROTECT_RE = re.compile(
    rf"(.)\b({_LD}*[^\W\d_]{_LD}*)|^({_LD}+[^\W\d_]{_LD}*)", re.UNICODE)


def protect_caps(value):
    """Brace-protect any word carrying a capital away from the first position."""
    def repl(m):
        lead = m.group(1) or ""
        word = m.group(2) or m.group(3) or ""
        # never brace a LaTeX command name: "\{Lambda}" is not "\Lambda"
        if lead == "\\":
            return m.group(0)
        if any(c.isupper() for c in word):
            return f"{lead}{{{word}}}"
        return m.group(0)
    return PROTECT_RE.sub(repl, value)


# ----------------------------------------------------------------------------
# Cleaning steps. Each one can be switched off from the command line
# (--no-<step>); the defaults below are what the HDR build uses.
#
#   escape        Zotero's escapeSpecialCharacters. Off = raw values, which
#                 breaks on the first "&" or "%": for debugging only.
#   protect-caps  brace every capitalised word, so the style cannot lowercase it
#   keep-latex    titles typed as LaTeX in Zotero ("$z_{\rm eff}$",
#                 "$\Lambda$CDM", "\textit{Planck}") are written as LaTeX
#                 instead of being escaped into literal "\$z\_\{..." text
#   fix-allcaps   titles stored in capitals ("AN OPTIMAL EXTRACTION ALGORITHM
#                 FOR CCD SPECTROSCOPY.") are rewritten in title case, keeping
#                 the acronyms the rest of the library writes in capitals
#   eprint        write eprint/archivePrefix from the arXiv id the item already
#                 carries (archiveID, arxiv.org url, 10.48550 DOI, extra,
#                 journal field), so the style can print an arXiv link. Only
#                 when every one of those sources gives the same id.
#   arxiv-journal drop a journal field that is nothing but that same arXiv id
#                 ("arXiv:2110.05503 [astro-ph]", "arXiv e-prints"), which the
#                 style would otherwise print as if it were a journal
# ----------------------------------------------------------------------------
OPTIONS = {"escape": True, "protect-caps": True, "keep-latex": True,
           "fix-allcaps": True, "eprint": True, "arxiv-journal": True}

_AX_ID = r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?"
EPRINT_CONFLICTS = []    # (title, {id: [fields]}), printed at the end of the run


def arxiv_id(flds):
    """The one arXiv id an item carries, or None (absent, or sources disagree)."""
    found = {}

    def add(src, val):
        for m in re.finditer(_AX_ID, val or ""):
            found.setdefault(m.group(1), []).append(src)

    if flds.get("archiveID", "").lower().startswith("arxiv:"):
        add("archiveID", flds["archiveID"])
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$", flds.get("url", ""))
    if m:
        add("url", m.group(1))
    m = re.match(r"10\.48550/arxiv\.(.+)$", flds.get("DOI", ""), re.I)
    if m:
        add("DOI", m.group(1))
    for src in ("extra", "publicationTitle", "pages", "reportNumber",
                "journalAbbreviation"):
        for m in re.finditer(r"arxiv[:\s]*\s*(\S+)", flds.get(src, ""), re.I):
            add(src, m.group(1))
    # "_eprint: 1611.00037", as written by ADS/BibTeX imports
    for m in re.finditer(r"(?:^|\n)\s*_?eprint\s*:\s*(\S+)", flds.get("extra", ""), re.I):
        add("extra", m.group(1))
    if len(found) > 1:
        EPRINT_CONFLICTS.append((flds.get("title", ""), found))
        return None
    return next(iter(found), None)


# "arXiv:2110.05503 [astro-ph, physics:physics]", "arXiv e-prints", "ArXiv"
ARXIV_JOURNAL = re.compile(r"^\s*arxiv(\s*e-prints)?\s*(:\s*\S+(\s*\[[^\]]*\])?)?\s*$", re.I)


# Fields where keep-latex applies. Names and notes keep Zotero's escaping.
LATEX_FIELDS = {"title", "booktitle", "journal", "series"}

# Math-mode-only commands that also occur outside $...$ in Zotero titles
# ("Lyman-{\alpha}"). Outside math they are wrapped in \ensuremath.
MATH_ONLY = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho", "sigma", "tau",
    "phi", "varphi", "chi", "psi", "omega", "Gamma", "Delta", "Theta",
    "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega", "sim", "simeq",
    "approx", "leq", "geq", "lesssim", "gtrsim", "pm", "times", "odot", "ell",
}
_CMD_RE = re.compile(r"\\([A-Za-z]+)")


def _balanced(s):
    depth = 0
    for i, c in enumerate(s):
        if c == "{" and (i == 0 or s[i - 1] != "\\"):
            depth += 1
        elif c == "}" and (i == 0 or s[i - 1] != "\\"):
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def latex_segments(value):
    """Split a value into [(is_math, text)] if it reads as valid LaTeX.

    Returns None when the value carries no LaTeX, or LaTeX that BibTeX would
    choke on (odd number of "$", unbalanced braces); the caller then falls
    back to Zotero's escaping, which is always safe.
    """
    if "$" not in value and "\\" not in value:
        return None
    parts = re.split(r"(?<!\\)\$", value)
    if len(parts) % 2 == 0 or not all(_balanced(p) for p in parts):
        return None
    return [(i % 2 == 1, p) for i, p in enumerate(parts)]


_TEXT_MAP = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
             "^": r"{\textasciicircum}", "~": r"{\textasciitilde}",
             "|": r"{\textbar}", "<": r"{\textless}", ">": r"{\textgreater}"}


def _escape_text(s):
    """Escape the text part of a LaTeX title, leaving commands and braces."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            m = _CMD_RE.match(s, i)
            if m:                                   # \command
                cmd = m.group(1)
                out.append(r"\ensuremath{\%s}" % cmd if cmd in MATH_ONLY
                           else m.group(0))
                i = m.end()
            else:                                   # \' \" \& \{ ...
                out.append(s[i:i + 2])
                i += 2
            continue
        out.append(_TEXT_MAP.get(c, c))
        i += 1
    return "".join(out)


def latex_value(value, protect):
    """keep-latex: write a LaTeX title as LaTeX, math kept verbatim.

    Math is braced as {$...$} so that no bibliography style can change the
    case of "$\\Lambda$" or "$H_0$" -- BibTeX does not know about "$".
    """
    segs = latex_segments(value)
    if segs is None:
        return None
    maths, text = [], []
    for is_math, s in segs:
        if is_math:
            maths.append(re.sub(r"(?<!\\)([%#&])", r"\\\1", s))
            text.append("\x00%d\x00" % (len(maths) - 1))
        else:
            text.append(_escape_text(s))
    out = "".join(text)
    if protect:
        out = protect_caps(out)
    return re.sub("\x00(\\d+)\x00", lambda m: "{$%s$}" % maths[int(m.group(1))], out)


# fix-allcaps: small words kept lower case inside a title-cased title.
SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
               "into", "of", "on", "or", "over", "per", "the", "through", "to",
               "via", "vs", "with", "within", "without"}
ROMAN = re.compile(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)$")
ALLCAPS_REPORT = []      # (original, rewritten), printed at the end of the run


def caps_ratio(title):
    """Fraction of the words of a title written in capitals (math ignored)."""
    words = re.findall(r"[A-Za-z]{2,}", re.sub(r"\$[^$]*\$|\\[A-Za-z]+", "", title))
    return sum(w.isupper() for w in words) / len(words) if len(words) >= 3 else 0.


def is_allcaps(title):
    return caps_ratio(title) > 0.7


def learn_acronyms(titles):
    """Words written in capitals in ordinary titles, and never in lower case.

    "CCD" or "AMR" qualify; "THE" or "COSMOLOGY" do not, although partly
    capitalised titles carry them, because "the" and "cosmology" also occur
    in lower case elsewhere in the library.
    """
    caps, lower = set(), set()
    for t in titles:
        # half-capitalised titles ("The Spitzer-WISE SURVEY OF THE ECLIPTIC
        # POLES") would teach ordinary words as acronyms
        if not t or caps_ratio(t) > 0.3:
            continue
        caps |= set(re.findall(r"\b[A-Z][A-Z0-9]*[A-Z0-9]\b", t))
        lower |= {w.upper() for w in re.findall(r"\b[a-z][a-z0-9]+\b", t)}
    return caps - lower


def title_case(title, acronyms):
    """Rewrite an all-capitals title in title case, keeping known acronyms."""
    def word(w, first):
        if w in acronyms or ROMAN.match(w) or any(c.isdigit() for c in w):
            return w
        if not first and w.lower() in SMALL_WORDS:
            return w.lower()
        return w[:1].upper() + w[1:].lower()

    out, first = [], True
    for tok in re.split(r"(\$[^$]*\$|\\[A-Za-z]+|[A-Za-z0-9]+)", title):
        if re.fullmatch(r"[A-Za-z0-9]+", tok or ""):
            out.append(word(tok, first))
            first = False
        else:
            out.append(tok)
            # after a colon or a period the next word starts a new clause
            if re.search(r"[:.?!]\s*$", tok or ""):
                first = True
    return "".join(out)


def field_value(name, value):
    """One field, escaped and case-protected the way Zotero writes it."""
    if name in RAW_FIELDS or not OPTIONS["escape"]:
        return value
    protect = OPTIONS["protect-caps"] and name in CASE_PROTECTED
    if OPTIONS["keep-latex"] and name in LATEX_FIELDS:
        out = latex_value(value, protect)
        if out is not None:
            return out
    value = escape(value)
    if protect:
        value = protect_caps(value)
    return value


class Library:
    def __init__(self, path):
        tmp = tempfile.mkdtemp(prefix="zot2bib_")
        self.copy = os.path.join(tmp, "zotero.sqlite")
        shutil.copy2(path, self.copy)          # safe while Zotero is running
        self.db = sqlite3.connect(self.copy)

    def items(self):
        rows = self.db.execute(
            """select i.itemID, i.key, i.dateAdded, it.typeName
                 from items i join itemTypes it on it.itemTypeID = i.itemTypeID
                where it.typeName not in (?, ?, ?)
                  and i.itemID not in (select itemID from deletedItems)""",
            SKIP_TYPES).fetchall()
        return rows

    def fields(self, iid):
        return {r[0]: r[1] for r in self.db.execute(
            """select f.fieldName, v.value from itemData d
                 join itemDataValues v on v.valueID = d.valueID
                 join fields f on f.fieldID = d.fieldID where d.itemID = ?""", (iid,))}

    def creators(self, iid):
        return self.db.execute(
            """select ct.creatorType, c.lastName, c.firstName, c.fieldMode
                 from itemCreators ic
                 join creators c on c.creatorID = ic.creatorID
                 join creatorTypes ct on ct.creatorTypeID = ic.creatorTypeID
                where ic.itemID = ? order by ic.orderIndex""", (iid,)).fetchall()

    def collections(self):
        rows = self.db.execute(
            "select collectionID, collectionName, parentCollectionID from collections").fetchall()
        by_id = {r[0]: r for r in rows}
        paths = {}
        for cid, name, parent in rows:
            parts, p = [name], parent
            while p:
                parts.insert(0, by_id[p][1])
                p = by_id[p][2]
            paths[cid] = "/".join(parts)
        return paths

    def membership(self):
        out = {}
        for cid, iid in self.db.execute("select collectionID, itemID from collectionItems"):
            out.setdefault(iid, []).append(cid)
        return out


def entry(typ, key, flds, creators):
    """Render one BibTeX entry the way Zotero's translator does."""
    bt = TYPE_MAP.get(typ, "misc")
    lines = [f"@{bt}{{{key},"]

    def put(name, value):
        if value:
            lines.append("\t%s = {%s}," % (name, field_value(name, value)))

    eprint = arxiv_id(flds) if OPTIONS["eprint"] else None
    title = flds.get("title", "")
    if OPTIONS["fix-allcaps"] and is_allcaps(title):
        fixed = title_case(title, ACRONYMS)
        if (title, fixed) not in ALLCAPS_REPORT:
            ALLCAPS_REPORT.append((title, fixed))
        title = fixed
    put("title", title)

    # container
    if bt == "article":
        journal = flds.get("publicationTitle", "")
        if eprint and OPTIONS["arxiv-journal"] and ARXIV_JOURNAL.match(journal):
            journal = ""        # the id is kept, in eprint
        put("journal", journal)
    elif bt in ("inproceedings", "incollection"):
        put("booktitle", flds.get("proceedingsTitle") or flds.get("bookTitle", ""))
    if bt == "phdthesis":
        put("school", flds.get("university") or flds.get("publisher", ""))
    elif bt == "techreport":
        put("institution", flds.get("institution") or flds.get("publisher", ""))
    else:
        put("publisher", flds.get("publisher", ""))

    for zf, bf in FIELD_MAP.items():
        if zf == "title":
            continue
        v = flds.get(zf)
        if v:
            put(bf, v)

    if eprint:
        lines.append("\teprint = {%s}," % eprint)
        lines.append("\tarchivePrefix = {arXiv},")

    put("number", flds.get("issue") or flds.get("reportNumber")
        or flds.get("seriesNumber", ""))

    def name(ln, fn, mode):
        # A literal "and" inside a name would be read by BibTeX as the
        # separator between two authors, which is a hard error. Zotero braces
        # it; so do we. fieldMode 1 means the whole name sits in lastName.
        ln = AND.sub("{and}", escape((ln or "").strip()))
        fn = AND.sub("{and}", escape((fn or "").strip()))
        if mode == 1 or not fn:
            return "{%s}" % ln
        return "%s, %s" % (ln, fn)

    authors = [c for c in creators if c[0] == "author"]
    editors = [c for c in creators if c[0] == "editor"]
    if not authors and creators:
        authors = creators[:1]
    lines.append("\tauthor = {%s},"
                 % " and ".join(name(ln, fn, md) for _, ln, fn, md in authors)) if authors else None
    lines.append("\teditor = {%s},"
                 % " and ".join(name(ln, fn, md) for _, ln, fn, md in editors)) if editors else None

    date = flds.get("date", "")
    m = re.match(r"(\d{4})-(\d{2})", date)
    if m:
        put("year", m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
            lines.append("\tmonth = %s," %
                         ["jan", "feb", "mar", "apr", "may", "jun",
                          "jul", "aug", "sep", "oct", "nov", "dec"][month - 1])
    else:
        m = re.search(r"\b(\d{4})\b", date)
        if m:
            put("year", m.group(1))

    put("note", flds.get("extra", "").replace("\n", " "))
    lines.append("}")
    return "\n".join(lines)


ACRONYMS = set()


def report_allcaps():
    """The rewritten titles, for a check by eye: the fix belongs in Zotero."""
    for title, found in EPRINT_CONFLICTS:
        print(f"no eprint written, arXiv ids disagree in {title[:60]!r}: {found}")
    if ALLCAPS_REPORT:
        print(f"\n{len(ALLCAPS_REPORT)} all-capitals title(s) rewritten in title case "
              "(fix them in Zotero to silence this):")
        for old, new in sorted(ALLCAPS_REPORT):
            print(f"  {old[:70]}\n    -> {new[:70]}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bibutils export")
    ap.add_argument("-d", "--database", default=DB)
    ap.add_argument("-o", "--output", default=".")
    ap.add_argument("--flat", action="store_true",
                    help="one zotero_library.bib instead of one file per collection")
    ap.add_argument("--unfiled", action="store_true",
                    help="list the items that belong to no collection, and say "
                         "which of them duplicate an item that is filed")
    ap.add_argument("--check", metavar="DIR",
                    help="compare generated keys with real Zotero exports in DIR")
    ap.add_argument("--keys", metavar="FILE",
                    help="citation-key registry (bibutils.keys): one stable, unique key "
                         "per item across all collections; created on first use")
    for step in OPTIONS:
        ap.add_argument(f"--no-{step}", dest=step.replace("-", "_"),
                        action="store_false", help=f"skip the {step} cleaning step")
    args = ap.parse_args(argv)
    for step in OPTIONS:
        OPTIONS[step] = getattr(args, step.replace("-", "_"))

    if not os.path.exists(args.database):
        sys.exit(f"error: no Zotero database at {args.database}")

    lib = Library(args.database)
    paths, memb = lib.collections(), lib.membership()

    global ACRONYMS
    ACRONYMS = learn_acronyms(v for (v,) in lib.db.execute(
        """select v.value from itemData d join itemDataValues v on v.valueID = d.valueID
             join fields f on f.fieldID = d.fieldID where f.fieldName = 'title'"""))

    # Zotero allocates citation keys per export: each file it writes starts
    # with an empty key table, so the same item gets the plain key in every
    # collection it belongs to, and only a collision *inside one file* gets
    # the "-1" suffix. Reproducing that exactly is what keeps the keys already
    # cited in the manuscript resolving. Allocating globally instead would let
    # a duplicate -- or an item filed in no collection at all -- take the plain
    # key and push its twin to "-1", silently breaking those citations.
    #
    # Order is itemID ascending, which is the order Zotero itself iterates in.
    items = sorted(lib.items(), key=lambda r: r[0])
    cache = {}

    # With a registry, keys come from it (see bibutils.keys): unique across
    # the whole library and stable, instead of allocated file by file.
    registry, assigned = None, None
    if args.keys and not (args.unfiled or args.check):
        from . import keys as _keys
        fresh = not os.path.exists(args.keys)
        registry = _keys.load(args.keys)
        if fresh:
            n = _keys.seed(lib, registry)
            print(f"key registry created: {n} existing keys recorded unchanged")
        assigned, events = _keys.assign(lib, registry)

    def render(iid, ikey, added, typ, used):
        if iid not in cache:
            cache[iid] = (lib.fields(iid), lib.creators(iid))
        flds, crs = cache[iid]
        author = next((c[1] for c in crs if c[0] == "author"), None) or \
                 (crs[0][1] if crs else None)
        key = assigned[iid] if assigned is not None and iid in assigned \
            else item_key(flds, author, added, used)
        return key, entry(typ, key, flds, crs)

    os.makedirs(args.output, exist_ok=True)

    if args.unfiled:
        def norm(t):
            return re.sub(r"[^a-z0-9]", "", (t or "").lower())[:60]

        filed = {}
        for iid, ikey, added, typ in lib.items():
            if iid not in memb:
                continue
            f = lib.fields(iid)
            where = paths[memb[iid][0]]
            if f.get("DOI"):
                filed.setdefault(("doi", f["DOI"].lower()), (iid, where))
            filed.setdefault(("title", norm(f.get("title"))), (iid, where))

        rows = [r for r in lib.items() if r[0] not in memb]
        dup, orphan = [], []
        for iid, ikey, added, typ in rows:
            f = lib.fields(iid)
            twin = (filed.get(("doi", (f.get("DOI") or "").lower()))
                    if f.get("DOI") else None)
            twin = twin or filed.get(("title", norm(f.get("title"))))
            crs = lib.creators(iid)
            who = crs[0][1] if crs else "?"
            year = (re.search(r"\b(\d{4})\b", f.get("date", "")) or [""])
            year = year.group(1) if hasattr(year, "group") else ""
            rec = (who, year, f.get("title", ""), twin)
            (dup if twin else orphan).append(rec)

        print(f"{len(rows)} item(s) in no collection\n")
        print(f"{len(dup)} of them duplicate an item that IS filed:")
        for who, year, title, twin in sorted(dup):
            print(f"  {who:<20} {year:<5} {title[:58]}")
            print(f"  {'':<26} duplicate of the copy in {twin[1]}")
        print(f"\n{len(orphan)} of them exist nowhere else:")
        for who, year, title, _ in sorted(orphan):
            print(f"  {who:<20} {year:<5} {title[:58]}")
        return 0

    if args.check:
        used = set()
        mine = set()
        for cid in sorted(paths):
            per = set()
            for iid, ikey, added, typ in items:
                if cid in memb.get(iid, []):
                    mine.add(render(iid, ikey, added, typ, per)[0])
        real = set()
        for f in os.listdir(args.check):
            if f.endswith(".bib"):
                txt = open(os.path.join(args.check, f), encoding="utf-8",
                           errors="replace").read()
                real |= set(re.findall(r"^@\w+\{([^,]+),", txt, re.M))
        missing, extra = real - mine, mine - real
        print(f"{len(real)} keys in {args.check}, {len(mine)} generated")
        print(f"  matched : {len(real & mine)}")
        print(f"  missing : {len(missing)}")
        for k in sorted(missing)[:20]:
            print("      -", k)
        print(f"  extra   : {len(extra)}  (items not in those exports)")
        return 0 if not missing else 1

    if args.flat:
        out = os.path.join(args.output, "zotero_library.bib")
        used, n = set(), 0
        with open(out, "w", encoding="utf-8") as fh:
            for iid, ikey, added, typ in items:
                fh.write(render(iid, ikey, added, typ, used)[1] + "\n\n")
                n += 1
        report_allcaps()
        print(f"{n} entries -> {out}")
        return 0

    written, total = 0, 0
    for cid, path in sorted(paths.items(), key=lambda kv: kv[1]):
        rows = [r for r in items if cid in memb.get(r[0], [])]
        if not rows:
            continue
        name = path.replace("/", "_").replace(":", "-") + ".bib"
        used = set()
        with open(os.path.join(args.output, name), "w", encoding="utf-8") as fh:
            for iid, ikey, added, typ in rows:
                fh.write(render(iid, ikey, added, typ, used)[1] + "\n\n")
        written += 1
        total += len(rows)
        print(f"  {len(rows):4d}  {name}")
    orphans = sum(1 for r in items if not memb.get(r[0]))
    report_allcaps()
    if registry is not None:
        _keys.save(registry, args.keys)
        labels = {"new": "new entry", "inherited": "inherited (replaces a retired record)",
                  "pinned": "pinned in Zotero", "retired": "retired (no longer exported)"}
        for kind in ("new", "inherited", "pinned", "retired"):
            ev = [e for e in events if e[0] == kind]
            if ev:
                print(f"\n{len(ev)} key(s) {labels[kind]}:")
                for _, key, title in sorted(ev, key=lambda e: e[1]):
                    print(f"  {key:40} {title[:60]}")
    print(f"\n{written} files, {total} entries -> {args.output}")
    if orphans:
        print(f"{orphans} item(s) in no collection, therefore not exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
