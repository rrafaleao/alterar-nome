from .main_routes import main
from .products import products
from .auth import auth

all_blueprints = [
    main,
    products,
    auth,
]