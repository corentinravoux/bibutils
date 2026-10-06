// ---------------------------------------------------------------------------
// Export the whole Zotero library to one BibTeX file -- Corentin Ravoux
//
// Zotero: Tools > Developer > Run JavaScript, tick "Run as async function", Run.
//
// One translator call for the entire library instead of one per collection:
// a few seconds rather than a few minutes, and it no longer depends on the
// collection structure at all, so reorganising collections cannot break it.
//
// Splitting into the three bibli_hdr_*.bib files is done afterwards by
// create_bib_hdr.py, which is where every other transformation already lives.
//
// Then, in a terminal:
//     cd ~/Documents/Biblio/bib_files && python3 create_bib_hdr.py
// or just:   ~/Documents/Biblio/bib_update.sh
// ---------------------------------------------------------------------------

const OUT    = "/home/ravoux/Documents/Biblio/bib_files/zotero_library.bib";
const BIBTEX = "9cb70025-a888-4a29-a210-93ec52da40d4";

const t0 = Date.now();
const items = (await Zotero.Items.getAll(Zotero.Libraries.userLibraryID, true))
                .filter(i => i.isRegularItem());

const tr = new Zotero.Translate.Export();
tr.setItems(items);
tr.setLocation(Zotero.File.pathToFile(OUT));
tr.setTranslator(BIBTEX);
tr.setDisplayOptions({ exportNotes: false, exportFileData: false,
                       useJournalAbbreviation: false });
await tr.translate();

return "exported " + items.length + " items in "
     + ((Date.now() - t0) / 1000).toFixed(1) + " s\n" + OUT;
