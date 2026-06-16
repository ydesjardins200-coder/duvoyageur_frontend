/* ============================================================
   Du Voyageur — front-end logic
   Turns the form into a TripRequest and POSTs it to the backend.
   ============================================================ */

/* >>> SET THIS after you deploy the backend on Railway <<<
   Example: "https://duvoyageur-backend-production.up.railway.app"
   No trailing slash. */
const API_BASE = "https://duvoyageurbackend-production.up.railway.app";

document.querySelector("[data-year]").textContent = new Date().getFullYear();

/* Map the airport <select> value "City|IATA" into the two fields the
   backend expects. */
function splitOrigin(value) {
  const [city, iata] = (value || "").split("|");
  return { origin_city: city || null, origin_airport_iata: iata || null };
}

/* Build a TripRequest payload, omitting empty fields so the backend
   keeps them null. */
function buildPayload(form) {
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

  // Children ages go into the notes so the agent sees them even though we
  // don't build individual passenger records on the form.
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

  // Drop null keys for a clean body.
  Object.keys(payload).forEach((k) => payload[k] == null && delete payload[k]);
  return payload;
}

const form = document.getElementById("trip-form");
const errEl = form.querySelector("[data-error]");
const btn = form.querySelector("[data-submit]");
const doneEl = document.querySelector("[data-done]");

function showError(msg) {
  errEl.textContent = msg;
  errEl.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errEl.hidden = true;

  // Native validation for required fields.
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  if (API_BASE.includes("REPLACE-WITH")) {
    showError("Le formulaire n'est pas encore relié au serveur. (API_BASE à configurer.)");
    return;
  }

  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "Envoi en cours…";

  try {
    const res = await fetch(`${API_BASE}/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload(form)),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Swap the form for the confirmation.
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
