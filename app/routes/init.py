from .main_routes import main
from .auth import auth
from .register import registration
from .stores import storefront
from .admin import admin

all_blueprints = [
    main,
    registration,
    auth,
    admin,
    storefront,
]