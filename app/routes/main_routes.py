from flask import Blueprint, render_template, jsonify, request
from config.database import db
from app.models.product import Product
from app.models.store import Store

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


@main.get("/api/zappshop/products")
def zappshop_products():
    """API para listar produtos disponíveis na ZappShop"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        
        # Buscar produtos ativos que estão marcados para aparecer na ZappShop
        # e que pertencem a lojas com onboarding completo
        query = db.session.query(Product).join(Store).filter(
            Product.active == True,
            Product.show_in_zappshop == True,
            Store.onboarding_completed == True
        )
        
        if search:
            query = query.filter(
                (Product.title.ilike(f'%{search}%')) | 
                (Product.description.ilike(f'%{search}%'))
            )
        
        query = query.order_by(Product.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        products_data = []
        for product in pagination.items:
            store = Store.query.get(product.store_id)
            product_dict = product.to_dict()
            product_dict['store_name'] = store.name if store else 'Loja'
            product_dict['store_slug'] = store.slug if store else ''
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