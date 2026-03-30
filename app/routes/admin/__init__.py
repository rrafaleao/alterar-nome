from flask import Blueprint, session

from app.models.store import Store

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.app_context_processor
def inject_admin_store_identity():
	"""Disponibiliza nome/logo da loja atual em todos os templates do admin."""
	store_id = session.get("store_id")
	if not store_id:
		return {
			"admin_store_name": "Zapp",
			"admin_store_logo": None,
		}

	store = Store.query.get(store_id)
	if not store:
		return {
			"admin_store_name": "Zapp",
			"admin_store_logo": None,
		}

	return {
		"admin_store_name": store.name or "Minha Loja",
		"admin_store_logo": store.logo_url,
	}

from .dashboard import *
from .sales import *
from .catalog import *
from .store import *
from .marketing import *
from .settings import *
from .products import *
from .categories import *
from .stock import *