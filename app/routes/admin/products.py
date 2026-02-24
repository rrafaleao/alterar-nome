"""
APIs para gerenciamento de produtos
"""
import os
import uuid
from flask import jsonify, request, session, current_app
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from . import admin
from .decorators import login_required, store_required
from config.database import db
from app.models.product import Product, ProductImage, ProductStock, ProductSizeStock
from app.models.category import Category

# Extensões permitidas para imagens
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin.route('/api/products', methods=['GET'])
@login_required
@store_required
def get_products():
    """
    API para listar produtos com filtros e paginação
    Query params:
    - page: número da página (padrão: 1)
    - per_page: itens por página (padrão: 10)
    - search: busca por título, descrição ou SKU
    - category_id: filtrar por categoria
    - active: filtrar por status (true/false)
    - sort: ordenação (recent, name_asc, name_desc, price_asc, price_desc)
    """
    try:
        store_id = session.get('store_id')
        
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Filtros
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', '')
        active = request.args.get('active', '')
        sort = request.args.get('sort', 'recent')
        
        # Query base
        query = Product.query.filter_by(store_id=store_id)
        
        # Aplicar busca
        if search:
            query = query.filter(
                or_(
                    Product.title.contains(search),
                    Product.description.contains(search),
                    Product.sku.contains(search)
                )
            )
        
        # Filtrar por categoria
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        # Filtrar por status
        if active:
            is_active = active.lower() == 'true'
            query = query.filter_by(active=is_active)
        
        # Ordenação
        if sort == 'name_asc':
            query = query.order_by(Product.title.asc())
        elif sort == 'name_desc':
            query = query.order_by(Product.title.desc())
        elif sort == 'price_asc':
            query = query.order_by(Product.price.asc())
        elif sort == 'price_desc':
            query = query.order_by(Product.price.desc())
        else:  # recent (padrão)
            query = query.order_by(Product.created_at.desc())
        
        # Paginação
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Buscar informações de estoque
        products_data = []
        for product in pagination.items:
            product_dict = product.to_dict()
            
            # Buscar estoque
            stock = ProductStock.query.filter_by(product_id=product.id).first()
            if stock:
                product_dict['stock'] = {
                    'quantity': stock.quantity,
                    'reserved_quantity': stock.reserved_quantity,
                    'available': stock.quantity - stock.reserved_quantity
                }
            else:
                product_dict['stock'] = {
                    'quantity': 0,
                    'reserved_quantity': 0,
                    'available': 0
                }
            
            # Buscar categoria
            if product.category_id:
                category = Category.query.get(product.category_id)
                product_dict['category_name'] = category.name if category else None
            else:
                product_dict['category_name'] = None
            
            products_data.append(product_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'products': products_data,
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar produtos'
        }), 500


