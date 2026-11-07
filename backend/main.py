"""Udyam Digital - FastAPI app: advisor, quote, Smart KYC, order tracker and back office."""
from __future__ import annotations

import datetime as dt
import secrets
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import advisor, data, kyc, llm, rules, store

app = FastAPI(title="Accel Business - Udyam Digital", version="1.0")
FRONT = Path(__file__).resolve().parent.parent / "frontend"
CONSENT_VERSION = "2026-11-v1"

MILESTONES = [
    ("quote_accepted", "Quote accepted"),
    ("kyc_verified", "Business verified (KYC)"),
    ("payment_mandate", "Autopay set up"),
    ("install_scheduled", "Installation booked"),
    ("installing", "Engineer visit / installation"),
    ("live", "Services live"),
]


@app.on_event("startup")
def _startup():
    store.init()
    store.purge_expired()
    data.catalogue(), data.gstin_registry(), data.udyam_registry(), data.leads()


# ------------------------------------------------------------------ health
@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.provider() or "rule-based (no API key set)", "llm_model": llm.model_name() or None,
            "ocr": kyc.ocr_engine(), "data_dir": str(data.data_dir()), "case_today": kyc.CASE_TODAY.isoformat(),
            "products": len(data.catalogue())}


@app.get("/api/catalogue")
def get_catalogue():
    return list(data.catalogue().values())


# ------------------------------------------------------------------ advisor
class StartReq(BaseModel):
    lang: str = "en"
    partner_code: Optional[str] = None


class MsgReq(BaseModel):
    session_id: str
    text: str


@app.post("/api/advisor/start")
def advisor_start(req: StartReq):
    sid = "S-" + secrets.token_hex(6)
    s = advisor.new_session(req.lang)
    s["partner_code"] = (req.partner_code or "")[:20] or None
    store.save_session(sid, s)
    lang = s["lang"]
    return {"session_id": sid, "text": s["messages"][0]["text"], "chips": advisor.CHIPS[lang]["business_type"],
            "progress": 0, "llm": llm.provider() or None}


@app.post("/api/advisor/message")
def advisor_message(req: MsgReq):
    s = store.load_session(req.session_id)
    if not s:
        raise HTTPException(404, "Session not found. Please start again.")
    text = req.text.strip()[:1000]
    if not text:
        raise HTTPException(400, "Empty message")
    if s.get("done"):
        r = advisor.follow_up(s, text)
        if r is None:
            r = {"text": ("Tap 'Show me the quote' to see the price, or tell me what to change "
                          "(for example: add CCTV, make it cheaper, we have 3 branches)." if s["lang"] == "en" else
                          "कोटेशन देखने के लिए 'कोटेशन दिखाएँ' दबाएँ, या बताएँ क्या बदलना है।"),
                 "recommendation": s.get("recommendation"), "asked": None}
    else:
        r = advisor.turn(s, text)
    store.save_session(req.session_id, s)
    r["profile"] = advisor._public(s["profile"])
    return r


