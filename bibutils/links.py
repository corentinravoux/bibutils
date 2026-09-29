"""Online checks of the links a bibliography will print.

Every arXiv id is looked up on the arXiv API and every DOI on Crossref (or,
for DOIs registered elsewhere -- Zenodo, ASCL, ... -- on the doi.org handle
registry). Each record found is compared with the Zotero item it is attached
to: title, first author and year. The point is to catch a link that resolves
to the *wrong* paper, not only a link that does not resolve.

Results are cached as JSON, so a rerun only queries what is new.
"""
import difflib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

from .integrity import arxiv_candidates, norm

UA = {"User-Agent": "bibutils/0.1 (bibliography link checker)"}
ATOM = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def _get(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return 200, urllib.request.urlopen(req, timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return e.code, b""
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
    return 0, b""


def _load(path):
    return json.load(open(path)) if path and os.path.exists(path) else {}


def fetch_arxiv(ids, cache=None, batch=80):
    """{id: record or None}; arXiv asks for one request every 3 seconds."""
    out = _load(cache)
    todo = [i for i in sorted(ids) if i not in out]
    for s in range(0, len(todo), batch):
        chunk = todo[s:s + batch]
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"id_list": ",".join(chunk), "max_results": len(chunk)})
        code, xml = _get(url)
        if code != 200:
            raise RuntimeError(f"arXiv API unreachable (HTTP {code})")
        got = {}
        for e in ET.fromstring(xml).findall("a:entry", ATOM):
            eid = e.find("a:id", ATOM).text.rsplit("/abs/", 1)[-1]
            base = re.sub(r"v\d+$", "", eid)
            title = e.find("a:title", ATOM)
            if title is None:
                continue
            doi, jref = e.find("x:doi", ATOM), e.find("x:journal_ref", ATOM)
            got[base] = dict(
                title=" ".join(title.text.split()),
                authors=[a.find("a:name", ATOM).text for a in e.findall("a:author", ATOM)],
                published=e.find("a:published", ATOM).text[:10],
                doi=doi.text if doi is not None else "",
                journal_ref=jref.text if jref is not None else "")
        for i in chunk:
            out[i] = got.get(i)
        if cache:
            json.dump(out, open(cache, "w"), indent=0)
        time.sleep(3.5)
    return out


def _one_doi(doi):
    code, body = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if code == 200:
        m = json.loads(body)["message"]
        return doi, dict(
            source="crossref", title=" ".join((m.get("title") or [""])[0].split()),
            container=(m.get("container-title") or [""])[0], volume=m.get("volume", ""),
            issue=m.get("issue", ""), page=m.get("page", "") or m.get("article-number", ""),
            year=(m.get("issued", {}).get("date-parts") or [[None]])[0][0],
            authors=[a.get("family", a.get("name", "")) for a in m.get("author", [])[:5]])
    hc, hb = _get("https://doi.org/api/handles/" + urllib.parse.quote(doi, safe="/"))
    if hc == 200 and json.loads(hb).get("responseCode") == 1:
        return doi, dict(source="handle-only")
    return doi, dict(source="NOT FOUND", crossref=code, handle=hc)


def fetch_dois(dois, cache=None, workers=4):
    """{doi: record}; source is crossref, handle-only or NOT FOUND."""
    out = _load(cache)
    todo = [d for d in sorted(dois) if d not in out]
    with ThreadPoolExecutor(workers) as ex:
        for i, (doi, meta) in enumerate(ex.map(_one_doi, todo)):
            out[doi] = meta
            if cache and i % 100 == 0:
                json.dump(out, open(cache, "w"), indent=0)
    if cache:
        json.dump(out, open(cache, "w"), indent=0)
    return out


def _sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def _first_author(item):
    a = [c for c in item["creators"] if c[0] == "author"] or item["creators"]
    return norm(a[0][1]) if a else ""


def _year(s):
    m = re.search(r"\b(1[89]|20)\d\d\b", s or "")
    return int(m.group(0)) if m else None


