import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "GridGuardianPrototype (portfolio demo; contact: g.d.hruthik2001@gmail.com)"}


async def geocode_address(address: str) -> tuple[float, float] | None:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        results = r.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
