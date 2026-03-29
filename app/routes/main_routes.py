from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from config.database import db
from app.models.product import Product
from app.models.store import Store
from app.models.category import Category
from app.models.promotion import Promotion, PromotionProduct, PromotionCategory
from datetime import datetime
from sqlalchemy import func

main = Blueprint("main", __name__, url_prefix="/")

@main.get("/")
def index():
    # Buscar 3 lojas parceiras (com onboarding completo e publicadas)
    partner_stores = Store.query.filter(
        Store.onboarding_completed == True,
        Store.is_published == True
    ).order_by(Store.created_at.desc()).limit(3).all()
    
    return render_template('main.html', partner_stores=partner_stores)


@main.get("/zappshop")
def zappshop():
    """Página do marketplace ZappShop com produtos de todas as lojas"""
    return render_template('/zapp_shop/zappshop.html')


@main.get("/zappshop/auth/login")
def zappshop_customer_login_redirect():
    """Redireciona o login da ZappShop para o mesmo login de cliente usado nas lojas."""
    store = Store.query.filter(
        Store.onboarding_completed == True,
        Store.is_published == True
    ).order_by(Store.created_at.desc()).first()

    if not store:
        return redirect(url_for('main.zappshop'))

    return redirect(
        url_for(
            'storefront.customer_login_page',
            slug=store.slug,
            next=url_for('main.zappshop')
        )
    )


