"""bibutils -- Zotero to BibTeX to Overleaf, with checks that nothing is lost.

    bibutils.zotero     read zotero.sqlite, export .bib (Zotero-compatible keys)
    bibutils.build      merge exports into a project bibliography, cleaning steps
    bibutils.integrity  prove the cleaned .bib still says what Zotero says
    bibutils.links      check every arXiv id and DOI online
    bibutils.overleaf   publish to an Overleaf git clone
    bibutils.publist    compare a LaTeX publication list with INSPIRE-HEP
"""
__version__ = "0.1.0"
