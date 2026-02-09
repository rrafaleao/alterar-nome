"""
APIs para gerenciamento de categorias
"""
from flask import jsonify, request, session
from . import admin
from .decorators import login_required, store_required
from config.database import db
from app.models.category import Category
import re


def generate_slug(name):
    """Gera um slug a partir do nome"""
    slug = name.lower().strip()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug


@admin.route('/api/categories', methods=['GET'])
@login_required
@store_required
def get_categories():
    """
    API para listar categorias
    Query params:
    - search: busca por nome
    - parent_id: filtrar por categoria pai (use 'root' para categorias raiz)
    """
    try:
        store_id = session.get('store_id')
        
        # Parâmetros de filtro
        search = request.args.get('search', '')
        parent_id = request.args.get('parent_id', '')
        
        # Query base
        query = Category.query.filter_by(store_id=store_id)
        
        # Aplicar busca
        if search:
            query = query.filter(Category.name.ilike(f'%{search}%'))
        
        # Filtrar por categoria pai
        if parent_id == 'root':
            query = query.filter(Category.parent_id.is_(None))
        elif parent_id:
            query = query.filter_by(parent_id=parent_id)
        
        # Ordenar por nome
        query = query.order_by(Category.name.asc())
        
        categories = query.all()
        
        # Preparar dados com contagem de produtos
        categories_data = []
        for category in categories:
            cat_dict = category.to_dict()
            cat_dict['products_count'] = len(category.products) if category.products else 0
            cat_dict['children_count'] = len(category.children) if category.children else 0
            categories_data.append(cat_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'categories': categories_data,
                'total': len(categories_data)
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar categorias'
        }), 500


@admin.route('/api/categories/<category_id>', methods=['GET'])
@login_required
@store_required
def get_category(category_id):
    """API para obter uma categoria específica"""
    try:
        store_id = session.get('store_id')
        
        category = Category.query.filter_by(id=category_id, store_id=store_id).first()
        
        if not category:
            return jsonify({
                'success': False,
                'error': 'Categoria não encontrada'
            }), 404
        
        cat_dict = category.to_dict()
        cat_dict['products_count'] = len(category.products) if category.products else 0
        cat_dict['children_count'] = len(category.children) if category.children else 0
        
        return jsonify({
            'success': True,
            'data': cat_dict
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar categoria: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar categoria'
        }), 500


@admin.route('/api/categories', methods=['POST'])
@login_required
@store_required
def create_category():
    """API para criar nova categoria"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        # Validações
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Nome é obrigatório'
            }), 400
        
        # Gerar slug
        slug = data.get('slug') or generate_slug(data.get('name'))
        
        # Verificar se slug já existe para esta loja
        existing = Category.query.filter_by(store_id=store_id, slug=slug).first()
        if existing:
            # Adicionar sufixo numérico
            counter = 1
            base_slug = slug
            while Category.query.filter_by(store_id=store_id, slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Validar parent_id se fornecido
        parent_id = data.get('parent_id')
        if parent_id:
            parent = Category.query.filter_by(id=parent_id, store_id=store_id).first()
            if not parent:
                return jsonify({
                    'success': False,
                    'error': 'Categoria pai não encontrada'
                }), 400
        
        # Criar categoria
        category = Category(
            store_id=store_id,
            name=data.get('name'),
            slug=slug,
            parent_id=parent_id if parent_id else None
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Categoria criada com sucesso',
            'data': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar categoria: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao criar categoria'
        }), 500


@admin.route('/api/categories/<category_id>', methods=['PUT'])
@login_required
@store_required
def update_category(category_id):
    """API para atualizar categoria"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        category = Category.query.filter_by(id=category_id, store_id=store_id).first()
        
        if not category:
            return jsonify({
                'success': False,
                'error': 'Categoria não encontrada'
            }), 404
        
        # Atualizar nome
        if 'name' in data:
            category.name = data['name']
            # Atualizar slug também se nome mudar
            if not data.get('slug'):
                new_slug = generate_slug(data['name'])
                # Verificar se não conflita com outra categoria
                existing = Category.query.filter(
                    Category.store_id == store_id,
                    Category.slug == new_slug,
                    Category.id != category_id
                ).first()
                if not existing:
                    category.slug = new_slug
        
        # Atualizar slug manualmente
        if 'slug' in data:
            new_slug = generate_slug(data['slug'])
            existing = Category.query.filter(
                Category.store_id == store_id,
                Category.slug == new_slug,
                Category.id != category_id
            ).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Já existe uma categoria com este slug'
                }), 400
            category.slug = new_slug
        
        # Atualizar parent_id
        if 'parent_id' in data:
            parent_id = data['parent_id']
            
            # Não pode ser pai de si mesmo
            if parent_id == category_id:
                return jsonify({
                    'success': False,
                    'error': 'Categoria não pode ser pai de si mesma'
                }), 400
            
            # Verificar se não está criando ciclo
            if parent_id:
                parent = Category.query.filter_by(id=parent_id, store_id=store_id).first()
                if not parent:
                    return jsonify({
                        'success': False,
                        'error': 'Categoria pai não encontrada'
                    }), 400
                
                # Verificar ciclo
                current = parent
                while current.parent_id:
                    if current.parent_id == category_id:
                        return jsonify({
                            'success': False,
                            'error': 'Não é possível criar referência circular'
                        }), 400
                    current = Category.query.get(current.parent_id)
            
            category.parent_id = parent_id if parent_id else None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Categoria atualizada com sucesso',
            'data': category.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar categoria: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar categoria'
        }), 500


@admin.route('/api/categories/<category_id>', methods=['DELETE'])
@login_required
@store_required
def delete_category(category_id):
    """API para deletar categoria"""
    try:
        store_id = session.get('store_id')
        
        category = Category.query.filter_by(id=category_id, store_id=store_id).first()
        
        if not category:
            return jsonify({
                'success': False,
                'error': 'Categoria não encontrada'
            }), 404
        
        # Verificar se tem produtos associados
        if category.products and len(category.products) > 0:
            return jsonify({
                'success': False,
                'error': f'Não é possível excluir. Esta categoria possui {len(category.products)} produto(s) associado(s).'
            }), 400
        
        # Atualizar subcategorias para não ter pai
        for child in category.children:
            child.parent_id = None
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Categoria excluída com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao deletar categoria: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir categoria'
        }), 500


@admin.route('/api/categories/stats', methods=['GET'])
@login_required
@store_required
def get_categories_stats():
    """API para obter estatísticas das categorias"""
    try:
        store_id = session.get('store_id')
        
        # Total de categorias
        total_categories = Category.query.filter_by(store_id=store_id).count()
        
        # Categorias raiz (sem pai)
        root_categories = Category.query.filter_by(store_id=store_id, parent_id=None).count()
        
        # Subcategorias
        sub_categories = total_categories - root_categories
        
        # Categorias vazias (sem produtos)
        categories = Category.query.filter_by(store_id=store_id).all()
        empty_categories = sum(1 for cat in categories if not cat.products or len(cat.products) == 0)
        
        return jsonify({
            'success': True,
            'data': {
                'total_categories': total_categories,
                'root_categories': root_categories,
                'sub_categories': sub_categories,
                'empty_categories': empty_categories
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar estatísticas'
        }), 500
