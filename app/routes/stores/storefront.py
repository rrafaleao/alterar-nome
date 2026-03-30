from flask import render_template, abort, request, jsonify
from datetime import datetime
from sqlalchemy import and_
from config.database import db
from app.models.store import Store, StoreCustomization
from app.models.product import Product
from app.models.category import Category
from app.models.customer_favorite import CustomerFavorite
from app.models.order import Order, OrderItem
from app.models.product_review import ProductReview
from app.models.promotion import Promotion, PromotionProduct, PromotionCategory
from app.models.store_admin import StoreAdmin
from . import storefront
from .customer_auth import sync_customer_session_for_store


def render_store_not_found(slug):
    """Renderiza uma tela amigavel quando a loja nao existe."""
    return render_template('stores/store_not_found.html', requested_slug=slug), 404


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


def get_product_reviews_data(store_id, product_id):
    reviews = ProductReview.query.filter(
        ProductReview.store_id == store_id,
        ProductReview.product_id == product_id,
        ProductReview.status == 'reviewed',
        ProductReview.rating.isnot(None)
    ).order_by(ProductReview.created_at.desc()).all()

    avg_rating = 0.0
    if reviews:
        avg_rating = float(sum((review.rating or 0) for review in reviews)) / len(reviews)

    return reviews, avg_rating, len(reviews)


def get_review_eligibility(store_id, product_id, customer_id):
    if not customer_id:
        return None

    pending_order = db.session.query(Order).join(
        OrderItem,
        OrderItem.order_id == Order.id
    ).outerjoin(
        ProductReview,
        and_(
            ProductReview.order_id == Order.id,
            ProductReview.customer_id == Order.user_id,
            ProductReview.product_id == OrderItem.product_id,
        )
    ).filter(
        Order.store_id == store_id,
        Order.user_id == customer_id,
        Order.status == 'delivered',
        OrderItem.product_id == product_id,
        ProductReview.id.is_(None)
    ).order_by(
        Order.updated_at.desc(),
        Order.placed_at.desc()
    ).first()

    if not pending_order:
        return None

    return {
        'eligible': True,
        'order_id': pending_order.id,
        'placed_at': pending_order.placed_at,
    }


@storefront.route('/<slug>')
def view_store(slug):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            return render_store_not_found(slug)

        current_customer = sync_customer_session_for_store(store)
        
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
        if current_customer and current_customer.is_active:
            is_admin = StoreAdmin.is_admin(store.id, current_customer.id)
        
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
            return render_store_not_found(slug)

        current_customer = sync_customer_session_for_store(store)
        
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
        
        reviews, avg_rating, review_count = get_product_reviews_data(store.id, product.id)

        review_eligibility = None
        if current_customer and current_customer.is_active:
            review_eligibility = get_review_eligibility(store.id, product.id, current_customer.id)

        # Verificar se o cliente logado é admin da loja
        is_admin = False
        if current_customer and current_customer.is_active:
            is_admin = StoreAdmin.is_admin(store.id, current_customer.id)
        
        return render_template(
            'stores/product_detail.html',
            store=store,
            product=product,
            promo=promo_info,
            reviews=reviews,
            avg_rating=avg_rating,
            review_count=review_count,
            review_eligibility=review_eligibility,
            customization=customization,
            is_admin=is_admin
        )
        
    except Exception as e:
        print(f"Erro ao carregar página do produto: {e}")
        abort(500)


