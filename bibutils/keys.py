"""Citation-key registry: one stable, unique key per Zotero item.

Zotero allocates keys per export file, so two different papers can receive
the same key in two collections, and a merged bibliography has to drop one
of them. The registry removes that failure mode for good:

  - an item that has a key keeps it, whatever later happens to its date or
    title (the manuscript cites the key, not the metadata);
  - a new item gets the key of the Zotero pattern, or the first free "-1",
    "-2", ... suffix if that key is, or ever was, used by another item --
    a key is never reused for a different paper;
  - a new item that is the same paper (same DOI or arXiv id) as an item that
    is no longer exported -- a re-import replacing an old record -- inherits
    its key, so citations keep working across the replacement;
  - a key pinned in Zotero (citationKey field, or "Citation Key:" in Extra)
    always wins.

The registry is a JSON file keyed by Zotero's own item key (8 characters,
stable for the life of the item). Retired entries are kept for ever: they
are what lets a successor inherit a key, and what stops a key being reused.
"""
import json
import os
import re

from . import zotero as z

VERSION = 1


def _norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def identity(flds, creators):
    """What identifies the paper of an item, independently of Zotero."""
    doi = (flds.get("DOI") or "").strip().lower()
    arxiv = z.arxiv_id(flds)
    if doi.startswith("10.48550/arxiv."):
        arxiv, doi = arxiv or doi.split("arxiv.", 1)[1], ""
    first = next((c[1] for c in creators if c[0] == "author"), None) or \
        (creators[0][1] if creators else "")
    return dict(doi=doi, arxiv=arxiv or "", title=_norm_title(flds.get("title")),
                author=_norm_title(first))


def load(path):
    if path and os.path.exists(path):
        reg = json.load(open(path, encoding="utf-8"))
        if reg.get("version") != VERSION:
            raise SystemExit(f"error: {path}: unknown registry version")
        return reg
    return {"version": VERSION, "entries": {}}


def save(reg, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)            # never leave a half-written registry


def _author(creators):
    return next((c[1] for c in creators if c[0] == "author"), None) or \
        (creators[0][1] if creators else None)


def exported_rows(lib):
    """(itemID, itemKey, dateAdded, type) of every item in some collection."""
    memb = lib.membership()
    return [r for r in sorted(lib.items(), key=lambda r: r[0]) if memb.get(r[0])]


def assign(lib, reg):
    """{itemID: key} for every exported item; updates reg in place.

    Returns (keys, events): events lists what this run decided, for the report
    ("new", "inherited", "pinned", "retired").
    """
    entries = reg["entries"]
    used = {e["key"] for e in entries.values()}
    rows = exported_rows(lib)
    exported = {ikey for _, ikey, _, _ in rows}
    retired = {zk: e for zk, e in entries.items() if zk not in exported}
    taken_by_successor = set()
    keys, events, active = {}, [], {}
    for iid, ikey, added, typ in rows:
        flds, crs = lib.fields(iid), lib.creators(iid)
        ident = identity(flds, crs)
        pinned = z.item_key(flds, None, added, set()) if (
            flds.get("citationKey") or re.search(r"(?im)^\s*citation key\s*:", flds.get("extra") or "")
        ) else None
        if pinned:
            key = pinned
            if entries.get(ikey, {}).get("key") != key:
                events.append(("pinned", key, flds.get("title", "")))
        elif ikey in entries:
            key = entries[ikey]["key"]
        else:
            heirs = [zk for zk, e in retired.items() if zk not in taken_by_successor and (
                (ident["doi"] and e.get("doi") == ident["doi"]) or
                (ident["arxiv"] and e.get("arxiv") == ident["arxiv"]))]
            if len(heirs) == 1:
                key = retired[heirs[0]]["key"]
                taken_by_successor.add(heirs[0])
                entries[heirs[0]]["successor"] = ikey
                events.append(("inherited", key, flds.get("title", "")))
            else:
                base = z.cite_key(_author(crs), flds.get("title", ""), flds.get("date", ""),
                                  added, set())
                key, i = base, 0
                while key in used:
                    i += 1
                    key = f"{base}-{i}"
                events.append(("new", key, flds.get("title", "")))
        if key in active:
            raise SystemExit(f"error: key {key!r} pinned on two items "
                             f"({active[key]} and {ikey}); fix one in Zotero")
        active[key] = ikey
        used.add(key)
        keys[iid] = key
        entries[ikey] = dict(key=key, status="active", **ident)
    for zk, e in retired.items():
        if e.get("status") == "active":
            e["status"] = "retired"
            events.append(("retired", e["key"], ""))
    return keys, events


def seed(lib, reg, status="active"):
    """Record the keys the legacy per-collection export gives today.

    Used once, to start a registry without moving any existing key: for each
    key the first collection file (sorted) holding it wins, exactly as the
    merged bibliography did. Items not yet registered are added; keys already
    in the registry are never taken twice.
    """
    paths, memb = lib.collections(), lib.membership()
    rows = sorted(lib.items(), key=lambda r: r[0])
    byname = {}
    for cid, path in paths.items():
        sel = [r for r in rows if cid in memb.get(r[0], [])]
        if sel:
            byname[path.replace("/", "_").replace(":", "-") + ".bib"] = sel
    used = {e["key"] for e in reg["entries"].values()}
    added = 0
    for name in sorted(byname):
        per = set()
        for iid, ikey, date_added, typ in byname[name]:
            flds, crs = lib.fields(iid), lib.creators(iid)
            key = z.item_key(flds, _author(crs), date_added, per)
            if ikey in reg["entries"] or key in used:
                continue
            reg["entries"][ikey] = dict(key=key, status=status, **identity(flds, crs))
            used.add(key)
            added += 1
    return added
