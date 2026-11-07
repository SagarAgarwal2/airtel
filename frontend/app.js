/* Accel Business · Udyam Digital — owner journey (advisor → quote → KYC → book → track) */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const app = $("#app");
  const S = load() || {};
  S.lang = S.lang || "en";
  const params = new URLSearchParams(location.search);
  if (params.get("ref")) S.partner = params.get("ref").slice(0, 20);
  if (params.get("lang") === "hi") S.lang = "hi";

  const T = {
    en: {
      track: "Track order", footer: "Synthetic demo for YTL Hackathon 2026 · Track A. No real customer data.",
      heroT: "Get your business online in one sitting",
      heroP: "Answer five quick questions (plus your GSTIN if you have one). Get one bundle, one monthly price and one bill. Verify on your phone and book the installation, with no visit needed.",
      start: "Start with the advisor", f1: "One bundle", f1d: "Internet, SIMs, billing, CCTV and more", f2: "One price", f2d: "Toggle add-ons and see the total change",
      f3: "Phone KYC", f3d: "GSTIN lookup, photo upload, instant checks", f4: "Live tracker", f4d: "No more calling to ask about status",
      resume: "Continue your order", partner: "Partner referral", typeHere: "Type your answer…", send: "Send",
      thinking: "Advisor is thinking…", seeQuote: "See my quote", quote: "Your quote", perMonth: "/month",
      beforeGst: "before GST", setup: "one-time setup", contract: "Minimum term", install: "Ready in about", days: "days",
      included: "In your bundle", addons: "Add-ons you can switch on", notIncl: "Not available for you yet",
      accept: "Accept quote & continue", coverage: "Coverage check", yourDetails: "Your details", name: "Your name",
      mobile: "Mobile number", createOrder: "Create my order", consentT: "Before we verify your business",
      consentP: "We check your documents only to verify your business and activate your connection, as required for telecom services.",
      c1: "I agree that Accel may check my GSTIN and Udyam number with the registries and read the documents I upload, to verify my business for this order.",
      c2: "Send me offers on WhatsApp (optional)", cWhat: "What we collect", cWhatD: "GST certificate, Udyam certificate, authorised signatory ID and one utility bill. Nothing else.",
      cKeep: "How long we keep it", cKeepD: "Uploaded images are encrypted and deleted automatically 24 hours after upload in this demo. You can delete them any time from your tracker.",
      cRights: "Your rights", cRightsD: "You can see, correct or withdraw consent at any time. We never share documents with the AI advisor.",
      agree: "I agree, continue", kycT: "Verify your business", gstin: "GSTIN (optional, fills details for you)", lookup: "Look up",
      upload: "Upload", replace: "Replace", sample: "Demo: load a sample applicant", verify: "Check my documents",
      checking: "Reading documents and checking registries…", fix: "Fix", bookT: "Book installation", pickDay: "Pick a day",
      pickWin: "Pick a time window", upi: "UPI ID for autopay", upiNote: "Nothing is charged until your services are live.",
      confirm: "Confirm booking", trackT: "Order tracker", orderId: "Order ID", code: "6-digit code", open: "Open",
      help: "Need help?", deleteDocs: "Delete my documents", resumeCode: "Save this to check your order anytime",
      review: "A verifier will review your documents within 4 working hours. You will get a WhatsApp update.",
      verified: "Business verified. You can book your installation now.", action: "Please fix the items below and check again.",
    },
    hi: {
      track: "ऑर्डर ट्रैक करें", footer: "YTL हैकाथॉन 2026 के लिए सिंथेटिक डेमो। कोई असली ग्राहक डेटा नहीं।",
      heroT: "एक ही बार में अपना व्यवसाय ऑनलाइन करें",
      heroP: "पाँच आसान सवालों के जवाब दें (GSTIN हो तो वह भी)। एक बंडल, एक मासिक कीमत और एक बिल पाएँ। फ़ोन पर ही सत्यापन और इंस्टॉलेशन बुक करें।",
      start: "सलाहकार से शुरू करें", f1: "एक बंडल", f1d: "इंटरनेट, सिम, बिलिंग, CCTV और बहुत कुछ", f2: "एक कीमत", f2d: "ऐड-ऑन चुनें, कुल तुरंत बदले",
      f3: "फ़ोन पर KYC", f3d: "GSTIN से जानकारी, फ़ोटो अपलोड, तुरंत जाँच", f4: "लाइव ट्रैकर", f4d: "स्टेटस के लिए कॉल की ज़रूरत नहीं",
      resume: "अपना ऑर्डर जारी रखें", partner: "पार्टनर रेफ़रल", typeHere: "अपना जवाब लिखें…", send: "भेजें",
      thinking: "सलाहकार सोच रहा है…", seeQuote: "मेरा कोटेशन देखें", quote: "आपका कोटेशन", perMonth: "/माह",
      beforeGst: "GST से पहले", setup: "एक बार का सेटअप", contract: "न्यूनतम अवधि", install: "लगभग तैयार", days: "दिन में",
      included: "आपके बंडल में", addons: "ऐड-ऑन जो आप जोड़ सकते हैं", notIncl: "अभी आपके लिए उपलब्ध नहीं",
      accept: "कोटेशन स्वीकार करें", coverage: "कवरेज जाँच", yourDetails: "आपकी जानकारी", name: "आपका नाम",
      mobile: "मोबाइल नंबर", createOrder: "ऑर्डर बनाएँ", consentT: "सत्यापन से पहले आपकी सहमति",
      consentP: "हम आपके दस्तावेज़ सिर्फ़ आपके व्यवसाय के सत्यापन और कनेक्शन चालू करने के लिए जाँचते हैं।",
      c1: "मैं सहमत हूँ कि Accel मेरे GSTIN और Udyam नंबर की रजिस्ट्री से जाँच करे और इस ऑर्डर के लिए मेरे अपलोड किए दस्तावेज़ पढ़े।",
      c2: "WhatsApp पर ऑफ़र भेजें (वैकल्पिक)", cWhat: "हम क्या लेते हैं", cWhatD: "GST प्रमाणपत्र, Udyam प्रमाणपत्र, अधिकृत हस्ताक्षरकर्ता ID और एक बिजली बिल। इसके अलावा कुछ नहीं।",
      cKeep: "कितने समय तक रखते हैं", cKeepD: "इस डेमो में अपलोड की गई तस्वीरें एन्क्रिप्ट होती हैं और 24 घंटे बाद अपने आप हट जाती हैं। आप ट्रैकर से कभी भी हटा सकते हैं।",
      cRights: "आपके अधिकार", cRightsD: "आप कभी भी देख, सुधार या सहमति वापस ले सकते हैं। दस्तावेज़ AI सलाहकार को नहीं भेजे जाते।",
      agree: "सहमत हूँ, आगे बढ़ें", kycT: "अपने व्यवसाय का सत्यापन करें", gstin: "GSTIN (वैकल्पिक)", lookup: "खोजें",
      upload: "अपलोड", replace: "बदलें", sample: "डेमो: सैंपल आवेदक लोड करें", verify: "दस्तावेज़ जाँचें",
      checking: "दस्तावेज़ पढ़े जा रहे हैं और रजिस्ट्री जाँची जा रही है…", fix: "सुधारें", bookT: "इंस्टॉलेशन बुक करें", pickDay: "दिन चुनें",
      pickWin: "समय चुनें", upi: "ऑटोपे के लिए UPI ID", upiNote: "सेवाएँ चालू होने तक कोई शुल्क नहीं।",
      confirm: "बुकिंग पक्की करें", trackT: "ऑर्डर ट्रैकर", orderId: "ऑर्डर ID", code: "6 अंकों का कोड", open: "खोलें",
      help: "मदद चाहिए?", deleteDocs: "मेरे दस्तावेज़ हटाएँ", resumeCode: "ऑर्डर देखने के लिए इसे सहेजें",
      review: "एक सत्यापनकर्ता 4 कार्य घंटों में आपके दस्तावेज़ देखेगा। आपको WhatsApp पर अपडेट मिलेगा।",
      verified: "व्यवसाय सत्यापित। अब इंस्टॉलेशन बुक करें।", action: "नीचे दी गई चीज़ें सुधारें और फिर से जाँचें।",
    },
  };
  const t = (k) => (T[S.lang] && T[S.lang][k]) || T.en[k] || k;
  const rs = (n) => "₹" + Number(n || 0).toLocaleString("en-IN");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function save() { try { localStorage.setItem("udyam", JSON.stringify(S)); } catch (e) {} }
  function load() { try { return JSON.parse(localStorage.getItem("udyam") || "null"); } catch (e) { return null; } }
  function toast(m) { const el = $("#toast"); el.textContent = m; el.classList.add("on"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("on"), 2600); }
  async function api(path, opts = {}) {
    const o = { method: opts.method || (opts.body || opts.form ? "POST" : "GET"), headers: { ...(opts.headers || {}) } };
    if (opts.body) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(opts.body); }
    if (opts.form) { const f = new FormData(); Object.entries(opts.form).forEach(([k, v]) => f.append(k, v)); o.body = f; }
    const r = await fetch(path, o);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { const d = j.detail; throw new Error(typeof d === "string" ? d : (d && d.message) || "Something went wrong"); }
    return j;
  }
  const idem = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random());

  function applyI18n() {
    document.documentElement.lang = S.lang;
    $("#langBtn").textContent = S.lang === "en" ? "हिंदी" : "English";
    document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  }
  $("#langBtn").onclick = () => { S.lang = S.lang === "en" ? "hi" : "en"; save(); applyI18n(); route(); };

  /* ---------------------------------------------------------------- router */
  function go(h) { location.hash = h; }
  window.addEventListener("hashchange", route);
  function route() {
    applyI18n();
    const h = location.hash || "#/";
    document.body.classList.remove("has-composer");
    if (h.startsWith("#/advisor")) return viewAdvisor();
    if (h.startsWith("#/quote")) return viewQuote();
    if (h.startsWith("#/details")) return viewDetails();
    if (h.startsWith("#/consent")) return viewConsent();
    if (h.startsWith("#/kyc")) return viewKyc();
    if (h.startsWith("#/book")) return viewBook();
    if (h.startsWith("#/track")) return viewTrack(h.split("/")[2]);
    return viewHome();
  }

  /* ---------------------------------------------------------------- home */
  function viewHome() {
    app.innerHTML = `
      <section class="card hero">
        <span class="pill red">Udyam Digital</span>
        <h1>${t("heroT")}</h1>
        <p class="lead">${t("heroP")}</p>
        <button class="btn block" id="go">${t("start")} →</button>
        <div class="feat">
          <div><b>${t("f1")}</b>${t("f1d")}</div><div><b>${t("f2")}</b>${t("f2d")}</div>
          <div><b>${t("f3")}</b>${t("f3d")}</div><div><b>${t("f4")}</b>${t("f4d")}</div>
        </div>
        ${S.partner ? `<p class="small muted">${t("partner")}: <b>${esc(S.partner)}</b></p>` : ""}
      </section>
      ${S.orderId ? `<div class="card spread"><div><b>${t("resume")}</b><div class="small muted">${esc(S.orderId)}</div></div>
        <a class="btn sec" href="#/track/${esc(S.orderId)}">${t("open")}</a></div>` : ""}`;
    $("#go").onclick = async () => {
      S.sessionId = null; S.messages = []; S.rec = null; S.orderId = null; S.code = null; save();
      go("#/advisor");
    };
  }

  /* ---------------------------------------------------------------- advisor */
  async function viewAdvisor() {
    document.body.classList.add("has-composer");
    app.innerHTML = `<div class="steps" id="steps">${"<span></span>".repeat(6)}</div>
      <div class="chat" id="chat"></div><div id="chips" class="chips"></div><div style="height:70px"></div>
      <div class="composer"><form id="f"><input id="in" autocomplete="off" placeholder="${t("typeHere")}" aria-label="${t("typeHere")}">
      <button class="btn" aria-label="${t("send")}">➤</button></form></div>`;
    $("#f").onsubmit = (e) => { e.preventDefault(); const v = $("#in").value.trim(); if (v) { $("#in").value = ""; send(v); } };
    if (!S.sessionId) {
      const r = await api("/api/advisor/start", { body: { lang: S.lang, partner_code: S.partner || null } });
      S.sessionId = r.session_id; S.messages = [{ role: "assistant", text: r.text }]; S.chips = r.chips; S.progress = 0; save();
    }
    renderChat();
  }
  function renderChat(typing) {
    const chat = $("#chat"); if (!chat) return;
    chat.innerHTML = (S.messages || []).map((m) => m.html ? `<div class="bundle">${m.html}</div>` :
      `<div class="msg ${m.role === "user" ? "u" : "a"}">${esc(m.text)}</div>`).join("") +
      (typing ? `<div class="typing"><span class="spin"></span> ${t("thinking")}</div>` : "");
    const chips = $("#chips");
    chips.innerHTML = typing ? "" : (S.chips || []).map((c) => `<button class="chip">${esc(c)}</button>`).join("") +
      (S.rec ? `<button class="btn" id="toQuote">${t("seeQuote")} →</button>` : "");
    chips.querySelectorAll(".chip").forEach((b) => (b.onclick = () => {
      const v = b.textContent;
      if (/quote|कोटेशन/i.test(v) && S.rec) return go("#/quote");
      if (/^(Yes, I have one|हाँ, GSTIN है)$/.test(v)) { $("#in").focus(); $("#in").placeholder = "e.g. 08YKZXS5189L1ZO"; return; }
      send(v);
    }));
    if ($("#toQuote")) $("#toQuote").onclick = () => go("#/quote");
    document.querySelectorAll("#steps span").forEach((s, i) => s.classList.toggle("on", i < (S.progress || 0)));
    window.scrollTo(0, document.body.scrollHeight);
  }
  async function send(text) {
    S.messages.push({ role: "user", text }); renderChat(true);
    try {
      const r = await api("/api/advisor/message", { body: { session_id: S.sessionId, text } });
      S.messages.push({ role: "assistant", text: r.text });
      if (r.recommendation) { S.rec = r.recommendation; S.messages.push({ role: "assistant", html: bundleHtml(r.recommendation) }); initQuoteState(); }
      S.chips = r.chips || (S.rec ? [] : S.chips); S.progress = r.progress ?? S.progress; save();
    } catch (e) { S.messages.push({ role: "assistant", text: "⚠ " + e.message }); }
    renderChat();
  }
  function bundleHtml(rec) {
    return `<div class="spread"><h3>${esc(rec.segment_label)}</h3><span class="pill ok">${rs(rec.quote.monthly)}${t("perMonth")}</span></div>
      <ul>${rec.items.map((i) => `<li><b>${esc(i.name)}</b>${i.qty > 1 ? " ×" + i.qty : ""} <span class="muted small">· ${esc(i.why)}</span></li>`).join("")}</ul>
      ${rec.excluded.length ? `<div class="small"><b>${t("notIncl")}:</b> ${rec.excluded.map((e) => `<span class="x">${esc(e.name)}</span> (${esc(e.reasons[0])}${e.alternative ? "; " + esc(e.alternative) : ""})`).join("; ")}</div>` : ""}
      ${rec.notes.length ? `<div class="tiny muted" style="margin-top:6px">${rec.notes.map(esc).join(" ")}</div>` : ""}`;
  }
  function initQuoteState() {
    S.enabled = S.rec.items.map((i) => i.id); S.qty = {};
    [...S.rec.items, ...S.rec.addons].forEach((i) => (S.qty[i.id] = i.qty));
  }

  /* ---------------------------------------------------------------- quote */
  async function viewQuote() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    if (qs.get("s") && qs.get("s") !== S.sessionId) {   // link from WhatsApp
      try { const a = await api("/api/advisor/" + qs.get("s")); S.sessionId = qs.get("s"); S.rec = a.recommendation; S.lang = a.lang; S.messages = a.messages; initQuoteState(); save(); } catch (e) {}
    }
    if (!S.rec) return go("#/advisor");
    app.innerHTML = `<div class="card"><span class="spin"></span></div>`;
    const q = await api("/api/quote", { body: { session_id: S.sessionId, enabled: S.enabled, quantities: S.qty } });
    if (q.auto_removed && q.auto_removed.length) { toast("Removed (needs a connection it depends on): " + q.auto_removed.join(", ")); S.enabled = q.items.map((i) => i.id); save(); }
    const all = [...S.rec.items, ...S.rec.addons];
    const lineHtml = (i) => {
      const on = S.enabled.includes(i.id); const cur = q.items.find((x) => x.id === i.id) || i;
      const perUnit = /per (site|line|user|device|camera|counter|vehicle|channel|IP)/.test(i.unit);
      return `<div class="line"><label class="sw"><input type="checkbox" data-id="${i.id}" ${on ? "checked" : ""} ${i.core ? "disabled" : ""}><span></span></label>
        <div><div class="nm">${esc(i.name)}</div><div class="why">${esc(i.why)}</div>
          <div class="tiny muted">${esc(i.unit)} · ${rs(i.unit_price)} · ${i.min_contract} mo min${i.setup ? " · setup " + rs(cur.setup) : ""}</div>
          ${perUnit && on ? `<div class="qty"><button data-q="${i.id}" data-d="-1" aria-label="less">−</button><b>${cur.qty}</b><button data-q="${i.id}" data-d="1" aria-label="more">+</button></div>` : ""}
        </div><div class="amt">${on ? rs(cur.monthly) : `<span class="muted">${rs(i.monthly)}</span>`}</div></div>`;
    };
    app.innerHTML = `
      <h2>${t("quote")}</h2>
      <div class="card"><div class="spread"><b>${t("coverage")}</b><span class="pill ${q.coverage.fibre ? "ok" : "warn"}">${esc(q.coverage.note)}</span></div></div>
      <div class="card"><h3>${t("included")}</h3>${S.rec.items.map(lineHtml).join("")}
        ${S.rec.addons.length ? `<h3 style="margin-top:14px">${t("addons")}</h3>${S.rec.addons.map(lineHtml).join("")}` : ""}
        ${S.rec.excluded.length ? `<h3 style="margin-top:14px">${t("notIncl")}</h3>${S.rec.excluded.map((e) => `<div class="small" style="margin:4px 0"><span class="x">✕</span> <b>${esc(e.name)}</b> · ${esc(e.reasons.join("; "))}${e.alternative ? ` · ${esc(e.alternative)}` : ""}</div>`).join("")}` : ""}
        <div class="total" id="tot">
          <div class="spread"><div><div class="big">${rs(q.quote.monthly)}<span class="small muted">${t("perMonth")}</span></div>
            <div class="small muted">${t("beforeGst")} · ${rs(q.quote.monthly_incl_gst)} incl. 18% GST · ${rs(q.quote.setup)} ${t("setup")}</div>
            <div class="small muted">${t("contract")}: ${q.quote.longest_contract_months} mo · ${t("install")} ${q.quote.expected_install_days} ${t("days")}</div></div></div>
          <button class="btn block" id="acc" style="margin-top:10px" ${q.items.length ? "" : "disabled"}>${t("accept")} →</button>
        </div></div>
      <a class="btn ghost" href="#/advisor">← Back to advisor</a>`;
    app.querySelectorAll("input[data-id]").forEach((c) => (c.onchange = () => {
      const id = c.dataset.id; S.enabled = c.checked ? [...new Set([...S.enabled, id])] : S.enabled.filter((x) => x !== id); save(); viewQuote().then(() => $("#tot") && $("#tot").classList.add("flash"));
    }));
    app.querySelectorAll("button[data-q]").forEach((b) => (b.onclick = () => {
      const id = b.dataset.q; S.qty[id] = Math.max(1, (S.qty[id] || 1) + Number(b.dataset.d)); save(); viewQuote();
    }));
    $("#acc").onclick = () => go("#/details");
  }

  /* ---------------------------------------------------------------- details */
  function viewDetails() {
    app.innerHTML = `<h2>${t("yourDetails")}</h2><div class="card">
      <label class="f" for="nm">${t("name")}</label><input class="f" id="nm" autocomplete="name">
      <label class="f" for="mb">${t("mobile")}</label><input class="f" id="mb" inputmode="numeric" maxlength="14" placeholder="98xxxxxx10">
      ${S.partner ? `<p class="small muted">${t("partner")}: ${esc(S.partner)}</p>` : ""}
      <button class="btn block" id="mk" style="margin-top:14px">${t("createOrder")}</button></div>`;
    const key = idem();
    $("#mk").onclick = async () => {
      $("#mk").disabled = true;
      try {
        const r = await api("/api/order", { body: { session_id: S.sessionId, enabled: S.enabled, quantities: S.qty, contact_name: $("#nm").value || "Owner", mobile: $("#mb").value, partner_code: S.partner || null }, headers: { "Idempotency-Key": key } });
        S.orderId = r.order_id; S.code = r.resume_code; save(); go("#/consent");
      } catch (e) { toast(e.message); $("#mk").disabled = false; }
    };
  }

  /* ---------------------------------------------------------------- consent */
  function viewConsent() {
    app.innerHTML = `<div class="card"><span class="pill">${esc(S.orderId)}</span> <span class="small muted">${t("resumeCode")}: <b>${esc(S.code)}</b></span></div>
      <h2>${t("consentT")}</h2><div class="card"><p>${t("consentP")}</p>
      <dl class="kv"><dt>${t("cWhat")}</dt><dd>${t("cWhatD")}</dd><dt>${t("cKeep")}</dt><dd>${t("cKeepD")}</dd><dt>${t("cRights")}</dt><dd>${t("cRightsD")}</dd></dl>
      <label class="check"><input type="checkbox" id="c1"><span>${t("c1")}</span></label>
      <label class="check"><input type="checkbox" id="c2"><span>${t("c2")}</span></label>
      <button class="btn block" id="ok" disabled>${t("agree")}</button></div>`;
    $("#c1").onchange = () => ($("#ok").disabled = !$("#c1").checked);
    $("#ok").onclick = async () => {
      await api(`/api/kyc/${S.orderId}/consent`, { body: { code: S.code, verification: true, marketing: $("#c2").checked, lang: S.lang } });
      go("#/kyc");
    };
  }

  /* ---------------------------------------------------------------- KYC */
  const DOCS = [["gst_certificate", "GST certificate", "GST प्रमाणपत्र"], ["udyam_certificate", "Udyam certificate", "Udyam प्रमाणपत्र"],
    ["signatory_id", "Signatory ID", "हस्ताक्षरकर्ता ID"], ["address_proof", "Utility bill (≤ 90 days)", "बिजली बिल (90 दिन तक)"]];
  function viewKyc() {
    S.docs = S.docs && S.docs._order === S.orderId ? S.docs : { _order: S.orderId };
    const card = ([k, en, hi]) => {
      const d = S.docs[k]; const bad = d && d.quality && d.quality.blurry;
      return `<div class="doc ${d ? (bad ? "bad" : "done") : ""}"><b>${S.lang === "hi" ? hi : en}</b>
        <div class="tiny muted">${d ? (bad ? "Too blurry, retake" : (d.quality && d.quality.straightened ? "Straightened automatically · " : "") + "Read ✓") : "JPG / PNG"}</div>
        <label class="btn sec" style="margin-top:auto">${d ? t("replace") : t("upload")}<input type="file" accept="image/*" capture="environment" data-doc="${k}"></label></div>`;
    };
    app.innerHTML = `<h2>${t("kycT")}</h2>
      <div class="card"><label class="f" for="g">${t("gstin")}</label><div class="row"><input class="f" id="g" maxlength="15" placeholder="08YKZXS5189L1ZO" style="text-transform:uppercase"><button class="btn sec" id="lk">${t("lookup")}</button></div><div id="gres" class="small" style="margin-top:8px"></div></div>
      <div class="card"><div class="docs">${DOCS.map(card).join("")}</div>
        <div style="margin-top:14px;padding:10px 12px;border-radius:12px;background:var(--bg)"><div class="small"><b>${t("sample")}</b> <span class="muted">(fills all 4 documents, ~5–10 s)</span></div>
          <div class="row wrap" style="margin-top:8px">${Array.from({ length: 12 }, (_, i) => "K" + String(i + 1).padStart(2, "0")).map((k) => `<button class="chip ${S.docs && S.docs._sample === k ? "on" : ""}" data-s="${k}">${k}</button>`).join("")}</div></div>
        <button class="btn block" id="vf" style="margin-top:14px">${t("verify")}</button></div>
      <div id="out"></div>`;
    $("#lk").onclick = async () => {
      const g = $("#g").value.trim().toUpperCase();
      const r = await api("/api/lookup/gstin/" + encodeURIComponent(g));
      $("#gres").innerHTML = !r.valid ? `<span class="x">${esc(r.message)}</span>` : !r.found ? `<span class="x">${esc(r.message)}</span>` :
        `<b>${esc(r.trade_name)}</b> · ${esc(r.constitution)} · ${esc(r.state)} <span class="pill ${r.status === "Active" ? "ok" : "bad"}">${esc(r.status)}</span><div class="muted">${esc(r.address)}</div>`;
    };
    app.querySelectorAll("input[type=file]").forEach((inp) => (inp.onchange = async () => {
      const f = inp.files[0]; if (!f) return; const k = inp.dataset.doc;
      toast("Reading " + f.name + "…");
      try { const r = await api(`/api/kyc/${S.orderId}/upload`, { form: { code: S.code, doc_type: k, file: f } }); S.docs[k] = r; save(); viewKyc(); }
      catch (e) { toast(e.message); }
    }));
    app.querySelectorAll("button[data-s]").forEach((b) => (b.onclick = async () => {
      app.querySelectorAll("button[data-s]").forEach((x) => (x.disabled = true));
      b.innerHTML = `<span class="spin"></span>`; toast("Reading " + b.dataset.s + "'s 4 documents…");
      try {
        const r = await api(`/api/kyc/${S.orderId}/sample`, { body: { code: S.code, applicant: b.dataset.s } });
        S.docs = { _order: S.orderId, _sample: r.applicant }; Object.entries(r.docs).forEach(([k, v]) => (S.docs[k] = v)); save(); viewKyc(); toast("Loaded " + r.applicant + ". Now tap 'Check my documents'");
      } catch (e) { toast(e.message); b.textContent = b.dataset.s; }
    }));
    $("#vf").onclick = async () => {
      $("#out").innerHTML = `<div class="card"><span class="spin"></span> ${t("checking")}</div>`;
      try { const r = await api(`/api/kyc/${S.orderId}/verify`, { form: { code: S.code } }); renderKyc(r); }
      catch (e) { $("#out").innerHTML = `<div class="banner bad">${esc(e.message)}</div>`; }
    };
  }
  function renderKyc(r) {
    const b = r.status === "verified" ? ["ok", t("verified")] : r.status === "manual_review" ? ["warn", t("review")] : ["bad", t("action")];
    const ex = r.extracted || {};
    $("#out").innerHTML = `<div class="card"><div class="banner ${b[0]}">${b[1]}</div>
      <dl class="kv" style="margin-bottom:8px"><dt>Business</dt><dd>${esc(ex.business || "–")}</dd><dt>GSTIN</dt><dd>${esc(ex.gstin || "–")} ${ex.gstin_status ? `<span class="pill ${ex.gstin_status === "Active" ? "ok" : "bad"}">${esc(ex.gstin_status)}</span>` : ""}</dd>
      <dt>Signatory</dt><dd>${esc(ex.signatory || "–")} · ID ${esc(ex.signatory_id || "–")}</dd></dl>
      ${r.checks.map((c) => `<div class="res"><span class="ic ${c.result}">${c.result === "pass" ? "✓" : c.result === "warn" ? "!" : "✕"}</span>
        <div><b>${esc(c.label)}</b><div class="small muted">${esc(c.detail)}</div>${c.fix ? `<div class="small"><b>${t("fix")}:</b> ${esc(c.fix)}</div>` : ""}
        ${c.result === "fail" && c.owner === "reviewer" ? `<span class="pill warn">Sent to reviewer</span>` : ""}</div></div>`).join("")}
      ${r.status === "verified" ? `<button class="btn block" id="bk" style="margin-top:12px">${t("bookT")} →</button>` :
        `<a class="btn sec block" style="margin-top:12px" href="#/track/${esc(S.orderId)}">${t("trackT")}</a>`}</div>`;
    if ($("#bk")) $("#bk").onclick = () => go("#/book");
    $("#out").scrollIntoView({ behavior: "smooth" });
  }

  /* ---------------------------------------------------------------- book */
  async function viewBook() {
    const o = await api(`/api/order/${S.orderId}?code=${S.code}`);
    const slots = await api(`/api/slots?days=${Math.min(o.quote.expected_install_days, 7)}`);
    let day = slots[0].date, win = slots[0].windows[0];
    const draw = () => {
      app.innerHTML = `<h2>${t("bookT")}</h2><div class="card">
        <label class="f">${t("pickDay")}</label><div class="slots">${slots.map((s) => `<button class="slot ${s.date === day ? "on" : ""}" data-d="${s.date}">${s.label}</button>`).join("")}</div>
        <label class="f">${t("pickWin")}</label><div class="slots">${slots[0].windows.map((w) => `<button class="slot ${w === win ? "on" : ""}" data-w="${w}">${w}</button>`).join("")}</div>
        <label class="f" for="upi">${t("upi")}</label><input class="f" id="upi" placeholder="name@okbank">
        <p class="small muted">${t("upiNote")} ${rs(o.quote.monthly_incl_gst)}${t("perMonth")} incl. GST.</p>
        <button class="btn block" id="cf">${t("confirm")}</button></div>`;
      app.querySelectorAll("[data-d]").forEach((b) => (b.onclick = () => { day = b.dataset.d; draw(); }));
      app.querySelectorAll("[data-w]").forEach((b) => (b.onclick = () => { win = b.dataset.w; draw(); }));
      const key = idem();
      $("#cf").onclick = async () => {
        $("#cf").disabled = true;
        try { await api(`/api/order/${S.orderId}/book`, { body: { code: S.code, date: day, window: win, upi_id: $("#upi").value || "demo@okbank" }, headers: { "Idempotency-Key": key } }); go("#/track/" + S.orderId); }
        catch (e) { toast(e.message); $("#cf").disabled = false; }
      };
    };
    draw();
  }

  /* ---------------------------------------------------------------- track */
  async function viewTrack(id) {
    id = id || S.orderId;
    if (!id || !(id === S.orderId && S.code)) {
      app.innerHTML = `<h2>${t("trackT")}</h2><div class="card"><label class="f">${t("orderId")}</label><input class="f" id="oid" value="${esc(id || "")}" placeholder="UD-XXXXXX">
        <label class="f">${t("code")}</label><input class="f" id="cd" inputmode="numeric" maxlength="6"><button class="btn block" id="op" style="margin-top:12px">${t("open")}</button></div>`;
      $("#op").onclick = () => { S.orderId = $("#oid").value.trim().toUpperCase(); S.code = $("#cd").value.trim(); save(); go("#/track/" + S.orderId); };
      return;
    }
    let r;
    try { r = await api(`/api/track/${id}?code=${S.code}`); } catch (e) { app.innerHTML = `<div class="banner bad">${esc(e.message)}</div>`; return; }
    const next = r.kyc_status === "consented" || r.kyc_status === "documents_uploaded" || r.kyc_status === "not_started" || r.kyc_status === "action_needed"
      ? `<a class="btn block" href="#/${r.kyc_status === "not_started" ? "consent" : "kyc"}">${t("kycT")} →</a>`
      : r.status === "kyc_verified" ? `<a class="btn block" href="#/book">${t("bookT")} →</a>` : "";
    app.innerHTML = `<h2>${t("trackT")}</h2>
      <div class="card"><div class="spread"><div><b>${esc(r.order_id)}</b><div class="small muted">${esc(r.business_type || "")} · ${esc(r.city || "")}</div></div>
        <span class="pill red">${rs(r.quote.monthly)}${t("perMonth")}</span></div>
        ${r.slot ? `<p class="small">Installation: <b>${esc(r.slot.date)}</b>, ${esc(r.slot.window)}</p>` : ""}${next}</div>
      <div class="card"><ul class="tl">${r.timeline.map((s) => `<li class="${s.done ? "done" : ""} ${s.current ? "current" : ""}"><span class="dot"></span>
        <b>${esc(s.label)}</b><div class="small muted">${s.at ? esc(s.at) : s.expected ? "Expected " + esc(s.expected) : s.current ? "In progress" : ""}</div></li>`).join("")}</ul></div>
      <div class="card"><h3>Products</h3><table class="t"><tr><th>Item</th><th>Status</th><th>ETA</th></tr>
        ${r.products.map((p) => `<tr><td>${esc(p.name)}${p.qty > 1 ? " ×" + p.qty : ""}</td><td><span class="pill ${p.status === "Live" ? "ok" : ""}">${esc(p.status)}</span></td><td class="small">${esc(p.eta || "–")}</td></tr>`).join("")}</table></div>
      <div class="card"><h3>${t("help")}</h3><p class="small">${esc(r.help.phone)} · WhatsApp ${esc(r.help.whatsapp)}<br><span class="muted">${esc(r.help.note)}</span></p>
        <button class="btn sec" id="del">${t("deleteDocs")}</button> <button class="btn ghost" id="rf">↻ Refresh</button></div>`;
    $("#rf").onclick = () => viewTrack(id);
    $("#del").onclick = async () => { const x = await api(`/api/order/${id}/delete-documents`, { form: { code: S.code } }); toast(`Deleted ${x.deleted} document(s)`); };
  }

  route();
})();
