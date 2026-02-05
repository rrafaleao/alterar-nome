from flask import render_template, jsonify, session
from . import admin
from .decorators import login_required, store_required
from app.models.store import Store
from app.models.product import Product
from app.models.category import Category


@admin.route('/dashboard')
@login_required
@store_required
def dashboard():
    """Página principal do dashboard"""
    return render_template('admin/dashboard.html')


@admin.route('/dashboard/stats', methods=['GET'])
@login_required
@store_required
def dashboard_stats():
    """API para obter estatísticas do dashboard"""
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