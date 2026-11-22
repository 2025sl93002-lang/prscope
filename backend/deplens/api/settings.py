"""Settings endpoints: analysis preferences, license policy, privacy info."""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from deplens import __version__
from deplens.analyzers.licenses import DEFAULT_POLICY
from deplens.api.deps import db_dep
from deplens.db import Database

router = APIRouter(prefix="/api/settings", tags=["settings"])

PRIVACY_INFO = {
    "local_data": [
        "Project paths you choose to scan",
        "Resolved dependency inventories and relationships",
        "Analysis findings, decisions, and verification notes",
    ],
    "sent_to_public_apis": [
        "Package names and versions (to OSV.dev for advisories)",
        "Package names (to the npm registry for versions, licenses, publish times)",
    ],
    "never_sent": [
        "Your repository source code",
        "Project or file contents",
        "Any personal information or identifiers",
    ],
    "external_sources": [
        {"name": "OSV.dev", "url": "https://osv.dev", "purpose": "vulnerability advisories"},
        {
            "name": "npm registry",
            "url": "https://registry.npmjs.org",
            "purpose": "package metadata",
        },
    ],
    "telemetry": "DepLens collects no telemetry and requires no account or login.",
}


class SettingsBody(BaseModel):
    online_default: Optional[bool] = None
    license_policy: Optional[Dict[str, str]] = None
    scan_exclusions: Optional[list] = None


@router.get("")
def get_settings(db: Database = Depends(db_dep)):
    return {
        "online_default": db.get_setting("online_default", True),
        "license_policy": db.get_setting("license_policy", DEFAULT_POLICY),
        "default_license_policy": DEFAULT_POLICY,
        "scan_exclusions": db.get_setting("scan_exclusions", []),
        "privacy": PRIVACY_INFO,
        "version": __version__,
    }


@router.put("")
def update_settings(body: SettingsBody, db: Database = Depends(db_dep)):
    if body.online_default is not None:
        db.set_setting("online_default", body.online_default)
    if body.license_policy is not None:
        db.set_setting("license_policy", body.license_policy)
    if body.scan_exclusions is not None:
        db.set_setting("scan_exclusions", body.scan_exclusions)
    return get_settings(db)