@admin.route('/api/products/stats', methods=['GET'])
@login_required
@store_required
def get_products_stats():
    """API para obter estatísticas dos produtos"""
    try:
        store_id = session.get('store_id')
        
        # Total de produtos
        total_products = Product.query.filter_by(store_id=store_id).count()
        
        # Produtos ativos
        active_products = Product.query.filter_by(store_id=store_id, active=True).count()
        
        # Produtos sem estoque
        out_of_stock = db.session.query(Product).join(ProductStock).filter(
            Product.store_id == store_id,
            ProductStock.quantity == 0
        ).count()
        
        # Valor total do inventário
        products = Product.query.filter_by(store_id=store_id).all()
        total_inventory_value = 0
        
        for product in products:
            stock = ProductStock.query.filter_by(product_id=product.id).first()
            if stock:
                total_inventory_value += product.price * stock.quantity
        
        return jsonify({
            'success': True,
            'data': {
                'total_products': total_products,
                'active_products': active_products,
                'inactive_products': total_products - active_products,
                'out_of_stock': out_of_stock,
                'inventory_value': float(total_inventory_value)
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar estatísticas'
        }), 500


@admin.route('/api/products', methods=['POST'])
@login_required
@store_required
def create_product():
    """API para criar novo produto"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        # Validações
        if not data.get('title'):
            return jsonify({
                'success': False,
                'error': 'Título é obrigatório'
            }), 400
        
        if not data.get('price'):
            return jsonify({
                'success': False,
                'error': 'Preço é obrigatório'
            }), 400
        
        # Criar produto
        product = Product(
            store_id=store_id,
            title=data.get('title'),
            description=data.get('description', ''),
            sku=data.get('sku', ''),
            price=float(data.get('price')),
            category_id=data.get('category_id') if data.get('category_id') else None,
            active=data.get('active', True)
        )
        
        db.session.add(product)
        db.session.flush()  # Para obter o ID do produto
        
        # Criar registro de estoque
        initial_stock = int(data.get('initial_stock', 0))
        stock = ProductStock(
            product_id=product.id,
            quantity=initial_stock,
            reserved_quantity=0
        )
        
        db.session.add(stock)
        
        # Criar estoque por tamanho se fornecido
        size_stocks_data = data.get('size_stocks', [])
        if size_stocks_data:
            for size_data in size_stocks_data:
                if size_data.get('size') and size_data.get('quantity', 0) > 0:
                    size_stock = ProductSizeStock(
                        product_id=product.id,
                        size=size_data['size'],
                        quantity=int(size_data['quantity']),
                        reserved_quantity=0
                    )
                    db.session.add(size_stock)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Produto criado com sucesso',
            'data': product.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar produto: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao criar produto'
        }), 500


@admin.route('/api/products/<product_id>', methods=['GET'])
@login_required
@store_required
def get_product(product_id):
    """API para obter um produto específico"""
    try:
        store_id = session.get('store_id')
        
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        product_dict = product.to_dict()
        
        # Buscar estoque
        stock = ProductStock.query.filter_by(product_id=product.id).first()
        if stock:
            product_dict['stock'] = {
                'quantity': stock.quantity,
                'reserved_quantity': stock.reserved_quantity,
                'available': stock.quantity - stock.reserved_quantity
            }
        else:
            product_dict['stock'] = {
                'quantity': 0,
                'reserved_quantity': 0,
                'available': 0
            }
        
        # Buscar categoria
        if product.category_id:
            category = Category.query.get(product.category_id)
            product_dict['category_name'] = category.name if category else None
            product_dict['category_has_size'] = category.has_size if category else False
        else:
            product_dict['category_name'] = None
            product_dict['category_has_size'] = False
        
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


@admin.route('/api/products/<product_id>', methods=['PUT'])
@login_required
@store_required
def update_product(product_id):
    """API para atualizar produto"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        # Atualizar campos
        if 'title' in data:
            product.title = data['title']
        if 'description' in data:
            product.description = data['description']
        if 'sku' in data:
            product.sku = data['sku']
        if 'price' in data:
            product.price = float(data['price'])
        if 'category_id' in data:
            product.category_id = data['category_id'] if data['category_id'] else None
        if 'active' in data:
            product.active = data['active']
        
        # Atualizar estoque geral
        if 'stock_quantity' in data:
            stock = ProductStock.query.filter_by(product_id=product_id).first()
            if stock:
                stock.quantity = int(data['stock_quantity'])
            else:
                stock = ProductStock(
                    product_id=product_id,
                    quantity=int(data['stock_quantity']),
                    reserved_quantity=0
                )
                db.session.add(stock)
        
        # Atualizar estoque por tamanho
        if 'size_stocks' in data:
            # Remover estoques antigos
            ProductSizeStock.query.filter_by(product_id=product_id).delete()
            
            # Adicionar novos
            for size_data in data['size_stocks']:
                if size_data.get('size') and size_data.get('quantity', 0) >= 0:
                    size_stock = ProductSizeStock(
                        product_id=product_id,
                        size=size_data['size'],
                        quantity=int(size_data['quantity']),
                        reserved_quantity=0
                    )
                    db.session.add(size_stock)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Produto atualizado com sucesso',
            'data': product.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar produto: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar produto'
        }), 500


@admin.route('/api/products/<product_id>/toggle', methods=['PATCH'])
@login_required
@store_required
def toggle_product_status(product_id):
    """API para ativar/desativar produto"""
    try:
        store_id = session.get('store_id')
        
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        product.active = not product.active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso',
            'data': {
                'active': product.active
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar status: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar status'
        }), 500


