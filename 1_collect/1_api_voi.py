"""
=============================================================================
Projet      : Observatoire Global de la Mobilité (Marseille)
Livrable    : Bloc E1 - Script 1/6
Rôle        : Extraction automatisée de données depuis une API Web (VOI MDS).
Compétence  : C1 (Automatiser l'extraction de données depuis un service web)
Auteur      : Bruno Coulet
=============================================================================

Contexte et adaptation pour le RNCP :
Pour ce projet d'Observatoire, le script d'origine utilisé en entreprise a été
refactorisé. L'ancienne version impliquait un wrapper complexe via `subprocess`
et `curl` pour contourner un proxy très strict.
Pour cette version, le code a été modernisé avec le standard `requests`.
L'authentification (OAuth2) est centralisée dans le module `utils.py`.
L'extraction interroge dynamiquement le paramètre `end_time` (H-1) afin de
garantir la récupération d'une tranche horaire consolidée côté serveur.

Input       : API VOI MDS Provider
Output      : DataFrame Pandas en mémoire (ou fichier JSON local)

Exécution   : uv run 1_collect/1_api_voi.py
PROCHAINE ÉTAPE : uv run 1_collect/2_scrap_waryme.py
"""


import requests
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv


# Import de la fonction d'authentification centralisée (sans proxy)
from utils import get_access_token

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
DATA_DIR = Path("data/trips")

def get_trips(token, zone_id=66, end_time=None):
    """
    Extraction propre via API REST.
    L'API VOI ne renvoie qu'une heure de données à la fois et n'attend que end_time !
    """

    if end_time is None:
        # On recule d'une heure pour être sûr que la tranche horaire est clôturée côté serveur
        end_time = datetime.now(timezone.utc) - timedelta(hours=1)

    # Format YYYY-MM-DDTHH exigé par VOI
    end_str = end_time.strftime("%Y-%m-%dT%H")

    # La vraie URL stricte avec uniquement end_time
    url = f"https://api.voiapp.io/v1/partner-apis/mds/{zone_id}/trips?end_time={end_str}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.mds+json;version=2.0"
    }

    print(f"\n[API VOI] Extraction de la dernière heure de trajets (Fin : {end_str})...")

    try:
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"❌ Erreur API ({response.status_code}) : {response.text}")

        response.raise_for_status()
        data = response.json()

        output_dir = DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"trips_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Données enregistrées dans {output_file}")
        return data

    except Exception as e:
        print(f"Erreur lors de l'extraction des trajets : {e}")
        return None

def scan_latest_trips():
    """Scanne le dossier data/trips pour trouver le fichier le plus récent."""
    if not DATA_DIR.exists():
        return None
    files = list(DATA_DIR.glob("trips_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)

def raw_data_update(zone_id=66):
    """Orchestrateur : Génère le token puis extrait les données."""
    token = get_access_token()
    if not token:
        print("Arrêt du pipeline : Impossible d'obtenir un token d'accès.")
        return

    latest = scan_latest_trips()
    if latest:
        print(f"Dernier fichier détecté : {latest.name}")
        print("Extraction du dernier bloc horaire disponible...")
    else:
        print("Aucun historique trouvé. Lancement d'une extraction initiale horaire.")

    get_trips(token=token, zone_id=zone_id)


if __name__ == "__main__":
    print("Démarrage du pipeline de collecte Web API (Source 1)")
    raw_data_update()
