"""Collects every version-1 route into a single router.

Each feature area adds its own router here as its roadmap phase is built.
"""

from fastapi import APIRouter, Depends

from app.api.deps import verify_origin
from app.api.v1 import (
    account,
    admin,
    admin_directory,
    auth,
    discovery,
    health,
    matches,
    societies,
    verifications,
)

# `verify_origin` runs before every route below: a change requested by a
# website other than our frontend is refused.
api_router = APIRouter(dependencies=[Depends(verify_origin)])
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(societies.router)
api_router.include_router(verifications.router)
api_router.include_router(discovery.router)
api_router.include_router(matches.router)
api_router.include_router(admin.router)
api_router.include_router(admin_directory.router)
