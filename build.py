#!/usr/bin/env python3
"""
build.py — site bilingue : FR à la racine, EN sous /en/.

Ce que fait le script (idempotent, relançable sans risque) :
  1. Injecte le header et le footer partagés dans chaque page :
       FR : partials/header.html / partials/footer.html
       EN : partials/header.en.html / partials/footer.en.html
     (marqueurs <!-- @header --> / <!-- @footer --> ou blocs existants)
  2. Active l'item de menu de la page (Destinations / Par pays / Type / Guides).
  3. Pages EN : réécrit les liens internes vers les slugs anglais
     (i18n/slugs.json), les chemins d'assets en absolu (/assets/…), et ajoute
     ?lang=en aux liens vers le portail.
  4. SEO : chaque page reçoit son <link rel="canonical">, ses hreflang
     (fr-CA, en-CA, x-default → FR) et son og:url, entre
     <!-- seo:start --> et <!-- seo:end -->.
  5. Le sélecteur de langue du header pointe vers la page équivalente.
  6. Régénère sitemap.xml (avec les alternates hreflang) et robots.txt.

NOUVELLE PAGE : créer la page FR à la racine, ajouter son slug EN dans
i18n/slugs.json, créer la page EN dans en/, puis lancer : python3 build.py
"""
import json, re, pathlib, datetime

ROOT = pathlib.Path(__file__).parent
DOMAIN = "https://duvoyageur.ca"
SLUGS = json.loads((ROOT / "i18n" / "slugs.json").read_text(encoding="utf-8"))   # fr -> en
FR_OF = {v: k for k, v in SLUGS.items()}                                          # en -> fr
PART = {lang: {k: (ROOT / "partials" / f"{k}{'' if lang == 'fr' else '.en'}.html").read_text(encoding="utf-8").strip()
               for k in ("header", "footer")} for lang in ("fr", "en")}
SKIP = {"demande.html"}                # redirigée vers le portail (_redirects)
NOINDEX = {"404.html"}


def categorie(fr_name):
    if fr_name == "destinations.html" or fr_name.startswith("voyage-"):
        return "destinations.html"
    if fr_name in ("par-type.html", "les-iles.html") or fr_name.startswith(("top-hotels-", "type-")):
        return "par-type.html"
    if fr_name == "par-pays.html" or fr_name.startswith("pays-"):
        return "par-pays.html"
    if fr_name == "guides.html" or fr_name.startswith("guide-"):
        return "guides.html"
    return None


def url(lang, fr_name):
    if lang == "fr":
        return f"{DOMAIN}/" if fr_name == "index.html" else f"{DOMAIN}/{fr_name}"
    en = SLUGS[fr_name]
    return f"{DOMAIN}/en/" if en == "index.html" else f"{DOMAIN}/en/{en}"


def path(lang, fr_name):
    """Chemin relatif au site (pour le sélecteur de langue)."""
    return url(lang, fr_name)[len(DOMAIN):]


def en_links(html):
    """Liens internes -> slugs EN ; assets en absolu ; portail en anglais."""
    def href(m):
        attr, val = m.group(1), m.group(2)
        if val.startswith(("http://", "https://")) and "/portail" in val:
            return f'{attr}="{val}{"&" if "?" in val else "?"}lang=en"' if "lang=en" not in val else m.group(0)
        if re.match(r"^(https?:|mailto:|tel:|#|/|data:|\{\{)", val):
            return m.group(0)
        if val.startswith("assets/") or val in ("styles.css", "app.js") or val.split("?")[0].endswith((".css", ".js", ".webp", ".png", ".jpg", ".svg", ".ico")):
            return f'{attr}="/{val}"'
        page, _, frag = val.partition("#")
        if page in SLUGS:
            return f'{attr}="{SLUGS[page]}{"#" + frag if frag else ""}"'
        return m.group(0)
    html = re.sub(r'\b(href|src)="([^"]*)"', href, html)
    html = re.sub(r'url\((["\']?)assets/', r'url(\1/assets/', html)
    return html


def header_for(lang, fr_name):
    h = PART[lang]["header"]
    cat = categorie(fr_name)
    home = "index.html"
    if fr_name == "index.html":
        h = (h.replace('href="index.html#processus"', 'href="#processus"')
              .replace('href="index.html#faq"', 'href="#faq"')
              .replace(f'<a class="brand" href="{home}"', '<a class="brand" href="#top"'))
    if cat:
        h = h.replace(f'<a class="nav__link" href="{cat}">',
                      f'<a class="nav__link nav__link--on" href="{cat}" aria-current="page">')
    other = "en" if lang == "fr" else "fr"
    h = h.replace("{{ALT}}", path(other, fr_name))
    return h


