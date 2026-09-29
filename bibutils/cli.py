"""Command line: bibutils <command> ...  (and bib-hdr = bibutils run hdr)."""
import argparse
import os
import re
import sys

from . import build as _build
from . import config
from . import zotero as _zotero

USAGE = """bibutils <command> [options]

  run PROFILE     export + build + integrity check [+ --push] for one project
  export          Zotero database -> one .bib per collection
  build           per-collection .bib -> <prefix>_*.bib
  verify BIB      compare BIB with the Zotero database [--online: check links]
  push            copy <prefix>_*.bib into an Overleaf clone, commit, push
  publist         compare a LaTeX publication list with INSPIRE-HEP
  keys-seed       record the keys an older database gave, as retired keys

`bibutils <command> -h` for the options of one command.
Profiles live in ~/.config/bibutils/config.toml (see config.example.toml).
"""


def cited_keys(root):
    """Every key cited by a .tex file under root (\\cite, \\citep, ...)."""
    keys = set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".tex"):
                text = open(os.path.join(dirpath, f), encoding="utf-8", errors="replace").read()
                for group in re.findall(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", text):
                    keys |= {k.strip() for k in group.split(",") if k.strip()}
    return keys


def cmd_verify(argv):
    from . import integrity
    ap = argparse.ArgumentParser(prog="bibutils verify")
    ap.add_argument("bib")
    ap.add_argument("-d", "--database", default=_zotero.DB)
    ap.add_argument("--online", action="store_true",
                    help="also look every arXiv id and DOI up online")
    ap.add_argument("--cache", help="directory for the online lookups (JSON)")
    ap.add_argument("--cited", help="LaTeX project directory: flag the cited entries")
    ap.add_argument("--keys", help="citation-key registry used by the export")
    a = ap.parse_args(argv)
    from . import keys as _keys
    items, clashes = integrity.zotero_items(a.database, _keys.load(a.keys) if a.keys else None)
    verified = None
    if a.online:
        from . import links
        found = links.check_links(items, a.cache, cited_keys(a.cited) if a.cited else None)
        links.print_links(found)
        verified = found["verified_arxiv"]
    if clashes:
        print(f"\n{len(clashes)} key(s) held by two different Zotero items (one is dropped):")
        for c in clashes:
            print(f"  {c['key']}\n    kept   : {c['kept'][0]} :: {c['kept'][1][:70]}"
                  f"\n    dropped: {c['dropped'][0]} :: {c['dropped'][1][:70]}")
    print()
    bib, problems, intended = integrity.check(a.bib, items, verified)
    integrity.print_report(bib, problems, intended)
    return 1 if problems else 0


def cmd_push(argv):
    from . import overleaf
    ap = argparse.ArgumentParser(prog="bibutils push")
    ap.add_argument("src_dir")
    ap.add_argument("repo")
    ap.add_argument("--prefix", default="bibli_hdr")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        overleaf.push_bib(a.src_dir, a.repo, a.prefix, a.branch, dry_run=a.dry_run)
    except overleaf.PushError as e:
        sys.exit(f"error: {e}")
    return 0


def cmd_publist(argv):
    from . import publist
    ap = argparse.ArgumentParser(prog="bibutils publist")
    ap.add_argument("recid", help="INSPIRE author record id")
    ap.add_argument("tex", nargs="+", help=".tex files of the publication list")
    a = ap.parse_args(argv)
    return publist.main(a.recid, a.tex)


def cmd_keys_seed(argv):
    from . import keys, zotero
    ap = argparse.ArgumentParser(
        prog="bibutils keys-seed",
        description="Record the keys an older Zotero database gave (a backup), so that "
                    "a re-imported paper can inherit its old key and no key is reused.")
    ap.add_argument("registry")
    ap.add_argument("database", help="zotero.sqlite to read the keys from (e.g. a backup)")
    ap.add_argument("--status", choices=("active", "retired"), default="retired",
                    help="active: today's library, recorded first; retired: history")
    a = ap.parse_args(argv)
    reg = keys.load(a.registry)
    n = keys.seed(zotero.Library(a.database), reg, status=a.status)
    keys.save(reg, a.registry)
    print(f"{n} key(s) from {a.database} recorded as {a.status}")
    return 0


def cmd_run(argv, profile_name=None):
    ap = argparse.ArgumentParser(
        prog="bib-hdr" if profile_name else "bibutils run",
        description="Zotero -> <prefix>_*.bib [-> Overleaf] for one configured project. "
                    "Every cleaning step can be switched off with --no-<step>.")
    if not profile_name:
        ap.add_argument("profile")
    ap.add_argument("--push", action="store_true", help="push to the Overleaf clone")
    ap.add_argument("--dry-run", action="store_true", help="with --push: stop before committing")
    ap.add_argument("--no-export", action="store_true", help="rebuild from the exports on disk")
    ap.add_argument("--no-verify", action="store_true", help="skip the integrity check")
    for step in list(_zotero.OPTIONS) + list(_build.CLEANING):
        ap.add_argument(f"--no-{step}", dest="off", action="append_const", const=step)
    a = ap.parse_args(argv)
    p = config.profile(profile_name or a.profile)
    off = set(p["disable"]) | set(a.off or [])
    db = p.get("database") or _zotero.DB
    say = lambda s: print(f"\n==> {s}")

    if not a.no_export:
        say("exporting Zotero")
        _zotero.main(["-d", db, "-o", p["export_dir"], "--keys", p["keys_file"]]
                     + [f"--no-{s}" for s in _zotero.OPTIONS if s in off])
    say("building")
    _build.build(p["export_dir"], p["out_dir"], p["prefix"], p["chunks"],
                 [s for s in _build.CLEANING if s in off])
    if not a.no_verify and p["chunks"] == 1:
        from . import integrity, keys as _keys
        say("integrity check against Zotero")
        items, _ = integrity.zotero_items(db, _keys.load(p["keys_file"]))
        bib, problems, intended = integrity.check(
            os.path.join(p["out_dir"], f"{p['prefix']}_0.bib"), items)
        integrity.print_report(bib, problems, intended)
        if problems:
            sys.exit("error: the build altered information (above); not pushed")
    if p.get("overleaf_repo"):
        from .integrity import read_bib
        built = set()
        for i in range(p["chunks"]):
            built |= set(read_bib(os.path.join(p["out_dir"], f"{p['prefix']}_{i}.bib")))
        missing = sorted(cited_keys(p["overleaf_repo"]) - built)
        say(f"cited keys: {len(cited_keys(p['overleaf_repo']))}, missing from the bib: {len(missing)}")
        for k in missing:
            print(f"  \\cite{{{k}}} has no entry")
        if missing and a.push:
            sys.exit("error: the manuscript cites keys the bibliography lacks; not pushed")
    if a.push:
        from . import overleaf
        if not p.get("overleaf_repo"):
            sys.exit("error: profile has no overleaf_repo")
        say("pushing to Overleaf")
        try:
            overleaf.push_bib(p["out_dir"], p["overleaf_repo"], p["prefix"], p["branch"],
                              p["commit_message"], dry_run=a.dry_run)
        except overleaf.PushError as e:
            sys.exit(f"error: {e}")
    else:
        say("not pushed -- rerun with --push")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    table = {"export": _zotero.main, "build": _build.main, "verify": cmd_verify,
             "push": cmd_push, "publist": cmd_publist, "run": cmd_run,
             "keys-seed": cmd_keys_seed}
    if cmd not in table:
        sys.exit(f"unknown command '{cmd}'\n\n{USAGE}")
    return table[cmd](rest) or 0


def hdr(argv=None):
    """bib-hdr: the HDR manuscript profile."""
    return cmd_run(sys.argv[1:] if argv is None else argv, profile_name="hdr") or 0
