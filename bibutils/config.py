"""Per-user configuration: one profile per LaTeX/Overleaf project.

Read from $BIBUTILS_CONFIG or ~/.config/bibutils/config.toml. Nothing
machine-specific lives in the package itself; see config.example.toml.

    [zotero]
    database = "~/Zotero/zotero.sqlite"

    [profile.hdr]
    export_dir    = "~/Documents/Biblio/bib_files"      # per-collection exports
    out_dir       = "~/Documents/Biblio/bib_files/out"  # built <prefix>_*.bib
    prefix        = "bibli_hdr"
    chunks        = 1
    overleaf_repo = "~/Software/overleaf/<project-id>"
    branch        = "main"
    disable       = []          # cleaning steps to switch off
"""
import os
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:                                   # pragma: no cover
    import tomli as tomllib

DEFAULT_PATH = "~/.config/bibutils/config.toml"
PROFILE_DEFAULTS = dict(prefix="bibli", chunks=1, branch="main", disable=[],
                        commit_message="Update bibliography from Zotero export")
PATH_KEYS = ("export_dir", "out_dir", "overleaf_repo", "database")


def config_path():
    return os.path.expanduser(os.environ.get("BIBUTILS_CONFIG", DEFAULT_PATH))


def load():
    path = config_path()
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def profile(name):
    """A profile with defaults filled in and every path expanded."""
    cfg = load()
    profiles = cfg.get("profile", {})
    if name not in profiles:
        known = ", ".join(sorted(profiles)) or "none"
        raise SystemExit(f"error: no profile '{name}' in {config_path()} (known: {known})")
    p = dict(PROFILE_DEFAULTS, **profiles[name])
    p.setdefault("database", cfg.get("zotero", {}).get("database"))
    for k in PATH_KEYS:
        if p.get(k):
            p[k] = os.path.expanduser(p[k])
    missing = [k for k in ("export_dir", "out_dir") if not p.get(k)]
    if missing:
        raise SystemExit(f"error: profile '{name}' lacks {', '.join(missing)}")
    return p