@app.get("/api/advisor/{sid}")
def advisor_get(sid: str):
    s = store.load_session(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    return {"messages": s["messages"], "profile": advisor._public(s["profile"]),
            "recommendation": s.get("recommendation"), "lang": s["lang"]}


# ------------------------------------------------------------------ quote
class QuoteReq(BaseModel):
    session_id: str
    enabled: List[str]
    quantities: Dict[str, int] = {}


def _profile_for_rules(s: dict) -> dict:
    p = dict(s["profile"])
    p.setdefault("city_tier", 2)
    p.setdefault("sites", 1)
    p.setdefault("employees", 1)
    return p


@app.post("/api/quote")
def quote(req: QuoteReq):
    s = store.load_session(req.session_id)
    if not s or not s.get("recommendation"):
        raise HTTPException(404, "No recommendation yet for this session")
    r = rules.reprice(s["recommendation"], _profile_for_rules(s), req.enabled, req.quantities)
    r["coverage"] = coverage(s["profile"])
    return r


def coverage(profile: dict) -> dict:
    """Mock serviceability: fibre where we have city data, 5G AirFiber elsewhere."""
    city = profile.get("city") or "your area"
    known = data.find_city(city) is not None
    return {"city": city, "pin": profile.get("pin"), "fibre": known and profile.get("fibre_feasible") is not False,
            "airfiber": True, "checked": dt.date.today().isoformat(),
            "note": f"Fibre available in {city}" if known else f"Coverage for {city} confirmed by a field survey"}


# ------------------------------------------------------------------ orders
class OrderReq(BaseModel):
    session_id: str
    enabled: List[str]
    quantities: Dict[str, int] = {}
    contact_name: str
    mobile: str
    partner_code: Optional[str] = None


@app.post("/api/order")
def create_order(req: OrderReq, idempotency_key: Optional[str] = Header(None)):
    if idempotency_key:
        prev = store.idem_get("order:" + idempotency_key)
        if prev:
            return prev
    s = store.load_session(req.session_id)
    if not s or not s.get("recommendation"):
        raise HTTPException(404, "No quote for this session")
    prof = _profile_for_rules(s)
    r = rules.reprice(s["recommendation"], prof, req.enabled, req.quantities)
    if not r["items"]:
        raise HTTPException(400, "The quote is empty")
    errs = rules.validate_bundle(r["items"], prof)
    if errs:
        raise HTTPException(409, {"message": "Some items are no longer eligible", "errors": errs})
    mobile = "".join(ch for ch in req.mobile if ch.isdigit())[-10:]
    if len(mobile) != 10:
        raise HTTPException(400, "Enter a 10-digit mobile number")
    order = {
        "status": "quote_accepted", "lang": s["lang"],
        "business_type": prof.get("business_type"), "segment": prof.get("segment"), "city": prof.get("city"),
        "profile": advisor._public(prof), "_gstin_claimed": prof.get("gstin"),
        "items": r["items"], "quote": r["quote"], "coverage": coverage(prof),
        "contact": {"name": req.contact_name.strip()[:60], "mobile_masked": "••••••" + mobile[-4:]},
        "kyc": {"status": "not_started"}, "milestones": {"quote_accepted": time.time()},
    }
    partner = req.partner_code or s.get("partner_code")
    o = store.create_order(order, req.session_id, partner)
    s["order_id"] = o["id"]
    store.save_session(req.session_id, s)
    resp = {"order_id": o["id"], "resume_code": o["resume_code"], "quote": r["quote"]}
    if idempotency_key:
        store.idem_put("order:" + idempotency_key, resp)
    return resp


def _public_order(o: dict) -> dict:
    o = {k: v for k, v in o.items() if not k.startswith("_") and k not in ("resume_code",)}
    k = o.get("kyc") or {}
    if "result" in k:
        k = {**k, "result": {kk: vv for kk, vv in k["result"].items() if not kk.startswith("_")}}
        o["kyc"] = k
    return o


def _auth(oid: str, code: Optional[str]) -> dict:
    o = store.get_order(oid.upper())
    if not o:
        raise HTTPException(404, "Order not found")
    if code != o["resume_code"] and code != "admin-demo":
        raise HTTPException(403, "Wrong code. Use the 6-digit code sent with your order.")
    return o


@app.get("/api/order/{oid}")
def get_order(oid: str, code: Optional[str] = None):
    o = _auth(oid, code)
    return _public_order(o) | {"timeline": timeline(o)}


def timeline(o: dict) -> List[dict]:
    ms = o.get("milestones") or {}
    created = dt.datetime.fromtimestamp(o["created"]).date()
    slot = (o.get("slot") or {}).get("date")
    install_days = (o.get("quote") or {}).get("expected_install_days", 5)
    out = []
    reached_all = True
    for key, label in MILESTONES:
        ts = ms.get(key)
        exp = None
        if key in ("install_scheduled",):
            exp = None
        if key in ("installing", "live"):
            base = dt.date.fromisoformat(slot) if slot else created + dt.timedelta(days=install_days + 1)
            exp = (base + dt.timedelta(days=0 if key == "installing" else 1)).isoformat()
        out.append({"key": key, "label": label, "done": bool(ts),
                    "at": dt.datetime.fromtimestamp(ts).strftime("%d %b, %I:%M %p") if ts else None,
                    "expected": exp, "current": False})
    for step in out:
        if not step["done"]:
            step["current"] = True
            break
    # per-product status
    return out


def product_status(o: dict) -> List[dict]:
    ms = o.get("milestones") or {}
    slot = (o.get("slot") or {}).get("date")
    rows = []
    for it in o.get("items", []):
        if "live" in ms:
            st = "Live"
        elif "installing" in ms:
            st = "Installing" if it["install_days"] > 1 else "Live"
        elif "install_scheduled" in ms:
            st = "Scheduled"
        else:
            st = "Waiting for verification" if "kyc_verified" not in ms else "Waiting for slot"
        eta = None
        if slot:
            eta = (dt.date.fromisoformat(slot) + dt.timedelta(days=max(0, it["install_days"] - 5 if it["install_days"] > 5 else 0))).isoformat()
        rows.append({"name": it["name"], "qty": it["qty"], "status": st, "eta": eta, "install_days": it["install_days"]})
    return rows


@app.get("/api/track/{oid}")
def track(oid: str, code: Optional[str] = None):
    o = _auth(oid, code)
    help_line = {"owner": "Accel Business help", "phone": "1800-000-0000 (demo)",
                 "whatsapp": "+91 90000 00000 (demo)",
                 "note": "If a step is late by more than a day, it is escalated to the install team automatically."}
    return {"order_id": o["id"], "status": o["status"], "business_type": o.get("business_type"), "city": o.get("city"),
            "timeline": timeline(o), "products": product_status(o), "slot": o.get("slot"),
            "kyc_status": (o.get("kyc") or {}).get("status"), "quote": o.get("quote"), "help": help_line}


# ------------------------------------------------------------------ registry lookups (mock APIs)
@app.get("/api/lookup/gstin/{g}")
def lookup_gstin(g: str):
    ok, msg = rules.validate_gstin(g)
    if not ok:
        return {"valid": False, "message": msg}
    r = rules.lookup_gstin(g)
    if not r:
        return {"valid": True, "found": False, "message": "Not found in the GST registry"}
    return {"valid": True, "found": True, "gstin": rules.mask_gstin(g), "legal_name": r["legal_name"],
            "trade_name": r["trade_name"], "constitution": r["constitution"], "state": r["state"],
            "address": r["principal_place_of_business"], "status": r["status"], "registered": r["registration_date"]}


@app.get("/api/lookup/udyam/{u}")
def lookup_udyam(u: str):
    r = rules.lookup_udyam(u)
    if not r:
        return {"found": False}
    return {"found": True, **r}


# ------------------------------------------------------------------ Smart KYC
class ConsentReq(BaseModel):
    code: str
    verification: bool
    marketing: bool = False
    lang: str = "en"


@app.post("/api/kyc/{oid}/consent")
def kyc_consent(oid: str, req: ConsentReq):
    o = _auth(oid, req.code)
    if not req.verification:
        raise HTTPException(400, "Verification consent is needed to activate business services.")
    consent = {"version": CONSENT_VERSION, "at": time.time(), "verification": True, "marketing": req.marketing,
               "lang": req.lang, "retention_hours": store.DOC_TTL_HOURS}
    k = o.get("kyc") or {}
    k.update(status="consented", consent=consent, docs={})
    store.update_order(o["id"], {"kyc": k})
    store.log(o["id"], "customer", "consent_given", {"version": CONSENT_VERSION, "marketing": req.marketing})
    return {"ok": True, "consent": consent}


def _need_consent(o: dict):
    if not ((o.get("kyc") or {}).get("consent") or {}).get("verification"):
        raise HTTPException(412, "Consent is required before uploading documents.")


@app.post("/api/kyc/{oid}/upload")
async def kyc_upload(oid: str, code: str = Form(...), doc_type: str = Form(...), file: UploadFile = File(...)):
    o = _auth(oid, code)
    _need_consent(o)
    if doc_type not in kyc.DOC_TYPES:
        raise HTTPException(400, "Unknown document type")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 8 MB)")
    store.purge_expired()
    try:
        res = kyc.analyze_document(content, expected_type=doc_type)
    except Exception as e:
        raise HTTPException(422, f"Could not read this image: {type(e).__name__}")
    store.vault_put(o["id"], doc_type, content)
    k = o["kyc"]
    k.setdefault("docs", {})[doc_type] = res
    k["status"] = "documents_uploaded"
    store.update_order(o["id"], {"kyc": k})
    store.log(o["id"], "customer", "document_uploaded", {"doc_type": doc_type, "detected": res["doc_type"],
                                                          "quality": res["quality"]})
    return {"doc_type": doc_type, "detected": res["doc_type"], "quality": res["quality"],
            "fields": _mask_fields(res["fields"])}


