"""Check that a cleaned .bib carries exactly the information Zotero holds.

Every field that identifies a reference is compared, entry by entry, between
the raw Zotero value and the final .bib value, after both are reduced to a
comparable form (LaTeX, markup, accents, case and punctuation removed), plus
a strict pass on numbers and relation signs. Any difference is reported;
none is expected except the intended ones, which are counted separately.
"""
import re
import sys
import unicodedata
from collections import Counter, defaultdict

# ------------------------------------------------------------- arXiv ids
# Deliberately independent of bibutils.zotero.arxiv_id: a checker that reused
# the code it checks would agree with it by construction.
AX_NEW = r"(\d{4}\.\d{4,5})(v\d+)?"
AX_OLD = r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?"


def arxiv_candidates(f):
    """Every arXiv id a raw Zotero item carries, as (field, id) pairs."""
    out = []

    def add(src, val):
        for pat in (AX_NEW, AX_OLD):
            for m in re.finditer(pat, val):
                out.append((src, m.group(1)))

    if f.get("archiveID", "").lower().startswith("arxiv:"):
        add("archiveID", f["archiveID"])
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$", f.get("url", ""))
    if m:
        add("url", m.group(1))
    m = re.match(r"10\.48550/arxiv\.(.+)$", f.get("DOI", ""), re.I)
    if m:
        add("DOI", m.group(1))
    for src in ("extra", "publicationTitle", "pages", "reportNumber", "journalAbbreviation"):
        for m in re.finditer(r"arxiv[:\s]*\s*(\S+)", f.get(src, ""), re.I):
            add(src, m.group(1))
    for m in re.finditer(r"(?:^|\n)\s*_?eprint\s*:\s*(\S+)", f.get("extra", ""), re.I):
        add("extra", m.group(1))
    return out


# ---------------------------------------------------------------- bib parsing
def split_entries(text):
    out, i = [], 0
    while True:
        at = text.find("@", i)
        if at == -1:
            return out
        br = text.find("{", at)
        depth, j = 0, br
        while j < len(text):
            depth += text[j] == "{"
            depth -= text[j] == "}"
            if depth == 0:
                break
            j += 1
        out.append((text[at + 1:br].strip().lower(), text[br + 1:j]))
        i = j + 1


def split_fields(body):
    key, rest = body.split(",", 1)
    fields, i = {}, 0
    pat = re.compile(r"\s*([A-Za-z][A-Za-z0-9_+:-]*)\s*=\s*")
    while True:
        m = pat.match(rest, i)
        if not m:
            break
        i = m.end()
        if rest[i] == "{":
            depth, j = 0, i
            while True:
                depth += rest[j] == "{"
                depth -= rest[j] == "}"
                if depth == 0:
                    break
                j += 1
            val, i = rest[i + 1:j], j + 1
        else:
            j = i
            while j < len(rest) and rest[j] not in ",\n":
                j += 1
            val, i = rest[i:j].strip(), j
        while i < len(rest) and rest[i] in " \t\r\n,":
            i += 1
        fields[m.group(1).lower()] = val
    return key.strip(), fields


def read_bib(path):
    return {k: (t, f) for t, b in split_entries(open(path, encoding="utf-8").read())
            if t not in ("comment", "string", "preamble")
            for k, f in [split_fields(b)]}

# ------------------------------------------------------------- normalisation
GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
         "η": "eta", "θ": "theta", "κ": "kappa", "λ": "lambda", "μ": "mu",
         "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau",
         "φ": "phi", "ϕ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
         "Γ": "gamma", "Δ": "delta", "∆": "delta", "Θ": "theta", "Λ": "lambda",
         "Ξ": "xi", "Π": "pi", "Σ": "sigma", "Φ": "phi", "Ψ": "psi", "Ω": "omega",
         "ß": "ss", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe",
         "ł": "l", "Ł": "l", "ı": "i", "đ": "d", "Đ": "d", "þ": "th", "ð": "d",
         "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}
