# Advisor test scenarios

15 conversations played through the advisor in rule-based mode (no LLM key). Every bundle is re-checked against the catalogue rules (city tier, size, GSTIN, dependencies).

| # | Scenario | Bundle (monthly, before GST) | Left out (reason) | Rule check |
|---|---|---|---|---|
| 1 | Kirana, no GST, wants WhatsApp | Biz Fibre 100, Business Postpaid 299 ×2, Cloud POS & Billing · **₹2,196** | WhatsApp Business API Starter (needs an active GSTIN) | ✅ |
| 2 | CA firm, tier 1, GSTIN typed | Biz Fibre 1G, Business Postpaid 599 ×4, Cloud Email & Office Suite ×18, Backup 4G/5G Failover, Cloud Telephony / SIP ×2 · **₹11,144** | – | ✅ |
| 3 | Dental clinic, tight budget | Biz Fibre 100, Business Postpaid 299, Cloud Email & Office Suite ×4 · **₹1,798** | – | ✅ |
| 4 | Restaurant chain, 4 outlets (Hindi) | Biz Fibre 300 ×4, Business Postpaid 599 ×4, Cloud CCTV ×8, Backup 4G/5G Failover ×4, Cloud POS & Billing ×4 · **₹14,376** | – | ✅ |
| 5 | Textile unit, machines | Internet Leased Line 20, Business Postpaid 599 ×3, Machine Monitoring IoT ×10 · **₹11,287** | – | ✅ |
| 6 | Salon, no GST, tiny budget | Biz Fibre 100, Business Postpaid 299 ×2, Secure Wi-Fi with Guest Network · **₹1,996** | WhatsApp Business API Starter (needs an active GSTIN) | ✅ |
| 7 | Cancelled GSTIN | Biz Fibre 300, Business Postpaid 599 ×2, Cloud Email & Office Suite ×6 · **₹3,447** | Cloud Telephony / SIP (needs an active GSTIN) | ✅ |
| 8 | Tier-2 office asking for 1 Gbps | Biz Fibre 300, Business Postpaid 599 ×5, Cloud Email & Office Suite ×30 · **₹8,244** | – | ✅ |
| 9 | Pharmacy chain, 3 branches, SD-WAN | Biz Fibre 300 ×3, Business Postpaid 299 ×3, Cloud CCTV ×6, Cloud POS & Billing ×3, Managed SD-WAN ×3 · **₹15,885** | – | ✅ |
| 10 | Gym chain, 2 sites, 8 staff, SD-WAN not eligible | Biz Fibre 300 ×2, Business Postpaid 599 ×2, Cloud CCTV ×4 · **₹4,992** | Managed SD-WAN (needs at least 10 employees) | ✅ |
| 11 | Coaching centre, no fibre | Biz 5G AirFiber 100, Business Postpaid 599, Website + Domain Starter, Secure Wi-Fi with Guest Network · **₹2,196** | – | ✅ |
| 12 | Bakery with delivery vans | Biz Fibre 100, Business Postpaid 299 ×2, Fleet Tracker ×2, Cloud POS & Billing · **₹2,594** | – | ✅ |
| 13 | Diagnostic lab, security | Biz Fibre 300, Business Postpaid 599 ×3, Cloud Backup 1 TB, Cloud Email & Office Suite ×14, Endpoint Security ×14 · **₹6,931** | Toll-free Number (needs an active GSTIN) | ✅ |
| 14 | Furniture workshop, 8 staff (below leased-line min) | Biz Fibre 300, Business Postpaid 599 ×3, Cloud CCTV ×2 · **₹3,694** | – | ✅ |
| 15 | Hindi kirana, chips only | Biz Fibre 100, Business Postpaid 299, Cloud POS & Billing · **₹1,897** | – | ✅ |

Result: 15/15 bundles pass every eligibility rule.