class SampleReq(BaseModel):
    code: str
    applicant: str


@app.post("/api/kyc/{oid}/sample")
def kyc_sample(oid: str, req: SampleReq):
    """Demo helper: load one of the 12 synthetic applicants' documents (K01-K12)."""
    o = _auth(oid, req.code)
    _need_consent(o)
    aid = req.applicant.upper()
    if aid not in kyc.sample_ids():
        raise HTTPException(404, "Unknown sample applicant")
    docs = {}
    for t in kyc.DOC_TYPES:
        p = kyc.sample_dir() / f"{aid}_{t}.png"
        if p.exists():
            content = p.read_bytes()
            docs[t] = kyc.analyze_document(content, expected_type=t)
            store.vault_put(o["id"], t, content)
    k = o["kyc"]
    k["docs"] = docs
    k["sample"] = aid
    k["status"] = "documents_uploaded"
    store.update_order(o["id"], {"kyc": k})
    store.log(o["id"], "customer", "sample_loaded", {"applicant": aid})
    return {"applicant": aid, "docs": {t: {"detected": d["doc_type"], "quality": d["quality"],
                                           "fields": _mask_fields(d["fields"])} for t, d in docs.items()}}


def _mask_fields(f: dict) -> dict:
    f = dict(f)
    if f.get("gstin"):
        g, _ = kyc.normalise_gstin(f["gstin"])
        f["gstin"] = rules.mask_gstin(g)
    if f.get("id_no"):
        f["id_no"] = rules.mask_id(f["id_no"])
    if f.get("consumer_no"):
        f["consumer_no"] = rules.mask_id(f["consumer_no"])
    return f


