import re
import traceback
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from app.models.product import Product
from app.models.store import Store
from app.models.store_customer import StoreCustomer
from app.routes.stores.customer_auth import (
    ensure_customer_for_store,
    find_customer_by_email_and_password,
    get_customers_by_email,
)
from config.database import db

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="zappshop-mobile-api-v1")


def _generate_customer_token(customer):
    payload = {
        "customer_id": customer.id,
        "email": customer.email,
        "store_id": customer.store_id,
    }
    return _serializer().dumps(payload)


def _decode_customer_token(token):
    return _serializer().loads(token, max_age=TOKEN_TTL_SECONDS)


def _parse_bearer_token(auth_header):
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def _find_store_or_none(store_slug):
    if not store_slug:
        return None

    clean_slug = store_slug.strip().lower()
    if not clean_slug:
        return None

    return Store.query.filter_by(slug=clean_slug, onboarding_completed=True).first()


def _is_valid_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email or ""))


def _extract_customer_payload(data):
    return {
        "store_slug": (data.get("store_slug") or "").strip().lower(),
        "full_name": (data.get("full_name") or "").strip(),
        "email": (data.get("email") or "").strip().lower(),
        "phone": (data.get("phone") or "").strip(),
        "password": data.get("password") or "",
        "confirm_password": data.get("confirm_password") or "",
    }


def require_customer_token(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = _parse_bearer_token(auth_header)

        if not token:
            return jsonify({
                "success": False,
                "error": "Token ausente. Use Authorization: Bearer <token>."
            }), 401

        try:
            payload = _decode_customer_token(token)
        except (BadSignature, BadTimeSignature):
            return jsonify({
                "success": False,
                "error": "Token invalido ou expirado"
            }), 401

        customer = StoreCustomer.query.filter_by(id=payload.get("customer_id")).first()
        if not customer or not customer.is_active:
            return jsonify({
                "success": False,
                "error": "Cliente nao encontrado ou inativo"
            }), 401

        request.customer = customer
        return handler(*args, **kwargs)

    return wrapper


@api_v1.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"success": True, "message": "API v1 online"}), 200


@api_v1.route("/customers/exists", methods=["GET"])
def customer_exists():
    email = (request.args.get("email") or "").strip().lower()
    store_slug = (request.args.get("store_slug") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "error": "email e obrigatorio"}), 400

    if not _is_valid_email(email):
        return jsonify({"success": False, "error": "email invalido"}), 400

    store = None
    if store_slug:
        store = _find_store_or_none(store_slug)
        if not store:
            return jsonify({"success": False, "error": "loja nao encontrada"}), 404

    exists_global = StoreCustomer.query.filter_by(email=email).first() is not None
    exists_in_store = False

    if store:
        exists_in_store = StoreCustomer.query.filter_by(store_id=store.id, email=email).first() is not None

    return jsonify({
        "success": True,
        "data": {
            "email": email,
            "exists_global": exists_global,
            "store": {
                "id": store.id,
                "slug": store.slug,
                "name": store.name,
            } if store else None,
            "exists_in_store": exists_in_store,
        }
    }), 200


@api_v1.route("/auth/register", methods=["POST"])
def api_register_customer():
    try:
        data = request.get_json(silent=True) or {}
        payload = _extract_customer_payload(data)

        errors = {}

        if not payload["store_slug"]:
            errors["store_slug"] = "store_slug e obrigatorio"

        if not payload["full_name"] or len(payload["full_name"]) < 3:
            errors["full_name"] = "full_name deve ter pelo menos 3 caracteres"

        if not payload["email"]:
            errors["email"] = "email e obrigatorio"
        elif not _is_valid_email(payload["email"]):
            errors["email"] = "email invalido"

        if not payload["password"]:
            errors["password"] = "password e obrigatorio"
        elif len(payload["password"]) < 6:
            errors["password"] = "password deve ter pelo menos 6 caracteres"

        if payload["password"] != payload["confirm_password"]:
            errors["confirm_password"] = "confirm_password nao confere"

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        store = _find_store_or_none(payload["store_slug"])
        if not store:
            return jsonify({"success": False, "error": "loja nao encontrada"}), 404

        existing_in_store = StoreCustomer.query.filter_by(store_id=store.id, email=payload["email"]).first()
        if existing_in_store:
            return jsonify({
                "success": False,
                "errors": {"email": "Este email ja esta cadastrado nesta loja"}
            }), 409

        existing_accounts = get_customers_by_email(payload["email"])
        linked_existing_account = False

        if existing_accounts:
            source_customer = find_customer_by_email_and_password(payload["email"], payload["password"])
            if not source_customer:
                return jsonify({
                    "success": False,
                    "errors": {
                        "email": "Este email ja existe na ZappShop. Use a senha correta para vincular"
                    }
                }), 409

            customer = ensure_customer_for_store(store, source_customer)
            linked_existing_account = True
        else:
            customer = StoreCustomer(
                store_id=store.id,
                email=payload["email"],
                password_hash=generate_password_hash(payload["password"]),
                full_name=payload["full_name"],
                phone=payload["phone"] or None,
                is_active=True,
            )
            db.session.add(customer)
            db.session.commit()

        if not customer or not customer.is_active:
            return jsonify({
                "success": False,
                "error": "Conta inativa para esta loja"
            }), 403

        token = _generate_customer_token(customer)

        return jsonify({
            "success": True,
            "message": "Cliente cadastrado com sucesso",
            "data": {
                "linked_existing_account": linked_existing_account,
                "token": token,
                "token_type": "Bearer",
                "expires_in_seconds": TOKEN_TTL_SECONDS,
                "customer": customer.to_dict(),
                "store": {
                    "id": store.id,
                    "slug": store.slug,
                    "name": store.name,
                }
            }
        }), 201

    except Exception as exc:
        db.session.rollback()
        print(f"Erro no cadastro da API: {exc}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Erro ao cadastrar cliente"
        }), 500


