"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 2/6
Rôle        : Extraction par Web Scraping et parsing de DOM HTML.
Compétences : C1 (Téléchargement et parsing de données utiles depuis l'HTML)
              C4 (Anonymisation des données personnelles pour le RGPD)
Auteur      : Bruno Coulet
=============================================================================

Contexte et adaptation pour le RNCP :
En entreprise, l'absence d'API et le pare-feu m'ont poussé à développer
un bot d'automatisation (RPA) naviguant sur Waryme pour exporter des CSV.
Pour cette évaluation (validant la capacité à "parser du DOM HTML"), le
script a été adapté : il isole le code HTML de la page des résultats et
utilise Playwright pour extraire la donnée brute directement depuis
les balises (<table>, <tr>, <td>).
De plus, la colonne 'nom_emetteur' est supprimée en mémoire vive (RAM)
avant toute sauvegarde, appliquant le principe de Privacy by Design (RGPD).

Input       : data/data_raw/waryme_sample.html
Output      : data/waryme_alerts_clean.csv

Exécution   : uv run 1_collect/2_scrap_waryme.py
PROCHAINE ÉTAPE : uv run 1_collect/3_csv_navettes.py
"""


from playwright.sync_api import sync_playwright
import os
from pathlib import Path
import pandas as pd

def mock_scrap_waryme():
    print("Démarrage du pipeline de Web Scraping (Source 2) - Mode Local Mock")

    # Fichier source HTML local simulant la page Waryme (extrait via Playwright en entreprise)
    html_path = f"file://{Path(os.getcwd()) / 'data_raw' / 'waryme_sample.html'}"


    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Ouverture de la page locale simulée...")
        page.goto(html_path)

        print("Extraction du tableau des alertes (Parsing HTML)...")
        # Cible toutes les lignes du corps du tableau
        rows = page.locator("#alertsTable tbody tr").all()

        data = []
        for row in rows:
            # Pour chaque ligne, extrait le texte de chaque cellule <td>
            cells = row.locator("td").all_inner_texts()
            data.append(cells)

        browser.close()

        # 1. Conversion en DataFrame
        df = pd.DataFrame(data, columns=["Date", "Type", "Zone", "nom_emetteur"])

        # 2. Application de la règle RGPD (Privacy by Design - Compétence C4)
        print("Application du filtre RGPD (Suppression des données personnelles)...")
        df = df.drop(columns=['nom_emetteur'])

        # 3. Sauvegarde
        output_path = Path("data/waryme_alerts_clean.csv")
        output_path.parent.mkdir(exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ Scraping et nettoyage réussis ! Données enregistrées dans {output_path}")

if __name__ == "__main__":
    mock_scrap_waryme()