def inject(html, block, tag, regex, marker):
    if tag in html:
        return re.sub(regex, lambda m: block, html, count=1, flags=re.S)
    if marker in html:
        return html.replace(marker, block, 1)
    return html


def seo_block(lang, fr_name):
    if fr_name in NOINDEX:
        return ""
    c = url(lang, fr_name)
    return ("<!-- seo:start -->\n"
            f'<link rel="canonical" href="{c}">\n'
            f'<link rel="alternate" hreflang="fr-CA" href="{url("fr", fr_name)}">\n'
            f'<link rel="alternate" hreflang="en-CA" href="{url("en", fr_name)}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{url("fr", fr_name)}">\n'
            f'<meta property="og:locale:alternate" content="{"en_CA" if lang == "fr" else "fr_CA"}">\n'
            "<!-- seo:end -->")


def apply_seo(html, lang, fr_name):
    html = re.sub(r"\n?<!-- seo:start -->.*?<!-- seo:end -->", "", html, flags=re.S)
    html = re.sub(r'\n?<link rel="canonical"[^>]*>', "", html)
    html = re.sub(r'\n?<link rel="alternate" hreflang="[^"]*"[^>]*>', "", html)
    block = seo_block(lang, fr_name)
    if block:
        html = re.sub(r"(</title>)", r"\1\n" + block.replace("\\", "\\\\"), html, count=1)
        html = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r"\g<1>" + url(lang, fr_name) + r"\2", html)
    html = re.sub(r'<html lang="[^"]*"', f'<html lang="{"fr-CA" if lang == "fr" else "en-CA"}"', html, count=1)
    return html


def build_page(p, lang, fr_name):
    html = p.read_text(encoding="utf-8")
    orig = html
    hdr, ftr = header_for(lang, fr_name), PART[lang]["footer"]
    if lang == "en":
        hdr, ftr = en_links(hdr), en_links(ftr)
    html = inject(html, hdr, '<header class="nav">', r'<header class="nav">.*?</header>', "<!-- @header -->")
    html = inject(html, ftr, '<footer class="footer">', r'<footer class="footer">.*?</footer>', "<!-- @footer -->")
    if lang == "en":
        html = en_links(html)
    html = apply_seo(html, lang, fr_name)
    if html != orig:
        p.write_text(html, encoding="utf-8")
        return True
    return False


def sitemap():
    today = datetime.date.today().isoformat()
    rows = []
    for fr_name in SLUGS:
        if fr_name in NOINDEX or not (ROOT / fr_name).exists() or not (ROOT / "en" / SLUGS[fr_name]).exists():
            continue
        pr = "1.0" if fr_name == "index.html" else ("0.8" if fr_name.startswith(("voyage-", "pays-", "top-hotels", "destinations", "par-")) else "0.6")
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>'
                       for h, u in (("fr-CA", url("fr", fr_name)), ("en-CA", url("en", fr_name)), ("x-default", url("fr", fr_name))))
        for lang in ("fr", "en"):
            rows.append(f"  <url><loc>{url(lang, fr_name)}</loc><lastmod>{today}</lastmod><priority>{pr}</priority>{alts}</url>")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /partials/\nDisallow: /i18n/\n\nSitemap: {DOMAIN}/sitemap.xml\n",
                                     encoding="utf-8")
    return len(rows)


def main():
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        if p.name in SKIP:
            continue
        if p.name not in SLUGS:
            print(f"  !! {p.name} absent de i18n/slugs.json (ignorée)")
            continue
        changed += build_page(p, "fr", p.name)
    for p in sorted((ROOT / "en").glob("*.html")):
        if p.name not in FR_OF:
            print(f"  !! en/{p.name} absent de i18n/slugs.json (ignorée)")
            continue
        changed += build_page(p, "en", FR_OF[p.name])
    missing = [SLUGS[f] for f in SLUGS if not (ROOT / "en" / SLUGS[f]).exists()]
    if missing:
        print(f"  !! {len(missing)} page(s) EN manquante(s) : {', '.join(missing[:6])}{'…' if len(missing) > 6 else ''}")
    n = sitemap()
    print(f"build.py terminé — {changed} page(s) mise(s) à jour, sitemap : {n} URL.")


if __name__ == "__main__":
    main()