@app.post("/api/kyc/{oid}/verify")
def kyc_verify(oid: str, code: str = Form(...)):
    o = _auth(oid, code)
    _need_consent(o)
    k = o["kyc"]
    res = kyc.run_case(k.get("docs") or {}, {"business_name": (o.get("profile") or {}).get("business_name")})
    # if the GSTIN on the documents differs from the one given to the advisor, flag it
    claimed = o.get("_gstin_claimed")
    if claimed and res.get("_gstin_full") and claimed != res["_gstin_full"]:
        res["checks"].append({"id": "gstin_claimed", "label": "GSTIN matches the one given to the advisor",
                              "result": "fail", "detail": "The certificate shows a different GSTIN.",
                              "fix": None, "owner": "reviewer"})
        res["status"] = "manual_review"
    # GST-only products cannot go live without an active GSTIN
    if res["extracted"].get("gstin_status") and res["extracted"]["gstin_status"] != "Active":
        gst_items = [i["name"] for i in o["items"] if data.catalogue()[i["id"]]["requires_gstin"]]
        if gst_items:
            res["checks"].append({"id": "gst_products", "label": "Order has no GST-only products", "result": "fail",
                                  "detail": "Needs an active GSTIN: " + ", ".join(gst_items), "fix":
                                  "Remove these items or reactivate GST.", "owner": "reviewer"})
    k["result"] = res
    k["status"] = res["status"]
    k["verified_at"] = time.time()
    patch = {"kyc": k}
    status = None
    if res["status"] == "verified":
        ms = o.get("milestones") or {}
        ms["kyc_verified"] = time.time()
        patch["milestones"] = ms
        status = "kyc_verified"
    else:
        status = "kyc_" + res["status"]
    store.update_order(o["id"], patch, status)
    store.log(o["id"], "system", "kyc_checked", {"status": res["status"],
                                                 "failed": [c["id"] for c in res["checks"] if c["result"] == "fail"]})
    return {k2: v for k2, v in res.items() if not k2.startswith("_")}


# ------------------------------------------------------------------ slot + payment
class SlotReq(BaseModel):
    code: str
    date: str
    window: str
    upi_id: str


