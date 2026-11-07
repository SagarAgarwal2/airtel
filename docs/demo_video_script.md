# Demo video script (3 minutes max)

Record the screen with QuickTime (File → New Screen Recording) or OBS. Use Chrome's phone emulation (DevTools → toggle device toolbar → iPhone 12/13) for the owner screens and a normal window for the back office. Narrate live, or record the voice-over separately.

**Before recording**
1. `./run.sh`, then open `http://localhost:8000/?ref=JPR-PARTNER-07`. The partner code shows partner credit.
2. In DevTools → Application → Local Storage, clear `udyam` so you start fresh.
3. Optional: set `GEMINI_API_KEY` (free tier) before `./run.sh` so the advisor runs on the LLM. Without a key it uses the rule-based fallback, and the demo still works.
4. Do one practice run that stops after checking sample **K01**. That leaves a case in the back-office review queue for the last scene (the recorded run moves on to K06, which clears its own order).
5. Keep `http://localhost:8000/admin` open in a second tab.

| Time | Screen | What to do | What to say |
|---|---|---|---|
| 0:00–0:15 | Home | Show the landing page and tap **हिंदी** and back | "Only 7% of Accel's SMB leads activate, and the quote is the steepest drop-off: only 44% of assessed leads accept one. Udyam Digital gets a business online in one sitting, on a phone, in Hindi or English." |
| 0:15–0:50 | Advisor | Type: *"I run a kirana store in Jaipur, me and my son"* → *"Mobile hotspot, need UPI billing, CCTV and WhatsApp for customers"* → tap **No GSTIN** → **Not sure** | "The GenAI advisor asks five questions, plus a GSTIN if the owner has one. The owner can answer them all in one line. A rules engine, not the AI, picks the products: tier, size, GSTIN and dependencies. WhatsApp API needs a GSTIN, so it's left out, with the reason and an alternative." |
| 0:50–1:15 | Quote | Switch on **Secure Wi-Fi**, press **+** on CCTV, switch off Cloud POS, and watch the total change | "One monthly price, setup and GST shown separately, minimum term and install time. Every toggle is re-priced on the server, and dependencies are enforced, so add-ons can't be bought without the connection they need." |
| 1:15–1:30 | Details → Consent | Enter name and mobile; show the consent screen | "Consent comes before any upload. It's plain language, says what we collect and why, documents are deleted after 24 hours, and marketing is a separate opt-in." |
| 1:30–2:10 | Smart KYC | Type GSTIN `37IHKXV5167L1ZS` → **Look up** (shows *Cancelled*). Load sample **K01** → **Check my documents** → show red checks. Then load **K04** (blurry) and **K11** (old bill) quickly, then **K06** → verified | "OCR reads the documents, then we check the registries, not just the paper. K01 looks clean but its GSTIN is cancelled, so it goes to a human reviewer. Blurry photo or a 257-day-old bill? The owner gets a specific fix. K06 passes every check and clears automatically." |
| 2:10–2:30 | Book → Tracker | Pick a slot, enter `demo@okaxis`, **Confirm** → tracker | "Pick an install slot and set up UPI autopay. Nothing is charged until services are live. The tracker shows every milestone and product ETA, so there's no need to call support." |
| 2:30–2:50 | Back office | **KYC review queue** (K01 case) → **Approve**. **Who to call next** tab. **Orders** → **Post next milestone**, then flip back to the tracker and **Refresh** | "Reviewers see only the failed checks. Sales gets a call list ranked by a propensity score: the top 20% of leads hold 44% of activations. Ops posts milestones and the owner's tracker updates." |
| 2:50–3:00 | Architecture image | Show `docs/architecture.png` | "One Journey API and one case ID. The AI never sees documents and never sets prices. Our pilot targets activation in 9 days or less and an acquisition cost near ₹9.8k, down from ₹15.1k." |

**Tips:** rehearse once, since KYC takes about 3 seconds per applicant. Keep the browser zoomed to 100%. Trim pauses in iMovie. Export at 1080p and keep it under 3:00.
