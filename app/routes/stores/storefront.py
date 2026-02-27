from flask import render_template, abort, request, jsonify, session
from datetime import datetime
from config.database import db
from app.models.store import Store, StoreCustomization
from app.models.product import Product
from app.models.category import Category
from app.models.customer_favorite import CustomerFavorite
from app.models.promotion import Promotion, PromotionProduct, PromotionCategory
from app.models.store_admin import StoreAdmin
from . import storefront


def get_active_promotions(store_id):
    """Busca promoções ativas da loja"""
    now = datetime.utcnow()
    return Promotion.query.filter(
        Promotion.store_id == store_id,
        Promotion.is_active == True,
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).all()


def calculate_product_promotion(product, active_promotions):
    """Calcula se um produto tem promoção e retorna os dados"""
    for promo in active_promotions:
        applies = False
        
        if promo.applies_to == 'all':
            applies = True
        elif promo.applies_to == 'products':
            product_ids = [pp.product_id for pp in promo.products]
            if product.id in product_ids:
                applies = True
        elif promo.applies_to == 'categories':
            category_ids = [pc.category_id for pc in promo.categories]
            if product.category_id and product.category_id in category_ids:
                applies = True
        
        if applies:
            original_price = float(product.price)
            promo_price = promo.calculate_discount(original_price)
            discount_percent = ((original_price - promo_price) / original_price) * 100
            return {
                'has_promotion': True,
                'promotion_name': promo.name,
                'original_price': original_price,
                'promo_price': promo_price,
                'discount_percent': round(discount_percent),
                'discount_type': promo.discount_type,
                'discount_value': float(promo.discount_value)
            }
    
    return {'has_promotion': False}