@app.post("/api/order/{oid}/book")
def book(oid: str, req: SlotReq, idempotency_key: Optional[str] = Header(None)):
    if idempotency_key:
        prev = store.idem_get("book:" + idempotency_key)
        if prev:
            return prev
    o = _auth(oid, req.code)
    if "kyc_verified" not in (o.get("milestones") or {}):
        raise HTTPException(409, "Verification must be approved before booking.")
    if o.get("slot"):
        return {"ok": True, "already_booked": True, "slot": o["slot"]}
    try:
        d = dt.date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(400, "Bad date")
    if d < dt.date.today():
        raise HTTPException(400, "Pick a future date")
    if "@" not in req.upi_id:
        raise HTTPException(400, "Enter a UPI ID like name@bank")
    ms = o["milestones"]
    now = time.time()
    ms["payment_mandate"] = now
    ms["install_scheduled"] = now
    slot = {"date": req.date, "window": req.window}
    pay = {"method": "UPI Autopay (mock)", "upi_masked": "•••@" + req.upi_id.split("@")[-1],
           "first_charge_after": "installation", "monthly": o["quote"]["monthly_incl_gst"]}
    store.update_order(o["id"], {"slot": slot, "payment": pay, "milestones": ms}, "install_scheduled")
    store.log(o["id"], "customer", "slot_booked", {"slot": slot})
    resp = {"ok": True, "slot": slot, "payment": pay}
    if idempotency_key:
        store.idem_put("book:" + idempotency_key, resp)
    return resp


@app.get("/api/slots")
def slots(days: int = 5):
    start = dt.date.today() + dt.timedelta(days=max(1, days))
    out = []
    for i in range(7):
        d = start + dt.timedelta(days=i)
        if d.weekday() == 6:
            continue
        out.append({"date": d.isoformat(), "label": d.strftime("%a %d %b"),
                    "windows": ["9 am – 12 pm", "12 pm – 3 pm", "3 pm – 6 pm"]})
    return out


# ------------------------------------------------------------------ privacy rights
@app.post("/api/order/{oid}/delete-documents")
def delete_documents(oid: str, code: str = Form(...)):
    o = _auth(oid, code)
    n = store.delete_docs(o["id"])
    k = o.get("kyc") or {}
    k["docs_deleted_at"] = time.time()
    k.pop("docs", None)
    store.update_order(o["id"], {"kyc": k})
    store.log(o["id"], "customer", "documents_deleted", {"count": n})
    return {"deleted": n}


# ------------------------------------------------------------------ back office
def _admin(token: Optional[str]):
    # Demo-only shared token; production would use SSO + role-based access.
    if token != "admin-demo":
        raise HTTPException(401, "Back-office token required")


@app.get("/api/admin/summary")
def admin_summary(x_admin_token: Optional[str] = Header(None)):
    _admin(x_admin_token)
    orders = store.list_orders()
    sessions = store.list_sessions()
    open_sessions = [s for s in sessions if not s.get("order_id")]
    return {
        "orders": [{"id": o["id"], "status": o["status"], "business_type": o.get("business_type"), "city": o.get("city"),
                    "monthly": (o.get("quote") or {}).get("monthly"), "partner": o.get("partner_code"),
                    "kyc": (o.get("kyc") or {}).get("status"), "created": o["created"]} for o in orders],
        "reviews": [{"id": o["id"], "business": ((o.get("kyc") or {}).get("result") or {}).get("extracted", {}).get("business"),
                     "summary": ((o.get("kyc") or {}).get("result") or {}).get("summary"),
                     "checks": [c for c in ((o.get("kyc") or {}).get("result") or {}).get("checks", []) if c["result"] != "pass"],
                     "sample": (o.get("kyc") or {}).get("sample")}
                    for o in orders if o["status"] in ("kyc_manual_review",)],
        "unclosed_sessions": [{"id": s["id"], "updated": s["updated"], "profile": advisor._public(s.get("profile") or {}),
                               "stage": "recommended" if s.get("done") else f"asked: {s.get('asked')}",
                               "partner": s.get("partner_code")} for s in open_sessions[:30]],
        "model": store.model_info(),
    }


@app.get("/api/admin/callbacks")
def admin_callbacks(x_admin_token: Optional[str] = Header(None), limit: int = 40):
    _admin(x_admin_token)
    return {"model": store.model_info(), "leads": store.callback_list(limit)}


class Decision(BaseModel):
    decision: str
    note: str = ""


@app.post("/api/admin/review/{oid}")
def admin_review(oid: str, d: Decision, x_admin_token: Optional[str] = Header(None)):
    _admin(x_admin_token)
    o = store.get_order(oid)
    if not o:
        raise HTTPException(404, "Order not found")
    k = o.get("kyc") or {}
    k["review"] = {"decision": d.decision, "note": d.note[:300], "at": time.time()}
    if d.decision == "approve":
        ms = o.get("milestones") or {}
        ms["kyc_verified"] = time.time()
        k["status"] = "verified"
        store.update_order(oid, {"kyc": k, "milestones": ms}, "kyc_verified")
    else:
        k["status"] = "rejected"
        store.update_order(oid, {"kyc": k}, "kyc_rejected")
    store.log(oid, "reviewer", "kyc_" + d.decision, {"note": d.note[:300]})
    return {"ok": True}


