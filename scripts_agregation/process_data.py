"""
process_data.py
Auteur : Bruno Coulet - RTM
Date   : 2026-06-19
Version: 2.1

----------------------------------------

Utilisation depuis la racine du projet (`scripts_waryme/`) :

    uv run -m scripts.process.process_data

Traitement d’un fichier spécifique :

    uv run -m scripts.process.process_data <chemin_fichier>

Traitement d’un dossier complet :

    uv run -m scripts.process.process_data <chemin_dossier>

Alternative sans uv :

    .venv\\Scripts\\python.exe -m scripts.process.process_data <chemin>

-----------------------------------------


Description :
Pipeline de traitement des fichiers CSV d’alertes Waryme.

Ce script permet de :
- Charger les données brutes issues du scraping (data_raw)
- Enrichir les données avec les informations IRIS (géolocalisation)
- Anonymiser les émetteurs
- Normaliser les colonnes (codes postaux, encodage, séparateur)
- Sauvegarder les données traitées dans data_processed

Fonctionnement :
- Peut traiter un fichier unique ou un dossier complet
- Conserve l’arborescence des fichiers en sortie
- Détecte automatiquement encodage et séparateur CSV

Entrées :
- Dossier source : data_raw (serveur)
- Fichiers CSV exportés depuis Waryme

Sorties :
- Données enrichies dans :
  \\\\sv039\\Commun_dirdev$\\DATA\\SID\\RTM_Alerte\\data_processed

Dépendances :
- pandas / geopandas
- config.paths :
    • RAW_DATA_DIR
    • DATA_DIR
- modules internes :
    • scripts.process.add_iris
    • scripts.process.anonymize_emetteur

Notes :
- Utilise les imports en mode module (`-m`) → garantit la cohérence du projet
- Compatible stockage serveur (chemins UNC)
- Intégré dans les pipelines :
    • scripts.scrap_process_last_week
    • scripts.scrap_process_selection

Pipeline recommandé :
    scraping → process_data → exploitation Power BI
"""


from pathlib import Path
import sys
import pandas as pd
from scripts.process.add_iris import add_iris_to_alertes, load_iris_marseille
from scripts.process.anonymize_emetteur import anonymize_emetteur

import os
from config.paths import PROJECT_ROOT, PLAYWRIGHT_DIR, RAW_DATA_DIR, DATA_DIR, PATH_IRIS


POSTAL_CODE_COLUMNS = [
    "Dernière position : code postal",
    "Position initiale : code postal",
]


def detect_csv_separator(path: Path) -> str:
    """Detecte un separateur CSV simple pour conserver le format d'origine."""
    with path.open("r", encoding="utf-8", errors="replace") as f:
        header = f.readline()

    candidates = [";", ",", "\t", "|"]
    best = max(candidates, key=lambda sep: header.count(sep))
    return best if header.count(best) > 0 else ","


def detect_csv_encoding(path: Path) -> str:
    """Detecte l'encodage CSV (utf-8-sig, utf-8, sinon cp1252)."""
    raw = path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def normalize_postal_code_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Force les colonnes de code postal a rester des entiers nullables."""
    out = df.copy()

    for col in POSTAL_CODE_COLUMNS:
        if col in out.columns:
            cleaned = (
                out[col]
                .astype(str)
                .str.strip()
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
            )
            out[col] = pd.to_numeric(cleaned, errors="coerce").astype("Int32")

    return out


def resolve_selection_arg(arg: str | None, input_folder: Path) -> Path:
    """Convertit l'argument utilisateur en path absolu fichier ou dossier."""
    if arg is None or arg in {"all", "*"}:
        return input_folder

    p = Path(arg)
    if p.is_absolute() and p.exists():
        return p

    # Cas 1: chemin relatif deja resoluble depuis le CWD courant.
    if p.exists():
        return p.resolve()

    # Cas 2: argument explicite commence par data_raw/... ou data_dev/...
    if p.parts and p.parts[0] in {RAW_DATA_DIR.name, LEGACY_DATA_DEV_FOLDER.name}:
        return PROJECT_ROOT / p

    return input_folder / p


def list_csv_files(selection_path: Path) -> list[Path]:
    """Retourne les CSV a traiter depuis un fichier ou dossier."""
    if selection_path.is_file():
        return [selection_path]
    if selection_path.is_dir():
        return list(selection_path.rglob("*.csv"))
    raise ValueError("Le chemin donne n'est ni un fichier ni un dossier.")


def build_output_path(src: Path, input_folder: Path) -> Path:
    """Construit le chemin de sortie en conservant l'arborescence relative."""
    try:
        relative = src.relative_to(input_folder)
    except ValueError:
        relative = Path(src.name)

    out_path = DATA_DIR / relative
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def process_file(path: Path, input_folder: Path, iris_gdf) -> Path:
    """Charge un CSV, applique le pipeline et ecrit la sortie."""
    sep = detect_csv_separator(path)
    encoding = detect_csv_encoding(path)

    # Lecture en string pour eviter l'inference automatique des types par pandas.
    df = pd.read_csv(path, sep=sep, encoding=encoding, dtype="string")
    df = normalize_postal_code_columns(df)
    df = add_iris_to_alertes(df, iris_gdf)
    df = anonymize_emetteur(df)

    out_path = build_output_path(path, input_folder)
    df.to_csv(out_path, index=False, sep=sep, encoding=encoding)
    return out_path


def process_selection(selection_path: Path, input_folder: Path) -> None:
    """Traite l'ensemble des CSV trouves dans la selection."""
    csv_files = list_csv_files(selection_path)
    print(f"Fichiers a traiter : {len(csv_files)}")

    iris_gdf = load_iris_marseille(PATH_IRIS)

    for path in csv_files:
        out_path = process_file(path, input_folder, iris_gdf)
        print(f"OK : {path} -> {out_path}")


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit(
            "Usage: uv run scripts/process/process_data.py "
            "<chemin_vers_un_fichier_csv_ou_un_dossier>"
        )

    input_folder = RAW_DATA_DIR
    if not input_folder.exists():
        raise FileNotFoundError(
            "Aucun dossier source trouve. Creez data_raw (ou data_dev en transition)."
        )

    arg = sys.argv[1] if len(sys.argv) == 2 else None
    target = resolve_selection_arg(arg, input_folder)

    print("\n=== RESOLUTION DES CHEMINS ===")
    print(f"SOURCE PAR DEFAUT : {input_folder}")
    print(f"CIBLE            : {DATA_DIR}")
    print(f"SELECTION        : {arg!r} -> {target}")

    if not target.exists():
        raise FileNotFoundError(f"Le chemin specifie est introuvable : {target}")

    if not target.is_file() and not target.is_dir():
        raise ValueError(f"Le chemin doit pointer vers un fichier CSV ou un dossier : {target}")

    process_selection(target, input_folder)


if __name__ == "__main__":
    main()