@storefront.route('/<slug>')
def view_store(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        # Buscar produtos ativos da loja
        products = Product.query.filter_by(
            store_id=store.id, 
            active=True
        ).order_by(Product.created_at.desc()).limit(12).all()
        
        # Buscar categorias da loja
        categories = Category.query.filter_by(
            store_id=store.id
        ).order_by(Category.name).all()
        
        # Buscar promoções ativas
        active_promotions = get_active_promotions(store.id)
        
        # Calcular promoções para cada produto
        products_with_promo = []
        for product in products:
            promo_info = calculate_product_promotion(product, active_promotions)
            products_with_promo.append({
                'product': product,
                'promo': promo_info
            })
        
        # Preparar dados de customização
        customization = {
            'primary_color': '#667eea',
            'secondary_color': '#764ba2'
        }
        
        if store.customization:
            customization['primary_color'] = store.customization.primary_color or '#667eea'
            customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
        
        template_name = 'layout1.html'
        
        if store.customization and store.customization.theme:
            template_type = store.customization.theme.get('template', 'default')
            template_map = {
                'default': 'layout1.html',
                'modern': 'layout1.html',
                'minimal': 'layout1.html',
                'colorful': 'layout1.html',
                'elegant': 'layout1.html'
            }
            template_name = template_map.get(template_type, 'layout1.html')
        
        # Verificar se o cliente logado é admin da loja
        is_admin = False
        if session.get('customer_id') and session.get('customer_store_id') == store.id:
            is_admin = StoreAdmin.is_admin(store.id, session.get('customer_id'))
        
        return render_template(
            f'layouts/{template_name}', 
            store=store,
            products=products,
            products_with_promo=products_with_promo,
            categories=categories,
            customization=customization,
            is_admin=is_admin
        )
        
    except Exception as e:
        print(f"Erro ao buscar loja: {e}")
        abort(500)


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


@storefront.route('/<slug>/produto/<product_id>')
def store_product_page(slug, product_id):
    """Página de detalhes do produto com todas as imagens e informações"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        product = Product.query.filter_by(id=product_id, store_id=store.id, active=True).first()
        
        if not product:
            abort(404)
        
        # Buscar promoções ativas para calcular possível desconto
        active_promotions = get_active_promotions(store.id)
        promo_info = calculate_product_promotion(product, active_promotions)
        
        # Preparar dados de customização
        customization = {
            'primary_color': '#667eea',
            'secondary_color': '#764ba2'
        }
        
        if store.customization:
            customization['primary_color'] = store.customization.primary_color or '#667eea'
            customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
        
        # Verificar se o cliente logado é admin da loja
        is_admin = False
        if session.get('customer_id') and session.get('customer_store_id') == store.id:
            is_admin = StoreAdmin.is_admin(store.id, session.get('customer_id'))
        
        return render_template(
            'stores/product_detail.html',
            store=store,
            product=product,
            promo=promo_info,
            customization=customization,
            is_admin=is_admin
        )
        
    except Exception as e:
        print(f"Erro ao carregar página do produto: {e}")
        abort(500)


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


@storefront.route('/<slug>/categoria/<category_id>')
def store_category_page(slug, category_id):
    """Página de categoria mostrando produtos filtrados"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)
        
        # Buscar a categoria
        category = Category.query.filter_by(id=category_id, store_id=store.id).first()
        
        if not category:
            abort(404)
        
        # Buscar produtos da categoria
        products = Product.query.filter_by(
            store_id=store.id,
            category_id=category_id,
            active=True
        ).order_by(Product.created_at.desc()).all()
        
        # Buscar todas as categorias para a navegação
        categories = Category.query.filter_by(store_id=store.id).order_by(Category.name).all()
        
        # Buscar promoções ativas
        active_promotions = get_active_promotions(store.id)
        
        # Calcular promoções para cada produto
        products_with_promo = []
        for product in products:
            promo_info = calculate_product_promotion(product, active_promotions)
            products_with_promo.append({
                'product': product,
                'promo': promo_info
            })
        
        # Preparar dados de customização
        customization = {
            'primary_color': '#667eea',
            'secondary_color': '#764ba2'
        }
        
        if store.customization:
            customization['primary_color'] = store.customization.primary_color or '#667eea'
            customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
        
        # Verificar se o cliente logado é admin da loja
        is_admin = False
        if session.get('customer_id') and session.get('customer_store_id') == store.id:
            is_admin = StoreAdmin.is_admin(store.id, session.get('customer_id'))
        
        return render_template(
            'stores/category.html',
            store=store,
            category=category,
            products=products,
            products_with_promo=products_with_promo,
            categories=categories,
            customization=customization,
            is_admin=is_admin
        )
        
    except Exception as e:
        print(f"Erro ao carregar página da categoria: {e}")
        abort(500)


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


# ========================================
# FAVORITES
# ========================================

@storefront.route('/<slug>/favorites')
def favorites_page(slug):
    """Página de favoritos do cliente"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    
    if not store:
        abort(404)
    
    # Se não estiver logado, redireciona para login
    if not session.get('customer_id') or session.get('customer_store_id') != store.id:
        from flask import redirect, url_for
        return redirect(url_for('storefront.customer_login_page', slug=slug))
    
    # Buscar favoritos do cliente
    favorites = CustomerFavorite.query.filter_by(
        customer_id=session.get('customer_id')
    ).order_by(CustomerFavorite.created_at.desc()).all()
    
    # Filtrar produtos ativos da loja
    favorite_products = [
        fav.product for fav in favorites 
        if fav.product and fav.product.active and fav.product.store_id == store.id
    ]
    
    # Buscar categorias da loja
    categories = Category.query.filter_by(store_id=store.id).order_by(Category.name).all()
    
    # Preparar dados de customização
    customization = {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2'
    }
    
    if store.customization:
        customization['primary_color'] = store.customization.primary_color or '#667eea'
        customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
    
    # Verificar se o cliente logado é admin da loja
    is_admin = False
    if session.get('customer_id') and session.get('customer_store_id') == store.id:
        is_admin = StoreAdmin.is_admin(store.id, session.get('customer_id'))
    
    return render_template(
        'stores/favorites.html',
        store=store,
        products=favorite_products,
        categories=categories,
        customization=customization,
        is_admin=is_admin
    )


@storefront.route('/<slug>/favorites/toggle', methods=['POST'])
def toggle_favorite(slug):
    """Adiciona ou remove um produto dos favoritos"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404
        
        # Verifica se está logado
        customer_id = session.get('customer_id')
        customer_store_id = session.get('customer_store_id')
        
        if not customer_id or customer_store_id != store.id:
            return jsonify({
                'success': False, 
                'error': 'Você precisa estar logado para favoritar produtos',
                'redirect': f'/{slug}/auth/login'
            }), 401
        
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'ID do produto é obrigatório'}), 400
        
        # Verifica se o produto existe e pertence à loja
        product = Product.query.filter_by(id=product_id, store_id=store.id, active=True).first()
        
        if not product:
            return jsonify({'success': False, 'error': 'Produto não encontrado'}), 404
        
        # Verifica se já é favorito
        existing_favorite = CustomerFavorite.query.filter_by(
            customer_id=customer_id,
            product_id=product_id
        ).first()
        
        if existing_favorite:
            # Remove dos favoritos
            db.session.delete(existing_favorite)
            db.session.commit()
            return jsonify({
                'success': True,
                'action': 'removed',
                'message': 'Produto removido dos favoritos'
            }), 200
        else:
            # Adiciona aos favoritos
            new_favorite = CustomerFavorite(
                customer_id=customer_id,
                product_id=product_id
            )
            db.session.add(new_favorite)
            db.session.commit()
            return jsonify({
                'success': True,
                'action': 'added',
                'message': 'Produto adicionado aos favoritos'
            }), 200
            
    except Exception as e:
        print(f"Erro ao favoritar produto: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar favorito'
        }), 500


