"""Compare a LaTeX publication list with an author's INSPIRE-HEP record.

The list is any set of .tex files whose entries link to arXiv
(https://arxiv.org/abs/<id>), such as a moderncv \\cventry list. Reported:

  - papers on INSPIRE that the list does not contain;
  - entries the list still calls a preprint that INSPIRE shows as published,
    with the journal reference to use;
  - entries of the list that INSPIRE does not know.

Nothing is edited: what goes into a CV is the author's decision.
"""
import json
import re
import urllib.parse
import urllib.request

API = "https://inspirehep.net/api/literature"
FIELDS = "titles,arxiv_eprints,publication_info,earliest_date,document_type,authors.full_name,dois"
PREPRINT = re.compile(r"arxiv preprint|submitted|in preparation", re.I)


def inspire_records(recid, size=500):
    q = urllib.parse.urlencode({"q": f"authors.recid:{recid}", "size": size,
                                "sort": "mostrecent", "fields": FIELDS})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "bibutils/0.1"})
    hits = json.loads(urllib.request.urlopen(req, timeout=60).read())["hits"]["hits"]
    out = {}
    for h in hits:
        m = h["metadata"]
        ax = (m.get("arxiv_eprints") or [{}])[0].get("value")
        if not ax:
            continue
        pubs = [p for p in m.get("publication_info", []) if p.get("journal_title")]
        authors = m.get("authors", [])
        out[ax] = dict(title=m["titles"][0]["title"], date=m.get("earliest_date", ""),
                       first_author=authors[0]["full_name"] if authors else "",
                       n_authors=len(authors), journal=pubs[0] if pubs else None,
                       types=m.get("document_type", []))
    return out


def journal_ref(p):
    """INSPIRE publication_info -> 'JCAP 10 (2025) 004'."""
    if not p:
        return ""
    parts = [p.get("journal_title", ""), p.get("journal_volume", "")]
    if p.get("journal_issue"):
        parts.append(f"no. {p['journal_issue']}")
    parts.append(f"({p.get('year', '')})")
    parts.append(p.get("artid") or p.get("page_start", ""))
    return " ".join(x for x in map(str, parts) if x and x != "()")


def list_entries(tex_paths):
    """{arXiv id: (file, 'preprint'|'published', entry text)} from .tex files."""
    out = {}
    for path in tex_paths:
        text = open(path, encoding="utf-8").read()
        for chunk in re.split(r"\n(?=\\\w*entry)", text):
            if chunk.lstrip().startswith("%"):
                continue
            for ax in re.findall(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/\d{7})", chunk):
                state = "preprint" if PREPRINT.search(chunk) else "published"
                out[ax] = (path, state, " ".join(chunk.split())[:160])
    return out


def compare(recid, tex_paths):
    ins, cv = inspire_records(recid), list_entries(tex_paths)
    new = {a: r for a, r in ins.items() if a not in cv}
    now_published = {a: (cv[a], journal_ref(ins[a]["journal"])) for a in cv
                     if cv[a][1] == "preprint" and a in ins and ins[a]["journal"]}
    unknown = sorted(a for a in cv if a not in ins)
    return new, now_published, unknown


def main(recid, tex_paths):
    new, published, unknown = compare(recid, tex_paths)
    print(f"{len(new)} paper(s) on INSPIRE missing from the list:")
    for a, r in sorted(new.items(), key=lambda kv: kv[1]["date"], reverse=True):
        who = r["first_author"] + (" et al." if r["n_authors"] > 1 else "")
        print(f"  {r['date'][:10]}  {a:<11} {r['title'][:80]}  -- {who}")
    print(f"\n{len(published)} preprint(s) of the list now published:")
    for a, ((path, _, text), ref) in sorted(published.items()):
        print(f"  {a:<11} {ref:<32} {text[:70]}")
    print(f"\n{len(unknown)} arXiv id(s) of the list unknown to INSPIRE: {', '.join(unknown)}")
    return 0
