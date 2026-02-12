from flask import Blueprint

storefront = Blueprint("storefront", __name__)

from .storefront import *
from .auth import *
