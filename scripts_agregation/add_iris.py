"""
Rôle: Enrichit les trajets Parquet avec les codes IRIS Marseille.
Responsabilité: Jointure spatiale (start/end location) avec iris_marseille.geojson, export résultat.

Source/Destination:
- Source trajets  : data/trips/**/*.parquet
- Source IRIS     : data/geofencing/iris_marseille.geojson
- Cible           : data/trips_iris/**/*.parquet

Exécution:
- uv run -m scripts.enrich.add_iris             # traite TOUS les fichiers du dossier source
- uv run -m scripts.enrich.add_iris 2025        # traite les fichiers de data/trips/2025
- uv run -m scripts.enrich.add_iris 2026/01     # traite les fichiers de data/trips/2026/01
- uv run -m scripts.enrich.add_iris 2026/trips_2026_01_01.parquet  # traite UNIQUEMENT ce fichier

Note: Relancer après convert_to_parquet.py si les trajets sont filtrés/modifiés.
"""

from unittest import result

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pathlib import Path
import sys
from config.paths import DATA_DIR,TRIPS_DIR, TRIPS_IRIS_DIR, IRIS_FILE



# ====================================================
# 1. CHARGEMENT IRIS
# ====================================================
print("Chargement des IRIS...")

iris = gpd.read_file(IRIS_FILE)
# print("Colonnes IRIS :", iris.columns.tolist())

# Filtrer Marseille
iris_marseille = iris[iris["com_code"] == "13055"].copy()

# S’assurer du CRS
if iris_marseille.crs is None:
    iris_marseille.set_crs(epsg=4326, inplace=True)
else:
    iris_marseille = iris_marseille.to_crs(epsg=4326)
# print(f"Nombre d'IRIS Marseille : {len(iris_marseille)}")


# ====================================================
# 2. Fonction d’ajout IRIS à un DF trips
# ====================================================
# def add_iris_to_trips(df, iris_gdf):
#     """
#     Ajoute les colonnes IRIS de départ et d'arrivée.
#     """

#     # ------------ START ------------
#     print(" - Calcul IRIS de début...")

#     gdf_start = gpd.GeoDataFrame(
#         df.copy(),
#         geometry=gpd.points_from_xy(
#             df["start_location_lng"],
#             df["start_location_lat"],
#             crs="EPSG:4326"
#         )
#     )

#     gdf_start_merged = gpd.sjoin(
#         gdf_start[["geometry"]],
#         iris_gdf[["iris_code", "iris_name", "geometry"]],
#         how="left",
#         predicate="within"
#     )

#     df["zone_iris_start_code"] = gdf_start_merged["iris_code"].values
#     df["zone_iris_start_name"] = gdf_start_merged["iris_name"].values

#     # ------------ END ------------
#     print(" - Calcul IRIS de fin...")

#     gdf_end = gpd.GeoDataFrame(
#         df.copy(),
#         geometry=gpd.points_from_xy(
#             df["end_location_lng"],
#             df["end_location_lat"],
#             crs="EPSG:4326"
#         )
#     )

#     gdf_end_merged = gpd.sjoin(
#         gdf_end[["geometry"]],
#         iris_gdf[["iris_code", "iris_name", "geometry"]],
#         how="left",
#         predicate="within"
#     )

#     df["zone_iris_end_code"] = gdf_end_merged["iris_code"].values
#     df["zone_iris_end_name"] = gdf_end_merged["iris_name"].values

#     # Nettoyage
#     if "geometry" in df.columns:
#         df = df.drop(columns=["geometry"])

#     return df

