from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from functools import wraps
from config.database import db
from app.models.user import User
from app.models.store import Store
from app.models.product import Product
from app.models.category import Category
from sqlalchemy import func

admin = Blueprint("admin", __name__, url_prefix="/admin")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login_form'))
        return f(*args, **kwargs)
    return decorated_function


def store_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'store_id' not in session:
            return redirect(url_for('registration.show_registration_form'))
        return f(*args, **kwargs)
    return decorated_function


@admin.route('/dashboard')
@login_required
@store_required
def dashboard():
    return render_template('admin/dashboard.html')


@admin.route('/dashboard/stats', methods=['GET'])
@login_required
@store_required
def dashboard_stats():
    try:
        store_id = session.get('store_id')
        
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        total_products = Product.query.filter_by(store_id=store_id).count()
        active_products = Product.query.filter_by(store_id=store_id, active=True).count()
        total_categories = Category.query.filter_by(store_id=store_id).count()
        
        recent_products = Product.query.filter_by(store_id=store_id)\
            .order_by(Product.created_at.desc())\
            .limit(5)\
            .all()
        
        stats = {
            'store': {
                'id': store.id,
                'name': store.name,
                'slug': store.slug,
                'logo_url': store.logo_url,
                'is_published': store.is_published,
                'created_at': store.created_at.isoformat() if store.created_at else None
            },
            'products': {
                'total': total_products,
                'active': active_products,
                'inactive': total_products - active_products
            },
            'categories': {
                'total': total_categories
            },
            'recent_products': [p.to_dict() for p in recent_products]
        }
        
        if store.customization:
            stats['store']['customization'] = store.customization.to_dict()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar estatísticas'
        }), 500


@admin.route('/products')
@login_required
@store_required
def products_page():
    return render_template('admin/products.html')


@admin.route('/categories')
@login_required
@store_required
def categories_page():
    return render_template('admin/categories.html')


@admin.route('/orders')
@login_required
@store_required
def orders_page():
    return render_template('admin/orders.html')


@admin.route('/settings')
@login_required
@store_required
def settings_page():
    return render_template('admin/settings.html')


@admin.route('/settings/store', methods=['GET'])
@login_required
@store_required
def get_store_settings():
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        store_data = store.to_dict(include_details=True)
        
        return jsonify({
            'success': True,
            'data': store_data
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar configurações: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar configurações'
        }), 500


@admin.route('/my-store')
@login_required
@store_required
def my_store_info():
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'id': store.id,
                'name': store.name,
                'slug': store.slug,
                'description': store.description,
                'logo_url': store.logo_url,
                'is_published': store.is_published,
                'public_url': f'/{store.slug}'
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar informações da loja: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar loja'
        }), 500