# LaTeX commands standing for a symbol (dropped, like the symbol itself) or
# for pure markup (dropped, the argument is kept).
DROP_CMDS = ("ensuremath|textit|emph|mathrm|mathbf|mathcal|mathit|rm|text|textbf|bf|it|"
             "textrm|textsc|textsf|texttt|vphantom|textbackslash|textasciitilde|"
             "textasciicircum|textbar|textless|textgreater|sim|simeq|pm|times|leq|geq|"
             "le|ge|approx|lesssim|gtrsim|odot|in|equiv|sum|prec|star|leftrightarrow|"
             "circ|langle|rangle|perp|copyright|guillemotright|prime|cdot|ldots|dots|"
             "infty|propto|rightarrow|to|mid|quad|nobreakspace")
LATEX_LETTERS = {"o": "o", "O": "o", "ss": "ss", "ae": "ae", "AE": "ae", "oe": "oe",
                 "OE": "oe", "aa": "a", "AA": "a", "l": "l", "L": "l", "i": "i",
                 "dj": "d", "DJ": "d", "th": "th", "TH": "th", "dh": "d", "DH": "d"}


def norm(s):
    s = s or ""
    s = "".join(GREEK.get(c, c) for c in s)
    # accents: symbol accents (\'e, \"{o}) and letter accents (\c{c}, \v s)
    # -- a letter accent must not run into a longer command (\beta, \dj)
    s = re.sub(r"\\([\'\"`^~=.])\s*\{?\\?([A-Za-z])\}?", r"\2", s)
    s = re.sub(r"\\([uvHckdbr])(?![A-Za-z])\s*\{?\\?([A-Za-z])\}?", r"\2", s)
    s = re.sub(r"\\(%s)(?![A-Za-z])" % DROP_CMDS, " ", s)
    s = re.sub(r"\\(o|O|ss|ae|AE|oe|OE|aa|AA|l|L|i|dj|DJ|th|TH|dh|DH)(?![A-Za-z])",
               lambda m: LATEX_LETTERS[m.group(1)], s)
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)        # \alpha -> alpha
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


SYMBOLS = {"≤": " leq ", "⩽": " leq ", "≥": " geq ", "⩾": " geq ", "∼": " sim ",
           "~": " sim ", "±": " pm ", "×": " times ", "−": "-", "–": "-", "—": "-",
           "‑": "-", "<": " lt ", ">": " gt ", "=": " eq ", "≈": " approx ",
           "≃": " simeq ", "≲": " lesssim ", "≳": " gtrsim "}
LATEX_SYMBOLS = {"leq": "leq", "le": "leq", "geq": "geq", "ge": "geq", "sim": "sim",
                 "textasciitilde": "sim", "pm": "pm", "times": "times",
                 "textless": "lt", "textgreater": "gt", "approx": "approx",
                 "simeq": "simeq", "lesssim": "lesssim", "gtrsim": "gtrsim"}


def numbers(s):
    """Numbers (with their decimal point) and relation signs, in order.

    norm() drops punctuation, so it cannot see "z=2.3" become "z=23" or a
    minus sign disappear; this stricter view of the same field can.
    """
    s = s or ""
    s = re.sub(r"\\(%s)(?![A-Za-z])" % "|".join(LATEX_SYMBOLS),
               lambda m: " " + LATEX_SYMBOLS[m.group(1)] + " ", s)
    s = "".join(SYMBOLS.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"-+", "-", s.replace("{", "").replace("}", ""))
    return re.findall(r"\d+(?:\.\d+)?|-|(?<![A-Za-z])(?:leq|geq|sim|pm|times|lt|gt|eq|"
                      r"approx|simeq|lesssim|gtrsim)(?![A-Za-z])", s)


def split_names(field):
    """BibTeX name list -> ['family|given', ...], split on top-level ' and '."""
    names, depth, cur, i = [], 0, "", 0
    while i < len(field):
        c = field[i]
        depth += c == "{"
        depth -= c == "}"
        if depth == 0 and field.startswith(" and ", i):
            names.append(cur); cur = ""; i += 5; continue
        cur += c; i += 1
    names.append(cur)
    out = []
    for n in names:
        n = n.strip()
        if "," in n and not (n.startswith("{") and n.endswith("}") and _balanced_inner(n)):
            fam, giv = n.split(",", 1)
        else:
            fam, giv = n, ""
        out.append(norm(fam) + "|" + norm(giv))
    return out


