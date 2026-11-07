"""Plays 15 owner conversations through the advisor and checks every bundle against the catalogue rules.
Writes docs/advisor_scenarios.md. Run: python scripts/run_advisor_scenarios.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import advisor, rules, data  # noqa: E402

SCENARIOS = [
    ("Kirana, no GST, wants WhatsApp", "en", ["I run a kirana store in Jaipur, me and my son", "mobile hotspot, need UPI billing and WhatsApp for customers", "no", "not sure"]),
    ("CA firm, tier 1, GSTIN typed", "en", ["CA firm in Pune with 18 staff, GSTIN 27XUIXG0767D1ZP, need email, backup internet and cloud calling, budget 15000"]),
    ("Dental clinic, tight budget", "en", ["Dental clinic", "Lucknow", "4 people", "home broadband", "no", "2000"]),
    ("Restaurant chain, 4 outlets (Hindi)", "hi", ["रेस्टोरेंट चेन", "मुंबई, 4 आउटलेट", "60", "CCTV और बिलिंग चाहिए, बैकअप इंटरनेट भी", "हाँ", "पता नहीं"]),
    ("Textile unit, machines", "en", ["textile unit near 141001 with 35 workers, we have GST, machines need monitoring, around 20k per month"]),
    ("Salon, no GST, tiny budget", "en", ["salon in Surat, 3 staff, no GST, want whatsapp for customers and wifi for clients, under 1500"]),
    ("Cancelled GSTIN", "en", ["travel agency in Visakhapatnam, 6 people, 1 office", "need cloud calling and email", "37IHKXV5167L1ZS", "5000"]),
    ("Tier-2 office asking for 1 Gbps", "en", ["Law office in Nagpur, 30 staff, 1 office, have GST, need fast internet and email, no budget limit"]),
    ("Pharmacy chain, 3 branches, SD-WAN", "en", ["pharmacy chain with 3 branches in Bengaluru, 12 staff, GST yes", "need central management of all sites, billing and cctv", "10000"]),
    ("Gym chain, 2 sites, 8 staff, SD-WAN not eligible", "en", ["gym chain, 2 locations in Delhi, 8 staff, have gst, want sd-wan and cctv, budget 8000"]),
    ("Coaching centre, no fibre", "en", ["coaching centre in Patna, 10 teachers, 1 centre", "no fibre in our lane, need wifi and website", "no", "3000"]),
    ("Bakery with delivery vans", "en", ["Bakery in Kochi, 5 staff, one shop, no GST, we have 2 delivery vans to track, billing too, 3500 per month"]),
    ("Diagnostic lab, security", "en", ["diagnostic lab in Hyderabad, 14 employees, GSTIN 36ABCXD1234E1Z5", "need antivirus, data backup, email, toll free number", "12000"]),
    ("Furniture workshop, 8 staff (below leased-line min)", "en", ["furniture workshop in Jaipur, 8 workers, GST registered, need internet and cctv, budget 5000"]),
    ("Hindi kirana, chips only", "hi", ["किराना स्टोर", "जयपुर, 1 दुकान", "1–2", "मोबाइल हॉटस्पॉट, UPI बिलिंग चाहिए", "GSTIN नहीं है", "₹2,000 से कम"]),
]


def main():
    out = ["# Advisor test scenarios", "",
           "15 conversations played through the advisor in rule-based mode (no LLM key). Every bundle is re-checked "
           "against the catalogue rules (city tier, size, GSTIN, dependencies).", "",
           "| # | Scenario | Bundle (monthly, before GST) | Left out (reason) | Rule check |", "|---|---|---|---|---|"]
    failures = 0
    for n, (name, lang, msgs) in enumerate(SCENARIOS, 1):
        s = advisor.new_session(lang)
        for m in msgs:
            if s.get("done"):
                break
            advisor.turn(s, m)
        guard = 0
        while not s.get("done") and guard < 6:  # answer any remaining question with a neutral reply
            advisor.turn(s, {"tools": "nothing specific", "gst": "no", "budget": "not sure", "employees": "5",
                             "location": "Jaipur, 1 shop", "business_type": "shop"}.get(s.get("asked"), "ok"))
            guard += 1
        rec = s.get("recommendation")
        if not rec:
            out.append(f"| {n} | {name} | (no recommendation) | | ❌ |")
            failures += 1
            continue
        prof = dict(s["profile"])
        errs = rules.validate_bundle(rec["items"], prof)
        failures += bool(errs)
        items = ", ".join(i["name"] + (f" ×{i['qty']}" if i["qty"] > 1 else "") for i in rec["items"])
        excl = "; ".join(f"{e['name']} ({e['reasons'][0]})" for e in rec["excluded"]) or "–"
        out.append(f"| {n} | {name} | {items} · **₹{rec['quote']['monthly']:,}** | {excl} | {'✅' if not errs else '❌ ' + '; '.join(errs)} |")
    out += ["", f"Result: {len(SCENARIOS) - failures}/{len(SCENARIOS)} bundles pass every eligibility rule."]
    Path(__file__).resolve().parent.parent.joinpath("docs", "advisor_scenarios.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    return failures


if __name__ == "__main__":
    sys.exit(main())
