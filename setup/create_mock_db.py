"""
Rôle:
* Générer une base de données locale (Mock) pour l'environnement de développement et de démonstration.

Responsabilité:
* Créer une base SQLite légère (`mobilite_db.sqlite`)
* Injecter un jeu de données factice et simplifié (3 zones IRIS de test avec polygones vides)
  pour permettre de tester les requêtes SQL et les routes de l'API FastAPI hors-ligne
  sans nécessiter l'infrastructure PostgreSQL lourde de production
* A remplacer par 1_collect/5_sql_zones_iris.py en production

Exécution:
* uv run python setup/create_mock_db.py
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def setup_mock_db():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    # bloque l'exécution si l'URL n'est pas trouvée
    if db_url is None:
        print("Erreur critique : La variable DATABASE_URL est introuvable dans l'environnement.")
        sys.exit(1)

    print(f"Création de la base de données locale : {db_url}")

    # Pylance est apaisé : si le script arrive ici, db_url est un 'str'
    engine = create_engine(db_url)


    with engine.connect() as conn:
        # 1. Nettoyage et création de la table
        conn.execute(text("DROP TABLE IF EXISTS zones_iris"))
        conn.execute(text("""
            CREATE TABLE zones_iris (
                code_iris VARCHAR(50) PRIMARY KEY,
                nom_iris VARCHAR(255),
                ville VARCHAR(100),
                geometrie TEXT
            )
        """))

        # 2. Insertion de nos zones de test (Marseille)
        conn.execute(text("""
            INSERT INTO zones_iris (code_iris, nom_iris, ville, geometrie)
            VALUES
            ('132010101', 'Belsunce', 'Marseille', 'POLYGON(...)'),
            ('132060204', 'Lodi', 'Marseille', 'POLYGON(...)'),
            ('132020502', 'Arenc', 'Marseille', 'POLYGON(...)')
        """))
        conn.commit()
        print("Table 'zones_iris' créée et peuplée avec succès !")

if __name__ == "__main__":
    setup_mock_db()
