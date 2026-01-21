from .main_routes import main
from .products import products
from .stores import stores
from .auth import auth

all_blueprints = [
    main,
    products,
    stores,
    auth,
]