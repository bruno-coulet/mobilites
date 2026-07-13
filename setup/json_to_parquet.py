"""

uv run json_to_parquet.py

"""


import pandas as pd
import json
from pathlib import Path

def convert_my_json():

    json_files = Path("data/trips").glob("*.json")
    parquet_file = Path("data/trips/trips_sample.parquet")

    for json_file in json_files:
        if json_file.exists():
            print(f"Lecture et aplanissement du fichier {json_file.name}...")

            # Lit le JSON avec la librairie json native
            with open(json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            # Extrait uniquement la liste contenue dans la clé "trips"
            trips_list = raw_data.get("trips", [])
            # Charge cette liste aplatie dans Pandas
            df = pd.DataFrame(trips_list)

            print("Conversion au format Big Data (Parquet)...")
            df.to_parquet(parquet_file, index=False)
            print(f"Fichier créé avec succès : {parquet_file}")
        else:
            print("Fichier JSON introuvable.")

if __name__ == "__main__":
    convert_my_json()

