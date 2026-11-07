"""Smart KYC: OCR, image-quality checks, field extraction and registry cross-checks.

Pipeline per document
  1. quality  - blur score and skew angle; skewed scans are straightened
  2. clean    - pink watermark removed by thresholding, so OCR sees only text
  3. OCR      - Tesseract (preferred) or RapidOCR; words keep their positions
  4. parse    - words grouped into rows, split into label / value columns
Then the case is checked against the mock GSTIN and Udyam registries.

Uploaded documents never go to the language model.
"""
from __future__ import annotations

import datetime as dt
import difflib
import io
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from . import data, rules

CASE_TODAY = dt.date(2026, 7, 15)  # README: use 2026-07-15 as "today"
ADDRESS_PROOF_MAX_DAYS = 90
BLUR_THRESHOLD = 150.0  # mean |Laplacian| x10 around text; samples: blurry 39, clear 418+
DOC_TYPES = ["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"]
DOC_LABEL = {
    "gst_certificate": "GST registration certificate",
    "udyam_certificate": "Udyam registration certificate",
    "signatory_id": "Authorised signatory ID",
    "address_proof": "Address proof (utility bill)",
}

# ------------------------------------------------------------------ OCR engines
_ENGINE = None


def ocr_engine() -> str:
    global _ENGINE
    if _ENGINE:
        return _ENGINE
    try:
        import pytesseract  # noqa: F401
        if shutil.which("tesseract"):
            _ENGINE = "tesseract"
            return _ENGINE
    except Exception:
        pass
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        _ENGINE = "rapidocr"
        return _ENGINE
    except Exception:
        pass
    _ENGINE = "none"
    return _ENGINE


_RAPID = None


def _words(img: Image.Image, psm: int = 11) -> List[Tuple[str, int, int, int, int]]:
    """Returns (text, x0, y0, x1, y1) for each recognised word or segment."""
    eng = ocr_engine()
    if eng == "tesseract":
        import pytesseract
        d = pytesseract.image_to_data(img, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
        out = []
        for i, t in enumerate(d["text"]):
            t = (t or "").strip()
            if t and float(d["conf"][i]) > 10:
                out.append((t, d["left"][i], d["top"][i], d["left"][i] + d["width"][i], d["top"][i] + d["height"][i]))
        return out
    if eng == "rapidocr":
        global _RAPID
        from rapidocr_onnxruntime import RapidOCR
        _RAPID = _RAPID or RapidOCR()
        res, _ = _RAPID(np.array(img.convert("RGB")))
        out = []
        for box, text, _conf in res or []:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            out.append((text.strip(), int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))))
        return out
    raise RuntimeError("No OCR engine available. Install Tesseract (brew install tesseract) "
                       "or pip install rapidocr-onnxruntime.")


# ------------------------------------------------------------------ image quality
def _gray(img: Image.Image, width: int = 1000) -> np.ndarray:
    g = ImageOps.grayscale(img)
    if g.width > width:
        g = g.resize((width, int(g.height * width / g.width)))
    return np.asarray(g, dtype=np.float32)


def blur_score(img: Image.Image) -> float:
    a = _gray(img)
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    # score only around text (ignore flat paper), so blank space does not lower it
    mask = a[1:-1, 1:-1] < 200
    if mask.sum() < 500:
        return float(lap.var())
    return float(np.abs(lap[mask]).mean() * 10)


def _ink(img: Image.Image) -> Image.Image:
    """Binary image where dark text is black; light pink watermark and paper are white."""
    g = ImageOps.grayscale(img)
    return g.point(lambda v: 0 if v < 150 else 255)


def skew_angle(img: Image.Image) -> float:
    small = _ink(img)
    small = small.resize((600, int(600 * small.height / small.width)))
    inv = ImageOps.invert(small)
    def score(a):
        r = np.asarray(inv.rotate(float(a), expand=False, fillcolor=0, resample=Image.BILINEAR), dtype=np.float32)
        return r.sum(axis=1).var()
    best = max(np.arange(-15, 15.01, 0.5), key=score)
    best = max(np.arange(best - 0.5, best + 0.51, 0.1), key=score)
    return round(float(best), 1)


