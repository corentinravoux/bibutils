// Rejoin collaboration / team names that Zotero split like a person's name
// ("Collaboration, DESI" -> single-field "DESI Collaboration"), case by case.
//
// Run in Zotero: Tools > Developer > Run JavaScript, tick "Run as async function".
//   1. Run as is (APPLY = false): nothing is changed, the list of changes is printed.
//   2. Set APPLY = true and run again to save them.
// An entry is changed only if the author at that position still has exactly
// the name listed below; anything else is skipped and reported.
// Generated 2026-09-30 for this library; not a general tool.

const APPLY = false;

const CHANGES = [
 {
  "key": "STJVQZCS",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "C. M. S.",
  "name": "CMS Collaboration",
  "title": "Dark sector searches with the CMS experiment"
 },
 {
  "key": "2CP7J2BZ",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "CHIME",
  "name": "CHIME Collaboration",
  "title": "Detection of the Cosmological 21 cm Signal in Auto-corr"
 },
 {
  "key": "7U3QGQZ5",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "D. E. S.",
  "name": "DES Collaboration",
  "title": "Dark Energy Survey Year 6 Results: Cosmological Constra"
 },
 {
  "key": "ETKL3WYD",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "D. E. S.",
  "name": "DES Collaboration",
  "title": "Dark Energy Survey Year 6 Results: Cosmological Constra"
 },
 {
  "key": "IAU3SK5Q",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "D. E. S.",
  "name": "DES Collaboration",
  "title": "Dark Energy Survey Year 6 Results: Cosmological Constra"
 },
 {
  "key": "CC2F68MC",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "D. E. S.",
  "name": "DES Collaboration",
  "title": "Constraints on Dynamical Dark Energy from Multiple Prob"
 },
 {
  "key": "X8FNURAU",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "D. E. S.",
  "name": "DES Collaboration",
  "title": "Dark Energy Survey Year 6 Results: Cosmological Constra"
 },
 {
  "key": "KI3QZSEE",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI DR2 Results II: Measurements of Baryon Acoustic Os"
 },
 {
  "key": "7ZAS3W3V",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI DR2 Results I: Baryon Acoustic Oscillations from t"
 },
 {
  "key": "8L3VCKT9",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI 2024 VII: Cosmological Constraints from the Full-S"
 },
 {
  "key": "BH8NSHQA",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI 2024 IV: Baryon Acoustic Oscillations from the Lym"
 },
 {
  "key": "47J6HIM8",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI 2024 III: Baryon Acoustic Oscillations from Galaxi"
 },
 {
  "key": "BSDIVB5A",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI 2024 II: Sample Definitions, Characteristics, and "
 },
 {
  "key": "VB9NNUMB",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "Data Release 1 of the Dark Energy Spectroscopic Instrum"
 },
 {
  "key": "RY78A76M",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI 2024 VI: Cosmological Constraints from the Measure"
 },
 {
  "key": "H7AJZBEX",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "Data Release 1 of the Dark Energy Spectroscopic Instrum"
 },
 {
  "key": "H57YZ4MM",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI DR2 Results IV: Alcock-Paczyński Measurements from"
 },
 {
  "key": "9LGCLMRI",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "DESI",
  "name": "DESI Collaboration",
  "title": "DESI DR2 Results IV: Alcock-Paczyński Measurements from"
 },
 {
  "key": "MYHGETCQ",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Gaia",
  "name": "Gaia Collaboration",
  "title": "Gaia Data Release 2: Variable stars in the colour-absol"
 },
 {
  "key": "FCJ78SX5",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Gaia",
  "name": "Gaia Collaboration",
  "title": "Gaia Data Release 2. Summary of the contents and survey"
 },
 {
  "key": "T7REYKHW",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "H0DN",
  "name": "H0DN Collaboration",
  "title": "The Local Distance Network: a community consensus repor"
 },
 {
  "key": "JR5ATEM3",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "H0DN",
  "name": "H0DN Collaboration",
  "title": "The Local Distance Network: a community consensus repor"
 },
 {
  "key": "63UFQJTR",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "LSST Dark Energy Science",
  "name": "LSST Dark Energy Science Collaboration",
  "title": "The LSST DESC DC2 Simulated Sky Survey"
 },
 {
  "key": "SVNPS9E5",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2018 results. VIII. Gravitational lensing"
 },
 {
  "key": "357IBWGU",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2015 results. XXIV. Cosmology from Sunyaev-Zeldo"
 },
 {
  "key": "PE96JHXR",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2013 results. XXVII. Doppler boosting of the CMB"
 },
 {
  "key": "33JJE5PK",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2015 results. XVI. Isotropy and statistics of th"
 },
 {
  "key": "7GIMGLVZ",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2018 results. VII. Isotropy and Statistics of th"
 },
 {
  "key": "T7MNIKFK",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck intermediate results. LIII. Detection of velocit"
 },
 {
  "key": "YCDA3BFE",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2015 results. XIII. Cosmological parameters"
 },
 {
  "key": "URFKUMIN",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "Planck",
  "name": "Planck Collaboration",
  "title": "Planck 2015 results. XXIV. Cosmology from Sunyaev-Zeldo"
 },
 {
  "key": "T5PYJXL6",
  "index": 6,
  "oldLast": "Collaboration",
  "oldFirst": "The Dark Energy Science",
  "name": "The Dark Energy Science Collaboration",
  "title": "The shape of the Photon Transfer Curve of CCD sensors"
 },
 {
  "key": "344QXGKM",
  "index": 6,
  "oldLast": "Collaboration",
  "oldFirst": "The Dark Energy Science",
  "name": "The Dark Energy Science Collaboration",
  "title": "The shape of the Photon Transfer Curve of CCD sensors"
 },
 {
  "key": "J2H28Y8P",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "The Dark Energy Survey",
  "name": "The Dark Energy Survey Collaboration",
  "title": "The Dark Energy Survey: Cosmology Results With ~1500 Ne"
 },
 {
  "key": "EDYMMMSU",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "The LIGO Scientific",
  "name": "The LIGO Scientific Collaboration",
  "title": "GWTC-4.0: Constraints on the Cosmic Expansion Rate and "
 },
 {
  "key": "TQB39BUA",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "The LIGO Scientific",
  "name": "The LIGO Scientific Collaboration",
  "title": "GW170817: Observation of Gravitational Waves from a Bin"
 },
 {
  "key": "B6J2TVPN",
  "index": 4,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "Using Host Galaxy Photometric Redshifts to Improve Cosm"
 },
 {
  "key": "EYYY9RX8",
  "index": 11,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "A Fully Photometric Approach to Type Ia Supernova Cosmo"
 },
 {
  "key": "E6W36KRS",
  "index": 10,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "Forecast for growth-rate measurement using peculiar vel"
 },
 {
  "key": "JQADUQ84",
  "index": 11,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "Type Ia supernova growth-rate measurement with LSST sim"
 },
 {
  "key": "KMYREAU9",
  "index": 11,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "Slitless spectrophotometry with forward modelling: prin"
 },
 {
  "key": "XJR5RZDI",
  "index": 11,
  "oldLast": "Collaboration",
  "oldFirst": "The LSST Dark Energy Science",
  "name": "The LSST Dark Energy Science Collaboration",
  "title": "Type Ia supernova growth-rate measurement with LSST sim"
 },
 {
  "key": "8QH3MYJZ",
  "index": 0,
  "oldLast": "Collaboration",
  "oldFirst": "The Simons Observatory",
  "name": "The Simons Observatory Collaboration",
  "title": "The Simons Observatory: Science goals and forecasts"
 },
 {
  "key": "TQB39BUA",
  "index": 1,
  "oldLast": "Collaboration",
  "oldFirst": "The Virgo",
  "name": "The Virgo Collaboration",
  "title": "GW170817: Observation of Gravitational Waves from a Bin"
 },
 {
  "key": "5LW9ZK5F",
  "index": 14,
  "oldLast": "Collaboration",
  "oldFirst": "The WEAVE",
  "name": "The WEAVE Collaboration",
  "title": "WEAVE-QSO: A Massive Intergalactic Medium Survey for th"
 },
 {
  "key": "TWRSUP59",
  "index": 70,
  "oldLast": "Collaboration",
  "oldFirst": "the DES",
  "name": "the DES Collaboration",
  "title": "Discovery of a Candidate Binary Supermassive Black Hole"
 },
 {
  "key": "EDYMMMSU",
  "index": 2,
  "oldLast": "Collaboration",
  "oldFirst": "the KAGRA",
  "name": "the KAGRA Collaboration",
  "title": "GWTC-4.0: Constraints on the Cosmic Expansion Rate and "
 },
 {
  "key": "4SGCMZSB",
  "index": 10,
  "oldLast": "Collaboration",
  "oldFirst": "the LSST Dark Energy Science",
  "name": "the LSST Dark Energy Science Collaboration",
  "title": "Designing an Optimal LSST Deep Drilling Program for Cos"
 },
 {
  "key": "NJHYNG9N",
  "index": 24,
  "oldLast": "Collaboration",
  "oldFirst": "the LSST Dark Energy Science",
  "name": "the LSST Dark Energy Science Collaboration",
  "title": "A Joint Roman Space Telescope and Rubin Observatory Syn"
 },
 {
  "key": "RKZ3DSXS",
  "index": 13,
  "oldLast": "Collaboration",
  "oldFirst": "the LSST Dark Energy Science",
  "name": "the LSST Dark Energy Science Collaboration",
  "title": "Probing Physics Beyond the Standard Model through Combi"
 },
 {
  "key": "RQ6JBTSL",
  "index": 6,
  "oldLast": "Collaboration",
  "oldFirst": "the LSST Dark Energy Science",
  "name": "the LSST Dark Energy Science Collaboration",
  "title": "A Cohesive Deep Drilling Field Strategy for LSST Cosmol"
 },
 {
  "key": "D6B66G9J",
  "index": 20,
  "oldLast": "Collaboration",
  "oldFirst": "the LSST Dark Energy Science",
  "name": "the LSST Dark Energy Science Collaboration",
  "title": "StarDICE III: Characterization of the photometric instr"
 },
 {
  "key": "EDYMMMSU",
  "index": 1,
  "oldLast": "Collaboration",
  "oldFirst": "the Virgo",
  "name": "the Virgo Collaboration",
  "title": "GWTC-4.0: Constraints on the Cosmic Expansion Rate and "
 },
 {
  "key": "A3PNRUPM",
  "index": 0,
  "oldLast": "DESC)",
  "oldFirst": "The LSST Dark Energy Science Collaboration (LSST",
  "name": "The LSST Dark Energy Science Collaboration (LSST DESC)",
  "title": "The LSST DESC DC2 Simulated Sky Survey"
 },
 {
  "key": "YUFWU22J",
  "index": 0,
  "oldLast": "Planck",
  "oldFirst": "Collaboration",
  "name": "Planck Collaboration",
  "title": "Planck intermediate results. XIII. Constraints on pecul"
 },
 {
  "key": "GF5I36N9",
  "index": 15,
  "oldLast": "Team",
  "oldFirst": "The Roman Supernova Cosmology Project Infrastructure",
  "name": "The Roman Supernova Cosmology Project Infrastructure Team",
  "title": "Calibration-Induced Systematics in SALT3 Training and T"
 },
 {
  "key": "HS3Z4N6M",
  "index": 53,
  "oldLast": "Team",
  "oldFirst": "the Lazuli Science",
  "name": "the Lazuli Science Team",
  "title": "The Lazuli Space Observatory: Architecture & Capabiliti"
 },
 {
  "key": "QW9JGH8P",
  "index": 25,
  "oldLast": "Team",
  "oldFirst": "the MSE Science",
  "name": "the MSE Science Team",
  "title": "The Maunakea Spectroscopic Explorer"
 }
];

const lib = Zotero.Libraries.userLibraryID;
const out = [];
let saved = 0, skipped = 0;
for (const c of CHANGES) {
  const item = Zotero.Items.getByLibraryAndKey(lib, c.key);
  if (!item) { out.push(`SKIP  ${c.key}: item not found`); skipped++; continue; }
  const cr = item.getCreator(c.index);
  if (!cr || cr.lastName !== c.oldLast || cr.firstName !== c.oldFirst) {
    out.push(`SKIP  ${c.key}#${c.index}: expected "${c.oldLast}, ${c.oldFirst}", found "${cr ? cr.lastName + ", " + cr.firstName : "none"}"`);
    skipped++; continue;
  }
  out.push(`${APPLY ? "SAVE " : "would"} ${c.key}#${c.index}: "${c.oldLast}, ${c.oldFirst}" -> "${c.name}"   [${c.title}]`);
  if (APPLY) {
    item.setCreator(c.index, { lastName: c.name, firstName: "", fieldMode: 1,
                                creatorTypeID: cr.creatorTypeID });
    await item.saveTx();
    saved++;
  }
}
return out.join("\n") + `\n\n${APPLY ? saved + " saved" : "dry run, nothing saved"}, ${skipped} skipped`;
