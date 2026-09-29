"""Cleaning must change the representation of a reference, never its content.

Offline and self-contained: a few Zotero-like items (the real cases that
motivated each cleaning step) are exported, then checked with the integrity
comparator, which must find no difference -- and must find one as soon as a
field is corrupted.
"""
import pytest

from bibutils import integrity, zotero

ITEMS = {
    "des_dark_2024": dict(
        type="preprint",
        fields={"title": "Dark Energy Survey: A 2.1% measurement of the angular Baryonic "
                         "Acoustic Oscillation scale at redshift $z_{\\rm eff}$=0.85",
                "date": "2024-02-16", "url": "http://arxiv.org/abs/2402.10696",
                "DOI": "10.48550/arXiv.2402.10696", "archiveID": "arXiv:2402.10696"},
        creators=[["author", "Abbott", "T. M. C.", 0]]),
    "act_dr6_2025": dict(
        type="journalArticle",
        fields={"title": "The Atacama Cosmology Telescope: DR6 Power Spectra, Likelihoods "
                         "and $\\Lambda$CDM Parameters",
                "publicationTitle": "arXiv:2503.14452 [astro-ph]", "date": "2025-03-18",
                "url": "http://arxiv.org/abs/2503.14452"},
        creators=[["author", "Louis", "Thibaut", 0]]),
    "almgren_nyx_2013": dict(
        type="journalArticle",
        fields={"title": "Nyx: A MASSIVELY PARALLEL AMR CODE FOR COMPUTATIONAL COSMOLOGY",
                "publicationTitle": "The Astrophysical Journal", "volume": "765",
                "pages": "39", "date": "2013-03-01", "DOI": "10.1088/0004-637X/765/1/39"},
        creators=[["author", "Almgren", "Ann S.", 0], ["author", "Lukić", "Zarija", 0]]),
    "radinovic_2022": dict(
        type="journalArticle",
        fields={"title": "Lyman-{\\alpha} forest & voids at z ~ 3: 50% of $\\sigma_8$",
                "publicationTitle": "Monthly Notices of the Royal Astronomical Society",
                "volume": "512", "issue": "1", "pages": "1-15", "date": "2022"},
        creators=[["author", "Radinović", "Slađana", 0], ["author", "DESI Collaboration", "", 1]]),
}


def export(items, tmp_path):
    zotero.ACRONYMS = {"AMR"}
    text = "\n\n".join(zotero.entry(v["type"], k, v["fields"],
                                    [tuple(c) for c in v["creators"]])
                       for k, v in items.items())
    path = tmp_path / "out.bib"
    path.write_text(text, encoding="utf-8")
    return path


def test_titles_are_written_as_latex(tmp_path):
    bib = integrity.read_bib(export(ITEMS, tmp_path))
    assert "{$z_{\\rm eff}$}=0.85" in bib["des_dark_2024"][1]["title"]
    assert "{$\\Lambda$}{CDM}" in bib["act_dr6_2025"][1]["title"]
    assert "\\textbackslash" not in "".join(f["title"] for _, f in bib.values())
    # all capitals -> title case, known acronym kept
    assert bib["almgren_nyx_2013"][1]["title"].startswith("{Nyx}: {A} {Massively} {Parallel} {AMR}")
    # greek command outside math is made safe; "&" and "%" still escaped
    assert "\\ensuremath{\\alpha}" in bib["radinovic_2022"][1]["title"]
    assert "\\&" in bib["radinovic_2022"][1]["title"]


def test_arxiv_id_becomes_eprint(tmp_path):
    bib = integrity.read_bib(export(ITEMS, tmp_path))
    assert bib["des_dark_2024"][1]["eprint"] == "2402.10696"
    assert bib["act_dr6_2025"][1]["eprint"] == "2503.14452"
    assert "journal" not in bib["act_dr6_2025"][1]      # was only the arXiv id
    assert "eprint" not in bib["almgren_nyx_2013"][1]


def test_cleaning_loses_no_information(tmp_path):
    bib, problems, intended = integrity.check(export(ITEMS, tmp_path), ITEMS)
    assert problems == []
    assert intended["eprint added"] == 2


@pytest.mark.parametrize("old, new", [
    ("volume = {765}", "volume = {766}"),                       # a digit
    ("0.85", "085"),                                             # a decimal point
    (" and Lukić, Zarija", ""),                                  # an author dropped
    ("eprint = {2402.10696}", "eprint = {2402.10697}"),          # a link
    ("{Massively}", "{Massive}"),                                # a word
])
def test_corruption_is_detected(tmp_path, old, new):
    path = export(ITEMS, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    _, problems, _ = integrity.check(path, ITEMS)
    assert problems, f"corruption {old!r} -> {new!r} went unnoticed"