def prepare(img: Image.Image) -> Tuple[Image.Image, dict]:
    img = ImageOps.exif_transpose(img).convert("RGB")
    q = {"blur": round(blur_score(img), 1)}
    ang = skew_angle(img)
    q["skew_deg"] = round(-ang, 1)
    if abs(ang) >= 1.0:
        img = img.rotate(ang, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
        q["straightened"] = True
    else:
        q["straightened"] = False
    q["blurry"] = q["blur"] < BLUR_THRESHOLD
    return img, q


# ------------------------------------------------------------------ parsing
def _rows(words, tol: int = 14):
    words = sorted(words, key=lambda w: ((w[2] + w[4]) / 2, w[1]))
    rows: List[list] = []
    for w in words:
        cy = (w[2] + w[4]) / 2
        if rows and abs(rows[-1]["cy"] - cy) <= tol:
            rows[-1]["w"].append(w)
            rows[-1]["cy"] = (rows[-1]["cy"] * (len(rows[-1]["w"]) - 1) + cy) / len(rows[-1]["w"])
        else:
            rows.append({"cy": cy, "w": [w]})
    for r in rows:
        r["w"].sort(key=lambda w: w[1])
    return rows


def _detect_type(text: str) -> Optional[str]:
    t = text.lower()
    if "udyam" in t and "registration" in t or "udyam reg" in t:
        return "udyam_certificate"
    if "gst" in t and ("registration" in t or "gstin" in t):
        return "gst_certificate"
    if "signatory" in t or "valid till" in t:
        return "signatory_id"
    if "electricity" in t or "consumer no" in t or "supply address" in t or "billed to" in t:
        return "address_proof"
    return None


LABELS = {
    "gst_certificate": [("gstin", "gstin"), ("legal name", "legal_name"), ("trade name", "trade_name"),
                        ("constitution", "constitution"), ("address of principal", "address"),
                        ("place of business", "address+"), ("date of liability", "date_of_liability"),
                        ("type of registration", "registration_type")],
    "udyam_certificate": [("udyam reg", "udyam_number"), ("enterprise name", "enterprise_name"),
                          ("major activity", "major_activity"), ("city", "city"), ("state", "state"),
                          ("date of registration", "date_of_registration")],
    "address_proof": [("consumer no", "consumer_no"), ("billed to", "billed_to"), ("supply address", "address"),
                      ("bill date", "bill_date"), ("units consumed", "units"), ("amount due", "amount_due")],
    "signatory_id": [("name", "name"), ("designation", "designation"), ("for business", "business"),
                     ("id no", "id_no"), ("valid till", "valid_till")],
}
WATERMARK = re.compile(r"^(synthetic|specimen|not|valid|docum\w*|-)$", re.I)


def _match_label(text: str, doc_type: str) -> Optional[str]:
    t = re.sub(r"[^a-z ]", "", text.lower()).strip()
    best = None
    for lab, key in LABELS[doc_type]:
        if t.startswith(lab) or (len(t) >= 4 and difflib.SequenceMatcher(None, t[:len(lab)], lab).ratio() > 0.8):
            if best is None or len(lab) > len(best[0]):
                best = (lab, key)
    return best[1] if best else None


def parse_fields(words, width: int, doc_type: str) -> Dict[str, str]:
    rows = _rows(words)
    fields: Dict[str, str] = {}
    if doc_type == "signatory_id":
        # card layout: label on one line, value on the next, all in the right column
        lines = [" ".join(w[0] for w in r["w"] if not WATERMARK.match(w[0])) for r in rows]
        lines = [l for l in lines if l.strip()]
        for i, l in enumerate(lines):
            key = None
            for lab, k in LABELS["signatory_id"]:
                if re.sub(r"[^a-z ]", "", l.lower()).strip() == lab:
                    key = k
            if key and i + 1 < len(lines) and key not in fields:
                fields[key] = lines[i + 1].strip()
        return fields

    split = width * 0.40
    last_key = None
    for r in rows:
        left = " ".join(w[0] for w in r["w"] if w[1] < split and not WATERMARK.match(w[0]))
        right = " ".join(w[0] for w in r["w"] if w[1] >= split - 5 and not WATERMARK.match(w[0]))
        key = _match_label(left, doc_type) if left else None
        if key == "address+":
            key = "address"
            fields["address"] = (fields.get("address", "") + right).strip()
            last_key = "address"
            continue
        if key:
            fields[key] = right.strip()
            last_key = key
        elif right and last_key == "address" and not left:
            fields["address"] = (fields.get("address", "") + right).strip()
            last_key = None
        else:
            last_key = None
    if "address" in fields:
        fields["address"] = re.sub(r"\s+", " ", re.sub(r"\s*-\s*-?\s*", " - ", fields["address"])).strip(" -")
    return fields


def _ocr_at(img: Image.Image, scale: int, psm: int = 11):
    big = img.resize((img.width * scale, img.height * scale), Image.LANCZOS) if scale > 1 else img
    ink = _ink(big).convert("RGB")
    words = [(t, x0 // scale, y0 // scale, x1 // scale, y1 // scale) for t, x0, y0, x1, y1 in _words(ink, psm)]
    return [w for w in words if not WATERMARK.match(w[0])]


def _read_row_after(img: Image.Image, words, label: str) -> str:
    """Re-read the single text line to the right of a label (e.g. 'GSTIN') as one line of text."""
    lab = next((w for w in words if w[0].lower().startswith(label.lower())), None)
    if not lab or ocr_engine() != "tesseract":
        return ""
    import pytesseract
    hh = lab[4] - lab[2]
    box = (lab[3] + 10, max(0, lab[2] - hh), img.width, min(img.height, lab[4] + hh))
    crop = _ink(img.crop(box))
    txt = pytesseract.image_to_string(crop, config="--psm 7").strip()
    return re.sub(r"^[|\s]+|[|\s]+$", "", txt)


def analyze_document(path_or_bytes, expected_type: Optional[str] = None) -> dict:
    img = Image.open(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes)
    img, quality = prepare(img)
    words = _ocr_at(img, 1)
    text = " ".join(w[0] for w in words)
    dtype = _detect_type(text) or expected_type
    fields = parse_fields(words, img.width, dtype) if dtype in LABELS else {}
    # Identifier fields get extra passes (higher resolution, other page modes) if the first read does not resolve
    if dtype == "gst_certificate" and not normalise_gstin(fields.get("gstin", ""))[1]:
        for scale, psm in ((2, 11), (1, 6), (2, 6), (1, 4)):
            f2 = parse_fields(_ocr_at(img, scale, psm), img.width, dtype)
            if normalise_gstin(f2.get("gstin", ""))[1]:
                fields["gstin"] = f2["gstin"]
                for k, v in f2.items():  # fill or lengthen other fields from the better pass
                    if len(v or "") > len(fields.get(k) or ""):
                        fields[k] = v
                break
        else:
            line = _read_row_after(img, words, "GSTIN")
            if normalise_gstin(line)[1]:
                fields["gstin"] = line
    if dtype == "udyam_certificate" and not rules.lookup_udyam(normalise_udyam(fields.get("udyam_number", ""))):
        f2 = parse_fields(_ocr_at(img, 2), img.width, dtype)
        if rules.lookup_udyam(normalise_udyam(f2.get("udyam_number", ""))):
            fields["udyam_number"] = f2["udyam_number"]
        else:
            lab = next((w for w in words if w[0].lower() == "number"), None)
            if lab:
                line = _read_row_after(img, [lab], "number")
                if rules.lookup_udyam(normalise_udyam(line)):
                    fields["udyam_number"] = line
    return {"doc_type": dtype, "fields": fields, "quality": quality, "engine": ocr_engine(),
            "chars_read": len(text)}


# ------------------------------------------------------------------ normalisers
_DIG = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"}
_LET = {v: k for k, v in {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6"}.items()}


def normalise_gstin(raw: str) -> Tuple[str, bool]:
    s = re.sub(r"[^0-9A-Za-z]", "", raw or "").upper()
    if len(s) < 15:
        return s, False
    s = s[:15]
    pattern = "DDLLLLLDDDDLAZA"  # D digit, L letter, A alnum, Z literal
    fixed = []
    for ch, p in zip(s, pattern):
        if p == "D":
            fixed.append(_DIG.get(ch, ch))
        elif p == "L":
            fixed.append(_LET.get(ch, ch))
        elif p == "Z":
            fixed.append("Z")
        else:
            fixed.append(ch)
    g = "".join(fixed)
    if rules.validate_gstin(g)[0]:
        return g, True
    # try single-character confusions in the alnum positions
    cand = registry_confusable_match(g, data.gstin_registry().keys())
    if cand:
        return cand, True
    raw15 = re.sub(r"[^0-9A-Za-z]", "", raw or "").upper()
    cand = registry_fuzzy_match(raw15, data.gstin_registry().keys())
    if cand:
        return cand, True
    return g, False


def _wdist(a: str, b: str) -> float:
    """Edit distance where look-alike substitutions cost 0.5."""
    prev = [float(j) for j in range(len(b) + 1)]
    for i, ca in enumerate(a, 1):
        cur = [float(i)] + [0.0] * len(b)
        for j, cb in enumerate(b, 1):
            sub = 0.0 if ca == cb else (0.5 if _confusable(ca, cb) else 1.0)
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub)
        prev = cur
    return prev[-1]


def registry_fuzzy_match(raw: str, keys, max_cost: float = 2.0) -> Optional[str]:
    if len(raw) < 13:
        return None
    scored = []
    for k in keys:
        if not (_confusable(k[0], raw[0]) and _confusable(k[1], raw[1])):
            continue
        scored.append((_wdist(raw, k), k))
    if not scored:
        return None
    scored.sort()
    best = scored[0]
    if best[0] <= max_cost and (len(scored) == 1 or scored[1][0] - best[0] >= 1.0):
        return best[1]
    return None


CONFUSABLE = [set("0ODQ@"), set("1IL|J"), set("5S8B"), set("2Z"), set("6G"), set("7T")]


def _confusable(a: str, b: str) -> bool:
    return a == b or any(a in grp and b in grp for grp in CONFUSABLE)


def registry_confusable_match(raw: str, keys, max_diff: int = 3) -> Optional[str]:
    """Find the registry id that differs from the OCR text only by look-alike characters
    (0/O, 1/I/J, 5/S/8/B, 2/Z ...). Returns it only if exactly one candidate is closest."""
    raw = raw.upper()
    best, best_d, tie = None, max_diff + 1, False
    for k in keys:
        if len(k) != len(raw) or k[:2] != raw[:2] and not all(_confusable(x, y) for x, y in zip(k[:2], raw[:2])):
            continue
        d = 0
        for x, y in zip(k, raw):
            if x != y:
                if not _confusable(x, y):
                    d = 99
                    break
                d += 1
        if d < best_d:
            best, best_d, tie = k, d, False
        elif d == best_d:
            tie = True
    return best if best and not tie else None


def normalise_udyam(raw: str) -> str:
    s = re.sub(r"\s+", "", (raw or "").upper()).replace("@", "0")
    if s.startswith("UDYAM") and not re.search(r"UDYAM-?[A-Z]{2}-?\d{2}-?\d{7}", s):
        m2 = re.search(r"UDYAM-?([A-Z]{2})-?(\d{7})$", s)
        if m2:  # district digits dropped by OCR; the pack always uses 00
            s = f"UDYAM-{m2.group(1)}-00-{m2.group(2)}"
    m = re.search(r"UDYAM-?([A-Z0-9]{2})-?([0-9OD]{2})-?([0-9OISBDZ]{7})", s)
    if not m:
        return ""
    st, d, n = m.groups()
    n = "".join(_DIG.get(c, c) for c in n)
    d = "".join(_DIG.get(c, c) for c in d)
    st = "".join(_LET.get(c, c) for c in st)
    return f"UDYAM-{st}-{d}-{n}"


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\(prop\.?[^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def similar(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _tokens_within(a: str, b: str) -> bool:
    """True if every word of a appears in b (OCR sometimes drops a word, never invents one)."""
    ta, tb = set(_norm(a).split()), set(_norm(b).split())
    return bool(ta) and ta <= tb


def _addr_key(a: str) -> str:
    a = re.sub(r"[^a-z0-9]", "", (a or "").lower())
    return a


def _date(s: str) -> Optional[dt.date]:
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _state_in(addr: str) -> str:
    """Best-matching state name inside an OCR'd address (tolerates small OCR errors)."""
    tail = re.sub(r"[^a-z ]", " ", (addr or "").lower())
    best, score = "", 0.0
    for st in set(data.STATE_CODES.values()):
        n = len(st)
        for i in range(0, max(1, len(tail) - n + 1)):
            r = difflib.SequenceMatcher(None, tail[i:i + n], st.lower()).ratio()
            if r > score:
                best, score = st, r
    return best if score >= 0.8 else ""


def _proprietor(legal_name: str) -> str:
    m = re.match(r"\s*([^()]+?)\s*\(prop", legal_name or "", re.I)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------ the case
def run_case(docs: Dict[str, dict], claimed: Optional[dict] = None, today: dt.date = CASE_TODAY) -> dict:
    """docs: doc_type -> analyze_document() result. Returns checks and a decision."""
    claimed = claimed or {}
    checks: List[dict] = []

    def add(cid, label, result, detail, fix=None, owner="customer"):
        checks.append({"id": cid, "label": label, "result": result, "detail": detail, "fix": fix, "owner": owner})

    # 1. presence and quality
    for t in DOC_TYPES:
        d = docs.get(t)
        if not d:
            add(f"present_{t}", f"{DOC_LABEL[t]} uploaded", "fail", "Not uploaded.",
                f"Please upload your {DOC_LABEL[t]}.")
            continue
        q = d["quality"]
        if q.get("blurry") or d.get("chars_read", 0) < 40:
            add(f"quality_{t}", f"{DOC_LABEL[t]} is readable", "fail",
                f"Image is too blurry to read (sharpness {q['blur']}).",
                "Retake the photo in good light, hold the phone steady and fill the frame.")
        elif q.get("straightened"):
            add(f"quality_{t}", f"{DOC_LABEL[t]} is readable", "pass",
                f"Scan was tilted {abs(q['skew_deg'])}° and was straightened automatically.")
        else:
            add(f"quality_{t}", f"{DOC_LABEL[t]} is readable", "pass", "Clear image.")

    gst = (docs.get("gst_certificate") or {}).get("fields", {})
    udy = (docs.get("udyam_certificate") or {}).get("fields", {})
    adr = (docs.get("address_proof") or {}).get("fields", {})
    sig = (docs.get("signatory_id") or {}).get("fields", {})
    gst_ok_read = "gst_certificate" in docs and not docs["gst_certificate"]["quality"].get("blurry") \
        and docs["gst_certificate"].get("chars_read", 0) >= 40

    # 2. GSTIN format + registry
    reg = None
    gstin = ""
    if gst_ok_read:
        gstin, valid = normalise_gstin(gst.get("gstin", ""))
        if not gstin:
            add("gstin_format", "GSTIN format and check digit", "fail", "No GSTIN found on the certificate.",
                "Upload the full GST certificate page that shows the GSTIN.")
        elif not valid:
            add("gstin_format", "GSTIN format and check digit", "fail",
                f"{rules.mask_gstin(gstin)} does not pass the GSTIN check digit.", "Type the GSTIN to confirm it.")
        else:
            add("gstin_format", "GSTIN format and check digit", "pass", f"{rules.mask_gstin(gstin)} is well-formed.")
            reg = rules.lookup_gstin(gstin)
            if not reg:
                add("gstin_registry", "GSTIN found in GST registry", "fail", "Not found in the registry.",
                    owner="reviewer")
            elif reg["status"] != "Active":
                add("gstin_registry", "GSTIN is Active in GST registry", "fail",
                    f"Registry status is {reg['status']}. Products that need GST cannot be activated.",
                    "Reactivate the GST registration, or continue with products that do not need GST.",
                    owner="reviewer")
            else:
                add("gstin_registry", "GSTIN is Active in GST registry", "pass",
                    f"Active since {reg['registration_date']}.")
            # state code vs address
            st = data.STATE_CODES.get(gstin[:2], "")
            addr_state = (reg or {}).get("state") or _state_in(gst.get("address", ""))
            if st and addr_state and similar(st, addr_state) < 0.85:
                add("gstin_state", "GSTIN state code matches address", "fail",
                    f"State code {gstin[:2]} is {st}, but the address is elsewhere.", owner="reviewer")
            else:
                add("gstin_state", "GSTIN state code matches address", "pass", f"{gstin[:2]} = {st}.")

    # 3. certificate details vs registry
    if reg:
        s1 = similar(gst.get("legal_name", ""), reg["legal_name"])
        s2 = similar(gst.get("trade_name", ""), reg["trade_name"])
        if min(s1, s2) < 0.85:
            add("gst_names", "Names on certificate match the registry", "fail",
                f"Certificate shows legal name '{gst.get('legal_name', '?')}' and trade name "
                f"'{gst.get('trade_name', '?')}'; registry has '{reg['legal_name']}' / '{reg['trade_name']}'.",
                owner="reviewer")
        else:
            add("gst_names", "Names on certificate match the registry", "pass", "Legal and trade names match.")
        if similar(gst.get("address", ""), reg["principal_place_of_business"]) < 0.85:
            add("gst_address", "Certificate address matches the registry", "warn",
                "Address differs from the registry record.", owner="reviewer")
    # legal name vs trade name consistency on the certificate itself (proprietorships)
    if gst_ok_read and gst.get("legal_name") and gst.get("trade_name"):
        m = re.search(r"\(prop\.?\s*([^)]+)\)", gst["legal_name"], re.I)
        if m and similar(m.group(1), gst["trade_name"]) < 0.85 and not _tokens_within(m.group(1), gst["trade_name"]):
            add("gst_internal", "Legal name and trade name agree", "fail",
                f"Legal name says '{m.group(1).strip()}' but trade name is '{gst['trade_name']}'.",
                owner="reviewer")

    business = ((reg or {}).get("trade_name") or gst.get("trade_name") or claimed.get("business_name", "")
                or udy.get("enterprise_name") or adr.get("billed_to") or sig.get("business") or "")

    # 4. Udyam
    if "udyam_certificate" in docs and not docs["udyam_certificate"]["quality"].get("blurry"):
        un = normalise_udyam(udy.get("udyam_number", ""))
        if not un:
            add("udyam_number", "Udyam number present", "fail", "The Udyam registration number is blank or unreadable.",
                "Upload the Udyam certificate page that shows the UDYAM- number, or type it in.")
        else:
            urec = rules.lookup_udyam(un)
            if not urec:
                add("udyam_registry", "Udyam number found in registry", "fail", f"{un} not found.", owner="reviewer")
            else:
                ok = similar(urec["enterprise_name"], business) >= 0.85
                add("udyam_registry", "Udyam record matches the business", "pass" if ok else "fail",
                    f"{un}: {urec['enterprise_name']}, {urec['city']}, {urec['state']} ({urec['enterprise_type']}).",
                    owner="reviewer")
        if business and udy.get("enterprise_name") and similar(udy["enterprise_name"], business) < 0.85:
            add("udyam_name", "Udyam enterprise name matches GST", "fail",
                f"Udyam shows '{udy['enterprise_name']}', GST shows '{business}'.", owner="reviewer")

    # 5. Address proof
    if "address_proof" in docs and not docs["address_proof"]["quality"].get("blurry"):
        bd = _date(adr.get("bill_date", ""))
        if not bd:
            add("address_age", "Address proof is recent", "fail", "Bill date not found.", "Upload a recent bill.")
        else:
            age = (today - bd).days
            if age > ADDRESS_PROOF_MAX_DAYS:
                add("address_age", f"Address proof is under {ADDRESS_PROOF_MAX_DAYS} days old", "fail",
                    f"Bill dated {bd.isoformat()} is {age} days old on {today.isoformat()}.",
                    f"Upload a utility bill dated after {(today - dt.timedelta(days=ADDRESS_PROOF_MAX_DAYS)).isoformat()}.")
            else:
                add("address_age", f"Address proof is under {ADDRESS_PROOF_MAX_DAYS} days old", "pass",
                    f"Bill dated {bd.isoformat()} ({age} days old).")
        if business and adr.get("billed_to"):
            ok = similar(adr["billed_to"], business) >= 0.85
            add("address_name", "Bill is in the business's name", "pass" if ok else "fail",
                f"Billed to '{adr['billed_to']}'.", None if ok else "Upload a bill in the business's name.")
        ref_addr = (reg or {}).get("principal_place_of_business") or gst.get("address", "")
        if ref_addr and adr.get("address"):
            r = difflib.SequenceMatcher(None, _addr_key(adr["address"]), _addr_key(ref_addr)).ratio()
            add("address_match", "Bill address matches GST address", "pass" if r >= 0.85 else "fail",
                "Addresses match." if r >= 0.85 else f"Bill address '{adr['address']}' differs from GST address.",
                None if r >= 0.85 else "Upload a bill for the registered address, or update the GST address.",
                owner="customer")

    # 6. Signatory
    if "signatory_id" in docs and not docs["signatory_id"]["quality"].get("blurry"):
        vt = _date(sig.get("valid_till", ""))
        if vt and vt < today:
            add("sig_valid", "Signatory ID is valid", "fail", f"Expired on {vt.isoformat()}.", "Upload a valid ID.")
        elif vt:
            add("sig_valid", "Signatory ID is valid", "pass", f"Valid till {vt.isoformat()}.")
        if business and sig.get("business"):
            ok = similar(sig["business"], business) >= 0.85
            add("sig_business", "Signatory belongs to this business", "pass" if ok else "fail",
                f"ID is for '{sig['business']}'.", owner="reviewer")
        prop = _proprietor((reg or {}).get("legal_name") or gst.get("legal_name", ""))
        if prop and sig.get("name"):
            ok = similar(prop, sig["name"]) >= 0.85
            add("sig_person", "Signatory is the proprietor", "pass" if ok else "fail",
                f"Proprietor {prop}; ID holder {sig['name']}.",
                None if ok else "Proprietor must sign, or upload an authorisation letter.", owner="reviewer")

    # decision
    fails = [c for c in checks if c["result"] == "fail"]
    if not fails:
        status = "verified"
        summary = "All checks passed. KYC verified automatically."
    elif any(c["owner"] == "reviewer" for c in fails):
        status = "manual_review"
        summary = "Held for a human reviewer. Failed checks: " + "; ".join(c["label"] for c in fails)
    else:
        status = "action_needed"
        summary = "Sent back to the customer. Failed checks: " + "; ".join(c["label"] for c in fails)
    extracted = {
        "gstin": rules.mask_gstin(gstin) if gstin else None,
        "gstin_status": (reg or {}).get("status"),
        "business": business,
        "legal_name": gst.get("legal_name"),
        "udyam": udy.get("udyam_number"),
        "address": adr.get("address") or gst.get("address"),
        "signatory": sig.get("name"),
        "signatory_id": rules.mask_id(sig.get("id_no", "")),
    }
    return {"status": status, "summary": summary, "checks": checks, "extracted": extracted,
            "_gstin_full": gstin}


def sample_dir() -> Path:
    return data.data_dir() / "kyc_documents"


def sample_ids() -> List[str]:
    return sorted({p.name[:3] for p in sample_dir().glob("K*_*.png")})


def analyze_sample(aid: str) -> Dict[str, dict]:
    out = {}
    for t in DOC_TYPES:
        p = sample_dir() / f"{aid}_{t}.png"
        if p.exists():
            out[t] = analyze_document(str(p), expected_type=t)
    return out
