"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 1/6
Rôle        : Extraction automatisée de données depuis une API Web (VOI MDS).
Compétence  : C1 (Automatiser l'extraction de données depuis un service web)
Auteur      : Bruno Coulet
=============================================================================
"""
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
DATA_DIR = Path("data/trips")

# Chargement des identifiants tels qu'ils étaient dans votre utils.py
load_dotenv()
USER_ID = os.getenv("USER_ID")
PASSWORD = os.getenv("PASSWORD")
PROXY = os.getenv("PROXY")

def run_curl(cmd):
    """
    Exécute la commande curl. 
    Justification technique (C1) : Indispensable pour contourner le proxy de l'entreprise 
    avec la négociation transparente (--proxy-negotiate).
    """
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Erreur : Impossible de décoder le JSON.")
            return None
    else:
        print(f"Erreur cURL : {result.stderr}")
        return None


def get_access_token():
    """Récupère le token VOI via curl en passant par le wrapper JSON.

    La commande utilise le même mécanisme de fallback proxy que les autres
    requêtes pour fonctionner à la fois au bureau et hors du réseau d'entreprise.
    """
    token_url = "https://api.voiapp.io/v1/partner-apis/token"
    cmd = [
        "curl.exe",
        # "-s",
        "-x", PROXY,
        "--proxy-negotiate",
        "-u", ":",
        "--ssl-no-revoke",
        "--user", f"{USER_ID}:{PASSWORD}",
        "-X", "POST",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", "Content-Length: 29",
        "-d", "grant_type=client_credentials",
        token_url,
        ]
    
    # Le parsing JSON et le fallback proxy sont centralisés dans run_curl_json().
    data = run_curl_json(cmd)
    return data["access_token"]


def get_trips(token, zone_id=66, start_time=None, end_time=None):
    """
    Récupère les trajets récents pour une zone donnée et les enregistre en JSON.
    """
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://api.voiapp.io/v1/partner-apis/mds/{zone_id}/trips?start_time={start_str}&end_time={end_str}"

    cmd = [
        "curl",
        # "--proxy", PROXY,               # Décommentez si vous êtes sur le réseau d'entreprise
        # "--proxy-negotiate", "-u", ":", # Décommentez si vous êtes sur le réseau d'entreprise
        "--ssl-no-revoke",
        "--location", url,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Accept: application/vnd.mds+json;version=2.0"
    ]

    print(f"\n[API VOI] Extraction des trajets du {start_str} au {end_str}...")
    data = run_curl(cmd)

    if data:
        output_dir = DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"trips_{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Données enregistrées dans {output_file}")
        
    return data

def scan_latest_trips():
    """Scanne le dossier data/trips pour trouver le fichier le plus récent."""
    if not DATA_DIR.exists():
        return None
    files = list(DATA_DIR.glob("trips_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)

def raw_data_update(zone_id=66):
    """Orchestrateur : Génère le token puis met à jour de façon incrémentale."""
    token = get_access_token()
    if not token:
        print("❌ Arrêt du pipeline : Impossible d'obtenir un token d'accès.")
        return

    latest = scan_latest_trips()
    if latest:
        print(f"Dernier fichier détecté : {latest.name}")
        print("Mise à jour incrémentale sur les dernières 24h...")
    else:
        print("Aucun historique trouvé. Lancement d'une extraction initiale.")

    get_trips(token=token, zone_id=zone_id)

if __name__ == "__main__":
    print("🚀 Démarrage du pipeline de collecte Web API (Source 1)")
    raw_data_update()