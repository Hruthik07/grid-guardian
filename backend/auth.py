from fastapi import Header, HTTPException

from backend.db import get_organization_by_token


async def require_org(x_org_token: str | None = Header(default=None)) -> dict:
    if not x_org_token:
        raise HTTPException(status_code=401, detail="Missing X-Org-Token header")
    org = get_organization_by_token(x_org_token)
    if org is None:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Org-Token header")
    return org
