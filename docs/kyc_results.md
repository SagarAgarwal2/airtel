# Smart KYC results on the 12 sample applicants

Run with `python scripts/run_kyc_samples.py` (Tesseract 5.x and 4.1.1, and RapidOCR, all give the same 12/12 outcome). Case date fixed at 2026-07-15 as the README instructs.

| Applicant | Business | Outcome | What the checks found | Next step |
|---|---|---|---|---|
| K01 | Vindhya Tours & Travels | ⚠️ manual review | GSTIN is **Cancelled** in the registry; Udyam number blank on the certificate | Human reviewer queue |
| K02 | Harmony Dental Care | ✅ verified | GST certificate scanned at a 7° tilt, straightened automatically and then read | Auto-cleared → book install |
| K03 | Ganesh Woodcraft | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |
| K04 | Saffron Dental Care LLP | ⚠️ action needed | GST certificate photo is **blurry** (sharpness 39 vs 400+ for clear images) | Back to owner with a fix |
| K05 | Balaji Realty LLP | ⚠️ action needed | **Udyam certificate missing** | Back to owner with a fix |
| K06 | Saffron Unisex Salon | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |
| K07 | Neelgiri Physio Clinic | ⚠️ manual review | Legal name says *Shri Physio Clinic*, trade name *Neelgiri Physio Clinic* | Human reviewer queue |
| K08 | Green Leaf Legal Associates | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |
| K09 | Kaveri Insurance Advisors | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |
| K10 | Kaveri Stays LLP | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |
| K11 | Trinity Bake House Pvt Ltd | ⚠️ action needed | Electricity bill dated 2025-10-31, **257 days old** (limit 90 days on 2026-07-15) | Back to owner with a fix |
| K12 | Star Electronics | ✅ verified | All checks pass: GSTIN checksum, Active status, names, address, Udyam, bill age, signatory | Auto-cleared → book install |

**Checks run per applicant:** document present · image sharp enough · skew corrected · GSTIN format and check digit (OCR look-alike characters such as 0/O and 5/S are resolved against the registry) · GSTIN Active · GSTIN state code matches the address · certificate names match the registry · legal name matches trade name · Udyam number present and found · Udyam name matches · address proof under 90 days old · bill in the business's name · bill address matches the GST address · signatory ID valid · signatory belongs to the business · signatory is the proprietor (for proprietorships).

**Routing:** problems the owner can fix (blurry photo, missing page, old bill) go back to the owner with instructions. Registry or identity problems (cancelled GSTIN, name mismatch) go to a human reviewer and are never rejected automatically.