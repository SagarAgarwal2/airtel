"""Conversational advisor.

Flow: the owner answers up to six short questions (they can also say everything in
one message). Each message is parsed by a rule-based extractor and, when an LLM key
is set, by the LLM too. Once the profile is complete, rules.recommend() builds the
bundle. The LLM only phrases questions and the explanation; it never prices.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from . import data, llm, rules

SLOTS = ["business_type", "location", "employees", "tools", "gst", "budget"]

Q = {
    "en": {
        "business_type": "Namaste! I'm the Accel Business advisor. What kind of business do you run? "
                         "(for example: kirana store, dental clinic, CA firm, restaurant chain, textile unit)",
        "location": "Which city or PIN code is it in, and how many locations do you have?",
        "employees": "How many people work there in total?",
        "tools": "What do you use today for internet, and what would you like to do better? "
                 "(for example: billing/UPI, CCTV, email, WhatsApp for customers, backup internet)",
        "gst": "Do you have a GSTIN? Type it and I will fill in your details, or just say no.",
        "budget": "Roughly how much would you like to spend per month? You can also say 'not sure'.",
    },
    "hi": {
        "business_type": "नमस्ते! मैं Accel Business सलाहकार हूँ। आपका व्यवसाय किस तरह का है? "
                         "(जैसे: किराना स्टोर, डेंटल क्लिनिक, CA फर्म, रेस्टोरेंट चेन, टेक्सटाइल यूनिट)",
        "location": "आपका व्यवसाय किस शहर या पिन कोड में है, और आपकी कितनी शाखाएँ हैं?",
        "employees": "कुल कितने लोग काम करते हैं?",
        "tools": "अभी इंटरनेट के लिए क्या इस्तेमाल करते हैं, और क्या बेहतर करना चाहते हैं? "
                 "(जैसे: बिलिंग/UPI, CCTV, ईमेल, ग्राहकों के लिए WhatsApp, बैकअप इंटरनेट)",
        "gst": "क्या आपके पास GSTIN है? नंबर लिखें, मैं आपकी जानकारी भर दूँगा। नहीं है तो 'नहीं' लिखें।",
        "budget": "हर महीने लगभग कितना खर्च करना चाहेंगे? पक्का नहीं है तो 'पता नहीं' लिखें।",
    },
}
CHIPS = {
    "en": {
        "business_type": ["Kirana store", "Dental clinic", "CA firm", "Restaurant chain", "Textile unit"],
        "location": ["Jaipur, 1 shop", "Mumbai, 1 office", "Pune, 3 outlets"],
        "employees": ["1–2", "5", "15", "40"],
        "tools": ["Mobile hotspot, need UPI billing", "Home broadband, need email & backup", "Need CCTV and WhatsApp"],
        "gst": ["No GSTIN", "Yes, I have one"],
        "budget": ["Under ₹2,000", "₹2,000–5,000", "₹5,000–15,000", "Not sure"],
    },
    "hi": {
        "business_type": ["किराना स्टोर", "डेंटल क्लिनिक", "CA फर्म", "रेस्टोरेंट चेन", "टेक्सटाइल यूनिट"],
        "location": ["जयपुर, 1 दुकान", "मुंबई, 1 ऑफिस", "पुणे, 3 आउटलेट"],
        "employees": ["1–2", "5", "15", "40"],
        "tools": ["मोबाइल हॉटस्पॉट, UPI बिलिंग चाहिए", "ईमेल और बैकअप चाहिए", "CCTV और WhatsApp चाहिए"],
        "gst": ["GSTIN नहीं है", "हाँ, GSTIN है"],
        "budget": ["₹2,000 से कम", "₹2,000–5,000", "₹5,000–15,000", "पता नहीं"],
    },
}

HI_BUSINESS = {"किराना": "Kirana store", "डेंटल": "Dental clinic", "क्लिनिक": "Dental clinic", "दुकान": "Kirana store",
               "सैलून": "Salon", "बेकरी": "Bakery", "फार्मेसी": "Pharmacy", "मेडिकल": "Pharmacy", "रेस्टोरेंट": "Restaurant chain",
               "टेक्सटाइल": "Textile unit", "कोचिंग": "Coaching centre", "होटल": "Budget hotel group", "जिम": "Gym chain",
               "वकील": "Law office", "ट्रैवल": "Travel agency", "प्रिंटिंग": "Printing press", "फैक्ट्री": "Packaging unit"}
HI_CITY = {"जयपुर": "jaipur", "दिल्ली": "delhi", "मुंबई": "mumbai", "पुणे": "pune", "लखनऊ": "lucknow", "पटना": "patna",
           "इंदौर": "indore", "भोपाल": "bhopal", "नागपुर": "nagpur", "अहमदाबाद": "ahmedabad", "सूरत": "surat",
           "कोलकाता": "kolkata", "चेन्नई": "chennai", "बेंगलुरु": "bengaluru", "हैदराबाद": "hyderabad",
           "लुधियाना": "ludhiana", "वडोदरा": "vadodara", "नाशिक": "nashik", "कोच्चि": "kochi"}
EXTRA_TYPES = {
    "kirana": "Kirana store", "grocery": "Kirana store", "general store": "Kirana store",
    "clinic": "Dental clinic", "doctor": "Dental clinic", "hospital": "Diagnostic lab", "lab": "Diagnostic lab",
    "chartered accountant": "CA firm", "ca ": "CA firm", "accountant": "CA firm", "lawyer": "Law office",
    "advocate": "Law office", "coaching": "Coaching centre", "tuition": "Coaching centre", "school": "Pre-school chain",
    "restaurant": "Restaurant chain", "cafe": "Restaurant chain", "hotel": "Budget hotel group", "gym": "Gym chain",
    "garment": "Textile unit", "textile": "Textile unit", "auto parts": "Auto-parts unit", "plastic": "Plastic moulding unit",
    "food processing": "Food processing unit", "packaging": "Packaging unit",
    "medical store": "Pharmacy", "chemist": "Pharmacy", "beauty": "Salon", "parlour": "Salon",
    "real estate": "Real estate agency", "travel": "Travel agency", "insurance": "Insurance agency",
    "architect": "Architecture studio", "printing": "Printing press", "furniture": "Furniture workshop",
    "factory": "Packaging unit", "manufactur": "Packaging unit", "workshop": "Furniture workshop",
    "shop": "Kirana store", "store": "Kirana store", "office": "CA firm",
}
PIN_PREFIX = {"110": "delhi", "400": "mumbai", "411": "pune", "560": "bengaluru", "600": "chennai", "500": "hyderabad",
              "700": "kolkata", "380": "ahmedabad", "302": "jaipur", "226": "lucknow", "141": "ludhiana",
              "452": "indore", "462": "bhopal", "440": "nagpur", "422": "nashik", "800": "patna", "395": "surat",
              "390": "vadodara", "530": "visakhapatnam", "682": "kochi", "641": "coimbatore", "570": "mysuru"}
INTERNET = {"hotspot": "Mobile hotspot", "mobile data": "Mobile hotspot", "home broadband": "Home broadband",
            "broadband": "Business broadband", "leased": "Leased line", "wifi": "Home broadband", "jio": "Home broadband",
            "nothing": "None", "no internet": "None", "हॉटस्पॉट": "Mobile hotspot", "ब्रॉडबैंड": "Home broadband"}


# ---------------------------------------------------------------- rule-based extraction
def _num(text: str, words: List[str]) -> Optional[int]:
    t = text.lower()
    for w in words:
        m = re.search(r"(\d{1,4})\s*(?:\+|-|–)?\s*(?:\d{1,4}\s*)?(?:" + w + r")", t)
        if m:
            return int(m.group(1))
    return None


def heuristic_extract(text: str, asked: Optional[str], profile: dict) -> dict:
    t = " " + text.lower().replace("₹", " rs ").replace(",", "") + " "
    up: dict = {}
    # business type
    bt = None
    for k in sorted(data.business_types(), key=len, reverse=True):
        if k in t:
            bt = k.title() if k != "ca firm" else "CA firm"
            break
    if not bt:
        for k, v in list(EXTRA_TYPES.items()) + list(HI_BUSINESS.items()):
            if k in t:
                bt = v
                break
    if bt and (asked == "business_type" or not profile.get("business_type")):
        up["business_type"] = bt
    # city / pin
    pin = re.search(r"\b(\d{6})\b", t)
    city = data.find_city(t)
    if not city:
        for k, v in HI_CITY.items():
            if k in text:
                city = data.city_index().get(v)
    if pin:
        up["pin"] = pin.group(1)
        if not city and pin.group(1)[:3] in PIN_PREFIX:
            city = data.city_index().get(PIN_PREFIX[pin.group(1)[:3]])
    if city:
        up.update(city=city["city"], city_tier=city["tier"], state=city["state"])
    elif asked == "location" and re.search(r"[a-z]{3,}", t):
        word = re.findall(r"[a-z]{3,}", t)[0]
        up.update(city=word.title(), city_tier=2, city_unknown=True)
    # sites
    sites = _num(t, ["sites?", "locations?", "branch(?:es)?", "outlets?", "stores?", "shops?", "offices?",
                     "clinics?", "units?", "शाखा", "आउटलेट", "दुकान"])
    if sites is None and asked == "location":
        if re.search(r"\b(one|single|1)\b", t) or "एक" in text:
            sites = 1
    if sites is not None and 0 < sites < 200:
        up["sites"] = sites
    elif asked == "location" and city:
        up.setdefault("sites", profile.get("sites") or 1)
    # employees
    emp = _num(t, ["people", "staff", "employees?", "members?", "workers?", "persons?", "लोग", "कर्मचारी"])
    if emp is None and asked == "employees":
        m = re.search(r"(\d{1,4})", t)
        if m:
            emp = int(m.group(1))
        elif re.search(r"\b(just me|only me|myself|alone)\b", t):
            emp = 1
    if emp:
        up["employees"] = emp
    # GSTIN
    g = re.search(r"\b(\d{2}[a-z]{5}\d{4}[a-z][1-9a-z]z[0-9a-z])\b", t)
    if g:
        up["gstin"] = g.group(1).upper()
        up["has_gstin"] = True
    elif asked == "gst" or "gst" in t:
        if re.search(r"\b(no|not|don't|dont|nahi|nahin)\b", t) or "नहीं" in text:
            up["has_gstin"] = False
        elif re.search(r"\b(yes|have|haan|ha)\b", t) or "हाँ" in text or "हां" in text:
            up["has_gstin"] = True
    # internet & needs
    for k, v in INTERNET.items():
        if k in t:
            up["current_internet"] = v
            break
    needs = set(profile.get("needs") or [])
    for need, kws in rules.NEED_KEYWORDS.items():
        if need == "sims":
            continue
        if any(k in t for k in kws):
            needs.add(need)
    if ("backup" in t or "बैकअप" in text) and "failover" not in needs and "backup_data" not in needs:
        needs.add("failover" if any(w in t for w in ("internet", "connection", "इंटरनेट")) else "backup_data")
    if needs != set(profile.get("needs") or []):
        up["needs"] = sorted(needs)
    if asked == "tools" and "needs" not in up and "current_internet" not in up:
        up["tools_answered"] = True
    if any(x in t for x in ["fibre not", "no fibre", "fiber not", "no fiber"]):
        up["fibre_feasible"] = False
    # budget (ignore GSTIN / PIN digits)
    tb = re.sub(r"\b\d{2}[a-z]{5}\d{4}[a-z][1-9a-z]z[0-9a-z]\b|\b\d{6}\b(?!\s*(?:rs|/|per|a month|monthly))", " ", t)
    if re.search(r"not sure|no idea|don't know|dont know|pata nahi|any budget", tb) or "पता नहीं" in text:
        if asked == "budget" or "budget" in tb:
            up["budget"] = 0
    else:
        amt = None
        m = re.search(r"(?:budget|rs|under|below|upto|up to|around|about|max|within)\s*(?:of|is|:)?\s*(?:rs)?\s*(\d{1,3}(?:\.\d)?\s*k|\d{3,6})"
                      r"(?:\s*(?:-|–|to)\s*(?:rs)?\s*(\d{1,3}\s*k|\d{3,6}))?", tb)
        if not m:
            m = re.search(r"(\d{1,3}\s*k|\d{3,6})(?:\s*(?:-|–|to)\s*(\d{1,3}\s*k|\d{3,6}))?\s*(?:rs|rupees|per month|/month|a month|monthly|pm\b)", tb)
        if not m and asked == "budget":
            m = re.search(r"(\d{1,3}\s*k|\d{3,6})(?:\s*(?:-|–|to)\s*(\d{1,3}\s*k|\d{3,6}))?", tb)
        if m:
            v = m.group(2) or m.group(1)
            v = v.replace(" ", "")
            amt = int(float(v[:-1]) * 1000) if v.endswith("k") else int(v)
            if 200 <= amt <= 1000000:
                up["budget"] = amt
    # headcount words
    if "employees" not in up:
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                 "twelve": 12, "fifteen": 15, "twenty": 20, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5}
        for w, n in words.items():
            if re.search(r"\b" + w + r"\b\s*(?:people|staff|employees|workers|लोग)", t) or (asked == "employees" and w in t.split()):
                up["employees"] = n
                break
        else:
            if re.search(r"\b(?:me and (?:my )?\w+|two of us|husband and wife|father and son)\b", t):
                up["employees"] = 2
            elif re.search(r"\b(just me|only me|myself|alone|akela)\b", t):
                up["employees"] = 1
    return up


LLM_SYSTEM = """You extract a small-business profile for a telecom advisor in India.
Return ONLY JSON with any of these keys you can fill from the owner's latest message
(use the conversation for context; omit keys you cannot fill; never guess):
business_type (short English, e.g. "Dental clinic", "Kirana store", "Restaurant chain"),
city (English city name), pin (6 digits), sites (int), employees (int),
has_gstin (bool), gstin (15 chars), current_internet (one of: Mobile hotspot, Home broadband,
Business broadband, Leased line, Mixed per site, None),
needs (list from: email, backup_data, security, firewall, failover, telephony, tollfree, sms,
whatsapp, website, pos, wifi, cctv, iot, fleet, sdwan, static_ip),
budget (int rupees per month, 0 if unsure), fibre_feasible (bool, only if stated).
The owner may write in Hindi, Hinglish or English."""


def llm_extract(text: str, profile: dict, asked: Optional[str]) -> dict:
    out = llm.complete_json(LLM_SYSTEM, json.dumps({"known_profile": _public(profile), "question_asked": asked,
                                                    "owner_message": text}, ensure_ascii=False))
    if not isinstance(out, dict):
        return {}
    clean: dict = {}
    for k in ["business_type", "city", "pin", "current_internet", "gstin"]:
        if isinstance(out.get(k), str) and out[k].strip():
            clean[k] = out[k].strip()
    for k in ["sites", "employees", "budget"]:
        try:
            if out.get(k) is not None:
                clean[k] = int(out[k])
        except (TypeError, ValueError):
            pass
    for k in ["has_gstin", "fibre_feasible"]:
        if isinstance(out.get(k), bool):
            clean[k] = out[k]
    if isinstance(out.get("needs"), list):
        clean["needs"] = [n for n in out["needs"] if n in rules.NEED_PRODUCT]
    if "city" in clean:
        c = data.find_city(clean["city"])
        if c:
            clean.update(city=c["city"], city_tier=c["tier"], state=c["state"])
        else:
            clean.update(city_tier=2, city_unknown=True)
    if "gstin" in clean:
        clean["gstin"] = clean["gstin"].upper().replace(" ", "")
        clean["has_gstin"] = True
    return clean


def _public(p: dict) -> dict:
    q = {k: v for k, v in p.items() if not k.startswith("_")}
    if q.get("gstin"):
        q["gstin"] = rules.mask_gstin(q["gstin"])
    return q


# ---------------------------------------------------------------- dialogue
def missing(profile: dict) -> List[str]:
    m = []
    if not profile.get("business_type"):
        m.append("business_type")
    if not profile.get("city"):
        m.append("location")
    if not profile.get("employees"):
        m.append("employees")
    if not (profile.get("needs") or profile.get("current_internet") or profile.get("tools_answered")):
        m.append("tools")
    if profile.get("has_gstin") is None and not profile.get("gstin"):
        m.append("gst")
    if profile.get("budget") is None:
        m.append("budget")
    return m


def new_session(lang: str = "en") -> dict:
    lang = "hi" if lang == "hi" else "en"
    return {"lang": lang, "profile": {}, "asked": "business_type", "done": False,
            "messages": [{"role": "assistant", "text": Q[lang]["business_type"]}]}


def turn(session: dict, text: str) -> dict:
    lang = session.get("lang", "en")
    prof = session["profile"]
    asked = session.get("asked")
    session["messages"].append({"role": "user", "text": text})

    up = heuristic_extract(text, asked, prof)
    used_llm = False
    if llm.provider():
        l = llm_extract(text, prof, asked)
        if l:
            used_llm = True
            if "needs" in l:
                l["needs"] = sorted(set(l["needs"]) | set(up.get("needs") or prof.get("needs") or []))
            up.update(l)
    if asked == "location" and "sites" not in up and not prof.get("sites") and (up.get("city") or prof.get("city")):
        up["sites"] = 1
    if asked == "tools" and not any(k in up for k in ("needs", "current_internet")):
        up["tools_answered"] = True
    if asked == "budget" and "budget" not in up:
        up["budget"] = 0
    if asked == "gst" and "has_gstin" not in up and "gstin" not in up:
        up["has_gstin"] = False if re.search(r"\b(no|nahi)\b", text.lower()) else None
        if up["has_gstin"] is None:
            up.pop("has_gstin")
    if "needs" in up:
        prof["explicit_needs"] = sorted(set(prof.get("explicit_needs") or []) | set(up["needs"]))
    prof.update({k: v for k, v in up.items() if v is not None})
    # never ask the same question more than twice: fall back to a sensible default
    if asked and asked in missing(prof):
        session.setdefault("attempts", {})
        session["attempts"][asked] = session["attempts"].get(asked, 0) + 1
        if session["attempts"][asked] >= 2:
            default = {"employees": {"employees": 1}, "tools": {"tools_answered": True}, "gst": {"has_gstin": False},
                       "budget": {"budget": 0}, "location": {"city": "your city", "city_tier": 2, "sites": 1, "city_unknown": True}}
            prof.update(default.get(asked, {}))
    if prof.get("business_type"):
        prof["segment"] = rules.infer_segment(prof)

    reply: Dict = {"used_llm": used_llm}
    extra = ""
    if "gstin" in up:
        ok, msg = rules.validate_gstin(prof["gstin"])
        rec = rules.lookup_gstin(prof["gstin"]) if ok else None
        if rec:
            extra = (f"Found {rec['trade_name']} ({rec['constitution']}) in {rec['state']}, status {rec['status']}. "
                     if lang == "en" else
                     f"{rec['trade_name']} ({rec['state']}) मिला, स्थिति: {rec['status']}। ")
            prof["business_name"] = rec["trade_name"]
            if rec["status"] != "Active":
                extra += ("Because it is not Active, I will only suggest products that do not need GST. "
                          if lang == "en" else "यह Active नहीं है, इसलिए केवल वे प्रोडक्ट सुझाऊँगा जिनमें GST ज़रूरी नहीं। ")
        else:
            extra = (f"That GSTIN did not check out ({msg}) I will continue without it for now. "
                     if lang == "en" else "यह GSTIN सही नहीं लगा, अभी इसके बिना आगे बढ़ते हैं। ")
            prof.pop("gstin", None)
            prof["has_gstin"] = False
    if up.get("city_unknown") and "city" in up:
        extra += (f"I don't have coverage data for {prof['city']} yet, so I've assumed a tier-2 city; a coverage check runs before checkout. "
                  if lang == "en" else f"{prof['city']} का कवरेज डेटा अभी नहीं है; चेकआउट से पहले कवरेज जाँच होगी। ")

    need = missing(prof)
    if need:
        nxt = need[0]
        session["asked"] = nxt
        q = Q[lang][nxt]
        if nxt == "business_type":
            q = q.replace("Namaste! I'm the Accel Business advisor. ", "").replace("नमस्ते! मैं Accel Business सलाहकार हूँ। ", "")
        msg = (extra + q).strip()
        session["messages"].append({"role": "assistant", "text": msg})
        reply.update(text=msg, chips=CHIPS[lang][nxt], asked=nxt, progress=len(SLOTS) - len(need))
        return reply

    # complete -> recommend
    p = dict(prof)
    if not p.get("budget"):
        p.pop("budget", None)
    rec = rules.recommend(p)
    session["recommendation"] = rec
    session["asked"] = None
    session["done"] = True
    explanation = explain(rec, prof, lang)
    msg = (extra + explanation).strip()
    session["messages"].append({"role": "assistant", "text": msg})
    reply.update(text=msg, recommendation=rec, progress=len(SLOTS), asked=None,
                 chips=["Show me the quote", "Make it cheaper", "Add CCTV"] if lang == "en"
                 else ["कोटेशन दिखाएँ", "सस्ता करें", "CCTV जोड़ें"])
    return reply


def follow_up(session: dict, text: str) -> Optional[dict]:
    """After a recommendation: handle 'cheaper', 'add X', 'remove X' by editing the profile and re-running rules."""
    t = text.lower()
    prof = session["profile"]
    lang = session.get("lang", "en")
    changed = False
    if any(w in t for w in ["cheaper", "less", "budget", "सस्ता", "kam"]):
        cur = session["recommendation"]["quote"]["monthly"]
        prof["budget"] = int(cur * 0.75)
        changed = True
    for need, kws in rules.NEED_KEYWORDS.items():
        if need in rules.NEED_PRODUCT and any(k in t for k in kws):
            if any(w in t for w in ["remove", "without", "no ", "हटाएँ", "nahi"]):
                prof["needs"] = [n for n in prof.get("needs", []) if n != need]
            else:
                prof["needs"] = sorted(set(prof.get("needs") or rules.DEFAULT_NEEDS[prof["segment"]]) | {need})
                prof["explicit_needs"] = sorted(set(prof.get("explicit_needs") or []) | {need})
            changed = True
    up = heuristic_extract(text, None, prof)
    for k in ("employees", "sites", "city", "city_tier", "gstin", "has_gstin"):
        if k in up:
            prof[k] = up[k]
            changed = True
    if not changed:
        return None
    p = dict(prof)
    if not p.get("budget"):
        p.pop("budget", None)
    rec = rules.recommend(p)
    session["recommendation"] = rec
    msg = explain(rec, prof, lang)
    session["messages"].append({"role": "user", "text": text})
    session["messages"].append({"role": "assistant", "text": msg})
    return {"text": msg, "recommendation": rec, "asked": None, "progress": len(SLOTS)}


def template_explain(rec: dict, prof: dict, lang: str) -> str:
    q = rec["quote"]
    names = ", ".join(i["name"] + (f" ×{i['qty']}" if i["qty"] > 1 else "") for i in rec["items"])
    if lang == "hi":
        s = (f"आपके {prof.get('business_type', 'व्यवसाय')} के लिए सुझाव: {names}। "
             f"कुल ₹{q['monthly']:,}/माह (GST अलग), सेटअप ₹{q['setup']:,}। ")
        if rec["excluded"]:
            s += "शामिल नहीं: " + "; ".join(f"{e['name']} ({e['reasons'][0]})" for e in rec["excluded"]) + "। "
        s += "अगले स्क्रीन पर आप ऐड-ऑन जोड़/हटा सकते हैं।"
        return s
    bt = prof.get('business_type', 'business')
    bt = bt if bt[:2].isupper() else bt.lower()
    s = (f"Here's what I'd suggest for your {bt}: {names}. "
         f"That's ₹{q['monthly']:,} a month before GST, with ₹{q['setup']:,} one-time setup. ")
    core = next((i for i in rec["items"] if i.get("core")), None)
    if core:
        s += f"{core['name']}: {core['why'][0].lower() + core['why'][1:]}. "
    if rec["excluded"]:
        s += "Not included: " + "; ".join(
            f"{e['name']} ({e['reasons'][0]}" + (f", {e['alternative'].lower()}" if e.get('alternative') else "") + ")"
            for e in rec["excluded"]) + ". "
    s += "You can switch add-ons on or off on the quote."
    return s


EXPLAIN_SYSTEM = """You are the Accel Business advisor. Write a short, warm explanation (3-4 sentences, under 90 words)
of the recommended bundle for a small-business owner, in {lang}. Use plain words, no product codes.
Mention why the main connection fits, and anything left out with its reason. Use ONLY the facts and
rupee amounts given in the JSON; do not invent prices, discounts, speeds or products. End by saying they can
toggle add-ons on the quote screen."""


def explain(rec: dict, prof: dict, lang: str) -> str:
    base = template_explain(rec, prof, lang)
    if not llm.provider():
        return base
    facts = {"business": prof.get("business_type"), "city": prof.get("city"),
             "items": [{"name": i["name"], "qty": i["qty"], "monthly_rs": i["monthly"], "why": i["why"]} for i in rec["items"]],
             "total_monthly_rs_before_gst": rec["quote"]["monthly"], "setup_rs": rec["quote"]["setup"],
             "left_out": [{"name": e["name"], "reason": e["reasons"][0]} for e in rec["excluded"]],
             "notes": rec["notes"]}
    out = llm.complete(EXPLAIN_SYSTEM.format(lang="Hindi (Devanagari)" if lang == "hi" else "English"),
                       json.dumps(facts, ensure_ascii=False))
    if not out:
        return base
    # guardrail: every rupee figure in the text must come from the facts
    allowed = {str(rec["quote"]["monthly"]), str(rec["quote"]["setup"])} | {str(i["monthly"]) for i in rec["items"]}
    for amt in re.findall(r"₹\s?([\d,]+)", out):
        if amt.replace(",", "") not in allowed:
            return base
    return out.strip()
