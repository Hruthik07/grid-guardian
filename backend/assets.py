import csv
from pathlib import Path

ASSETS_CSV = Path(__file__).resolve().parent.parent / "data" / "assets.csv"

CRITICALITY_WEIGHT = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}


def load_assets() -> list[dict]:
    with open(ASSETS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assets = []
    for row in rows:
        assets.append({
            "asset_id": row["asset_id"],
            "name": row["name"],
            "type": row["type"],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "criticality": row["criticality"],
            "criticality_weight": CRITICALITY_WEIGHT.get(row["criticality"], 0.3),
        })
    return assets
