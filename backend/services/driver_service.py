"""Driver profile service."""

from sqlalchemy.orm import Session

from models.driver import Driver
from models.user import User
from schemas.driver_schema import DriverRegisterRequest, DriverUpdateRequest


class DriverError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def create_driver_profile(
    db: Session, user: User, req: DriverRegisterRequest
) -> Driver:
    existing = db.query(Driver).filter(Driver.user_id == user.id).first()
    if existing:
        raise DriverError(
            code="PROFILE_EXISTS",
            message="Driver profile already exists for this account",
            http_status=409,
        )

    from security.encryption import encrypt_field
    encrypted_national_id = encrypt_field(req.national_id_number)

    driver = Driver(
        user_id=user.id,
        full_name=req.full_name,
        national_id_number=encrypted_national_id,
        vehicle_type=req.vehicle_type,
        vehicle_plate_number=req.vehicle_plate_number,
        license_expiry=req.license_expiry,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def get_driver_by_user(db: Session, user_id: int) -> Driver | None:
    return db.query(Driver).filter(Driver.user_id == user_id).first()


def require_driver_profile(db: Session, user_id: int) -> Driver:
    d = get_driver_by_user(db, user_id)
    if d is None:
        raise DriverError(
            code="PROFILE_NOT_FOUND",
            message="Driver profile not found. Complete registration first.",
            http_status=404,
        )
    return d


def update_driver_profile(
    db: Session, driver: Driver, req: DriverUpdateRequest
) -> Driver:
    if req.full_name is not None:
        driver.full_name = req.full_name
    if req.vehicle_plate_number is not None:
        driver.vehicle_plate_number = req.vehicle_plate_number
    db.commit()
    db.refresh(driver)
    return driver


def _driver_to_dict(driver: Driver, user_status: str) -> dict:
    return {
        "id": driver.id,
        "user_id": driver.user_id,
        "full_name": driver.full_name,
        "vehicle_type": driver.vehicle_type,
        "vehicle_plate_number": driver.vehicle_plate_number,
        "is_online": driver.is_online,
        "is_on_delivery": driver.is_on_delivery,
        "stats": {
            "total_deliveries": driver.total_deliveries,
            "total_earnings_egp": float(driver.total_earnings_egp),
            "average_rating": float(driver.average_rating),
            "cancellation_rate": float(driver.cancellation_rate),
        },
        "status": user_status,
        "created_at": driver.created_at.isoformat(),
    }
