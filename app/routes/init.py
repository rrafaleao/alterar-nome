from .main_routes import main
from .auth import auth
from .register import registration
from .stores import storefront
from .admin import admin
from .api import api_v1

all_blueprints = [
    main,
    registration,
    auth,
    admin,
    storefront,
    api_v1,
]