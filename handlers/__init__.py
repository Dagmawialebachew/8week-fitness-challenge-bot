from .onboarding import router as onboarding
# from .payment import router as payment
from .debug_router import router as debug_router
from .tasks import router as tasks
from .admin import router as admin
from .group import router as group
from .user_dashboard import router as user_dashboard


# The order here is critical for the Dispatcher
all_routers = [
    # debug_router,
    group,
    admin,       # Admin first (highest priority)
    user_dashboard,
    onboarding,
    # payment,
    tasks,
    # dashboard,
]