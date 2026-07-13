"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 4/6
Rôle        : Extraction et requêtage analytique sur des données massives.
              Utilisation du format colonnaire Parquet et du moteur DuckDB.
Compétences : C1 (Automatiser l'extraction depuis un système Big Data)
              C2 (Requêter des données avec optimisation Predicate Pushdown)
Auteur      : Bruno Coulet
=============================================================================

Contexte et adaptation pour le RNCP :
Afin de ne pas saturer la mémoire RAM avec les gigaoctets d'historique
de flottes VOI, ce script ne charge pas les données via Pandas. Il exécute
une requête SQL analytique directement sur les fichiers `.parquet` stockés
sur le disque grâce au moteur DuckDB. L'optimisation colonnaire (Predicate
Pushdown) garantit des temps de réponse quasi-instantanés.

Input       : data/trips/*.parquet
Output      : DataFrame Pandas en mémoire

Exécution   : uv run 1_collect/4_duckdb_query.py
PROCHAINE ÉTAPE : uv run 1_collect/5_sql_zones_iris.py
"""

import duckdb
import pandas as pd
from pathlib import Path

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
PARQUET_DIR = Path("data/trips")

def extract_bigdata_parquet():
    """
    Interroge un dossier de fichiers Parquet (Big Data) via DuckDB.
    Justification technique (C1 & C2) : Traitement de volumes massifs sans
    saturer la RAM. Utilisation du format colonnaire Parquet et de requêtes
    SQL (DuckDB) avec projection et filtrage à la source.
    """
    if not PARQUET_DIR.exists() or not list(PARQUET_DIR.glob("*.parquet")):
        print(f"Erreur : Aucun fichier Parquet trouvé dans {PARQUET_DIR}.")
        print("Copiez quelques échantillons VOI (.parquet) dans le dossier 'data/trips/'.")
        return None

    print("\n[Système Big Data] Requêtage SQL sur les fichiers Parquet via DuckDB...")

    try:
        # Connexion DuckDB en mémoire
        con = duckdb.connect(database=':memory:')

        # Requête SQL analytique optimisée (C2) :
        # 1. read_parquet() lit directement tout le dossier.
        # 2. Projection stricte (seulement 4 colonnes sur les dizaines disponibles)
        #    pour limiter les I/O disque (gros avantage du format colonnaire).
        # 3. Filtrage WHERE pour ne charger que la donnée utile en RAM.
        query = f"""
            SELECT
                trip_id,
                start_time,
                end_time,
                distance
            FROM read_parquet('data/trips/*.parquet')
            WHERE start_time IS NOT NULL
        """

        print(f"Exécution de la requête analytique :\n{query}")

        # Exécution et conversion directe en DataFrame Pandas
        df_trips = con.execute(query).df()

        print(f"Extraction réussie : {len(df_trips)} trajets récupérés depuis l'entrepôt Parquet.")

        # Aperçu pour la démonstration au jury
        print("-" * 40)
        print("Aperçu des 3 premières lignes :")
        print(df_trips.head(3))
        print("-" * 40)

        return df_trips

    except Exception as e:
        print(f"Erreur lors de l'extraction Big Data : {e}")
        return None
    finally:
        # Fermeture propre de la connexion
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    print("Démarrage du pipeline de collecte Big Data (Source 5)")

    # Exécution de l'extraction
    df_parquet = extract_bigdata_parquet()

    if df_parquet is not None:
        print("Les données historiques de flottes (Parquet) sont prêtes pour l'agrégation finale.")