@main.get("/api/zappshop/products")
def zappshop_products():
    """API para listar produtos disponíveis na ZappShop (site e app mobile)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        category = request.args.get('category', '', type=str)
        store_id = request.args.get('store_id', '', type=str)
        min_price = request.args.get('min_price', None, type=float)
        max_price = request.args.get('max_price', None, type=float)
        sort_by = request.args.get('sort_by', 'recent', type=str)  # recent, price_asc, price_desc, name
        
        # Buscar produtos ativos que estão marcados para aparecer na ZappShop
        query = db.session.query(Product).join(Store).filter(
            Product.active == True,
            Product.show_in_zappshop == True,
            Store.onboarding_completed == True
        )
        
        # Filtro por busca
        if search:
            query = query.filter(
                (Product.title.ilike(f'%{search}%')) | 
                (Product.description.ilike(f'%{search}%'))
            )
        
        # Filtro por categoria (nome da categoria - consolidado de todas as lojas)
        if category:
            query = query.join(Category, Product.category_id == Category.id).filter(
                Category.name.ilike(f'%{category}%')
            )
        
        # Filtro por loja específica
        if store_id:
            query = query.filter(Product.store_id == store_id)
        
        # Filtro por preço
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        
        # Ordenação
        if sort_by == 'price_asc':
            query = query.order_by(Product.price.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Product.price.desc())
        elif sort_by == 'name':
            query = query.order_by(Product.title.asc())
        else:  # recent
            query = query.order_by(Product.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        products_data = []
        for product in pagination.items:
            store = Store.query.get(product.store_id)
            product_dict = product.to_dict()
            product_dict['store_name'] = store.name if store else 'Loja'
            product_dict['store_slug'] = store.slug if store else ''
            product_dict['store_logo'] = store.logo_url if store else None
            
            # Adicionar info de promoção se existir
            promo_info = _get_product_promotion(product)
            if promo_info:
                product_dict['promotion'] = promo_info
            
            # Adicionar nome da categoria
            if product.category:
                product_dict['category_name'] = product.category.name
            
            products_data.append(product_dict)
        
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
        print(f"Erro ao buscar produtos da ZappShop: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar produtos'
        }), 500


def _get_product_promotion(product):
    """Helper para buscar promoção ativa de um produto"""
    now = datetime.utcnow()
    
    # Buscar promoções ativas da loja do produto
    promotions = Promotion.query.filter(
        Promotion.store_id == product.store_id,
        Promotion.is_active == True,
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).all()
    
    for promo in promotions:
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
                'name': promo.name,
                'original_price': original_price,
                'promo_price': round(promo_price, 2),
                'discount_percent': round(discount_percent),
                'discount_type': promo.discount_type,
                'discount_value': float(promo.discount_value),
                'end_date': promo.end_date.isoformat() if promo.end_date else None
            }
    
    return None


@main.get("/api/zappshop/product/<product_id>")
def zappshop_product_detail(product_id):
    """API para detalhes de um produto específico"""
    try:
        product = db.session.query(Product).join(Store).filter(
            Product.id == product_id,
            Product.active == True,
            Product.show_in_zappshop == True,
            Store.onboarding_completed == True
        ).first()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        store = Store.query.get(product.store_id)
        product_dict = product.to_dict()
        product_dict['store_name'] = store.name if store else 'Loja'
        product_dict['store_slug'] = store.slug if store else ''
        product_dict['store_logo'] = store.logo_url if store else None
        product_dict['store_description'] = store.description if store else None
        
        # Info de promoção
        promo_info = _get_product_promotion(product)
        if promo_info:
            product_dict['promotion'] = promo_info
        
        # Nome da categoria
        if product.category:
            product_dict['category_name'] = product.category.name
        
        return jsonify({
            'success': True,
            'data': product_dict
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar produto: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar produto'
        }), 500


@main.get("/api/zappshop/stores")
def zappshop_stores():
    """API para listar lojas disponíveis na ZappShop"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        
        query = Store.query.filter(
            Store.onboarding_completed == True,
            Store.is_published == True
        )
        
        if search:
            query = query.filter(
                (Store.name.ilike(f'%{search}%')) |
                (Store.description.ilike(f'%{search}%'))
            )
        
        query = query.order_by(Store.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        stores_data = []
        for store in pagination.items:
            # Contar produtos ativos na ZappShop
            product_count = Product.query.filter(
                Product.store_id == store.id,
                Product.active == True,
                Product.show_in_zappshop == True
            ).count()
            
            store_dict = {
                'id': store.id,
                'name': store.name,
                'slug': store.slug,
                'description': store.description,
                'logo_url': store.logo_url,
                'product_count': product_count,
                'created_at': store.created_at.isoformat() if store.created_at else None
            }
            
            # Adicionar cores de customização se existir
            if store.customization:
                store_dict['primary_color'] = store.customization.primary_color
                store_dict['secondary_color'] = store.customization.secondary_color
            
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
        print(f"Erro ao buscar lojas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar lojas'
        }), 500


@main.get("/api/zappshop/store/<slug>")
def zappshop_store_detail(slug):
    """API para detalhes de uma loja específica"""
    try:
        store = Store.query.filter_by(
            slug=slug,
            onboarding_completed=True,
            is_published=True
        ).first()
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        # Contar produtos
        product_count = Product.query.filter(
            Product.store_id == store.id,
            Product.active == True,
            Product.show_in_zappshop == True
        ).count()
        
        # Buscar categorias da loja
        categories = Category.query.filter_by(store_id=store.id).all()
        
        store_dict = {
            'id': store.id,
            'name': store.name,
            'slug': store.slug,
            'description': store.description,
            'logo_url': store.logo_url,
            'product_count': product_count,
            'categories': [cat.to_dict() for cat in categories],
            'created_at': store.created_at.isoformat() if store.created_at else None
        }
        
        if store.customization:
            store_dict['primary_color'] = store.customization.primary_color
            store_dict['secondary_color'] = store.customization.secondary_color
        
        return jsonify({
            'success': True,
            'data': store_dict
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar loja: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar loja'
        }), 500


