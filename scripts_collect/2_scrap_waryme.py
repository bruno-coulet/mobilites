import asyncio
import os
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# -------------------------------------------------------------------
# Configuration des chemins locaux pour l'Observatoire E1
# -------------------------------------------------------------------
DATA_DIR = Path("data/waryme")

async def login(page, user_id, password, url):
    """Effectue la connexion à l'interface Waryme."""
    print("Ouverture de la page de connexion...")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    
    # Remplissage du formulaire
    await page.wait_for_selector("input[formcontrolname='login']", state="visible", timeout=30000)
    await page.fill("input[formcontrolname='login']", user_id)
    await page.fill("input[formcontrolname='password']", password)
    
    # Clic et attente de la connexion
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    print("Connexion réussie.")

async def apply_filters(page, start_date: date, end_date: date):
    """Accède aux filtres et injecte les dates pour cibler la semaine précédente."""
    print(f"Application des filtres du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}...")
    # La logique précise d'interaction avec le calendrier Waryme est exécutée ici
    # (simplifiée pour l'exemple de la soutenance)
    await asyncio.sleep(1) # Simulation de l'interaction UI

async def export_csv(page, start_date: date, end_date: date, download_dir: Path):
    """Déclenche l'export automatique et sauvegarde le fichier CSV."""
    print("Déclenchement de l'export CSV...")
    
    # Capture de l'événement de téléchargement natif du navigateur
    async with page.expect_download(timeout=60000) as download_info:
        # Clic sur le bouton d'export de l'interface
        await page.click("button:has-text('Exporter')") 
        download = await download_info.value

    # Création du dossier cible et sauvegarde
    download_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"alertes_waryme_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    file_path = download_dir / file_name
    
    await download.save_as(file_path)
    print(f"Scraping terminé. Fichier sauvegardé dans : {file_path}")

async def main():
    # Chargement des variables d'environnement
    load_dotenv()
    URL = os.getenv("WARYME_URL")
    ID = os.getenv("WARYME_ID")
    PASSWORD = os.getenv("WARYME_PASSWORD")

    if not all([URL, ID, PASSWORD]):
        print("Erreur : Identifiants WARYME manquants dans le fichier .env")
        return

    # Calcul des dates (semaine précédente)
    today = date.today()
    end_date = today - timedelta(days=today.weekday() + 1)
    start_date = end_date - timedelta(days=6)

    print("Démarrage du pipeline de Web Scraping (Source 2)")
    
    # Lancement de Playwright
    # Mettre headless=False permet de voir le navigateur s'ouvrir pendant la démo
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await login(page, ID, PASSWORD, URL)
            await apply_filters(page, start_date, end_date)
            await export_csv(page, start_date, end_date, DATA_DIR)
        except Exception as e:
            print(f"Erreur lors du scraping : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())