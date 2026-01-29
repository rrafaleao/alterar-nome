from .main_routes import main
from .products import products
from .auth import auth
from .register import registration
from .stores import storefront
from .admin import admin

all_blueprints = [
    main,
    products,
    registration,
    auth,
    admin,
    storefront,
]