@api_v1.route("/auth/login", methods=["POST"])
def api_login_customer():
    try:
        data = request.get_json(silent=True) or {}

        store_slug = (data.get("store_slug") or "").strip().lower()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        errors = {}

        if not store_slug:
            errors["store_slug"] = "store_slug e obrigatorio"

        if not email:
            errors["email"] = "email e obrigatorio"

        if not password:
            errors["password"] = "password e obrigatorio"

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        store = _find_store_or_none(store_slug)
        if not store:
            return jsonify({"success": False, "error": "loja nao encontrada"}), 404

        existing_accounts = get_customers_by_email(email)
        if not existing_accounts:
            return jsonify({
                "success": False,
                "errors": {"email": "email nao encontrado"}
            }), 401

        source_customer = find_customer_by_email_and_password(email, password)
        if not source_customer:
            return jsonify({
                "success": False,
                "errors": {"password": "senha incorreta"}
            }), 401

        customer = ensure_customer_for_store(store, source_customer)
        if not customer or not customer.is_active:
            return jsonify({
                "success": False,
                "error": "Conta inativa para esta loja"
            }), 403

        token = _generate_customer_token(customer)

        return jsonify({
            "success": True,
            "message": "Login realizado com sucesso",
            "data": {
                "token": token,
                "token_type": "Bearer",
                "expires_in_seconds": TOKEN_TTL_SECONDS,
                "customer": customer.to_dict(),
                "store": {
                    "id": store.id,
                    "slug": store.slug,
                    "name": store.name,
                }
            }
        }), 200

    except Exception as exc:
        print(f"Erro no login da API: {exc}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Erro ao realizar login"
        }), 500


@api_v1.route("/auth/me", methods=["GET"])
@require_customer_token
def api_auth_me():
    customer = request.customer
    store = Store.query.filter_by(id=customer.store_id).first()

    return jsonify({
        "success": True,
        "data": {
            "customer": customer.to_dict(),
            "store": {
                "id": store.id,
                "slug": store.slug,
                "name": store.name,
            } if store else None
        }
    }), 200


@api_v1.route("/products", methods=["GET"])
def api_list_products():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        per_page = max(1, min(per_page, 100))

        store_slug = (request.args.get("store_slug") or "").strip().lower()
        category_id = (request.args.get("category_id") or "").strip()
        search = (request.args.get("search") or "").strip()

        stores_query = Store.query.filter_by(onboarding_completed=True)
        if store_slug:
            stores_query = stores_query.filter_by(slug=store_slug)

        store_ids = [store.id for store in stores_query.all()]
        if not store_ids:
            return jsonify({
                "success": True,
                "data": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": 0,
                    "pages": 0,
                    "has_next": False,
                    "has_prev": False,
                }
            }), 200

        query = Product.query.filter(Product.store_id.in_(store_ids), Product.active.is_(True))

        if category_id:
            query = query.filter(Product.category_id == category_id)

        if search:
            like_search = f"%{search}%"
            query = query.filter((Product.title.ilike(like_search)) | (Product.description.ilike(like_search)))

        query = query.order_by(Product.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        stores = Store.query.filter(Store.id.in_(store_ids)).all()
        store_map = {store.id: store for store in stores}

        products_data = []
        for product in pagination.items:
            payload = product.to_dict()
            store = store_map.get(product.store_id)
            payload["store"] = {
                "id": store.id,
                "slug": store.slug,
                "name": store.name,
            } if store else None
            products_data.append(payload)

        return jsonify({
            "success": True,
            "data": products_data,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }
        }), 200

    except Exception as exc:
        print(f"Erro ao listar produtos da API: {exc}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Erro ao carregar produtos"
        }), 500