@storefront.route('/<slug>/produto/<product_id>/avaliar', methods=['POST'])
def submit_product_review(slug, product_id):
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        product = Product.query.filter_by(id=product_id, store_id=store.id, active=True).first()
        if not product:
            return jsonify({'success': False, 'error': 'Produto não encontrado'}), 404

        customer = sync_customer_session_for_store(store)
        if not customer or not customer.is_active:
            return jsonify({
                'success': False,
                'error': 'Você precisa estar logado para avaliar',
                'redirect': f'/{slug}/auth/login'
            }), 401

        data = request.get_json(silent=True) or {}
        order_id = (data.get('order_id') or '').strip()
        raw_comment = data.get('comment')
        comment = raw_comment.strip() if isinstance(raw_comment, str) else ''
        report_not_received = bool(data.get('not_received'))

        if not order_id:
            return jsonify({'success': False, 'error': 'Pedido inválido para avaliação'}), 400

        order = Order.query.filter_by(
            id=order_id,
            store_id=store.id,
            user_id=customer.id,
            status='delivered'
        ).first()

        if not order:
            return jsonify({'success': False, 'error': 'Este pedido não pode ser avaliado'}), 400

        has_product = OrderItem.query.filter_by(order_id=order.id, product_id=product.id).first()
        if not has_product:
            return jsonify({'success': False, 'error': 'Produto não encontrado neste pedido'}), 400

        existing_review = ProductReview.query.filter_by(
            order_id=order.id,
            customer_id=customer.id,
            product_id=product.id
        ).first()
        if existing_review:
            return jsonify({'success': False, 'error': 'Este item já foi avaliado'}), 400

        if report_not_received:
            if len(comment) < 5:
                return jsonify({
                    'success': False,
                    'error': 'Descreva rapidamente o problema para registrar que não recebeu o produto'
                }), 400
            review = ProductReview(
                store_id=store.id,
                order_id=order.id,
                customer_id=customer.id,
                product_id=product.id,
                status='not_received',
                rating=None,
                comment=comment,
            )
            db.session.add(review)
            db.session.commit()

            return jsonify({
                'success': True,
                'status': 'not_received',
                'message': 'Registro de não recebimento enviado com sucesso'
            }), 200

        raw_rating = data.get('rating')
        try:
            rating = int(raw_rating)
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Informe uma nota de 1 a 5 estrelas'}), 400

        review = ProductReview(
            store_id=store.id,
            order_id=order.id,
            customer_id=customer.id,
            product_id=product.id,
            status='reviewed',
            rating=rating,
            comment=comment[:1500] if comment else None,
        )
        db.session.add(review)
        db.session.commit()

        reviews, avg_rating, review_count = get_product_reviews_data(store.id, product.id)

        return jsonify({
            'success': True,
            'status': 'reviewed',
            'message': 'Avaliação enviada com sucesso',
            'review': {
                'rating': rating,
                'comment': review.comment,
                'customer_name': customer.full_name or 'Cliente',
                'created_at': review.created_at.strftime('%d/%m/%Y') if review.created_at else None,
            },
            'stats': {
                'avg_rating': round(avg_rating, 1),
                'review_count': review_count,
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao enviar avaliação: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao enviar avaliação'
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


@storefront.route('/<slug>/categoria/<category_id>')
def store_category_page(slug, category_id):
    """Página de categoria mostrando produtos filtrados"""
    try:
        store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
        
        if not store:
            abort(404)

        current_customer = sync_customer_session_for_store(store)
        
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
        if current_customer and current_customer.is_active:
            is_admin = StoreAdmin.is_admin(store.id, current_customer.id)
        
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

    customer = sync_customer_session_for_store(store)
    
    # Se não estiver logado, redireciona para login
    if not customer or not customer.is_active:
        from flask import redirect, url_for
        return redirect(url_for('storefront.customer_login_page', slug=slug))
    
    # Buscar favoritos do cliente
    favorites = CustomerFavorite.query.filter_by(
        customer_id=customer.id
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
    if customer.is_active:
        is_admin = StoreAdmin.is_admin(store.id, customer.id)
    
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
        
        # Verifica se está logado e sincroniza com a loja atual
        customer = sync_customer_session_for_store(store)
        
        if not customer or not customer.is_active:
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
            customer_id=customer.id,
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
                customer_id=customer.id,
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

        customer = sync_customer_session_for_store(store)

        if not customer or not customer.is_active:
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
            CustomerFavorite.customer_id == customer.id,
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

        customer = sync_customer_session_for_store(store)

        if not customer or not customer.is_active:
            return jsonify({
                'success': False,
                'error': 'Você precisa estar logado',
                'redirect': f'/{slug}/auth/login'
            }), 401
        
        favorites = CustomerFavorite.query.filter_by(
            customer_id=customer.id
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