def _balanced_inner(n):
    depth = 0
    for c in n[1:-1]:
        depth += c == "{"
        depth -= c == "}"
        if depth < 0:
            return False
    return depth == 0


def zotero_names(creators, kind):
    sel = [c for c in creators if c[0] == kind]
    if kind == "author" and not sel and creators:
        sel = creators[:1]
    return [norm(c[1]) + "|" + ("" if c[3] == 1 else norm(c[2])) for c in sel]

# ------------------------------------------------------------ expectations
TYPE = {"book": "book", "bookSection": "incollection", "journalArticle": "article",
        "magazineArticle": "article", "newspaperArticle": "article",
        "thesis": "phdthesis", "manuscript": "unpublished", "patent": "patent",
        "conferencePaper": "inproceedings", "report": "techreport"}
ARXIV_JOURNAL = re.compile(r"^\s*arxiv(\s*e-prints)?\s*(:\s*\S+(\s*\[[^\]]*\])?)?\s*$", re.I)
RAW = {"url", "doi"}                 # compared verbatim


def expected(item):
    """bib field -> raw Zotero value, from Zotero's own field names."""
    f, t = item["fields"], TYPE.get(item["type"], "misc")
    e = {"title": f.get("title", ""), "volume": f.get("volume", ""),
         "pages": f.get("pages") or f.get("numPages", ""),
         "doi": f.get("DOI", ""), "url": f.get("url", ""), "isbn": f.get("ISBN", ""),
         "issn": f.get("ISSN", ""), "edition": f.get("edition", ""),
         "series": f.get("series", ""), "address": f.get("place", ""),
         "chapter": f.get("section", ""), "language": f.get("language", ""),
         "number": f.get("issue") or f.get("reportNumber") or f.get("seriesNumber", ""),
         "note": f.get("extra", "")}
    if t == "article":
        e["journal"] = f.get("publicationTitle", "")
    if t in ("inproceedings", "incollection"):
        e["booktitle"] = f.get("proceedingsTitle") or f.get("bookTitle", "")
    if t == "phdthesis":
        e["school"] = f.get("university") or f.get("publisher", "")
    elif t == "techreport":
        e["institution"] = f.get("institution") or f.get("publisher", "")
    else:
        e["publisher"] = f.get("publisher", "")
    m = re.search(r"\b(\d{4})\b", f.get("date", ""))
    e["year"] = m.group(1) if m else ""
    return t, e


def check(bib_path, items, verified_arxiv=None):
    """Compare every entry of bib_path with its Zotero item.

    items: {key: item} from zotero_items(). verified_arxiv: arXiv ids confirmed
    online (bibutils.links), or None to skip that part. Returns
    (bib, problems, intended): problems is empty when nothing was altered.
    """
    bib = read_bib(bib_path)
    problems, intended = [], Counter()
    missing = sorted(set(items) - set(bib)); extra = sorted(set(bib) - set(items))
    for k in missing:
        problems.append((k, "entry", "in Zotero, missing from .bib", ""))
    for k in extra:
        problems.append((k, "entry", "in .bib, no Zotero item", ""))
    for key in sorted(set(bib) & set(items)):
        item = items[key]; btype, got = bib[key]
        etype, exp = expected(item)
        if btype != etype:
            problems.append((key, "type", etype, btype))
        for fld, raw in exp.items():
            have = got.get(fld, "")
            if fld in RAW:
                ok = have == raw
            else:
                ok = norm(have) == norm(raw)
                if ok and fld in ("title", "journal", "booktitle") and \
                        numbers(have) != numbers(raw):
                    problems.append((key, fld + " (numbers/signs)",
                                     numbers(raw), numbers(have)))
            if ok:
                continue
            if fld == "journal" and not have and ARXIV_JOURNAL.match(raw) and got.get("eprint"):
                ids = re.findall(r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})", raw)
                if all(i == got["eprint"] for i in ids):
                    intended["journal = bare arXiv id, moved to eprint"] += 1
                    continue
            problems.append((key, fld, raw, have))
        for kind in ("author", "editor"):
            z = zotero_names(item["creators"], kind)
            b = split_names(got[kind]) if got.get(kind) else []
            if z != b:
                problems.append((key, kind, z, b))
        # eprint must be the item's own arXiv id, verified online
        if "eprint" in got:
            own = {i for _, i in arxiv_candidates(item["fields"])}
            if own != {got["eprint"]}:
                problems.append((key, "eprint", sorted(own), got["eprint"]))
            elif verified_arxiv is not None and got["eprint"] not in verified_arxiv:
                problems.append((key, "eprint", "verified arXiv id", got["eprint"]))
            else:
                intended["eprint added" + (" (verified on arXiv)"
                                           if verified_arxiv is not None else "")] += 1
        extra_f = set(got) - set(exp) - {"author", "editor", "eprint", "archiveprefix",
                                         "month", "collaboration"}
        for fld in extra_f:
            problems.append((key, fld, "(no Zotero source)", got[fld]))
    return bib, problems, intended


