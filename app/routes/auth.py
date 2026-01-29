from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from config.database import db
from app.models.user import User
from app.models.store import Store
import traceback

auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route('/login', methods=['GET'])
def login_form():
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard'))
    return render_template('auth/login.html')


@auth.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        print(f"\n=== LOGIN ===")
        print(f"Email: {email}")
        
        errors = {}
        
        if not email:
            errors['email'] = 'Email é obrigatório'
        
        if not password:
            errors['password'] = 'Senha é obrigatória'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'success': False,
                'errors': {
                    'email': 'Usuário não encontrado'
                }
            }), 401
        
        if not check_password_hash(user.password_hash, password):
            return jsonify({
                'success': False,
                'errors': {
                    'password': 'Senha incorreta'
                }
            }), 401
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Usuário inativo. Entre em contato com o suporte.'
            }), 403
        
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.full_name
        session['is_seller'] = user.is_seller
        
        store = Store.query.filter_by(owner_id=user.id, onboarding_completed=True).first()
        
        if store:
            session['store_id'] = store.id
            session['store_slug'] = store.slug
            session['store_name'] = store.name
        
        print(f"Login bem-sucedido: {user.email}")
        print(f"Loja: {store.name if store else 'Nenhuma'}")
        print(f"=== FIM LOGIN ===\n")
        
        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso',
            'data': {
                'user_id': user.id,
                'user_name': user.full_name,
                'user_email': user.email,
                'is_seller': user.is_seller,
                'has_store': store is not None,
                'store_id': store.id if store else None,
                'store_slug': store.slug if store else None,
                'store_name': store.name if store else None,
                'redirect_url': '/admin/dashboard' if store else '/registration/'
            }
        }), 200
        
    except Exception as e:
        print(f"Erro no login: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar login. Tente novamente.'
        }), 500


@auth.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        user_email = session.get('user_email', 'Desconhecido')
        
        session.clear()
        
        print(f"Logout realizado: {user_email}")
        
        if request.method == 'GET':
            return redirect(url_for('auth.login_form'))
        
        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        }), 200
        
    except Exception as e:
        print(f"Erro no logout: {e}")
        if request.method == 'GET':
            return redirect(url_for('auth.login_form'))
        return jsonify({
            'success': False,
            'error': 'Erro ao processar logout'
        }), 500


@auth.route('/check', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_active:
            session.clear()
            return jsonify({
                'authenticated': False
            }), 200
        
        store = Store.query.filter_by(owner_id=user.id, onboarding_completed=True).first()
        
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.id,
                'name': user.full_name,
                'email': user.email,
                'is_seller': user.is_seller
            },
            'store': {
                'id': store.id,
                'name': store.name,
                'slug': store.slug
            } if store else None
        }), 200
    
    return jsonify({
        'authenticated': False
    }), 200


@auth.route('/register', methods=['GET'])
def register_form():
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard'))
    return render_template('auth/register.html')