def add_iris_to_trips(df, iris_gdf):
    """
    Ajoute les colonnes IRIS de départ et d'arrivée via jointure spatiale.

    Résultat :
    - 1 ligne par trip_id
    - colonnes IRIS propres (pas de liste, pas de "[...]")
    - compatible Power BI (types string simples)
    """

    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point
    import ast

    # ======================================================
    # 1. Création des géométries
    # ======================================================
    gdf = df.copy()

    gdf["geometry_start"] = gdf.apply(
        lambda x: Point(x["start_location_lng"], x["start_location_lat"]), axis=1
    )

    gdf["geometry_end"] = gdf.apply(
        lambda x: Point(x["end_location_lng"], x["end_location_lat"]), axis=1
    )

    gdf = gpd.GeoDataFrame(gdf, geometry="geometry_start", crs="EPSG:4326")

    # ======================================================
    # 2. Jointure spatiale START
    # ======================================================
    gdf_start = gpd.sjoin(
        gdf,
        iris_gdf[["geometry", "iris_code", "iris_name"]],
        how="left",
        predicate="within"
    ).rename(columns={
        "iris_code": "zone_iris_start_code",
        "iris_name": "zone_iris_start_name"
    })

    # ======================================================
    # 3. Jointure spatiale END
    # ======================================================
    gdf_end = gpd.GeoDataFrame(gdf, geometry="geometry_end", crs="EPSG:4326")

    gdf_end = gpd.sjoin(
        gdf_end,
        iris_gdf[["geometry", "iris_code", "iris_name"]],
        how="left",
        predicate="within"
    ).rename(columns={
        "iris_code": "zone_iris_end_code",
        "iris_name": "zone_iris_end_name"
    })

    # ======================================================
    # 4. Alignement propre (CRITIQUE)
    # ======================================================
    gdf_start = gdf_start.sort_index()
    gdf_end = gdf_end.sort_index()

    result = gdf.copy()

    result["zone_iris_start_code"] = gdf_start["zone_iris_start_code"].values
    result["zone_iris_start_name"] = gdf_start["zone_iris_start_name"].values
    result["zone_iris_end_code"] = gdf_end["zone_iris_end_code"].values
    result["zone_iris_end_name"] = gdf_end["zone_iris_end_name"].values

    # ======================================================
    # 5. Déduplication (1 ligne par trip)
    # ======================================================
    result = result.sort_values("trip_id").drop_duplicates(subset=["trip_id"])

    # ======================================================
    # 6. Flatten des colonnes IRIS (FIX FINAL)
    # ======================================================
    def flatten(val):
        if pd.isna(val):
            return None

        val_str = str(val)

        # cas "[...]"
        if val_str.startswith("[") and val_str.endswith("]"):
            try:
                parsed = ast.literal_eval(val_str)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return str(parsed[0])
            except:
                return val_str

        return val_str

    for col in [
        "zone_iris_start_code",
        "zone_iris_start_name",
        "zone_iris_end_code",
        "zone_iris_end_name"
    ]:
        result[col] = result[col].apply(flatten).astype("string")

    # ======================================================
    # 7. Nettoyage final
    # ======================================================
    result = result.drop(columns=["geometry_start", "geometry_end"], errors="ignore")

    return result

# ====================================================
# 3. Fonctions de traitement
# ====================================================

def iris_output_path(input_file: Path) -> Path:
    # Exemple: data/trips/2026/trips_2026_06.parquet
    rel = input_file.relative_to(TRIPS_DIR)
    return TRIPS_IRIS_DIR / rel

def find_files_to_process() -> list[Path]:
    input_files = list(TRIPS_DIR.glob("**/*.parquet"))
    files_to_process = []

    for f in input_files:
        out = iris_output_path(f)

        # logique incrémentale
        if not out.exists():
            files_to_process.append(f)
        elif out.stat().st_mtime < f.stat().st_mtime:
            # source plus récente → retraiter
            files_to_process.append(f)

    return files_to_process



