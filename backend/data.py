"""Loads the Track A synthetic data pack once and exposes lookups.

Everything here is read-only reference data: the product catalogue, the mock
GSTIN and Udyam registries, and the lead file (used for city tiers, business
types and the back-office callback list).
"""
from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    env = os.environ.get("DATA_DIR")
    candidates = [Path(env)] if env else []
    candidates += [
        ROOT / "data",
        ROOT.parent / "YTL_TrackA_Udyam_Digital_Data",
        ROOT / "data_link",
    ]
    for c in candidates:
        if c and (c / "product_catalogue.csv").exists():
            return c
    raise FileNotFoundError(
        "Could not find the data pack. Put YTL_TrackA_Udyam_Digital_Data next to this "
        "folder, or set DATA_DIR to its path."
    )


def _read(name: str) -> List[Dict[str, str]]:
    with open(data_dir() / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def catalogue() -> Dict[str, dict]:
    out = {}
    for r in _read("product_catalogue.csv"):
        out[r["product_id"]] = {
            "id": r["product_id"],
            "category": r["category"],
            "name": r["product_name"],
            "description": r["description"],
            "unit": r["unit"],
            "price_min": int(r["price_min_inr_per_month"]),
            "price_max": int(r["price_max_inr_per_month"]),
            "setup": int(r["one_time_setup_inr"]),
            "min_contract": int(r["min_contract_months"]),
            "tiers": [int(t) for t in r["available_city_tiers"].split(";") if t],
            "min_employees": int(r["min_employees"]),
            "min_sites": int(r["min_sites"]),
            "requires_gstin": r["requires_gstin"].strip().upper() == "Y",
            "requires_one_of": [x for x in r["requires_one_of"].split("|") if x],
            "install_days": int(r["typical_install_days"]),
            "segments": [s for s in r["target_segments"].split(";") if s],
        }
    return out


@lru_cache(maxsize=1)
def gstin_registry() -> Dict[str, dict]:
    return {r["gstin"].strip().upper(): r for r in _read("mock_gstin_registry.csv")}


@lru_cache(maxsize=1)
def udyam_registry() -> Dict[str, dict]:
    return {r["udyam_number"].strip().upper(): r for r in _read("mock_udyam_registry.csv")}


@lru_cache(maxsize=1)
def leads() -> List[Dict[str, str]]:
    return _read("smb_leads.csv")


@lru_cache(maxsize=1)
def city_index() -> Dict[str, dict]:
    """city (lower) -> {city, tier, state} learned from the leads file."""
    out: Dict[str, dict] = {}
    for r in leads():
        k = r["city"].strip().lower()
        if k not in out:
            out[k] = {"city": r["city"], "tier": int(r["city_tier"]), "state": r["state"]}
    # common alternate spellings
    alias = {"bangalore": "bengaluru", "bombay": "mumbai", "new delhi": "delhi", "vizag": "visakhapatnam",
             "mysore": "mysuru", "baroda": "vadodara", "cochin": "kochi", "calcutta": "kolkata", "madras": "chennai"}
    for a, k in alias.items():
        if k in out:
            out[a] = out[k]
    return out


@lru_cache(maxsize=1)
def business_types() -> Dict[str, str]:
    """business_type (lower) -> segment code (micro|prof|multi|mfg)."""
    seg_code = {
        "Micro retail & services": "micro",
        "Professional offices": "prof",
        "Small multi-site businesses": "multi",
        "Small manufacturers": "mfg",
    }
    out: Dict[str, str] = {}
    for r in leads():
        out.setdefault(r["business_type"].strip().lower(), seg_code[r["segment"]])
    return out


SEGMENT_LABEL = {
    "micro": "Micro retail & services",
    "prof": "Professional office",
    "multi": "Small multi-site business",
    "mfg": "Small manufacturer",
}

# GST state codes for the states that appear in the pack (plus common ones)
STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "36": "Telangana", "37": "Andhra Pradesh",
}
UDYAM_STATE = {
    "PB": "Punjab", "DL": "Delhi", "RJ": "Rajasthan", "UP": "Uttar Pradesh", "BR": "Bihar",
    "WB": "West Bengal", "MP": "Madhya Pradesh", "GJ": "Gujarat", "MH": "Maharashtra",
    "KR": "Karnataka", "KA": "Karnataka", "KL": "Kerala", "TN": "Tamil Nadu", "TS": "Telangana",
    "TG": "Telangana", "AP": "Andhra Pradesh", "HR": "Haryana",
}


def find_city(text: str) -> Optional[dict]:
    t = text.lower()
    best = None
    for k, v in city_index().items():
        if k in t and (best is None or len(k) > len(best[0])):
            best = (k, v)
    return best[1] if best else None
