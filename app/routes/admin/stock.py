"""
APIs para gerenciamento de estoque
"""
from flask import jsonify, request, session
from sqlalchemy import or_, func
from datetime import datetime
from . import admin
from .decorators import login_required, store_required
from config.database import db
from app.models.product import Product, ProductStock
from app.models.category import Category

# Limite para considerar estoque baixo
LOW_STOCK_THRESHOLD = 10


@admin.route('/api/stock', methods=['GET'])
@login_required
@store_required
def get_stock():
    """
    API para listar produtos com informações de estoque
    Query params:
    - page: número da página (padrão: 1)
    - per_page: itens por página (padrão: 10)
    - search: busca por título ou SKU
    - category_id: filtrar por categoria
    - status: filtrar por status (all, out_of_stock, low, ok)
    - sort: ordenação (recent, stock_asc, stock_desc, name_asc)
    """
    try:
        store_id = session.get('store_id')
        
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Filtros
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', '')
        status = request.args.get('status', 'all')
        sort = request.args.get('sort', 'recent')
        
        # Query base - join com ProductStock
        query = db.session.query(Product, ProductStock).outerjoin(
            ProductStock, Product.id == ProductStock.product_id
        ).filter(Product.store_id == store_id)
        
        # Aplicar busca
        if search:
            query = query.filter(
                or_(
                    Product.title.ilike(f'%{search}%'),
                    Product.sku.ilike(f'%{search}%')
                )
            )
        
        # Filtrar por categoria
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        # Filtrar por status de estoque
        if status == 'out_of_stock':
            query = query.filter(
                or_(
                    ProductStock.quantity == 0,
                    ProductStock.quantity.is_(None)
                )
            )
        elif status == 'low':
            query = query.filter(
                ProductStock.quantity > 0,
                ProductStock.quantity <= LOW_STOCK_THRESHOLD
            )
        elif status == 'ok':
            query = query.filter(ProductStock.quantity > LOW_STOCK_THRESHOLD)
        
        # Ordenação
        if sort == 'stock_asc':
            query = query.order_by(func.coalesce(ProductStock.quantity, 0).asc())
        elif sort == 'stock_desc':
            query = query.order_by(func.coalesce(ProductStock.quantity, 0).desc())
        elif sort == 'name_asc':
            query = query.order_by(Product.title.asc())
        else:  # recent (padrão)
            query = query.order_by(Product.created_at.desc())
        
        # Contar total antes de paginar
        total = query.count()
        
        # Paginação manual
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()
        
        # Processar resultados
        products_data = []
        for product, stock in results:
            quantity = stock.quantity if stock else 0
            reserved = stock.reserved_quantity if stock else 0
            available = quantity - reserved
            
            # Determinar status
            if quantity == 0:
                stock_status = 'out_of_stock'
                status_label = 'Sem Estoque'
            elif quantity <= LOW_STOCK_THRESHOLD:
                stock_status = 'low'
                status_label = 'Baixo'
            else:
                stock_status = 'ok'
                status_label = 'OK'
            
            # Calcular porcentagem para barra de progresso (max 50 unidades = 100%)
            max_stock = 50
            progress = min(100, (quantity / max_stock) * 100) if max_stock > 0 else 0
            
            # Formatar data
            last_updated = None
            if stock and stock.last_updated:
                last_updated = stock.last_updated.strftime('%d/%m/%Y %H:%M')
            elif product.created_at:
                last_updated = product.created_at.strftime('%d/%m/%Y %H:%M')
            
            products_data.append({
                'id': product.id,
                'title': product.title,
                'sku': product.sku or '-',
                'price': float(product.price) if product.price else 0,
                'category_id': product.category_id,
                'quantity': quantity,
                'reserved_quantity': reserved,
                'available': available,
                'status': stock_status,
                'status_label': status_label,
                'progress': progress,
                'last_updated': last_updated
            })
        
        # Calcular paginação
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'products': products_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_prev': page > 1,
                    'has_next': page < pages
                }
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar estoque: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar estoque'
        }), 500


