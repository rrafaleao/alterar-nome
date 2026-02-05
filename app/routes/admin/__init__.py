from flask import Blueprint

admin = Blueprint("admin", __name__, url_prefix="/admin")

from .dashboard import *
from .sales import *
from .catalog import *
from .store import *
from .marketing import *
from .settings import *
from .products import *