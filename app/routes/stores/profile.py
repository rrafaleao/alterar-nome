from decimal import Decimal

from flask import abort, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from config.database import db
from app.models.address import Address
from app.models.category import Category
from app.models.order import Order
from app.models.payment import Payment
from app.models.store import Store
from app.models.store_admin import StoreAdmin
from app.models.store_customer import StoreCustomer
from . import storefront
from .customer_auth import sync_customer_session_for_store


PROFILE_PAYMENT_SCOPE = "customer_profile"


STATUS_LABELS = {
    "pending": "Pendente",
    "paid": "Pago",
    "shipped": "Enviado",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
    "refunded": "Reembolsado",
}


PAYMENT_METHOD_LABELS = {
    "pix": "PIX",
    "credit_card": "Cartao de Credito",
    "debit_card": "Cartao de Debito",
    "boleto": "Boleto",
}


def _profile_context(store):
    customization = {
        "primary_color": "#667eea",
        "secondary_color": "#764ba2",
    }
    if store.customization:
        customization["primary_color"] = store.customization.primary_color or "#667eea"
        customization["secondary_color"] = store.customization.secondary_color or "#764ba2"

    categories = Category.query.filter_by(store_id=store.id).order_by(Category.name).all()
    return customization, categories


def _store_and_customer_or_login(slug):
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    if not store:
        abort(404)

    customer = sync_customer_session_for_store(store)
    if not customer or not customer.is_active:
        next_url = url_for("storefront.customer_profile", slug=slug)
        return store, None, redirect(url_for("storefront.customer_login_page", slug=slug, next=next_url))

    return store, customer, None


def _build_payment_profile_data(store, customer, method, details):
    return {
        "scope": PROFILE_PAYMENT_SCOPE,
        "store_id": store.id,
        "customer_id": customer.id,
        "method": method,
        "method_details": details,
    }


def _find_customer_profile_payment(store_id, customer_id):
    profile_rows = Payment.query.filter(Payment.order_id.is_(None)).order_by(
        Payment.updated_at.desc(),
        Payment.created_at.desc(),
    ).limit(300).all()

    for row in profile_rows:
        data = row.payment_data if isinstance(row.payment_data, dict) else {}
        if not data:
            continue
        if data.get("scope") != PROFILE_PAYMENT_SCOPE:
            continue
        if data.get("store_id") != store_id:
            continue
        if data.get("customer_id") != customer_id:
            continue
        return row

    return None


def _get_saved_payment_profile(store, customer):
    profile_row = _find_customer_profile_payment(store.id, customer.id)
    if not profile_row:
        return {
            "method": "",
            "method_details": {},
        }

    profile_data = profile_row.payment_data if isinstance(profile_row.payment_data, dict) else {}
    return {
        "method": profile_data.get("method") or profile_row.method or "",
        "method_details": profile_data.get("method_details") or {},
    }


def _upsert_payment_profile(store, customer, method, details):
    payload = _build_payment_profile_data(store, customer, method, details)
    row = _find_customer_profile_payment(store.id, customer.id)

    if row:
        row.method = method
        row.payment_data = payload
    else:
        row = Payment(
            order_id=None,
            method=method,
            amount=Decimal("0.00"),
            status="created",
            payment_data=payload,
        )
        db.session.add(row)


def _sanitize_payment_form(method, form_data):
    details = {}

    if method == "pix":
        pix_key = (form_data.get("pix_key") or "").strip()
        details["pix_key"] = pix_key

    if method in {"credit_card", "debit_card"}:
        holder = (form_data.get("card_holder") or "").strip()
        card_number = (form_data.get("card_number") or "").replace(" ", "")
        expiry = (form_data.get("card_expiry") or "").strip()
        details["card_holder"] = holder
        details["card_last4"] = card_number[-4:] if card_number else ""
        details["card_expiry"] = expiry

    if method == "boleto":
        document = "".join(ch for ch in (form_data.get("document") or "") if ch.isdigit())
        details["document"] = document

    return details