@admin.route('/api/stock/stats', methods=['GET'])
@login_required
@store_required
def get_stock_stats():
    """API para obter estatísticas de estoque"""
    try:
        store_id = session.get('store_id')
        
        # Total de produtos
        total_products = Product.query.filter_by(store_id=store_id).count()
        
        # Buscar todos os produtos com estoque
        products_with_stock = db.session.query(Product, ProductStock).outerjoin(
            ProductStock, Product.id == ProductStock.product_id
        ).filter(Product.store_id == store_id).all()
        
        total_stock = 0
        out_of_stock = 0
        low_stock = 0
        ok_stock = 0
        inventory_value = 0
        
        for product, stock in products_with_stock:
            quantity = stock.quantity if stock else 0
            total_stock += quantity
            
            # Calcular valor do inventário
            price = float(product.price) if product.price else 0
            inventory_value += price * quantity
            
            # Contar por status
            if quantity == 0:
                out_of_stock += 1
            elif quantity <= LOW_STOCK_THRESHOLD:
                low_stock += 1
            else:
                ok_stock += 1
        
        return jsonify({
            'success': True,
            'data': {
                'total_products': total_products,
                'total_stock': total_stock,
                'out_of_stock': out_of_stock,
                'low_stock': low_stock,
                'ok_stock': ok_stock,
                'inventory_value': inventory_value
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas de estoque: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar estatísticas'
        }), 500


@admin.route('/api/stock/<int:product_id>', methods=['PUT'])
@login_required
@store_required
def update_stock(product_id):
    """API para atualizar estoque de um produto"""
    try:
        store_id = session.get('store_id')
        
        # Verificar se o produto pertence à loja
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        data = request.get_json()
        
        # Buscar ou criar registro de estoque
        stock = ProductStock.query.filter_by(product_id=product_id).first()
        
        if not stock:
            stock = ProductStock(
                product_id=product_id,
                quantity=0,
                reserved_quantity=0
            )
            db.session.add(stock)
        
        # Atualizar campos
        if 'quantity' in data:
            new_quantity = int(data['quantity'])
            if new_quantity < 0:
                return jsonify({
                    'success': False,
                    'error': 'Quantidade não pode ser negativa'
                }), 400
            stock.quantity = new_quantity
        
        if 'reserved_quantity' in data:
            new_reserved = int(data['reserved_quantity'])
            if new_reserved < 0:
                return jsonify({
                    'success': False,
                    'error': 'Quantidade reservada não pode ser negativa'
                }), 400
            if new_reserved > stock.quantity:
                return jsonify({
                    'success': False,
                    'error': 'Quantidade reservada não pode ser maior que o estoque'
                }), 400
            stock.reserved_quantity = new_reserved
        
        # Atualizar timestamp
        stock.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estoque atualizado com sucesso',
            'data': {
                'product_id': product_id,
                'quantity': stock.quantity,
                'reserved_quantity': stock.reserved_quantity,
                'available': stock.quantity - stock.reserved_quantity,
                'last_updated': stock.last_updated.strftime('%d/%m/%Y %H:%M')
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar estoque: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar estoque'
        }), 500


@admin.route('/api/stock/bulk', methods=['PUT'])
@login_required
@store_required
def bulk_update_stock():
    """API para atualizar estoque de múltiplos produtos"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        if not data or 'updates' not in data:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos'
            }), 400
        
        updates = data.get('updates', [])
        updated = []
        errors = []
        
        for item in updates:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            
            if not product_id or quantity is None:
                errors.append({'product_id': product_id, 'error': 'Dados incompletos'})
                continue
            
            # Verificar se o produto pertence à loja
            product = Product.query.filter_by(id=product_id, store_id=store_id).first()
            if not product:
                errors.append({'product_id': product_id, 'error': 'Produto não encontrado'})
                continue
            
            # Buscar ou criar registro de estoque
            stock = ProductStock.query.filter_by(product_id=product_id).first()
            
            if not stock:
                stock = ProductStock(
                    product_id=product_id,
                    quantity=0,
                    reserved_quantity=0
                )
                db.session.add(stock)
            
            stock.quantity = int(quantity)
            stock.last_updated = datetime.utcnow()
            updated.append(product_id)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(updated)} produtos atualizados',
            'data': {
                'updated': updated,
                'errors': errors
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar estoque em lote: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar estoque'
        }), 500
