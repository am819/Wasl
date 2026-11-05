"""Merchant profile service."""

from sqlalchemy.orm import Session

from models.merchant import Merchant
from models.user import User
from schemas.merchant_schema import MerchantRegisterRequest, MerchantUpdateRequest


class MerchantError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def create_merchant_profile(
    db: Session, user: User, req: MerchantRegisterRequest
) -> Merchant:
    """Create a merchant profile linked to an existing user.

    The user's status must be 'approved' at some point before they can use
    the platform, but profile creation itself is allowed immediately after
    registration (status stays 'pending').
    """
    existing = db.query(Merchant).filter(Merchant.user_id == user.id).first()
    if existing:
        raise MerchantError(
            code="PROFILE_EXISTS",
            message="Merchant profile already exists for this account",
            http_status=409,
        )

    # Encrypt tax_id if provided
    tax_id_stored: str | None = None
    if req.tax_id:
        from security.encryption import encrypt_field
        tax_id_stored = encrypt_field(req.tax_id)

    merchant = Merchant(
        user_id=user.id,
        business_name=req.business_name,
        business_phone=req.business_phone,
        address_line1=req.address_line1,
        address_line2=req.address_line2,
        city=req.city,
        postal_code=req.postal_code,
        business_registration_number=req.business_registration_number,
        tax_id=tax_id_stored,
        contact_person_name=req.contact_person_name,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


def get_merchant_by_user(db: Session, user_id: int) -> Merchant | None:
    return db.query(Merchant).filter(Merchant.user_id == user_id).first()


def require_merchant_profile(db: Session, user_id: int) -> Merchant:
    m = get_merchant_by_user(db, user_id)
    if m is None:
        raise MerchantError(
            code="PROFILE_NOT_FOUND",
            message="Merchant profile not found. Complete registration first.",
            http_status=404,
        )
    return m


def update_merchant_profile(
    db: Session, merchant: Merchant, req: MerchantUpdateRequest
) -> Merchant:
    if req.business_name is not None:
        merchant.business_name = req.business_name
    if req.business_phone is not None:
        merchant.business_phone = req.business_phone
    if req.address_line1 is not None:
        merchant.address_line1 = req.address_line1
    if req.address_line2 is not None:
        merchant.address_line2 = req.address_line2
    if req.contact_person_name is not None:
        merchant.contact_person_name = req.contact_person_name
    db.commit()
    db.refresh(merchant)
    return merchant


def _merchant_to_dict(merchant: Merchant, user_status: str) -> dict:
    return {
        "id": merchant.id,
        "user_id": merchant.user_id,
        "business_name": merchant.business_name,
        "business_phone": merchant.business_phone,
        "address_line1": merchant.address_line1,
        "address_line2": merchant.address_line2,
        "city": merchant.city,
        "contact_person_name": merchant.contact_person_name,
        "stats": {
            "total_orders": merchant.total_orders,
            "total_delivery_fees_egp": float(merchant.total_delivery_fees_egp),
            "total_platform_commission_egp": float(
                merchant.total_platform_commission_egp
            ),
            "average_rating": float(merchant.average_rating),
        },
        "status": user_status,
        "created_at": merchant.created_at.isoformat(),
    }
