"""Runs Smart KYC on all 12 sample applicants and prints a results table."""
import json, sys, time
sys.path.insert(0, ".")
from backend import kyc
rows = []
for aid in kyc.sample_ids():
    t = time.time()
    docs = kyc.analyze_sample(aid)
    res = kyc.run_case(docs)
    fails = [c for c in res["checks"] if c["result"] != "pass"]
    rows.append({"applicant": aid, "status": res["status"], "issues": [f"{c['label']}: {c['detail']}" for c in fails],
                 "secs": round(time.time() - t, 1), "fields": {k: v["fields"] for k, v in docs.items()},
                 "quality": {k: v["quality"] for k, v in docs.items()}})
    print(f"{aid}  {res['status']:<14} {round(time.time()-t,1)}s")
    for c in fails: print("     -", c["label"], "|", c["detail"])
json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "kyc_results.json", "w"), indent=1)
