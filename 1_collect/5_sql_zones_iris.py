"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 5/6
Rôle        : Extraction d'un référentiel géographique par requête SQL.
Compétences : C1 (Extraction de données depuis une base de données)
              C2 (Développer des requêtes de type SQL)
Auteur      : Bruno Coulet
=============================================================================

Contexte et adaptation pour le RNCP :
Ce script se connecte à une base de données relationnelle via l'ORM
SQLAlchemy pour extraire le référentiel des zones IRIS de Marseille.
Pour garantir la résilience de la soutenance (absence de dépendance
à un conteneur Docker PostgreSQL le jour de l'oral), la chaîne de
connexion cible une base de données locale SQLite, tout en conservant
une exécution SQL stricte et standard.

Input       : Base de données SQL (data/mobilite_db.sqlite)
Output      : DataFrame Pandas en mémoire

Exécution   : uv run 1_collect/5_sql_zones_iris.py
PROCHAINE ÉTAPE : uv run 2_agregation/6_agregation_et_import.py
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError


def extract_iris_referential():
    """
    Extrait le référentiel géographique IRIS depuis une base PostgreSQL.
    Justification technique (C1 & C2) : Démontre la capacité à se connecter à un SGBDR
    via un moteur (SQLAlchemy) et à exécuter une requête SQL d'extraction ciblée.
    """
    load_dotenv()

    # Récupération de l'URL de connexion depuis le .env
    # Format attendu : postgresql://user:password@localhost:5432/nom_bdd
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("Erreur : La variable DATABASE_URL est manquante dans le fichier .env")
        print("Exemple à ajouter dans .env : DATABASE_URL=postgresql://postgres:admin@localhost:5432/mobilite_db")
        return None

    print("\n[Base de Données SQL] Connexion à l'instance PostgreSQL locale...")

    try:
        # Création du moteur SQLAlchemy
        engine = create_engine(db_url)

        # Requête SQL optimisée (C2) :
        # ne sélectionne QUE les colonnes nécessaires (pas de SELECT *)
        # filtre en amont sur la ville pour économiser la RAM.
        query = """
            SELECT code_iris, nom_iris, geometrie
            FROM zones_iris
            WHERE ville = 'Marseille'
        """

        print(f"Exécution de la requête SQL :\n{query}")

        # Extraction directe des résultats SQL dans un DataFrame Pandas
        df_iris = pd.read_sql(query, engine)

        print(f"Extraction réussie : {len(df_iris)} zones IRIS marseillaises récupérées.")
        # Aperçu des données pour validation (C1)
        print("-" * 40)
        print("Aperçu des 3 premières lignes :")
        print(df_iris.head(3))
        print("-" * 40)

        return df_iris

    # Erreur d'infrastructure : BDD injoignable, mauvais mot de passe, conteneur éteint
    except OperationalError as e:
        print(f"Erreur de connexion à l'instance PostgreSQL : {e}")
        print("Avez-vous bien lancé votre conteneur PostgreSQL en local et vérifié vos identifiants ?")
        return None

    # Erreur logique : La requête est invalide ou la table/colonne n'existe pas
    except ProgrammingError as e:
        print(f"Erreur SQL lors de l'exécution de la requête : {e}")
        print("La table 'zones_iris' a-t-elle été créée et peuplée dans la base de données ?")
        return None

    # Erreur de dépendance : Il manque le driver (ex: psycopg2) pour lire l'URL
    except ImportError as e:
        print(f"Erreur de driver de base de données : {e}")
        print("Assurez-vous que le paquet 'psycopg2' ou 'psycopg2-binary' est installé.")
        return None
    
if __name__ == "__main__":
    print("Démarrage du pipeline de collecte Base de Données (Source 4)")

    # Exécution de l'extraction
    df_referentiel = extract_iris_referential()

    if df_referentiel is not None:
        print("Le référentiel géographique est prêt pour la jointure d'agrégation finale.")
