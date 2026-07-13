from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

def setup_mock_db():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    print(f"Création de la base de données locale : {db_url}")
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
