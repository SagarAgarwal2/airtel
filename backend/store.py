"""SQLite persistence, encrypted document vault, audit log and propensity scoring."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import data

ROOT = Path(__file__).resolve().parent.parent
VAR = Path(os.environ.get("APP_VAR_DIR", ROOT / "var"))
VAR.mkdir(parents=True, exist_ok=True)
DB_PATH = VAR / "udyam.db"
VAULT = VAR / "vault"
VAULT.mkdir(exist_ok=True)
DOC_TTL_HOURS = 24  # demo retention for uploaded KYC documents

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created REAL, updated REAL, state TEXT);
        CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, created REAL, updated REAL, status TEXT,
            resume_code TEXT, session_id TEXT, partner_code TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, order_id TEXT,
            actor TEXT, kind TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS idem (key TEXT PRIMARY KEY, ts REAL, response TEXT);
        CREATE TABLE IF NOT EXISTS docs (id TEXT PRIMARY KEY, order_id TEXT, doc_type TEXT, path TEXT, created REAL);
        """)


# ---------------------------------------------------------------- sessions
def save_session(sid: str, state: dict):
    now = time.time()
    with _lock, _conn() as c:
        c.execute("INSERT INTO sessions(id,created,updated,state) VALUES(?,?,?,?) "
                  "ON CONFLICT(id) DO UPDATE SET updated=excluded.updated, state=excluded.state",
                  (sid, now, now, json.dumps(state, ensure_ascii=False)))


def load_session(sid: str) -> Optional[dict]:
    with _conn() as c:
        r = c.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
    return json.loads(r["state"]) if r else None


def list_sessions(limit: int = 200) -> List[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, created, updated, state FROM sessions ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "created": r["created"], "updated": r["updated"], **json.loads(r["state"])} for r in rows]


# ---------------------------------------------------------------- orders
def new_order_id() -> str:
    return "UD-" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))


def create_order(order: dict, session_id: str, partner_code: Optional[str]) -> dict:
    oid = new_order_id()
    code = f"{secrets.randbelow(1000000):06d}"
    now = time.time()
    order = {**order, "id": oid}
    with _lock, _conn() as c:
        c.execute("INSERT INTO orders(id,created,updated,status,resume_code,session_id,partner_code,data) VALUES(?,?,?,?,?,?,?,?)",
                  (oid, now, now, order.get("status", "quote_accepted"), code, session_id, partner_code,
                   json.dumps(order, ensure_ascii=False)))
    log(oid, "customer", "order_created", {"partner_code": partner_code})
    return {**order, "resume_code": code}


def get_order(oid: str) -> Optional[dict]:
    with _conn() as c:
        r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not r:
        return None
    o = json.loads(r["data"])
    o.update(id=r["id"], status=r["status"], created=r["created"], updated=r["updated"],
             partner_code=r["partner_code"], resume_code=r["resume_code"], session_id=r["session_id"])
    return o


def update_order(oid: str, patch: dict, status: Optional[str] = None) -> dict:
    o = get_order(oid)
    if o is None:
        raise KeyError(oid)
    for k in ("id", "created", "updated", "partner_code", "resume_code", "session_id"):
        o.pop(k, None)
    o.update(patch)
    if status:
        o["status"] = status
    with _lock, _conn() as c:
        c.execute("UPDATE orders SET data=?, status=?, updated=? WHERE id=?",
                  (json.dumps(o, ensure_ascii=False), o.get("status"), time.time(), oid))
    return get_order(oid)


def list_orders() -> List[dict]:
    with _conn() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM orders ORDER BY updated DESC").fetchall()]
    return [get_order(i) for i in ids]


# ---------------------------------------------------------------- audit log (identifiers masked by callers)
def log(order_id: Optional[str], actor: str, kind: str, detail: Any = None):
    with _lock, _conn() as c:
        c.execute("INSERT INTO events(ts,order_id,actor,kind,detail) VALUES(?,?,?,?,?)",
                  (time.time(), order_id, actor, kind, json.dumps(detail or {}, ensure_ascii=False)))


