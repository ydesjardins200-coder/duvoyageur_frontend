/* ============================================================
   Du Voyageur — front-end logic (runs on every page)
   - sets the footer year
   - handles the request form (only on demande.html)
   - scroll-reveal for .reveal elements
   ============================================================ */

const API_BASE = "https://duvoyageurbackend-production.up.railway.app";

/* Footer year (present on all pages). */
(() => {
  const y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();
})();

/* -------- Request form (only present on the demande page) -------- */
const form = document.getElementById("trip-form");
if (form) {
  const errEl = form.querySelector("[data-error]");
  const btn = form.querySelector("[data-submit]");
  const doneEl = document.querySelector("[data-done]");

  /* ----- Screenshot upload (mirrors the Messenger deal-image flow) ----- */
  const fileInput = form.querySelector("[data-file]");
  const zone = form.querySelector("[data-zone]");
  const preview = form.querySelector("[data-preview]");
  const thumb = form.querySelector("[data-thumb]");
  const shotName = form.querySelector("[data-shotname]");
  const removeBtn = form.querySelector("[data-remove]");
  const SOFT_REQUIRED = ["origin", "where", "dep", "adults"]; // a screenshot can fill these
  let selectedFile = null;

  const setScreenshotMode = (on) => {
    SOFT_REQUIRED.forEach((n) => {
      const el = form.elements[n];
      if (el) on ? el.removeAttribute("required") : el.setAttribute("required", "");
    });
  };

  const handleFile = (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    selectedFile = file;
    thumb.src = URL.createObjectURL(file);
    shotName.textContent = file.name || "capture";
    preview.hidden = false;
    zone.hidden = true;
    setScreenshotMode(true);
  };
  const clearFile = () => {
    selectedFile = null;
    fileInput.value = "";
    preview.hidden = true;
    zone.hidden = false;
    setScreenshotMode(false);
  };

  if (fileInput) {
    fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));
    removeBtn.addEventListener("click", clearFile);
    ["dragover", "dragenter"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("is-over"); }));
    ["dragleave", "drop"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("is-over"); }));
    zone.addEventListener("drop", (e) => {
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) { fileInput.files = e.dataTransfer.files; handleFile(f); }
    });
  }

  /* Shrink big phone screenshots before upload (keeps under model limits). */
  async function downscale(file, maxDim = 1600, quality = 0.82) {
    try {
      const bmp = await createImageBitmap(file);
      const scale = Math.min(1, maxDim / Math.max(bmp.width, bmp.height));
      const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = w; canvas.height = h;
      canvas.getContext("2d").drawImage(bmp, 0, 0, w, h);
      const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", quality));
      return blob || file;
    } catch (_) { return file; }
  }

  const splitOrigin = (value) => {
    const [city, iata] = (value || "").split("|");
    return { origin_city: city || null, origin_airport_iata: iata || null };
  };

  const buildPayload = () => {
    const v = (name) => {
      const el = form.elements[name];
      return el && el.value.trim() ? el.value.trim() : null;
    };
    const num = (name) => {
      const raw = v(name);
      return raw === null ? null : Number(raw);
    };

    const { origin_city, origin_airport_iata } = splitOrigin(v("origin"));

    const price = num("price");
    const price_seen = price === null ? null : {
      amount: price,
      currency: "CAD",
      basis: v("basis") || "per_person",
      raw: `${price} (${v("basis") === "total" ? "total" : "par personne"})`,
    };

    const ages = v("ages");
    const baseNotes = v("notes");
    const notesParts = [];
    if (baseNotes) notesParts.push(baseNotes);
    if (ages) notesParts.push(`Âge des enfants : ${ages}`);

    const payload = {
      origin_city,
      origin_airport_iata,
      hotel_name_raw: v("where"),
      departure_date: v("dep"),
      return_date: v("ret"),
      num_adults: num("adults"),
      num_children: num("children"),
      operator: v("operator"),
      price_seen,
      source: v("source") || "formulaire web",
      customer_name: v("name"),
      customer_email: v("email"),
      agent_notes: notesParts.join(" · ") || null,
      raw_message: v("where") ? `Formulaire web — ${v("where")}` : "Formulaire web",
      parse_confidence: 1.0,
    };
    Object.keys(payload).forEach((k) => payload[k] == null && delete payload[k]);
    return payload;
  };

  const showError = (msg) => { errEl.textContent = msg; errEl.hidden = false; };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errEl.hidden = true;
    if (!form.checkValidity()) { form.reportValidity(); return; }

    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = selectedFile ? "Lecture de ta capture…" : "Envoi en cours…";
    try {
      let res;
      if (selectedFile) {
        const blob = await downscale(selectedFile);
        const v = (n) => {
          const el = form.elements[n];
          return el && el.value.trim() ? el.value.trim() : null;
        };
        const fd = new FormData();
        fd.append("file", blob, "capture.jpg");
        const [oc, oi] = (v("origin") || "").split("|");
        const add = (k, val) => { if (val) fd.append(k, val); };
        add("email", v("email")); add("name", v("name"));
        add("origin_city", oc || null); add("origin_airport_iata", oi || null);
        add("where", v("where")); add("dep", v("dep")); add("ret", v("ret"));
        add("operator", v("operator")); add("notes", v("notes"));
        // Only override counts if the customer changed them from the defaults,
        // otherwise let the screenshot decide.
        const a = v("adults"); if (a && a !== "2") fd.append("adults", a);
        const ch = v("children"); if (ch && ch !== "0") fd.append("children", ch);
        res = await fetch(`${API_BASE}/intake/screenshot`, { method: "POST", body: fd });
      } else {
        res = await fetch(`${API_BASE}/intake`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildPayload()),
        });
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      form.hidden = true;
      doneEl.hidden = false;
      if (data && data.case_id) {
        doneEl.querySelector("[data-ref]").textContent = `Numéro de dossier : #${data.case_id}`;
      }
      doneEl.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      btn.disabled = false;
      btn.textContent = original;
      showError("On n'a pas pu envoyer ton dossier. Vérifie ta connexion et réessaie, ou écris-nous sur Messenger.");
    }
  });

  /* ?test=1 prefill for quick testing. */
  (function prefill() {
    if (new URLSearchParams(location.search).get("test") !== "1") return;
    const set = (name, value) => { const el = form.elements[name]; if (el) el.value = value; };
    const dep = new Date(); dep.setDate(dep.getDate() + 45);
    const ret = new Date(dep); ret.setDate(ret.getDate() + 7);
    const iso = (d) => d.toISOString().slice(0, 10);
    set("origin", "Montréal|YUL"); set("where", "Riu Palace Las Américas");
    set("dep", iso(dep)); set("ret", iso(ret));
    set("adults", "2"); set("children", "1"); set("ages", "8");
    set("price", "2400"); set("basis", "per_person"); set("operator", "Transat");
    set("source", "capture Messenger"); set("name", "Jean Test");
    set("email", "test@duvoyageur.ca"); set("notes", "Chambre swim-up si possible — DONNÉE DE TEST");
    const banner = document.createElement("p");
    banner.textContent = "Mode test : formulaire pré-rempli. Tu peux envoyer.";
    banner.style.cssText =
      "max-width:760px;margin:0 auto 1rem;padding:.6rem .9rem;border-radius:10px;" +
      "background:rgba(25,211,230,.18);color:#bdeef6;font-size:.9rem;text-align:center;";
    form.parentNode.insertBefore(banner, form);
  })();
}

/* -------- Scroll reveal (all pages, decorative, never blocks) -------- */
(function () {
  try {
    const els = document.querySelectorAll(".reveal");
    if (!els.length || !("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e, i) => {
        if (e.isIntersecting) {
          setTimeout(() => e.target.classList.add("in"), i * 80);
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.12 });
    els.forEach((el) => io.observe(el));
  } catch (_) { /* ignore */ }
})();