@storefront.route('/<slug>/perfil')
def customer_profile(slug):
    store, customer, redirect_response = _store_and_customer_or_login(slug)
    if redirect_response:
        return redirect_response

    section = (request.args.get("section") or "orders").strip().lower()
    if section not in {"orders", "account", "payment"}:
        section = "orders"

    orders = Order.query.filter_by(
        store_id=store.id,
        user_id=customer.id,
    ).order_by(
        Order.placed_at.desc(),
        Order.updated_at.desc(),
    ).all()

    last_address = Address.query.filter_by(user_id=customer.id).order_by(Address.created_at.desc()).first()
    payment_profile = _get_saved_payment_profile(store, customer)

    enabled_methods = [pm.method for pm in store.payment_methods if pm.is_enabled]
    if not enabled_methods:
        enabled_methods = ["pix", "credit_card", "debit_card", "boleto"]

    customization, categories = _profile_context(store)

    is_admin = StoreAdmin.is_admin(store.id, customer.id) if customer.is_active else False

    return render_template(
        'stores/profile.html',
        store=store,
        customer=customer,
        orders=orders,
        last_address=last_address,
        payment_profile=payment_profile,
        enabled_methods=enabled_methods,
        payment_method_labels=PAYMENT_METHOD_LABELS,
        status_labels=STATUS_LABELS,
        section=section,
        saved=request.args.get("saved"),
        error=request.args.get("error"),
        customization=customization,
        categories=categories,
        is_admin=is_admin,
    )


@storefront.route('/<slug>/perfil/conta', methods=['POST'])
def update_customer_account(slug):
    store, customer, redirect_response = _store_and_customer_or_login(slug)
    if redirect_response:
        return redirect_response

    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if len(full_name) < 3:
        return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="Nome invalido"))

    if not email:
        return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="E-mail obrigatorio"))

    existing_customer = StoreCustomer.query.filter(
        StoreCustomer.store_id == store.id,
        StoreCustomer.email == email,
        StoreCustomer.id != customer.id,
    ).first()
    if existing_customer:
        return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="E-mail ja esta em uso"))

    if password:
        if len(password) < 6:
            return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="Senha precisa ter 6 caracteres"))
        if password != password_confirm:
            return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="Confirmacao de senha invalida"))

    try:
        customer.full_name = full_name
        customer.email = email
        customer.phone = phone or None

        if password:
            customer.password_hash = generate_password_hash(password)

        cep = (request.form.get("cep") or "").strip()
        street = (request.form.get("street") or "").strip()
        number = (request.form.get("number") or "").strip()
        complement = (request.form.get("complement") or "").strip()
        neighborhood = (request.form.get("neighborhood") or "").strip()
        city = (request.form.get("city") or "").strip()
        state = (request.form.get("state") or "").strip().upper()

        has_address_data = any([cep, street, number, complement, neighborhood, city, state])
        if has_address_data:
            address = Address.query.filter_by(user_id=customer.id).order_by(Address.created_at.desc()).first()
            if not address:
                address = Address(user_id=customer.id)
                db.session.add(address)

            address.cep = cep
            address.street = street
            address.number = number
            address.complement = complement
            address.neighborhood = neighborhood
            address.city = city
            address.state = state

        db.session.commit()

        session["customer_name"] = customer.full_name
        session["customer_email"] = customer.email

        return redirect(url_for("storefront.customer_profile", slug=slug, section="account", saved="1"))

    except Exception:
        db.session.rollback()
        return redirect(url_for("storefront.customer_profile", slug=slug, section="account", error="Erro ao salvar conta"))


@storefront.route('/<slug>/perfil/pagamento', methods=['POST'])
def update_customer_payment_profile(slug):
    store, customer, redirect_response = _store_and_customer_or_login(slug)
    if redirect_response:
        return redirect_response

    method = (request.form.get("preferred_method") or "").strip()

    if method not in {"pix", "credit_card", "debit_card", "boleto"}:
        return redirect(url_for("storefront.customer_profile", slug=slug, section="payment", error="Metodo de pagamento invalido"))

    if store.payment_methods:
        enabled_methods = [pm.method for pm in store.payment_methods if pm.is_enabled]
        if enabled_methods and method not in enabled_methods:
            return redirect(url_for("storefront.customer_profile", slug=slug, section="payment", error="Metodo nao habilitado nesta loja"))

    details = _sanitize_payment_form(method, request.form)

    try:
        _upsert_payment_profile(store, customer, method, details)
        db.session.commit()
        return redirect(url_for("storefront.customer_profile", slug=slug, section="payment", saved="1"))
    except Exception:
        db.session.rollback()
        return redirect(url_for("storefront.customer_profile", slug=slug, section="payment", error="Erro ao salvar pagamento"))
