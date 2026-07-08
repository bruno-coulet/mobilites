import json
import subprocess
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv


"""
Utilisation de `subprocess.run(cmd)` et de `curl` dans ce script (au lieu de la librairie standard `requests`)
Les contraintes réseau de l'entreprise (proxy avec négociation NTLM/Kerberos) bloque les requêtes standard.  
Passer par un appel système `curl` avec `--proxy-negotiate` permet de surmonter une infrastructure technique complexe pour automatiser l'extraction
"""

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
DATA_DIR = Path("data/trips")

def run_curl(cmd):
    """
    Exécute la commande curl. 
    Pour contourner le proxy de l'entreprise 
    avec la négociation transparente (--proxy-negotiate)
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

def get_trips(token, zone_id=66, start_time=None, end_time=None):
    """
    Récupère les trajets récents pour une zone donnée et les enregistre en JSON .
    """
    # end_time par défaut = maintenant 
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    # start_time par défaut = 24h avant 
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    # Conversion au format ISO attendu par l'API MDS 
    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"https://api.voiapp.io/v1/partner-apis/mds/{zone_id}/trips?start_time={start_str}&end_time={end_str}" 

    # Construction de la requête CURL 
    cmd = [
        "curl",
        # "--proxy", "http://votre_proxy:port", # À décommenter si actif le jour J 
        # "--proxy-negotiate", "-u", ":",       # Authentification Windows transparente 
        "--ssl-no-revoke", 
        "--location", url, 
        "-H", f"Authorization: Bearer {token}", 
        "-H", "Accept: application/vnd.mds+json;version=2.0" 
    ]

    print(f"\n[API VOI] Extraction des trajets du {start_str} au {end_str}...")
    data = run_curl(cmd)

    if data:
        # Création du dossier cible si inexistant 
        output_dir = DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarde 
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"trips_{timestamp}.json" 
        
        with open(output_file, "w", encoding="utf-8") as f: 
            json.dump(data, f, ensure_ascii=False, indent=2) 
            
        print(f"✅ Données enregistrées dans {output_file}") 
        
    return data

def scan_latest_trips():
    """Scanne le dossier data/trips pour trouver le fichier le plus récent"""
    if not DATA_DIR.exists():
        return None
        
    files = list(DATA_DIR.glob("trips_*.json")) 
    if not files:
        return None
        
    # Retourne le fichier avec la date de modification la plus récente
    return max(files, key=lambda f: f.stat().st_mtime) 

def raw_data_update(token, zone_id=66):
    """
    Orchestrateur : Met à jour de façon incrémentale les données
    """
    latest = scan_latest_trips() 
    if latest:
        print(f"Dernier fichier détecté : {latest.name} ")
        print("Mise à jour incrémentale sur les dernières 24h...")
    else:
        print("Aucun historique trouvé. Lancement d'une extraction initiale.")

    # Déclenche l'extraction
    get_trips(token=token, zone_id=zone_id) 

if __name__ == "__main__": 
    # Chargement du token depuis le fichier .env
    load_dotenv()
    VOI_TOKEN = os.getenv("VOI_TOKEN")

    if not VOI_TOKEN:
        print("Erreur : VOI_TOKEN est manquant dans le fichier .env")
    else:
        print("Démarrage du pipeline de collecte Web API")
        raw_data_update(token=VOI_TOKEN) 