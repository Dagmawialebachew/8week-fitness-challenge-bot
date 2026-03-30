from .onboarding import router as onboarding
from .payment import router as payment
from .debug_router import router as debug_router
from .tasks import router as tasks
from .admin import router as admin
from .group import router as group
# from .dashboard import router as dashboard
# from .admin import router as admin
# from .fallback import router as fallback

# The order here is critical for the Dispatcher
all_routers = [
    admin,       # Admin first (highest priority)
    group,
    onboarding,
    payment,
    tasks,
    # dashboard,
]