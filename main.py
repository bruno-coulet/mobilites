"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Restitution
Rôle        : API REST sécurisée mettant à disposition les données consolidées.
              Implémentation de l'architecture REST, d'une documentation OpenAPI,
              et d'une sécurisation par X-API-Key (Standards OWASP).
Compétence  : C5 (Développer une API mettant à disposition le jeu de données)
Auteur      : Bruno Coulet
=============================================================================
"""

import os
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Configuration et Sécurité (Validation C5 - OWASP)
# -------------------------------------------------------------------
load_dotenv()
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Clé secrète attendue (à définir dans votre .env, ex: MOBILITE_API_KEY=mon_secret_123)
EXPECTED_API_KEY = os.getenv("MOBILITE_API_KEY", "cle_demo_soutenance")

# Configuration de la base de données cible (celle remplie à l'étape 6)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/mobilite_db")
engine = create_engine(DATABASE_URL)

# -------------------------------------------------------------------
# Initialisation de l'API (Validation C5 - REST & OpenAPI)
# -------------------------------------------------------------------
app = FastAPI(
    title="Observatoire de la Mobilité API",
    description="API REST sécurisée mettant à disposition les données consolidées de la mobilité marseillaise (VOI, Navettes, Alertes RTM).",
    version="1.0.0"
)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Middleware d'authentification. 
    Protège l'accès aux données consolidées de la collectivité.
    """
    if api_key_header == EXPECTED_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Accès refusé. Clé API manquante ou invalide.",
    )

# -------------------------------------------------------------------
# Endpoints (Points de terminaison REST)
# -------------------------------------------------------------------

@app.get("/api/v1/mobility/trips", tags=["Mobilité"])
def get_trips(limit: int = 50, api_key: str = Depends(get_api_key)):
    """
    Retourne les derniers trajets de trottinettes enrichis avec leur zone géographique.
    Nécessite une clé API valide.
    """
    query = text("""
        SELECT t.trip_id, t.start_time, t.end_time, i.nom_iris
        FROM fact_trips t
        LEFT JOIN dim_iris i ON t.zone_iris_start_code = i.code_iris
        LIMIT :limit
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"limit": limit}).mappings().all()
            return {"status": "success", "data": [dict(row) for row in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur base de données : {str(e)}")

@app.get("/api/v1/mobility/alerts/{code_iris}", tags=["Sécurité"])
def get_alerts_by_zone(code_iris: str, api_key: str = Depends(get_api_key)):
    """
    Retourne les statistiques d'incidents (Waryme) pour un quartier précis (Code IRIS).
    """
    query = text("""
        SELECT type_incident, COUNT(*) as nombre_incidents
        FROM fact_alerts
        WHERE code_iris = :code_iris
        GROUP BY type_incident
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"code_iris": code_iris}).mappings().all()
            return {
                "zone_iris": code_iris,
                "statistiques_securite": [dict(row) for row in result]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur base de données : {str(e)}")

@app.get("/health", tags=["Supervision"])
def health_check():
    """Route publique pour vérifier si l'API est en ligne."""
    return {"status": "online", "message": "API de l'Observatoire opérationnelle"}