def events(order_id: str) -> List[dict]:
    with _conn() as c:
        rows = c.execute("SELECT ts, actor, kind, detail FROM events WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
    return [{"ts": r["ts"], "actor": r["actor"], "kind": r["kind"], "detail": json.loads(r["detail"])} for r in rows]


# ---------------------------------------------------------------- idempotency
def idem_get(key: str) -> Optional[dict]:
    with _conn() as c:
        r = c.execute("SELECT response FROM idem WHERE key=?", (key,)).fetchone()
    return json.loads(r["response"]) if r else None


def idem_put(key: str, response: dict):
    with _lock, _conn() as c:
        c.execute("INSERT OR IGNORE INTO idem(key,ts,response) VALUES(?,?,?)", (key, time.time(), json.dumps(response)))


# ---------------------------------------------------------------- encrypted document vault
def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    key = os.environ.get("VAULT_KEY")
    kp = VAR / "vault.key"
    if not key:
        if not kp.exists():
            kp.write_bytes(Fernet.generate_key())
            try:
                os.chmod(kp, 0o600)
            except OSError:
                pass
        key = kp.read_bytes().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def vault_put(order_id: str, doc_type: str, content: bytes) -> str:
    did = secrets.token_hex(8)
    f = _fernet()
    blob = f.encrypt(content) if f else content
    p = VAULT / f"{did}.bin"
    p.write_bytes(blob)
    with _lock, _conn() as c:
        c.execute("DELETE FROM docs WHERE order_id=? AND doc_type=?", (order_id, doc_type))
        c.execute("INSERT INTO docs(id,order_id,doc_type,path,created) VALUES(?,?,?,?,?)",
                  (did, order_id, doc_type, str(p), time.time()))
    return did


def purge_expired() -> int:
    cutoff = time.time() - DOC_TTL_HOURS * 3600
    n = 0
    with _lock, _conn() as c:
        for r in c.execute("SELECT id, path FROM docs WHERE created < ?", (cutoff,)).fetchall():
            try:
                Path(r["path"]).unlink()
            except FileNotFoundError:
                pass
            n += 1
        c.execute("DELETE FROM docs WHERE created < ?", (cutoff,))
    return n


def delete_docs(order_id: str) -> int:
    with _lock, _conn() as c:
        rows = c.execute("SELECT path FROM docs WHERE order_id=?", (order_id,)).fetchall()
        for r in rows:
            try:
                Path(r["path"]).unlink()
            except FileNotFoundError:
                pass
        c.execute("DELETE FROM docs WHERE order_id=?", (order_id,))
    return len(rows)


# ---------------------------------------------------------------- propensity
_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        _MODEL = json.loads((Path(__file__).parent / "propensity_model.json").read_text())
    return _MODEL


def propensity(lead: Dict[str, str]) -> float:
    m = _model()
    z = m["intercept"]
    for c in m["categorical"]:
        z += m["weights"].get(f"{c}={lead.get(c, '')}", 0.0)
    for k, (col, scale, cap) in m["numeric"].items():
        try:
            v = float(lead.get(col) or 0)
        except ValueError:
            v = 0.0
        if cap:
            v = min(v, cap)
        z += m["weights"].get(k, 0.0) * v / scale
    return 1 / (1 + math.exp(-z))


def model_info() -> dict:
    m = _model()
    return {"auc_holdout": m["auc_holdout"], "top20_capture": m["top20_capture"]}


def callback_list(limit: int = 50) -> List[dict]:
    rows = []
    for r in data.leads():
        if r["outcome"] == "Activated":
            continue
        if r["drop_reason"] in ("Wrong or invalid number", "Only wanted a mobile plan"):
            continue
        rows.append({
            "lead_id": r["lead_id"], "business": r["business_name"], "type": r["business_type"],
            "segment": r["segment"], "city": r["city"], "source": r["lead_source"], "stage": r["stage_reached"],
            "drop_reason": r["drop_reason"], "contact": r["contact_name"].split()[0] + " •••",
            "language": r["preferred_language"], "score": round(propensity(r), 3),
        })
    rows.sort(key=lambda x: -x["score"])
    return rows[:limit]
