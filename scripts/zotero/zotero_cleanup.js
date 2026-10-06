// ---------------------------------------------------------------------------
// Leave only the new structure -- Corentin Ravoux
//
// Zotero: Tools > Developer > Run JavaScript, tick "Run as async function", Run.
// DRY_RUN is on: it reports and changes nothing until you set it to false.
//
// Three things, in this order:
//   1. file the ACCEL2 paper, which is cited in the HDR but sits in no
//      collection, into Simulations/Hydrodynamical and IGM
//   2. send to the TRASH the unfiled items that duplicate an item already
//      present in the new structure -- trash, not erase, so a mistake is
//      undoable from Zotero's own Trash
//   3. delete the empty legacy collections left behind by the reorganisation
//
// Not touched: two junk items ("Helium gas-bubble superlattice in copper and
// nickel", "Zotero | Connectors") and one arXiv page saved as a webpage
// ("[2004.10206] It's Dust ..."). Delete those by hand once you have looked
// at them -- they are not duplicates of anything, so no rule can decide.
// ---------------------------------------------------------------------------

const DRY_RUN = true;

const LIB = Zotero.Libraries.userLibraryID;
const out = [];
const TRASH = ["S7SJM2BE", "78YAJNMJ", "28UY5934", "EZZMGYPS", "S4SDF8DG", "QXW9DSCW", "QKYP62GF", "T6GUNFR4", "A3SMT386", "RCSZXZWV", "FVKZSKV5", "YCT99DPD", "EHMECJGA", "QD9DE469", "SEBHDYRW", "BKKB9D3A", "L6FESPZ4", "NAQM8W2X", "BWRMNR5V", "43W98PBA", "AG48RJLW", "JHFB6ICT", "6N5J3QB6", "CKJ6UUM9", "HPPEULNP", "DMTBPIMV", "5GBIQDIM", "U4KNPFRS", "JK6PCG4D", "QXXT49MM", "DWV4Z4MQ", "2XANCKT6", "YUY42ZMJ", "A6XK5YLI", "GW5AWAED", "FPT9CMLM", "SDHMMM52", "ZG8R9UJ6", "R94ENEIZ", "D88PUF4T", "8GIHPU7Q", "RJNA5T9W", "J7BS2X28", "ZEFCIMQG"];
const FILE_INTO = {"4YJ5TG5Y": "Simulations/Hydrodynamical and IGM"};
const LEGACY = ["21cm", "Auxtel", "Black Holes", "Books", "CMB", "Clustering", "DESI", "Dark Energy", "Dark Matter", "Dipole", "EFTofLSS", "Environment", "Euclid", "Forward Modeling", "GW", "LBG", "LSST", "Lazuli", "Lyman alpha", "Modified Gravity", "Neutrinos", "P1D", "Packages", "Peculiar Velocities", "Quasars", "Review", "SDSS", "Software", "Stars", "Structures", "Supernovae", "Thesis", "Tomography", "Voids", "Weak Lensing", "ZTF"];

function pathMap() {
  const all = Zotero.Collections.getByLibrary(LIB, true), byID = {}, map = {};
  all.forEach(c => byID[c.id] = c);
  for (const c of all) {
    let parts = [c.name], p = c.parentID;
    while (p) { parts.unshift(byID[p].name); p = byID[p].parentID; }
    map[parts.join("/")] = c;
  }
  return map;
}
const map = pathMap();

// 1 -------------------------------------------------------------- file it
let filed = 0;
for (const [key, path] of Object.entries(FILE_INTO)) {
  const id = Zotero.Items.getIDFromLibraryAndKey(LIB, key);
  if (!id) { out.push("missing item " + key); continue; }
  const item = Zotero.Items.get(id), target = map[path];
  if (!target) { out.push("missing collection " + path); continue; }
  if (item.getCollections().includes(target.id)) continue;
  out.push((DRY_RUN ? "would file  " : "filing      ") + item.getField("title").slice(0, 60)
           + "  ->  " + path);
  filed++;
  if (!DRY_RUN) { item.addToCollection(target.id); await item.saveTx(); }
}

// 2 ------------------------------------------------------------- trash it
let trashed = 0, absent = 0;
for (const key of TRASH) {
  const id = Zotero.Items.getIDFromLibraryAndKey(LIB, key);
  if (!id) { absent++; continue; }
  const item = Zotero.Items.get(id);
  if (item.deleted) { absent++; continue; }
  if (item.getCollections().length) {           // filed since this was generated
    out.push("SKIPPED, now in a collection: " + item.getField("title").slice(0, 60));
    continue;
  }
  trashed++;
  if (!DRY_RUN) { item.deleted = true; await item.saveTx(); }
}

// 3 ------------------------------------------------ drop the empty shells
let dropped = 0, kept = [];
for (const path of LEGACY) {
  const c = map[path];
  if (!c) continue;
  const nItems = c.getChildItems(true).length, nSubs = c.getChildCollections(true).length;
  if (nItems || nSubs) { kept.push(path + " (" + nItems + " items)"); continue; }
  dropped++;
  if (!DRY_RUN) await c.eraseTx();
}

out.push("");
out.push("filed into the new structure : " + filed);
out.push("unfiled duplicates trashed   : " + trashed + (absent ? "  (" + absent + " already gone)" : ""));
out.push("empty legacy collections gone: " + dropped);
if (kept.length) out.push("kept, not empty              : " + kept.join(", "));
out.push(DRY_RUN ? "\nDRY RUN -- nothing was written." : "\nApplied. Trashed items are in Zotero's Trash until you empty it.");
return out.join("\n");