# ------------------------------------------------- Zotero item behind each key
def zotero_items(database, registry=None):
    """{key: item} for every key of the build, reproducing the export exactly.

    With a key registry (bibutils.keys), keys come from it, as in the export;
    the registry passed in is not modified.

    Keys are allocated per collection file and the build keeps the first file
    (sorted) holding a key; so does this. Also returns the keys held by two
    *different* Zotero items, of which the build keeps only one.
    """
    from . import zotero as z
    lib = z.Library(database)
    if registry is not None:
        import copy
        from . import keys as _keys
        assigned, _, _ = _keys.assign(lib, copy.deepcopy(registry))
        items = {}
        for iid, key in assigned.items():
            (typ,), = lib.db.execute("select t.typeName from items i join itemTypes t "
                                     "on t.itemTypeID=i.itemTypeID where i.itemID=?", (iid,))
            items[key] = dict(iid=iid, type=typ, file=None, fields=lib.fields(iid),
                              creators=[list(c) for c in lib.creators(iid)])
        return items, []
    paths, memb = lib.collections(), lib.membership()
    rows = sorted(lib.items(), key=lambda r: r[0])
    files = {}
    for cid, path in paths.items():
        sel = [r for r in rows if cid in memb.get(r[0], [])]
        if not sel:
            continue
        name = path.replace("/", "_").replace(":", "-") + ".bib"
        used, keys = set(), []
        for iid, ikey, added, typ in sel:
            f, crs = lib.fields(iid), lib.creators(iid)
            author = next((c[1] for c in crs if c[0] == "author"), None) or \
                (crs[0][1] if crs else None)
            keys.append((z.item_key(f, author, added, used), iid, typ))
        files[name] = keys
    first, clashes = {}, []
    for name in sorted(files):
        for key, iid, typ in files[name]:
            if key not in first:
                first[key] = (iid, typ, name)
            elif first[key][0] != iid:
                clashes.append(dict(
                    key=key,
                    kept=(first[key][2], lib.fields(first[key][0]).get("title", "")),
                    dropped=(name, lib.fields(iid).get("title", ""))))
    items = {k: dict(iid=iid, type=typ, file=name, fields=lib.fields(iid),
                     creators=[list(c) for c in lib.creators(iid)])
             for k, (iid, typ, name) in first.items()}
    return items, clashes


def print_report(bib, problems, intended, out=sys.stdout):
    print(f"{len(bib)} entries checked", file=out)
    for k, v in intended.items():
        print(f"  intended: {v:4d}  {k}", file=out)
    print(f"{len(problems)} unexplained differences", file=out)
    by = defaultdict(list)
    for p in problems:
        by[p[1]].append(p)
    for fld, ps in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"\n[{fld}] {len(ps)}", file=out)
        for key, _, raw, have in ps:
            print(f"  {key}\n     zotero: {str(raw)[:150]}\n     bib   : {str(have)[:150]}",
                  file=out)
