from flask import Blueprint, jsonify, render_template, abort, request
from config.database import db
from app.models.store import Store, StoreCustomization
from app.models.user import User
from app.models.store_payment_method import StorePaymentMethod
from app.models.store_shipping_methods import StoreShippingMethod
from app.models.product import Product
from app.models.category import Category

storefront = Blueprint("storefront", __name__)


@storefront.route('/<slug>')
def view_store(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        store_data = store.to_dict(include_details=True)
        store_data['owner_name'] = store.owner.full_name if store.owner else None
        store_data['owner_email'] = store.owner.email if store.owner else None
        
        return jsonify({
            'success': True,
            'data': store_data
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar loja: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar loja'
        }), 500


@storefront.route('/<slug>/products')
def store_products(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category_id = request.args.get('category', None, type=str)
        search = request.args.get('search', '', type=str)
        
        query = Product.query.filter_by(store_id=store.id, active=True)
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if search:
            query = query.filter(
                (Product.title.ilike(f'%{search}%')) | 
                (Product.description.ilike(f'%{search}%'))
            )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        products_data = [product.to_dict() for product in pagination.items]
        
        return jsonify({
            'success': True,
            'data': products_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar produtos'
        }), 500


@storefront.route('/<slug>/products/<product_id>')
def store_product_detail(slug, product_id):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        product = Product.query.filter_by(id=product_id, store_id=store.id, active=True).first()
        
        if not product:
            abort(404)
        
        product_data = product.to_dict()
        
        return jsonify({
            'success': True,
            'data': product_data
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar produto: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar produto'
        }), 500


@storefront.route('/<slug>/categories')
def store_categories(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        categories = Category.query.filter_by(store_id=store.id).all()
        
        categories_data = [cat.to_dict() for cat in categories]
        
        return jsonify({
            'success': True,
            'data': categories_data
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar categorias'
        }), 500


@storefront.route('/<slug>/info')
def store_info(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        info = {
            'id': store.id,
            'name': store.name,
            'description': store.description,
            'logo_url': store.logo_url,
            'slug': store.slug,
            'person_type': store.person_type
        }
        
        if store.customization:
            info['customization'] = store.customization.to_dict()
        
        payment_methods = [pm.method for pm in store.payment_methods if pm.is_enabled]
        shipping_methods = [sm.method for sm in store.shipping_methods if sm.is_enabled]
        
        info['payment_methods'] = payment_methods
        info['shipping_methods'] = shipping_methods
        
        return jsonify({
            'success': True,
            'data': info
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar informações: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar informações'
        }), 500


@storefront.route('/stores')
def list_all_stores():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        
        query = Store.query.filter_by(onboarding_completed=True, is_published=True)
        
        if search:
            query = query.filter(
                (Store.name.ilike(f'%{search}%')) | 
                (Store.slug.ilike(f'%{search}%'))
            )
        
        pagination = query.order_by(Store.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        stores_data = []
        for store in pagination.items:
            store_dict = {
                'id': store.id,
                'name': store.name,
                'slug': store.slug,
                'description': store.description,
                'logo_url': store.logo_url,
                'created_at': store.created_at.isoformat() if store.created_at else None
            }
            
            if store.customization:
                store_dict['primary_color'] = store.customization.primary_color
                store_dict['template'] = store.customization.theme.get('template') if store.customization.theme else None
            
            stores_data.append(store_dict)
        
        return jsonify({
            'success': True,
            'data': stores_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao listar lojas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar lojas'
        }), 500