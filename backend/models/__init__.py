# Import all models so SQLAlchemy registers them with Base.metadata.
# This prevents NoReferencedTableError when models reference each other
# across files via ForeignKey strings.

from models.user import User  # noqa: F401
from models.user_session import UserSession  # noqa: F401
from models.audit_log import AuditLog  # noqa: F401
from models.merchant import Merchant  # noqa: F401
from models.driver import Driver  # noqa: F401
from models.order import Order  # noqa: F401
from models.order_item import OrderItem  # noqa: F401
from models.order_status_history import OrderStatusHistory  # noqa: F401
from models.tracking_token import TrackingToken  # noqa: F401
from models.financial_transaction import FinancialTransaction  # noqa: F401
from models.driver_assignment import DriverAssignment  # noqa: F401
