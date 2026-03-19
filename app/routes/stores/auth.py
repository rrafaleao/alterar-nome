from flask import render_template, jsonify, request, session, redirect, url_for
from werkzeug.security import generate_password_hash
from config.database import db
from app.models.store import Store
from app.models.store_customer import StoreCustomer
from . import storefront
from .customer_auth import (
    clear_customer_session,
    ensure_customer_for_store,
    find_customer_by_email_and_password,
    get_customers_by_email,
    set_customer_session,
    sync_customer_session_for_store,
)
import traceback
import re


def _get_safe_next_url(value):
    """Aceita apenas redirecionamentos internos relativos para evitar open redirect."""
    if not value:
        return None

    if not value.startswith('/'):
        return None

    if value.startswith('//') or '://' in value:
        return None

    return value


# ========================================
# PÁGINAS (GET)
# ========================================

@storefront.route('/<slug>/auth/login', methods=['GET'])
def customer_login_page(slug):
    """Página de login do cliente da loja"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    if not store:
        from flask import abort
        abort(404)

    next_url = _get_safe_next_url(request.args.get('next'))

    # Se já logado (inclusive vindo de outra loja), sincroniza e redireciona
    current_customer = sync_customer_session_for_store(store)
    if current_customer and current_customer.is_active:
        return redirect(next_url or url_for('storefront.view_store', slug=slug))

    customization = {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2'
    }
    if store.customization:
        customization['primary_color'] = store.customization.primary_color or '#667eea'
        customization['secondary_color'] = store.customization.secondary_color or '#764ba2'

    return render_template(
        'stores/auth/login.html',
        store=store,
        customization=customization,
        next_url=next_url
    )


@storefront.route('/<slug>/auth/register', methods=['GET'])
def customer_register_page(slug):
    """Página de registro do cliente da loja"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    if not store:
        from flask import abort
        abort(404)

    next_url = _get_safe_next_url(request.args.get('next'))

    current_customer = sync_customer_session_for_store(store)
    if current_customer and current_customer.is_active:
        return redirect(next_url or url_for('storefront.view_store', slug=slug))

    customization = {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2'
    }
    if store.customization:
        customization['primary_color'] = store.customization.primary_color or '#667eea'
        customization['secondary_color'] = store.customization.secondary_color or '#764ba2'

    return render_template(
        'stores/auth/register.html',
        store=store,
        customization=customization,
        next_url=next_url
    )


# ========================================
# API (POST)
# ========================================

