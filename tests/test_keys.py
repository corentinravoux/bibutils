"""Adding, replacing or editing a Zotero entry must never break a citation."""
import pytest

from bibutils import keys


class FakeLibrary:
    """The four calls keys.assign makes on a Zotero library."""

    def __init__(self):
        self.rows, self.flds, self.crs, self.memb = [], {}, {}, {}

    def add(self, iid, zkey, title, date, author, doi="", coll=(1,)):
        self.rows.append((iid, zkey, "2024-01-01 00:00:00", "journalArticle"))
        self.flds[iid] = {"title": title, "date": date, "DOI": doi}
        self.crs[iid] = [("author", author, "A.", 0)]
        self.memb[iid] = list(coll)

    def items(self):
        return self.rows

    def collections(self):
        return {1: "Probes/CMB", 2: "Probes/Clusters"}

    def membership(self):
        return {i: c for i, c in self.memb.items() if c}

    def fields(self, iid):
        return self.flds[iid]

    def creators(self, iid):
        return self.crs[iid]


def library():
    lib = FakeLibrary()
    lib.add(1, "AAAA1111", "Planck 2015 results. XVI. Isotropy", "2016", "Collaboration", "10.1/xvi")
    lib.add(2, "BBBB2222", "Planck 2015 results. XXIV. Clusters", "2015", "Collaboration",
            "10.1/xxiv", coll=(2,))
    return lib


def first_run(lib):
    reg = keys.load(None)
    keys.seed(lib, reg)
    return reg, keys.assign(lib, reg)[0]


def test_existing_keys_are_recorded_unchanged():
    lib = library()
    reg, k = first_run(lib)
    assert k == {1: "collaboration_planck_2016", 2: "collaboration_planck_2015"}


def test_new_entry_that_collides_gets_its_own_key():
    lib = library()
    reg, before = first_run(lib)
    lib.add(3, "CCCC3333", "Planck 2015 results. XIII. Parameters", "2016", "Collaboration", "10.1/xiii")
    k, events, _ = keys.assign(lib, reg)
    assert k[1] == before[1]                            # the cited key did not move
    assert k[3] == "collaboration_planck_2016-1"        # and the newcomer is not dropped
    assert len(set(k.values())) == len(k)
    assert ("new", "collaboration_planck_2016-1", lib.flds[3]["title"]) in events


def test_reimported_paper_inherits_the_old_key():
    lib = library()
    reg, before = first_run(lib)
    lib.memb[2] = []                                    # old record taken out of its collection
    lib.add(4, "DDDD4444", "Planck 2015 results. XXIV. Clusters", "2016", "Collaboration",
            "10.1/XXIV", coll=(2,))                     # journal version, same DOI, now 2016
    k, events, _ = keys.assign(lib, reg)
    assert k[4] == before[2] == "collaboration_planck_2015"
    assert 2 not in k


def test_editing_the_date_keeps_the_key():
    lib = library()
    reg, before = first_run(lib)
    lib.flds[2]["date"] = "2016-10"
    assert keys.assign(lib, reg)[0][2] == before[2]


def test_a_retired_key_is_never_given_to_another_paper():
    lib = library()
    reg, before = first_run(lib)
    lib.memb[2] = []                                    # retired, and no successor
    lib.add(5, "EEEE5555", "Planck 2015 results. XXV. Other", "2015", "Collaboration", "10.1/xxv")
    k, _, _ = keys.assign(lib, reg)
    assert k[5] != "collaboration_planck_2015"


def test_pinned_key_wins_and_a_duplicate_pin_is_refused():
    lib = library()
    reg, _ = first_run(lib)
    lib.flds[1]["citationKey"] = "planck_xvi"
    assert keys.assign(lib, reg)[0][1] == "planck_xvi"
    lib.flds[2]["citationKey"] = "planck_xvi"
    with pytest.raises(SystemExit):
        keys.assign(lib, reg)


def test_merged_duplicate_reports_the_key_to_cite_instead():
    lib = library()
    lib.add(6, "FFFF6666", "Planck 2015 results. XVI. Isotropy", "2016", "Collaboration", "10.1/xvi")
    reg, k = first_run(lib)                             # twin gets collaboration_planck_2016-1
    lib.memb[1] = []                                    # the cited record is merged away
    k, events, replaced = keys.assign(lib, reg)
    assert replaced == {"collaboration_planck_2016": 6} # reported, with its replacement
    assert "collaboration_planck_2016" not in k.values()  # but no longer exported
    assert k[6] == "collaboration_planck_2016-1"        # and no key moved