@main.get("/api/zappshop/categories")
def zappshop_categories():
    """API para listar categorias disponíveis (consolidadas de todas as lojas)"""
    try:
        # Buscar categorias únicas por nome das lojas ativas
        categories = db.session.query(
            Category.name,
            func.count(Product.id).label('product_count')
        ).join(Store, Category.store_id == Store.id).outerjoin(
            Product, 
            (Product.category_id == Category.id) & 
            (Product.active == True) & 
            (Product.show_in_zappshop == True)
        ).filter(
            Store.onboarding_completed == True,
            Store.is_published == True
        ).group_by(Category.name).having(
            func.count(Product.id) > 0
        ).order_by(Category.name).all()
        
        categories_data = [
            {
                'name': cat.name,
                'product_count': cat.product_count
            }
            for cat in categories
        ]
        
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


@main.get("/api/zappshop/featured")
def zappshop_featured():
    """API para produtos em destaque (com promoção ativa)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        now = datetime.utcnow()
        
        # Buscar produtos com promoção ativa
        products_with_promo = []
        
        # Primeiro, buscar promoções ativas
        active_promotions = Promotion.query.filter(
            Promotion.is_active == True,
            Promotion.start_date <= now,
            Promotion.end_date >= now
        ).all()
        
        seen_products = set()
        
        for promo in active_promotions:
            store = Store.query.get(promo.store_id)
            if not store or not store.onboarding_completed:
                continue
            
            # Buscar produtos que se aplicam a esta promoção
            if promo.applies_to == 'all':
                products = Product.query.filter(
                    Product.store_id == promo.store_id,
                    Product.active == True,
                    Product.show_in_zappshop == True
                ).limit(5).all()
            elif promo.applies_to == 'products':
                product_ids = [pp.product_id for pp in promo.products]
                products = Product.query.filter(
                    Product.id.in_(product_ids),
                    Product.active == True,
                    Product.show_in_zappshop == True
                ).all()
            elif promo.applies_to == 'categories':
                category_ids = [pc.category_id for pc in promo.categories]
                products = Product.query.filter(
                    Product.category_id.in_(category_ids),
                    Product.active == True,
                    Product.show_in_zappshop == True
                ).all()
            else:
                products = []
            
            for product in products:
                if product.id in seen_products:
                    continue
                seen_products.add(product.id)
                
                product_dict = product.to_dict()
                product_dict['store_name'] = store.name
                product_dict['store_slug'] = store.slug
                product_dict['store_logo'] = store.logo_url
                
                original_price = float(product.price)
                promo_price = promo.calculate_discount(original_price)
                discount_percent = ((original_price - promo_price) / original_price) * 100
                
                product_dict['promotion'] = {
                    'name': promo.name,
                    'original_price': original_price,
                    'promo_price': round(promo_price, 2),
                    'discount_percent': round(discount_percent),
                    'end_date': promo.end_date.isoformat() if promo.end_date else None
                }
                
                if product.category:
                    product_dict['category_name'] = product.category.name
                
                products_with_promo.append(product_dict)
                
                if len(products_with_promo) >= limit:
                    break
            
            if len(products_with_promo) >= limit:
                break
        
        return jsonify({
            'success': True,
            'data': products_with_promo[:limit]
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar produtos em destaque: {e}")


@main.get("/about")
def about():
    """Página Sobre a Zapp"""
    return render_template('about.html')


@main.get("/contact")
def contact():
    """Página de Contato"""
    return render_template('contact.html')


@main.get("/help")
def help():
    """Central de Ajuda"""
    return render_template('help.html')


@main.get("/api-docs")
def api_docs():
    """Documentação da API"""
    return render_template('api_docs.html')


@main.get("/test-db")
def test_db():
    """Rota para testar a conexão com o banco de dados"""
    try:
        # Tenta executar uma query simples
        result = db.session.execute(db.text("SELECT 1"))
        db.session.close()
        return jsonify({
            "status": "success",
            "message": "Conexão com o banco de dados estabelecida com sucesso!",
            "database": "Banco de dados funcionando corretamente"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Erro ao conectar ao banco de dados",
            "error": str(e)
        }), 500