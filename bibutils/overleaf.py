"""Publish generated .bib files to an Overleaf git clone.

Copies <src_dir>/<prefix>_*.bib into the clone, merges Overleaf's latest
state first, commits only when a file actually changed, and pushes.

Authentication is git's own: store the Overleaf token once with a credential
helper scoped to git.overleaf.com, e.g.

    git config --global credential.https://git.overleaf.com.helper \
        "store --file ~/.config/git/credentials-overleaf"

This module never reads, prints or stores a token.
"""
import filecmp
import glob
import os
import shutil
import subprocess

OVERLEAF_URL = "https://git.overleaf.com"


class PushError(RuntimeError):
    pass


def _git(repo, *args, check=True, capture=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")   # fail, never prompt
    r = subprocess.run(["git", "-C", repo, *args], env=env, text=True,
                       capture_output=capture)
    if check and r.returncode != 0:
        raise PushError(f"git {' '.join(args)} failed"
                        + (f":\n{r.stderr}" if capture else ""))
    return r


def push_bib(src_dir, repo, prefix="bibli_hdr", branch="main",
             message="Update bibliography from Zotero export", dry_run=False):
    """Copy, commit and push; returns True if something was pushed."""
    say = lambda s: print(f"==> {s}")
    repo = os.path.expanduser(repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise PushError(f"{repo} is not a git repository")
    helper = subprocess.run(["git", "config", "--get-urlmatch", "credential.helper",
                             OVERLEAF_URL], capture_output=True, text=True)
    if helper.returncode != 0:
        raise PushError(f"no git credential helper for {OVERLEAF_URL} "
                        "(see bibutils.overleaf docstring)")
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(src_dir, f"{prefix}_*.bib")))
    if not files:
        raise PushError(f"no {prefix}_*.bib in {src_dir} -- build first")
    for f in files:
        if os.path.getsize(os.path.join(src_dir, f)) == 0:
            raise PushError(f"empty source file {f}")
    say(f"publishing {len(files)} file(s): {' '.join(files)}")

    # A dirty clone would sweep an unrelated edit into the commit.
    status = _git(repo, "status", "--porcelain", capture=True).stdout.splitlines()
    dirty = [line[3:] for line in status if line[3:] not in files]
    if dirty:
        raise PushError("uncommitted changes in the clone: " + ", ".join(dirty))

    say(f"fetching {branch} from Overleaf")
    _git(repo, "fetch", "origin", branch)
    count = lambda rng: int(_git(repo, "rev-list", "--count", rng, capture=True).stdout)
    behind, ahead = count(f"HEAD..origin/{branch}"), count(f"origin/{branch}..HEAD")
    say(f"local is {ahead} ahead, {behind} behind origin/{branch}")
    if behind:
        if dry_run:
            say(f"dry run: would merge origin/{branch}")
        elif _git(repo, "-c", "pull.rebase=false", "merge", "--no-edit",
                  f"origin/{branch}", check=False).returncode:
            _git(repo, "merge", "--abort", check=False)
            raise PushError(f"merge conflict with Overleaf; resolve by hand in {repo}")

    changed = []
    for f in files:
        dst = os.path.join(repo, f)
        if os.path.exists(dst) and filecmp.cmp(os.path.join(src_dir, f), dst, shallow=False):
            say(f"{f} unchanged")
            continue
        say(f"updating {f}")
        changed.append(f)
        if not dry_run:
            shutil.copyfile(os.path.join(src_dir, f), dst)
    if not changed and not ahead:
        say("nothing to do")
        return False
    if dry_run:
        say("dry run: stopping before commit and push")
        return False
    if changed:
        _git(repo, "add", "--", *changed)
        if _git(repo, "diff", "--cached", "--quiet", check=False).returncode:
            _git(repo, "commit", "-m", message)
    say("pushing to Overleaf")
    _git(repo, "push", "origin", branch)
    say("done")
    return True
