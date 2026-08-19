from .geo import haversine_km, point_in_polygon

POINT_HAZARD_BASE_RADIUS_KM = {
    "USGS": 45,  # multiplied by magnitude below
    "NASA EONET": 150,
}


def _point_hazard_radius(hazard: dict) -> float:
    if hazard["source"] == "USGS":
        mag = float(hazard["event_type"].split("M")[-1] or 4)
        return POINT_HAZARD_BASE_RADIUS_KM["USGS"] * max(mag, 1)
    return POINT_HAZARD_BASE_RADIUS_KM.get(hazard["source"], 100)


def _asset_hit(asset: dict, hazard: dict) -> float | None:
    """Returns a proximity factor in (0, 1] if the asset is affected, else None."""
    if hazard["geometry_type"] == "polygon":
        for poly in hazard["polygons"]:
            if point_in_polygon(asset["lat"], asset["lon"], poly):
                return 1.0
        return None
    dist = haversine_km(asset["lat"], asset["lon"], hazard["lat"], hazard["lon"])
    radius = _point_hazard_radius(hazard)
    if dist > radius:
        return None
    return max(0.05, 1 - dist / radius)


def score_assets(assets: list[dict], hazards: list[dict]) -> list[dict]:
    results = []
    for asset in assets:
        hits = []
        for hazard in hazards:
            proximity = _asset_hit(asset, hazard)
            if proximity is None:
                continue
            contribution = hazard["severity_score"] * asset["criticality_weight"] * proximity
            hits.append({
                "source": hazard["source"],
                "event_type": hazard["event_type"],
                "headline": hazard["headline"],
                "severity": hazard["severity"],
                "proximity": round(proximity, 2),
                "contribution": round(contribution, 3),
            })
        risk_score = round(sum(h["contribution"] for h in hits), 3) if hits else 0.0
        results.append({
            **asset,
            "risk_score": risk_score,
            "hazards": sorted(hits, key=lambda h: -h["contribution"]),
        })
    return sorted(results, key=lambda a: -a["risk_score"])
