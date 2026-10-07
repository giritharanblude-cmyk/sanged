"""Company module API — single-row profile with audited updates (F-CMP-01..05)."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.security import require_user
from app.kernel import models

router = APIRouter(prefix="/api/v1/company", tags=["company"])


class CompanyProfileUpdate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    gstin: str = Field(default="", max_length=15)
    address: str = Field(default="", max_length=2000)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=255)
    website: str = Field(default="", max_length=255)
    signatory: str = Field(default="", max_length=200)
    pf_applicable: bool = True


def _profile_dict(profile: models.CompanyProfile) -> dict[str, Any]:
    return {
        "legal_name": profile.legal_name,
        "gstin": profile.gstin or "",
        "address": profile.address or "",
        "phone": profile.phone or "",
        "email": profile.email or "",
        "website": profile.website or "",
        "signatory": profile.signatory or "",
        "pf_applicable": profile.pf_applicable,
    }


@router.get("/profile")
def get_profile(
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """Single company profile row (F-CMP-04); empty skeleton when unset."""
    profile = db.scalars(select(models.CompanyProfile)).first()
    if not profile:
        return {
            "legal_name": "",
            "gstin": "",
            "address": "",
            "phone": "",
            "email": "",
            "website": "",
            "signatory": "",
            "pf_applicable": True,
        }
    return _profile_dict(profile)


@router.put("/profile")
def update_profile(
    data: CompanyProfileUpdate,
    db: Annotated[DbSession, Depends(get_db)],
    user: Annotated[models.User, Depends(require_user)],
) -> dict[str, str]:
    """Upsert the single profile row; every edit lands in the audit log
    (F-CMP-04: 'edits are audited')."""
    profile = db.scalars(select(models.CompanyProfile)).first()
    created = profile is None
    if not profile:
        profile = models.CompanyProfile(legal_name=data.legal_name)
        db.add(profile)
    profile.legal_name = data.legal_name
    profile.gstin = data.gstin or None
    profile.address = data.address or None
    profile.phone = data.phone or None
    profile.email = data.email or None
    profile.website = data.website or None
    profile.signatory = data.signatory or None
    profile.pf_applicable = data.pf_applicable
    db.add(
        models.AuditLog(
            actor=user.username,
            action="update" if not created else "create",
            entity="company_profile",
            entity_id=profile.id,
        )
    )
    db.commit()
    return {"message": "Company profile updated"}
