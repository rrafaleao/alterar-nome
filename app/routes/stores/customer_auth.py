from flask import session
from config.database import db
from app.models.store_customer import StoreCustomer
from werkzeug.security import check_password_hash


def clear_customer_session():
    """Remove dados de sessão do cliente comum."""
    session.pop('customer_id', None)
    session.pop('customer_email', None)
    session.pop('customer_name', None)
    session.pop('customer_store_id', None)
    session.pop('customer_store_slug', None)


def set_customer_session(customer, store):
    """Atualiza a sessão com o cliente da loja atual."""
    session['customer_id'] = customer.id
    session['customer_email'] = customer.email
    session['customer_name'] = customer.full_name
    session['customer_store_id'] = store.id
    session['customer_store_slug'] = store.slug


def get_customers_by_email(email):
    """Busca todas as contas de cliente comum pelo e-mail em todas as lojas."""
    if not email:
        return []

    return StoreCustomer.query.filter_by(email=email).order_by(StoreCustomer.created_at.asc()).all()


def find_customer_by_email_and_password(email, password):
    """Busca uma conta de cliente pelo e-mail e senha em qualquer loja."""
    if not email or not password:
        return None

    customers = get_customers_by_email(email)

    for customer in customers:
        if check_password_hash(customer.password_hash, password):
            return customer

    return None


def ensure_customer_for_store(store, source_customer):
    """
    Garante que exista um StoreCustomer para a loja atual com base no e-mail da conta origem.
    Se não existir, cria automaticamente reaproveitando os dados principais da conta origem.
    """
    if not store or not source_customer:
        return None

    customer = StoreCustomer.query.filter_by(store_id=store.id, email=source_customer.email).first()
    if customer:
        return customer

    customer = StoreCustomer(
        store_id=store.id,
        email=source_customer.email,
        password_hash=source_customer.password_hash,
        full_name=source_customer.full_name,
        phone=source_customer.phone,
        is_active=True,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def sync_customer_session_for_store(store):
    """
    Sincroniza a sessão do cliente comum para a loja acessada.
    Permite que a mesma conta funcione em qualquer loja usando o e-mail da sessão.
    """
    if not store:
        return None

    customer_email = (session.get('customer_email') or '').strip().lower()
    if not customer_email:
        return None

    session_customer_id = session.get('customer_id')
    session_store_id = session.get('customer_store_id')

    if session_customer_id and session_store_id == store.id:
        current_customer = StoreCustomer.query.get(session_customer_id)
        if current_customer and current_customer.email == customer_email:
            if session.get('customer_name') != current_customer.full_name:
                session['customer_name'] = current_customer.full_name
            return current_customer

    source_customer = StoreCustomer.query.filter_by(email=customer_email).order_by(StoreCustomer.created_at.asc()).first()
    if not source_customer:
        clear_customer_session()
        return None

    try:
        target_customer = ensure_customer_for_store(store, source_customer)
    except Exception:
        db.session.rollback()
        raise

    if not target_customer:
        return None

    set_customer_session(target_customer, store)
    return target_customer
