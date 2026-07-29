"""

Rôle:
- utilitaires transverses partagés par les modules métier de scripts/core.

Responsabilité:
- authentification VOI (get_access_token),
- exécution curl et parsing JSON,
- helpers de dates et format horaire,
- cache et rafraîchissement du token,
- lecture des variables d'environnement.

Entrées:
- USER_ID, PASSWORD, PROXY depuis le .env.

Sorties:
- stdout/stderr curl,
- access_token,
- helpers réutilisables par trips/status/vehicles/status_changes/zones.



"""

import os
from datetime import UTC, datetime

import requests
from dotenv import load_dotenv

# Chargement des identifiants (plus besoin du proxy pour la soutenance)
load_dotenv()
USER_ID = os.getenv("USER_ID")
PASSWORD = os.getenv("PASSWORD")

# Variables pour la mise en cache du token (valable 15 min selon VOI)
_cached_token = None
_cached_token_time = None



def get_access_token(max_age_minutes=14):
    """
    Récupère le token VOI via requêtes HTTP natives (requests).
    Implémente une logique de cache pour ne pas sur-solliciter l'API.
    """
    global _cached_token, _cached_token_time
    now = datetime.now(UTC)

    # 1. Vérification du cache
    if _cached_token and _cached_token_time and (now - _cached_token_time).total_seconds() < max_age_minutes * 60:
        return _cached_token

    # 2. Génération d'un nouveau token
    if not USER_ID or not PASSWORD:
        print("Erreur : USER_ID ou PASSWORD manquant dans le .env")
        return None

    print("\n[Authentification] Négociation d'un nouveau token VOI...")
    token_url = "https://api.voiapp.io/v1/partner-apis/token"

    try:
        # Standard OAuth2 : Le grant_type va dans le corps (form-urlencoded)
        payload = {"grant_type": "client_credentials"}

        # Les identifiants (USER_ID, PASSWORD) vont dans l'en-tête Basic Auth
        response = requests.post(
            token_url,
            data=payload,
            auth=(USER_ID, PASSWORD), # C'est ici que la magie opère !
            timeout=10
        )

        # En cas d'erreur 400, on affiche le message précis de l'API pour faciliter le débug
        if response.status_code != 200:
            print(f"Erreur API : {response.text}")

        response.raise_for_status()

        token = response.json().get("access_token")

        # Mise en cache
        _cached_token = token
        _cached_token_time = datetime.now(UTC)

        print("Token d'accès généré avec succès.")
        return token

    # Capture toutes les erreurs de la bibliothèque requests (timeout, refus de connexion, erreurs HTTP 4xx/5xx...)
    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau ou d'authentification avec l'API VOI : {e}")
        return None

    # Capture l'erreur si la réponse n'est pas du JSON (ex: proxy d'entreprise qui bloque la requête et renvoie du HTML)
    except ValueError as e:
        print(f"Erreur de format : La réponse n'est pas un JSON valide : {e}")
        return None