@storefront.route('/<slug>/auth/register', methods=['POST'])
def customer_register(slug):
    """Registra um novo cliente na loja"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        next_url = _get_safe_next_url(request.args.get('next'))

        data = request.get_json()

        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Validações
        errors = {}

        if not full_name or len(full_name) < 3:
            errors['full_name'] = 'Nome completo deve ter pelo menos 3 caracteres'

        if not email:
            errors['email'] = 'E-mail é obrigatório'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors['email'] = 'E-mail inválido'

        if not password:
            errors['password'] = 'Senha é obrigatória'
        elif len(password) < 6:
            errors['password'] = 'Senha deve ter pelo menos 6 caracteres'

        if password != confirm_password:
            errors['confirm_password'] = 'As senhas não coincidem'

        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        # Se já existe na loja atual, impede novo cadastro duplicado
        existing_in_store = StoreCustomer.query.filter_by(store_id=store.id, email=email).first()
        if existing_in_store:
            return jsonify({
                'success': False,
                'errors': {'email': 'Este e-mail já está cadastrado nesta loja. Faça login.'}
            }), 409

        # Se já existe em qualquer loja, vincula automaticamente esta loja
        existing_accounts = get_customers_by_email(email)
        if existing_accounts:
            source_customer = find_customer_by_email_and_password(email, password)

            if not source_customer:
                return jsonify({
                    'success': False,
                    'errors': {
                        'email': 'Este e-mail já está cadastrado na ZappShop. Use a senha correta para entrar.'
                    }
                }), 409

            customer = ensure_customer_for_store(store, source_customer)

            if not customer:
                return jsonify({
                    'success': False,
                    'error': 'Não foi possível vincular sua conta nesta loja. Tente novamente.'
                }), 500

            if not customer.is_active:
                return jsonify({
                    'success': False,
                    'error': 'Conta desativada para esta loja. Entre em contato com a loja.'
                }), 403

            set_customer_session(customer, store)

            redirect_url = (
                session.pop('checkout_redirect', None)
                or next_url
                or url_for('storefront.view_store', slug=slug)
            )

            return jsonify({
                'success': True,
                'message': 'Conta existente vinculada com sucesso! Você já pode comprar nesta loja.',
                'data': {
                    'customer_id': customer.id,
                    'customer_name': customer.full_name,
                    'customer_email': customer.email,
                    'redirect_url': redirect_url
                }
            }), 200

        # Cria o cliente
        customer = StoreCustomer(
            store_id=store.id,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            phone=phone if phone else None,
        )

        db.session.add(customer)
        db.session.commit()

        # Loga automaticamente após registro
        set_customer_session(customer, store)

        # Verificar se há redirecionamento pendente (ex: checkout)
        redirect_url = (
            session.pop('checkout_redirect', None)
            or next_url
            or url_for('storefront.view_store', slug=slug)
        )

        print(f"Novo cliente registrado: {customer.email} na loja {store.name}")

        return jsonify({
            'success': True,
            'message': 'Conta criada com sucesso!',
            'data': {
                'customer_id': customer.id,
                'customer_name': customer.full_name,
                'customer_email': customer.email,
                'redirect_url': redirect_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Erro no registro de cliente: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erro ao criar conta. Tente novamente.'
        }), 500


@storefront.route('/<slug>/auth/login', methods=['POST'])
def customer_login(slug):
    """Login do cliente da loja"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        next_url = _get_safe_next_url(request.args.get('next'))

        data = request.get_json()

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        errors = {}
        if not email:
            errors['email'] = 'E-mail é obrigatório'
        if not password:
            errors['password'] = 'Senha é obrigatória'

        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        existing_accounts = get_customers_by_email(email)

        if not existing_accounts:
            return jsonify({
                'success': False,
                'errors': {'email': 'E-mail não encontrado'}
            }), 401

        source_customer = find_customer_by_email_and_password(email, password)
        if not source_customer:
            return jsonify({
                'success': False,
                'errors': {'password': 'Senha incorreta'}
            }), 401

        customer = ensure_customer_for_store(store, source_customer)

        if not customer:
            return jsonify({
                'success': False,
                'error': 'Não foi possível preparar sua conta nesta loja. Tente novamente.'
            }), 500

        if not customer.is_active:
            return jsonify({
                'success': False,
                'error': 'Conta desativada para esta loja. Entre em contato com a loja.'
            }), 403

        # Salva sessão do cliente
        set_customer_session(customer, store)

        # Verificar se há redirecionamento pendente (ex: checkout)
        redirect_url = (
            session.pop('checkout_redirect', None)
            or next_url
            or url_for('storefront.view_store', slug=slug)
        )

        print(f"Login de cliente: {customer.email} na loja {store.name}")

        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso!',
            'data': {
                'customer_id': customer.id,
                'customer_name': customer.full_name,
                'customer_email': customer.email,
                'redirect_url': redirect_url
            }
        }), 200

    except Exception as e:
        print(f"Erro no login de cliente: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar login. Tente novamente.'
        }), 500


@storefront.route('/<slug>/auth/logout', methods=['GET', 'POST'])
def customer_logout(slug):
    """Logout do cliente da loja"""
    next_url = _get_safe_next_url(request.args.get('next'))

    try:
        customer_email = session.get('customer_email', 'Desconhecido')

        # Remove apenas dados do cliente (mantém sessão do admin se houver)
        clear_customer_session()

        print(f"Logout de cliente: {customer_email}")

        if request.method == 'GET':
            return redirect(next_url or url_for('storefront.view_store', slug=slug))

        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        }), 200

    except Exception as e:
        print(f"Erro no logout de cliente: {e}")
        if request.method == 'GET':
            return redirect(next_url or url_for('storefront.view_store', slug=slug))
        return jsonify({
            'success': False,
            'error': 'Erro ao processar logout'
        }), 500


@storefront.route('/<slug>/auth/check', methods=['GET'])
def customer_check_auth(slug):
    """Verifica se o cliente está logado"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    if not store:
        return jsonify({'authenticated': False}), 200

    customer = sync_customer_session_for_store(store)

    if customer and customer.is_active:
        return jsonify({
            'authenticated': True,
            'customer': {
                'id': customer.id,
                'name': customer.full_name,
                'email': customer.email,
            }
        }), 200

    return jsonify({'authenticated': False}), 200
