"""Deterministic eligibility, recommendation and pricing engine.

The language model never chooses products or prices. It gathers a business
profile; this module decides what is sellable, what it costs and why.
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

from . import data

GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")


# ---------------------------------------------------------------- identifiers
def gstin_checksum(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        v = GSTIN_CHARS.index(ch)
        p = v * (1 if i % 2 == 0 else 2)
        total += p // 36 + p % 36
    return GSTIN_CHARS[(36 - total % 36) % 36]


def validate_gstin(g: str) -> Tuple[bool, str]:
    g = (g or "").strip().upper()
    if len(g) != 15:
        return False, "A GSTIN has 15 characters."
    if not GSTIN_RE.match(g):
        return False, "The GSTIN pattern is not valid (2 digits, PAN, entity code, Z, check digit)."
    if g[:2] not in data.STATE_CODES:
        return False, f"State code {g[:2]} is not a valid GST state code."
    if gstin_checksum(g[:14]) != g[14]:
        return False, "The GSTIN check digit does not match. Please re-check the number."
    return True, "Format and check digit are valid."


def mask_gstin(g: str) -> str:
    g = (g or "").upper()
    return g[:2] + "•" * 8 + g[-5:] if len(g) == 15 else "•••"


def mask_id(s: str, keep: int = 4) -> str:
    s = s or ""
    return "•" * max(0, len(s) - keep) + s[-keep:]


def lookup_gstin(g: str) -> Optional[dict]:
    return data.gstin_registry().get((g or "").strip().upper())


def lookup_udyam(u: str) -> Optional[dict]:
    return data.udyam_registry().get((u or "").strip().upper())


# ---------------------------------------------------------------- profile
NEED_KEYWORDS = {
    "email": ["email", "e-mail", "mail", "office suite", "ईमेल"],
    "backup_data": ["data backup", "cloud backup", "backup of files", "storage", "files", "डेटा बैकअप"],
    "security": ["antivirus", "virus", "endpoint", "security", "cyber", "सुरक्षा"],
    "firewall": ["firewall"],
    "failover": ["failover", "backup internet", "backup connection", "uptime", "never go down", "downtime", "बैकअप इंटरनेट"],
    "telephony": ["telephony", "ivr", "landline", "cloud calling", "sip", "call centre", "calls"],
    "tollfree": ["toll-free", "toll free", "1800"],
    "sms": ["sms", "bulk sms", "otp"],
    "whatsapp": ["whatsapp", "व्हाट्सएप"],
    "website": ["website", "domain", "online store", "वेबसाइट"],
    "pos": ["pos", "billing", "bill", "invoice", "counter", "upi", "बिलिंग", "बिल"],
    "wifi": ["wifi", "wi-fi", "guest", "वाईफाई"],
    "cctv": ["cctv", "camera", "surveillance", "कैमरा"],
    "iot": ["iot", "machine", "sensor", "machines"],
    "fleet": ["fleet", "vehicle", "truck", "delivery van", "gps"],
    "sdwan": ["sd-wan", "sdwan", "central management", "manage all sites"],
    "static_ip": ["static ip", "fixed ip"],
    "sims": ["sim", "mobile plan", "phones", "postpaid"],
}

NEED_PRODUCT = {
    "email": "P16", "backup_data": "P17", "security": "P20", "firewall": "P21", "failover": "P09",
    "telephony": "P12", "tollfree": "P13", "sms": "P14", "whatsapp": "P15", "website": "P18",
    "pos": "P19", "wifi": "P22", "cctv": "P23", "iot": "P24", "fleet": "P25", "sdwan": "P10",
    "static_ip": "P11",
}

DEFAULT_NEEDS = {
    "micro": ["pos", "wifi"],
    "prof": ["email", "security", "backup_data"],
    "multi": ["failover", "cctv", "pos"],
    "mfg": ["email", "firewall", "iot"],
}


def infer_segment(profile: dict) -> str:
    bt = (profile.get("business_type") or "").lower()
    seg = data.business_types().get(bt)
    if not seg:
        for k, v in data.business_types().items():
            if k.split()[0] in bt and len(k.split()[0]) > 3:
                seg = v
                break
    sites = int(profile.get("sites") or 1)
    if seg == "mfg":
        return "mfg"
    if sites >= 2:
        return "multi"
    if seg in ("prof", "micro"):
        return seg
    if seg == "multi":
        return "multi" if sites >= 2 else "micro"
    emp = int(profile.get("employees") or 1)
    return "prof" if emp >= 5 else "micro"


def gstin_state(profile: dict) -> Tuple[bool, str]:
    """Returns (has_active_gstin, note)."""
    g = (profile.get("gstin") or "").strip().upper()
    if g:
        ok, msg = validate_gstin(g)
        if not ok:
            return False, f"GSTIN {mask_gstin(g)} failed validation: {msg}"
        rec = lookup_gstin(g)
        if not rec:
            return False, f"GSTIN {mask_gstin(g)} was not found in the registry."
        if rec["status"] != "Active":
            return False, f"GSTIN {mask_gstin(g)} is {rec['status']} in the registry, so GST-only products are held back."
        return True, f"GSTIN {mask_gstin(g)} is Active ({rec['trade_name']})."
    if profile.get("has_gstin") is True:
        return True, "Owner says the business has a GSTIN; it will be verified at KYC."
    return False, "No GSTIN, so products that need GST registration are left out."


# ---------------------------------------------------------------- eligibility
def check_product(pid: str, profile: dict, chosen: List[str], has_gstin: bool) -> List[str]:
    p = data.catalogue()[pid]
    reasons = []
    tier = profile.get("city_tier")
    if tier and int(tier) not in p["tiers"]:
        reasons.append(f"{p['name']} is sold only in tier-{'/'.join(map(str, p['tiers']))} cities")
    if int(profile.get("employees") or 1) < p["min_employees"]:
        reasons.append(f"{p['name']} needs at least {p['min_employees']} employees")
    if int(profile.get("sites") or 1) < p["min_sites"]:
        reasons.append(f"{p['name']} needs at least {p['min_sites']} sites")
    if p["requires_gstin"] and not has_gstin:
        reasons.append(f"{p['name']} needs an active GSTIN")
    if p["requires_one_of"] and not set(p["requires_one_of"]) & set(chosen):
        names = ", ".join(data.catalogue()[x]["name"] for x in p["requires_one_of"])
        reasons.append(f"{p['name']} works only with one of: {names}")
    return reasons


def validate_bundle(items: List[dict], profile: dict) -> List[str]:
    has_g, _ = gstin_state(profile)
    ids = [i["id"] for i in items]
    errs = []
    for i in items:
        errs += check_product(i["id"], profile, ids, has_g)
    return errs


# ---------------------------------------------------------------- recommender
WHY = {
    "P01": "Reliable 100 Mbps fibre for UPI, POS and a few devices",
    "P02": "300 Mbps fibre with room for staff, cloud apps and video calls",
    "P03": "1 Gbps fibre with priority support for a larger office",
    "P04": "5G AirFiber installs in about 2 days and needs no fibre at the shop",
    "P05": "Dedicated 20 Mbps leased line for machines and ERP that cannot drop",
    "P06": "Dedicated 100 Mbps leased line for a large unit",
    "P07": "Business SIM for the owner, with one bill",
    "P08": "Business postpaid lines with more data for staff",
    "P09": "Switches to 4G/5G automatically if the fibre goes down",
    "P10": "Manage every site's network from one place",
    "P11": "Fixed IP for remote access, servers or cameras",
    "P12": "One business number that rings on any phone",
    "P13": "A toll-free number customers can call",
    "P14": "10,000 SMS a month for reminders and offers",
    "P15": "Official WhatsApp Business API for catalogues and alerts",
    "P16": "Professional email on your own domain, with office apps",
    "P17": "1 TB of automatic cloud backup for important files",
    "P18": "A simple website with your own domain",
    "P19": "Cloud billing and POS that works with UPI",
    "P20": "Antivirus and protection for each computer",
    "P21": "Managed firewall to keep the network safe",
    "P22": "Secure Wi-Fi with a separate guest network",
    "P23": "Cloud CCTV you can watch on your phone",
    "P24": "Sensors that report machine health and downtime",
    "P25": "GPS tracking for delivery vehicles",
}


def _qty(pid: str, seg: str, emp: int, sites: int, profile: dict) -> int:
    if pid in ("P01", "P02", "P03", "P04", "P05", "P06", "P09", "P10", "P21", "P22"):
        return sites
    if pid == "P07":
        return max(1, min(emp, 2)) if seg == "micro" else 1
    if pid == "P08":
        return {"prof": min(max(1, math.ceil(emp / 5)), 5), "multi": sites, "mfg": 3}.get(seg, 1)
    if pid in ("P16", "P20"):
        return max(1, min(emp, 50))
    if pid == "P12":
        return max(1, math.ceil(emp / 10))
    if pid == "P19":
        return sites
    if pid == "P23":
        return int(profile.get("cameras") or 2 * sites)
    if pid == "P24":
        return int(profile.get("machines") or 10)
    if pid == "P25":
        return int(profile.get("vehicles") or 2)
    return 1


def _connectivity(seg: str, emp: int, tier: int, has_g: bool, profile: dict) -> str:
    if profile.get("fibre_feasible") is False:
        return "P04"
    if seg == "mfg":
        if has_g and emp >= 25 and profile.get("heavy_usage"):
            return "P06"
        if has_g and emp >= 10:
            return "P05"
        return "P02"
    if seg == "prof":
        if has_g and tier == 1 and emp >= 15:
            return "P03"
        return "P02"
    if seg == "multi":
        return "P02"
    return "P01"


def recommend(profile: dict) -> dict:
    """Build an eligible, priced bundle with a reason for every line."""
    seg = profile.get("segment") or infer_segment(profile)
    emp = int(profile.get("employees") or 1)
    sites = int(profile.get("sites") or 1)
    tier = int(profile.get("city_tier") or 2)
    has_g, gst_note = gstin_state(profile)
    cat = data.catalogue()

    chosen: List[str] = []
    excluded: List[dict] = []
    notes: List[str] = [gst_note]

    conn = _connectivity(seg, emp, tier, has_g, profile)
    chosen.append(conn)
    chosen.append("P07" if seg == "micro" else "P08")

    needs = list(profile.get("needs") or [])
    if not needs:
        needs = DEFAULT_NEEDS[seg]
        notes.append("No specific needs given, so the bundle uses what similar businesses usually buy.")
    for n in needs:
        pid = NEED_PRODUCT.get(n)
        if pid and pid not in chosen:
            chosen.append(pid)

    # eligibility pass (two passes so dependencies resolve after removals)
    for _ in range(2):
        keep = []
        for pid in chosen:
            why_not = check_product(pid, {**profile, "city_tier": tier, "employees": emp, "sites": sites}, chosen, has_g)
            if why_not:
                if not any(e["id"] == pid for e in excluded):
                    excluded.append({"id": pid, "name": cat[pid]["name"],
                                     "reasons": [r.replace(cat[pid]["name"] + " ", "", 1) for r in why_not],
                                     "alternative": _alternative(pid, has_g)})
            else:
                keep.append(pid)
        chosen = keep
        # make sure a connectivity product survives
        if not any(cat[c]["category"] == "Connectivity" and c not in ("P07", "P08") for c in chosen):
            chosen.insert(0, "P02" if seg != "micro" else "P01")

    items = []
    for pid in chosen:
        p = cat[pid]
        q = _qty(pid, seg, emp, sites, profile)
        items.append({
            "id": pid, "name": p["name"], "category": p["category"], "unit": p["unit"], "qty": q,
            "unit_price": p["price_min"], "monthly": p["price_min"] * q, "setup": p["setup"] * q,
            "min_contract": p["min_contract"], "install_days": p["install_days"],
            "why": WHY.get(pid, p["description"]), "core": pid == conn,
        })

    # budget fit: drop optional add-ons, then step fibre down, until it fits
    budget = profile.get("budget")
    if budget:
        budget = int(budget)
        protect = {NEED_PRODUCT[n] for n in (profile.get("explicit_needs") or []) if n in NEED_PRODUCT}
        items, dropped = _fit_budget(items, budget, profile, seg, emp, sites, protect)
        over = price(items)["monthly"] - budget
        if over > 0:
            notes.append("This is ₹{:,} above your ₹{:,} budget. It is the smallest bundle that still covers what you asked for.".format(over, budget))
        if dropped:
            notes.append("To get closer to ₹{:,}/month we changed: {}. You can add things back on the quote.".format(
                budget, ", ".join(dropped)))

    addons = suggest_addons([i["id"] for i in items], profile, has_g)
    return {
        "segment": seg,
        "segment_label": data.SEGMENT_LABEL[seg],
        "has_active_gstin": has_g,
        "items": items,
        "excluded": excluded,
        "addons": addons,
        "notes": [n for n in notes if n],
        "quote": price(items),
    }


def _alternative(pid: str, has_g: bool) -> Optional[str]:
    alt = {"P15": "P18", "P14": "P18", "P13": "P12", "P03": "P02", "P05": "P02", "P06": "P05",
           "P21": "P20", "P10": "P09", "P24": None, "P12": "P08"}.get(pid)
    if not alt:
        return None
    a = data.catalogue()[alt]
    if a["requires_gstin"] and not has_g:
        return None
    return f"Try {a['name']} instead"


def _fit_budget(items, budget, profile, seg, emp, sites, protect=frozenset()):
    """Cheapen step by step until the bundle fits: optional add-ons first, then smaller
    plans, then essentials. Items the owner asked for by name are never dropped."""
    cat = data.catalogue()
    dropped = []
    optional = ["P23", "P22", "P18", "P17", "P09", "P13", "P14", "P15", "P11", "P12", "P25", "P24"]
    essential = ["P19", "P20", "P16", "P21", "P10"]
    steps_down = [("P03", "P02"), ("P02", "P01"), ("P08", "P07"), ("P01", "P04")]

    def swap(item, new_id, label):
        p = cat[new_id]
        q = item["qty"] if p["unit"] == cat[item["id"]]["unit"] else 1
        item.update({"id": p["id"], "name": p["name"], "unit_price": p["price_min"], "qty": q,
                     "monthly": p["price_min"] * q, "setup": p["setup"] * q, "min_contract": p["min_contract"],
                     "install_days": p["install_days"], "why": WHY[p["id"]]})
        dropped.append(label)

    while price(items)["monthly"] > budget:
        cand = next((i for o in optional for i in items if i["id"] == o and o not in protect), None)
        if cand:
            items = [i for i in items if i is not cand]
            dropped.append(cand["name"])
            continue
        done = False
        for frm, to in steps_down[:3]:
            it = next((i for i in items if i["id"] == frm), None)
            if it and not (to == "P01" and seg in ("multi", "mfg")):
                swap(it, to, f"{cat[frm]['name']} (switched to {cat[to]['name']})")
                done = True
                break
        if done:
            continue
        cand = next((i for o in essential for i in items if i["id"] == o and o not in protect), None)
        if cand:
            items = [i for i in items if i is not cand]
            dropped.append(cand["name"])
            continue
        it = next((i for i in items if i["id"] == "P01"), None)
        if it and not any(i["id"] in ("P22",) for i in items):
            swap(it, "P04", "fibre (switched to 5G AirFiber)")
            continue
        break
    return items, dropped


def suggest_addons(chosen: List[str], profile: dict, has_g: bool) -> List[dict]:
    seg = profile.get("segment") or infer_segment(profile)
    emp = int(profile.get("employees") or 1)
    sites = int(profile.get("sites") or 1)
    tier = int(profile.get("city_tier") or 2)
    cat = data.catalogue()
    out = []
    for pid, p in cat.items():
        if pid in chosen or p["category"] == "Connectivity" and pid not in ("P09", "P11", "P10"):
            continue
        if seg not in p["segments"]:
            continue
        if check_product(pid, {**profile, "city_tier": tier, "employees": emp, "sites": sites}, chosen, has_g):
            continue
        q = _qty(pid, seg, emp, sites, profile)
        out.append({"id": pid, "name": p["name"], "qty": q, "unit_price": p["price_min"],
                    "monthly": p["price_min"] * q, "setup": p["setup"] * q, "min_contract": p["min_contract"],
                    "install_days": p["install_days"], "why": WHY.get(pid, p["description"]),
                    "category": p["category"], "unit": p["unit"]})
    return out[:6]


def price(items: List[dict]) -> dict:
    monthly = sum(i["monthly"] for i in items)
    setup = sum(i["setup"] for i in items)
    contract = max([i["min_contract"] for i in items] or [0])
    install = max([i["install_days"] for i in items] or [0])
    gst = round(monthly * 0.18)
    return {"monthly": monthly, "setup": setup, "gst_on_monthly": gst, "monthly_incl_gst": monthly + gst,
            "longest_contract_months": contract, "expected_install_days": install}


def reprice(base: dict, profile: dict, enabled_ids: List[str], quantities: Dict[str, int] = None) -> dict:
    """Re-price a quote after the owner toggles add-ons or edits quantities.

    Re-runs eligibility so a removed dependency also removes what relied on it.
    """
    quantities = quantities or {}
    pool = {i["id"]: dict(i) for i in base["items"] + base.get("addons", [])}
    chosen = list(dict.fromkeys(pid for pid in enabled_ids if pid in pool))
    has_g, _ = gstin_state(profile)
    removed = []
    changed = True
    while changed:
        changed = False
        for pid in list(chosen):
            if check_product(pid, profile, chosen, has_g):
                chosen.remove(pid)
                removed.append(pool[pid]["name"])
                changed = True
    items = []
    for pid in chosen:
        it = pool[pid]
        q = int(quantities.get(pid, it["qty"]))
        q = max(1, min(q, 500))
        p = data.catalogue()[pid]
        it.update({"qty": q, "monthly": p["price_min"] * q, "setup": p["setup"] * q})
        items.append(it)
    return {"items": items, "quote": price(items), "auto_removed": removed}