@admin.route('/api/products/<product_id>', methods=['DELETE'])
@login_required
@store_required
def delete_product(product_id):
    """API para deletar produto"""
    try:
        store_id = session.get('store_id')
        
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Produto excluído com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir produto: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir produto'
        }), 500


@admin.route('/api/products/<product_id>/images', methods=['POST'])
@login_required
@store_required
def upload_product_images(product_id):
    """API para fazer upload de imagens do produto"""
    try:
        print(f"=== Upload de imagens para produto {product_id} ===")
        store_id = session.get('store_id')
        print(f"Store ID da sessão: {store_id}")
        
        # Verificar se o produto existe e pertence à loja
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        print(f"Produto encontrado: {product is not None}")
        
        # Debug: verificar produto sem filtro de store
        product_any = Product.query.filter_by(id=product_id).first()
        if product_any:
            print(f"Produto existe com store_id: {product_any.store_id}")
        
        if not product:
            print(f"Produto {product_id} não encontrado na loja {store_id}")
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        print(f"Request files: {request.files}")
        print(f"Request files keys: {list(request.files.keys())}")
        
        if 'images' not in request.files:
            print("Nenhuma imagem encontrada no request")
            return jsonify({
                'success': False,
                'error': 'Nenhuma imagem enviada'
            }), 400
        
        files = request.files.getlist('images')
        print(f"Arquivos recebidos: {len(files)}")
        uploaded_images = []
        
        # Diretório de upload
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Obter a última posição de imagem
        last_image = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.position.desc()).first()
        position = (last_image.position + 1) if last_image else 0
        
        for file in files:
            print(f"Processando arquivo: {file.filename if file else 'None'}")
            if file and file.filename and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(upload_folder, filename)
                
                print(f"Salvando arquivo em: {filepath}")
                
                # Salvar arquivo
                file.save(filepath)
                
                # Criar registro no banco
                image = ProductImage(
                    product_id=product_id,
                    url=f"/static/uploads/products/{filename}",
                    position=position
                )
                db.session.add(image)
                uploaded_images.append(image)
                print(f"Imagem adicionada ao banco: {image.url}")
                position += 1
            else:
                print(f"Arquivo rejeitado: {file.filename if file else 'None'}")
        
        print(f"Total de imagens processadas: {len(uploaded_images)}")
        db.session.commit()
        print("Commit realizado com sucesso")
        
        return jsonify({
            'success': True,
            'message': f'{len(uploaded_images)} imagem(ns) enviada(s) com sucesso',
            'data': [img.to_dict() for img in uploaded_images]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        print(f"Erro ao fazer upload de imagens: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao fazer upload de imagens: {str(e)}'
        }), 500


@admin.route('/api/products/<product_id>/images/<image_id>', methods=['DELETE'])
@login_required
@store_required
def delete_product_image(product_id, image_id):
    """API para deletar uma imagem do produto"""
    try:
        store_id = session.get('store_id')
        
        # Verificar se o produto existe e pertence à loja
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        # Buscar a imagem
        image = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
        if not image:
            return jsonify({
                'success': False,
                'error': 'Imagem não encontrada'
            }), 404
        
        # Deletar arquivo físico
        if image.url.startswith('/static/'):
            filepath = os.path.join(current_app.root_path, image.url[1:])
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Deletar registro do banco
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Imagem excluída com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir imagem: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir imagem'
        }), 500


@admin.route('/api/products/<product_id>/images', methods=['GET'])
@login_required
@store_required
def get_product_images(product_id):
    """API para listar imagens do produto"""
    try:
        store_id = session.get('store_id')
        
        # Verificar se o produto existe e pertence à loja
        product = Product.query.filter_by(id=product_id, store_id=store_id).first()
        if not product:
            return jsonify({
                'success': False,
                'error': 'Produto não encontrado'
            }), 404
        
        images = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.position).all()
        
        return jsonify({
            'success': True,
            'data': [img.to_dict() for img in images]
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar imagens: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar imagens'
        }), 500