def process_files(file_paths: list[Path]):
    """
    Traite une liste spécifique de fichiers parquet.
    """
    print(f"\n=== TRAITEMENT DE {len(file_paths)} FICHIER(S) ===")
    
    for path in file_paths:
        if not path.exists():
            print(f" Fichier introuvable, ignoré : {path}")
            continue

        print(f"\nFichier : {path}")

        # Récupération de l'année depuis le dossier parent
        year = path.parent.name

        # Dossier de sortie : trips_iris/<année>/
        out_year_dir = TRIPS_IRIS_DIR / year
        out_year_dir.mkdir(exist_ok=True)

        # Renommage : trips_ → trips_iris_
        new_name = path.name.replace("trips_", "trips_iris_", 1)
        out_path = out_year_dir / new_name

        # LOGIQUE INCRÉMENTALE
        if out_path.exists():
            print(f"Déjà traité : {out_path.name}")
            continue


        # Lecture parquet
        df_trips = pd.read_parquet(path)
        print(f" - Lignes : {len(df_trips)}")

        # Colonnes nécessaires
        required_cols = [
            "start_location_lat",
            "start_location_lng",
            "end_location_lat",
            "end_location_lng"
        ]

        for col in required_cols:
            if col not in df_trips.columns:
                raise ValueError(f"Colonne manquante dans {path.name} : {col}")

        # Ajout IRIS
        df_out = add_iris_to_trips(df_trips, iris_marseille)

        # Enregistrement
        df_out.to_parquet(out_path, index=False)

        print(f" --> ÉCRIT : {out_path}")




def process_all_folder():
    files = find_files_to_process()

    print(f"\n=== TRAITEMENT INCRÉMENTAL : {len(files)} fichier(s) ===")

    if not files:
        print("Rien à traiter")
        return

    process_files(files)



def resolve_selection_args(args: list[str]) -> list[Path]:
    """
    Convertit une liste d'arguments (courts ou chemins) en liste de Path absolus.
    Règles :
      - '2025'              -> TRIPS_DIR / '2025' / '*.parquet'
      - '2026/01'           -> TRIPS_DIR / '2026' / '01' / '*.parquet'
      - 'fichier.parquet'   -> TRIPS_DIR / 'fichier.parquet'
      - Chemin absolu       -> utilisé tel quel
    """
    result = []
    
    for arg in args:
        p = Path(arg)

        # Si l'utilisateur donne un chemin absolu existant, on le respecte
        if p.is_absolute() and p.exists():
            if p.is_file():
                result.append(p)
            else:
                result.extend(p.rglob("trips_*.parquet"))
        else:
            # Sinon, on interprète 'arg' comme relatif à TRIPS_DIR
            candidate = TRIPS_DIR / p
            
            if candidate.is_file():
                result.append(candidate)
            elif candidate.is_dir():
                result.extend(candidate.rglob("trips_*.parquet"))
            else:
                # Vérifier si c'est un pattern de dossier partiel
                if "." not in arg:
                    print(f"⚠️  Le dossier n'existe pas : {candidate}")
                else:
                    raise FileNotFoundError(f"Le fichier spécifié est introuvable : {candidate}")
    
    return result



# ====================================================
# 4. BLOC MAIN

# uv run add_iris.py _________________________________ traite TOUS les fichiers du dossier source
# uv run add_iris.py 2025 ___________________________ traite les fichiers de TRIPS_DIR/2025
# uv run add_iris.py 2026/01 ________________________ traite les fichiers de TRIPS_DIR/2026/01
# uv run add_iris.py 2026/trips_2026_01_01.parquet _ traite UNIQUEMENT ce fichier

# ====================================================

if __name__ == "__main__":

    print("\n=== RÉSOLUTIONS DES CHEMINS ===")
    print(f"INPUT_FOLDER  : {TRIPS_DIR}")
    print(f"OUTPUT_FOLDER : {TRIPS_IRIS_DIR}")
    
    # Décider : traiter tout ou les fichiers spécifiés ?
    if len(sys.argv) < 2:
        # Aucun paramètre → traiter TOUT le dossier source
        print(f"SÉLECTION     : aucun paramètre -> traite tout")
        process_all_folder()
    else:
        # Paramètres fournis → traiter SEULEMENT ces fichiers/dossiers
        args = sys.argv[1:]
        print(f"SÉLECTION     : {args}")
        
        files = resolve_selection_args(args)
        
        if len(files) == 0:
            print("⚠️  Aucun fichier à traiter.")
        else:
            process_files(files)