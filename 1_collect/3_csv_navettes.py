"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 3/6
Rôle        : Ingestion et première lecture de données historiques tabulaires.
Compétence  : C1 (Automatiser l'extraction de données depuis un fichier CSV)
Auteur      : Bruno Coulet
=============================================================================

Contexte et adaptation pour le RNCP :
Ce script démontre l'utilisation de Pandas pour lire, typer et nettoyer
efficacement un fichier plat historique contenant les données d'exploitation
des navettes maritimes de la RTM. Les lignes entièrement vides sont
purgées dès la lecture pour garantir l'hygiène des données.

Input       : data/maritime_clean.csv
Output      : DataFrame Pandas en mémoire

Exécution   : uv run 1_collect/3_csv_navettes.py
PROCHAINE ÉTAPE : uv run 1_collect/4_duckdb_query.py
"""

import pandas as pd
from pathlib import Path

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
DATA_FILE = Path("data/maritime_clean.csv")

def extract_csv_data(file_path: Path):
    """
    Extrait les données d'exploitation maritimes depuis un fichier CSV local.
    Justification technique (C1) : Utilisation de Pandas pour lire, typer
    et nettoyer efficacement un fichier plat historique.
    """
    if not file_path.exists():
        print(f"Erreur : Le fichier {file_path} est introuvable. "
              "Veuillez le copier dans le dossier 'data/'.")
        return None

    print(f"\n[Fichier CSV] Lecture des données maritimes depuis {file_path.name}...")

    try:
        df = pd.read_csv(file_path, sep=",")

        lignes_initiales = len(df)
        # Suppression des lignes totalement vides
        df = df.dropna(how='all')

        print(f"Extraction réussie : {len(df)} lignes récupérées "
              f"({lignes_initiales - len(df)} lignes vides ignorées).")

        # Aperçu de la donnée chargée en mémoire
        print("-" * 40)
        print("Aperçu des 3 premières lignes :")
        print(df.head(3))
        print("-" * 40)

        return df

    except Exception as e:
        print(f"Erreur lors de la lecture du fichier CSV : {e}")
        return None

if __name__ == "__main__":
    print("Démarrage du pipeline de collecte par Fichier (Source 3)")

    # Exécution de l'extraction
    df_navettes = extract_csv_data(DATA_FILE)

    if df_navettes is not None:
        print(f"Les données des navettes maritimes sont prêtes pour l'agrégation finale.")
