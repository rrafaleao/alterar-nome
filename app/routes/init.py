from .main_routes import main
from .products import products
from .auth import auth
from .stores import registration

all_blueprints = [
    main,
    products,
    registration,
    auth,
]