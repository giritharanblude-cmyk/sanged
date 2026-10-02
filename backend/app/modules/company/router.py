from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession
from app.core.db import get_db
from app.kernel.auth import get_current_user
from app.kernel.models import User, CompanyProfile, AuditLog

router = APIRouter(prefix="/api/v1/company", tags=["company"])


class CompanyProfileUpdate(BaseModel):
    legal_name: str = Field(min_length=1)
    gstin: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    signatory: str = ""
    pf_applicable: bool = True


@router.get("/profile")
def get_profile(db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(CompanyProfile).first()
    if not profile:
        return {"legal_name": "", "gstin": "", "address": "", "phone": "", "email": "", "website": "", "signatory": "", "pf_applicable": True}
    return {"legal_name": profile.legal_name, "gstin": profile.gstin, "address": profile.address, "phone": profile.phone, "email": profile.email, "website": profile.website, "signatory": profile.signatory, "pf_applicable": profile.pf_applicable}


@router.put("/profile")
def update_profile(data: CompanyProfileUpdate, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(CompanyProfile).first()
    if not profile:
        profile = CompanyProfile(legal_name=data.legal_name)
        db.add(profile)
    profile.legal_name = data.legal_name
    profile.gstin = data.gstin
    profile.address = data.address
    profile.phone = data.phone
    profile.email = data.email
    profile.website = data.website
    profile.signatory = data.signatory
    profile.pf_applicable = data.pf_applicable
    log = AuditLog(actor=user.username, action="update", entity="company_profile")
    db.add(log)
    db.commit()
    return {"message": "Company profile updated"}