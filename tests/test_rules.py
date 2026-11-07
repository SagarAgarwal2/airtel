"""Unit tests for identifiers, eligibility and pricing. Run: python -m pytest -q"""
from backend import data, rules


def test_all_registry_gstins_pass_checksum():
    assert all(rules.validate_gstin(g)[0] for g in data.gstin_registry())


def test_bad_check_digit_rejected():
    g = "08YKZXS5189L1ZO"
    bad = g[:-1] + ("A" if g[-1] != "A" else "B")
    assert not rules.validate_gstin(bad)[0]


def test_no_gstin_excludes_gst_products():
    r = rules.recommend(dict(business_type="Kirana store", city_tier=2, employees=2, sites=1, has_gstin=False,
                             needs=["whatsapp", "pos"]))
    ids = [i["id"] for i in r["items"]]
    assert "P15" not in ids and any(e["id"] == "P15" for e in r["excluded"])
    assert all(not data.catalogue()[i]["requires_gstin"] for i in ids)


def test_cancelled_gstin_treated_as_no_gstin():
    r = rules.recommend(dict(business_type="Travel agency", city_tier=2, employees=6, sites=1,
                             gstin="37IHKXV5167L1ZS", needs=["telephony"]))
    assert not r["has_active_gstin"]
    assert "P12" not in [i["id"] for i in r["items"]]


def test_tier1_only_product_not_sold_in_tier2():
    r = rules.recommend(dict(business_type="CA firm", city_tier=2, employees=30, sites=1, has_gstin=True))
    assert "P03" not in [i["id"] for i in r["items"]]


def test_sdwan_needs_three_sites_and_ten_staff():
    small = rules.recommend(dict(business_type="Restaurant chain", city_tier=1, employees=8, sites=2, has_gstin=True, needs=["sdwan"]))
    big = rules.recommend(dict(business_type="Restaurant chain", city_tier=1, employees=40, sites=4, has_gstin=True, needs=["sdwan"]))
    assert "P10" not in [i["id"] for i in small["items"]]
    assert "P10" in [i["id"] for i in big["items"]]


def test_every_recommendation_is_valid():
    import itertools
    for bt, tier, emp, sites, g in itertools.product(
            ["Kirana store", "Dental clinic", "Restaurant chain", "Textile unit"], [1, 2], [1, 5, 12, 40], [1, 3], [True, False]):
        prof = dict(business_type=bt, city_tier=tier, employees=emp, sites=sites, has_gstin=g,
                    needs=["email", "cctv", "failover", "whatsapp", "sdwan", "firewall", "iot"])
        r = rules.recommend(prof)
        assert rules.validate_bundle(r["items"], prof) == [], (prof, r["items"])


def test_removing_fibre_removes_dependent_addons():
    prof = dict(business_type="Dental clinic", city_tier=2, employees=4, sites=1, has_gstin=True, needs=["failover"])
    base = rules.recommend(prof)
    ids = [i["id"] for i in base["items"] if i["id"] != "P02"]
    r = rules.reprice(base, prof, ids)
    assert "P09" not in [i["id"] for i in r["items"]]
    assert "Backup 4G/5G Failover" in r["auto_removed"]


def test_quote_maths():
    items = [{"monthly": 1499, "setup": 0, "min_contract": 12, "install_days": 5},
             {"monthly": 499, "setup": 1500, "min_contract": 12, "install_days": 3}]
    q = rules.price(items)
    assert q["monthly"] == 1998 and q["setup"] == 1500 and q["gst_on_monthly"] == 360


def test_budget_respected_or_explained():
    r = rules.recommend(dict(business_type="Dental clinic", city_tier=2, employees=4, sites=1, has_gstin=False, budget=2000))
    assert r["quote"]["monthly"] <= 2000 or any("above your" in n for n in r["notes"])