@storefront.route('/<slug>/favorites/check', methods=['POST'])
def check_favorites(slug):
    """Verifica quais produtos são favoritos"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404
        
        customer_id = session.get('customer_id')
        customer_store_id = session.get('customer_store_id')
        
        if not customer_id or customer_store_id != store.id:
            return jsonify({
                'success': True,
                'favorites': [],
                'logged_in': False
            }), 200
        
        data = request.get_json()
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({
                'success': True,
                'favorites': [],
                'logged_in': True
            }), 200
        
        # Busca favoritos do cliente que estão na lista
        favorites = CustomerFavorite.query.filter(
            CustomerFavorite.customer_id == customer_id,
            CustomerFavorite.product_id.in_(product_ids)
        ).all()
        
        favorite_ids = [fav.product_id for fav in favorites]
        
        return jsonify({
            'success': True,
            'favorites': favorite_ids,
            'logged_in': True
        }), 200
        
    except Exception as e:
        print(f"Erro ao verificar favoritos: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao verificar favoritos'
        }), 500


@storefront.route('/<slug>/favorites/list')
def list_favorites(slug):
    """Lista todos os favoritos do cliente (API)"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404
        
        customer_id = session.get('customer_id')
        customer_store_id = session.get('customer_store_id')
        
        if not customer_id or customer_store_id != store.id:
            return jsonify({
                'success': False,
                'error': 'Você precisa estar logado',
                'redirect': f'/{slug}/auth/login'
            }), 401
        
        favorites = CustomerFavorite.query.filter_by(
            customer_id=customer_id
        ).order_by(CustomerFavorite.created_at.desc()).all()
        
        # Filtrar produtos ativos da loja
        favorites_data = []
        for fav in favorites:
            if fav.product and fav.product.active and fav.product.store_id == store.id:
                favorites_data.append(fav.to_dict())
        
        return jsonify({
            'success': True,
            'data': favorites_data,
            'count': len(favorites_data)
        }), 200
        
    except Exception as e:
        print(f"Erro ao listar favoritos: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar favoritos'
        }), 500
