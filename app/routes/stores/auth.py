from flask import render_template, jsonify, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import db
from app.models.store import Store
from app.models.store_customer import StoreCustomer
from . import storefront
import traceback
import re


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

    # Se já logado, redireciona para a loja
    if session.get('customer_id') and session.get('customer_store_id') == store.id:
        return redirect(url_for('storefront.view_store', slug=slug))

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
        customization=customization
    )


@storefront.route('/<slug>/auth/register', methods=['GET'])
def customer_register_page(slug):
    """Página de registro do cliente da loja"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    if not store:
        from flask import abort
        abort(404)

    if session.get('customer_id') and session.get('customer_store_id') == store.id:
        return redirect(url_for('storefront.view_store', slug=slug))

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
        customization=customization
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

        # Verifica se email já cadastrado nesta loja
        existing = StoreCustomer.query.filter_by(store_id=store.id, email=email).first()
        if existing:
            return jsonify({
                'success': False,
                'errors': {'email': 'Este e-mail já está cadastrado nesta loja'}
            }), 409

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
        session['customer_id'] = customer.id
        session['customer_email'] = customer.email
        session['customer_name'] = customer.full_name
        session['customer_store_id'] = store.id
        session['customer_store_slug'] = store.slug

        print(f"Novo cliente registrado: {customer.email} na loja {store.name}")

        return jsonify({
            'success': True,
            'message': 'Conta criada com sucesso!',
            'data': {
                'customer_id': customer.id,
                'customer_name': customer.full_name,
                'customer_email': customer.email,
                'redirect_url': url_for('storefront.view_store', slug=slug)
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

        customer = StoreCustomer.query.filter_by(store_id=store.id, email=email).first()

        if not customer:
            return jsonify({
                'success': False,
                'errors': {'email': 'E-mail não encontrado nesta loja'}
            }), 401

        if not check_password_hash(customer.password_hash, password):
            return jsonify({
                'success': False,
                'errors': {'password': 'Senha incorreta'}
            }), 401

        if not customer.is_active:
            return jsonify({
                'success': False,
                'error': 'Conta desativada. Entre em contato com a loja.'
            }), 403

        # Salva sessão do cliente
        session['customer_id'] = customer.id
        session['customer_email'] = customer.email
        session['customer_name'] = customer.full_name
        session['customer_store_id'] = store.id
        session['customer_store_slug'] = store.slug

        print(f"Login de cliente: {customer.email} na loja {store.name}")

        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso!',
            'data': {
                'customer_id': customer.id,
                'customer_name': customer.full_name,
                'customer_email': customer.email,
                'redirect_url': url_for('storefront.view_store', slug=slug)
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
    try:
        customer_email = session.get('customer_email', 'Desconhecido')

        # Remove apenas dados do cliente (mantém sessão do admin se houver)
        session.pop('customer_id', None)
        session.pop('customer_email', None)
        session.pop('customer_name', None)
        session.pop('customer_store_id', None)
        session.pop('customer_store_slug', None)

        print(f"Logout de cliente: {customer_email}")

        if request.method == 'GET':
            return redirect(url_for('storefront.view_store', slug=slug))

        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        }), 200

    except Exception as e:
        print(f"Erro no logout de cliente: {e}")
        if request.method == 'GET':
            return redirect(url_for('storefront.view_store', slug=slug))
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

    if session.get('customer_id') and session.get('customer_store_id') == store.id:
        customer = StoreCustomer.query.get(session['customer_id'])
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
