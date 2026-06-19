#!/usr/bin/env python3
"""
build.py — injecte le header et le footer partagés dans toutes les pages.

POURQUOI
  Le header (nav + méga-menus) et le footer sont identiques sur toutes les pages.
  On les garde à UN SEUL endroit : partials/header.html et partials/footer.html.
  Ce script les réinjecte dans chaque page *.html du dossier.

USAGE
  1. Modifie partials/header.html ou partials/footer.html (la source unique).
  2. Lance :  python3 build.py
  3. Toutes les pages sont mises à jour. Commit + push.

NOUVELLE PAGE
  Crée ta page avec le <head> + <main> habituels, et mets simplement les
  marqueurs là où vont le header et le footer :

      <body>
      <!-- @header -->
        <main id="top"> ... ton contenu ... </main>
      <!-- @footer -->
      <script src="app.js"></script>
      </body>

  Puis lance python3 build.py : les marqueurs sont remplacés par les partials.
  (Sur une page déjà construite, le script remplace plutôt le bloc <header>/<footer>
  existant — donc relancer build.py est toujours sûr et idempotent.)

ÉTAT ACTIF DU MENU
  L'item de menu (Destinations / Type / Guides) s'allume automatiquement selon
  le nom du fichier — voir la fonction categorie() ci-dessous. Pas besoin de
  toucher au partial.
"""
import re, glob, pathlib

ROOT = pathlib.Path(__file__).parent
HEADER = (ROOT / "partials" / "header.html").read_text(encoding="utf-8").strip()
FOOTER = (ROOT / "partials" / "footer.html").read_text(encoding="utf-8").strip()

# Pages à ne pas toucher (pas de header/footer de site)
SKIP = set()

def categorie(nom):
    """Retourne le href de l'item de menu à activer pour cette page (ou None)."""
    if nom == "destinations.html" or nom.startswith("voyage-"):
        return "destinations.html"
    if nom in ("par-type.html", "les-iles.html") or nom.startswith("top-hotels-"):
        return "par-type.html"
    if nom == "par-pays.html" or nom.startswith("pays-"):
        return "par-pays.html"
    if nom == "guides.html" or nom.startswith("guide-"):
        return "guides.html"
    return None

def header_actif(cat, nom):
    """Applique l'état actif (desktop + drawer) + ajuste les ancres sur l'accueil."""
    h = HEADER
    # Sur l'accueil, les liens utilitaires et la marque pointent vers des ancres
    # internes (#processus, #faq, #top) plutôt que index.html#...
    if nom == "index.html":
        h = (h.replace('href="index.html#processus"', 'href="#processus"')
              .replace('href="index.html#faq"', 'href="#faq"')
              .replace('<a class="brand" href="index.html"', '<a class="brand" href="#top"'))
    if cat:
        h = h.replace(
            f'<a class="nav__link" href="{cat}">',
            f'<a class="nav__link nav__link--on" href="{cat}" aria-current="page">',
        )
    return h

def injecte(html, bloc_html, tag_ouvrant, regex_bloc, marqueur):
    """Remplace un bloc existant (<header>/<footer>) ou un marqueur <!-- @x -->."""
    if tag_ouvrant in html:
        return re.sub(regex_bloc, lambda m: bloc_html, html, count=1, flags=re.S)
    if marqueur in html:
        return html.replace(marqueur, bloc_html, 1)
    return html  # rien à faire

def main():
    changed = 0
    for path in sorted(ROOT.glob("*.html")):
        nom = path.name
        if nom in SKIP:
            continue
        html = path.read_text(encoding="utf-8")
        orig = html
        html = injecte(html, header_actif(categorie(nom), nom),
                       '<header class="nav">', r'<header class="nav">.*?</header>', "<!-- @header -->")
        html = injecte(html, FOOTER,
                       '<footer class="footer">', r'<footer class="footer">.*?</footer>', "<!-- @footer -->")
        if html != orig:
            path.write_text(html, encoding="utf-8")
            changed += 1
            print(f"  maj  {nom}")
    print(f"build.py terminé — {changed} page(s) mise(s) à jour.")

if __name__ == "__main__":
    main()