def check_links(items, cache_dir=None, cited=None):
    """Look up every link of items online; return a dict of findings.

    items: {key: item} from integrity.zotero_items(). cited: optional set of
    keys the manuscript cites, used to flag what matters.
    """
    cache = (lambda n: os.path.join(cache_dir, n)) if cache_dir else (lambda n: None)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    ax_ids, dois = set(), set()
    for v in items.values():
        ax_ids |= {i for _, i in arxiv_candidates(v["fields"])}
        d = v["fields"].get("DOI", "").strip()
        if d and not d.lower().startswith("10.48550"):
            dois.add(d)
    ax = fetch_arxiv(ax_ids, cache("arxiv.json"))
    dm = fetch_dois(dois, cache("doi.json"))

    f = dict(arxiv_missing=[], arxiv_conflict=[], doi_missing=[], mismatch=[], author=[],
             no_link=[], published_preprint=[], verified_arxiv={i for i, r in ax.items() if r})
    for key, v in sorted(items.items()):
        fl, fa, y = v["fields"], _first_author(v), _year(v["fields"].get("date", ""))
        c = "C" if cited and key in cited else " "
        ids = {i for _, i in arxiv_candidates(fl)}
        if len(ids) > 1:
            f["arxiv_conflict"].append((c, key, sorted(ids)))
        doi = fl.get("DOI", "").strip()
        jdoi = doi if doi and not doi.lower().startswith("10.48550") else ""
        for i in ids:
            r = ax.get(i)
            if r is None:
                f["arxiv_missing"].append((c, key, i))
                continue
            names = [norm(n.split()[-1]) for n in r["authors"]]
            if _sim(fl.get("title", ""), r["title"]) < 0.9 and not (
                    fa and any(fa in n or n in fa for n in names if n)):
                f["mismatch"].append((c, key, "arXiv " + i, fl.get("title", ""), r["title"]))
            if not jdoi and r["doi"]:
                f["published_preprint"].append((c, key, i, r["doi"], r["journal_ref"]))
        if jdoi:
            r = dm.get(jdoi, {})
            if r.get("source") == "NOT FOUND":
                f["doi_missing"].append((c, key, jdoi))
            elif r.get("source") == "crossref":
                cauth = [norm(a) for a in r["authors"]]
                bad_title = _sim(fl.get("title", ""), r["title"]) < 0.9
                bad_author = fa and cauth and not any(fa in a or a in fa for a in cauth if a) \
                    and "collaboration" not in fa
                bad_year = y and r["year"] and abs(int(r["year"]) - y) > 1
                found = f"{r['title']} ({r['year']}, {', '.join(r['authors'][:2])})"
                if (bad_title and bad_author) or bad_year or \
                        re.match(r"\s*(erratum|corrigendum|review of)", r["title"], re.I):
                    f["mismatch"].append((c, key, "DOI " + jdoi, fl.get("title", ""), found))
                elif bad_author and not any(
                        difflib.SequenceMatcher(None, fa, a).ratio() > 0.8 for a in cauth):
                    # same title, other author: a book review, or an author list
                    # the publisher records in another order
                    f["author"].append((c, key, "DOI " + jdoi, fa, found))
        if not jdoi and not ids:
            f["no_link"].append((c, key, v["type"], fl.get("title", "")))
    return f


def print_links(f, out=None):
    import sys
    out = out or sys.stdout
    sections = [
        ("arXiv ids that do not exist", "arxiv_missing"),
        ("items carrying two different arXiv ids", "arxiv_conflict"),
        ("DOIs that do not resolve", "doi_missing"),
        ("links that resolve to a DIFFERENT paper (check, then re-export)", "mismatch"),
        ("DOIs whose record has another first author (check by eye)", "author"),
        ("entries with neither DOI nor arXiv id (no link printed)", "no_link"),
        ("preprints now published (re-export the journal version)", "published_preprint"),
    ]
    for title, k in sections:
        rows = f[k]
        print(f"\n{len(rows)} {title}   [C = cited]", file=out)
        for r in rows:
            print("  " + " | ".join(str(x)[:110] for x in r), file=out)