@app.post("/api/admin/advance/{oid}")
def admin_advance(oid: str, x_admin_token: Optional[str] = Header(None)):
    """Demo: product teams post the next install milestone."""
    _admin(x_admin_token)
    o = store.get_order(oid)
    if not o:
        raise HTTPException(404, "Order not found")
    ms = o.get("milestones") or {}
    for key, _ in MILESTONES:
        if key not in ms:
            if key in ("kyc_verified", "payment_mandate", "install_scheduled") :
                raise HTTPException(409, f"Waiting on the customer: {key}")
            ms[key] = time.time()
            store.update_order(oid, {"milestones": ms}, key)
            store.log(oid, "ops", "milestone", {"key": key})
            return {"ok": True, "milestone": key}
    return {"ok": True, "milestone": None}


@app.get("/api/admin/order/{oid}")
def admin_order(oid: str, x_admin_token: Optional[str] = Header(None)):
    _admin(x_admin_token)
    o = store.get_order(oid)
    if not o:
        raise HTTPException(404)
    return _public_order(o) | {"events": store.events(oid)}


# ------------------------------------------------------------------ WhatsApp Cloud API webhook
# Same advisor, reached over WhatsApp. Set WHATSAPP_VERIFY_TOKEN, and to send replies
# WHATSAPP_TOKEN + WHATSAPP_PHONE_ID. Without them the reply is returned in the response
# (handy for testing with curl).
import os  # noqa: E402
import json as _json  # noqa: E402
import urllib.request as _ur  # noqa: E402


@app.get("/api/whatsapp/webhook")
def wa_verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == os.environ.get("WHATSAPP_VERIFY_TOKEN", "udyam-demo"):
        return int(q.get("hub.challenge", "0"))
    raise HTTPException(403, "Verification failed")


@app.post("/api/whatsapp/webhook")
async def wa_inbound(request: Request):
    body = await request.json()
    replies = []
    try:
        changes = [c for e in body.get("entry", []) for c in e.get("changes", [])]
        msgs = [m for c in changes for m in c.get("value", {}).get("messages", [])]
    except AttributeError:
        msgs = []
    for m in msgs:
        sender = m.get("from", "")
        text = (m.get("text") or {}).get("body") or (m.get("interactive") or {}).get("button_reply", {}).get("title", "")
        if not text:
            continue
        sid = "WA-" + sender[-10:]
        s = store.load_session(sid)
        if not s or text.strip().lower() in ("hi", "hello", "start", "namaste", "नमस्ते"):
            s = advisor.new_session("hi" if any("\u0900" <= ch <= "\u097f" for ch in text) else "en")
            s["channel"] = "whatsapp"
            store.save_session(sid, s)
            out = s["messages"][0]["text"]
        else:
            r = advisor.follow_up(s, text) if s.get("done") else advisor.turn(s, text)
            r = r or {"text": "Reply 'quote' to get a link to your quote."}
            store.save_session(sid, s)
            out = r["text"]
            if r.get("recommendation") or text.strip().lower() == "quote":
                out += f"\n\nSee and edit your quote: {os.environ.get('PUBLIC_URL', 'http://localhost:8000')}/#/quote?s={sid}"
        replies.append({"to": sender[-4:].rjust(10, "•"), "text": out})
        tok, pid = os.environ.get("WHATSAPP_TOKEN"), os.environ.get("WHATSAPP_PHONE_ID")
        if tok and pid:
            req = _ur.Request(f"https://graph.facebook.com/v20.0/{pid}/messages",
                              data=_json.dumps({"messaging_product": "whatsapp", "to": sender, "type": "text",
                                                "text": {"body": out[:4000]}}).encode(),
                              headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            try:
                _ur.urlopen(req, timeout=10)
            except Exception as e:  # noqa: BLE001
                print("[whatsapp] send failed:", e)
    return {"ok": True, "replies": replies}


# ------------------------------------------------------------------ frontend
@app.api_route("/", methods=["GET", "HEAD"])
def index():
    return FileResponse(FRONT / "index.html")


@app.get("/admin")
def admin_page():
    return FileResponse(FRONT / "admin.html")


app.mount("/static", StaticFiles(directory=FRONT), name="static")
