# Du Voyageur — Frontend

Static site (HTML / CSS / JS, no build step) for duvoyageur.netlify.com.
A landing page that explains the rebate concept and an intake form that sends a
customer's found trip to the backend.

## Files
- `index.html` — landing + intake form
- `styles.css` — teal + mango on sand
- `app.js` — turns the form into a `TripRequest` and POSTs it to the backend

## One required step before it works
Open `app.js` and set `API_BASE` to your deployed Railway backend URL:

```js
const API_BASE = "https://your-backend.up.railway.app";  // no trailing slash
```

Then push — Netlify auto-deploys.

## Backend must allow this origin
In the backend's Railway variables, add this site to `ALLOWED_ORIGINS`
(e.g. `https://duvoyageur.netlify.com`), or the browser blocks the form's POST.

## Local preview
Any static server works, e.g.:
```bash
python3 -m http.server 5500
```
Then open http://localhost:5500. (Submitting needs the backend running + CORS set.)
