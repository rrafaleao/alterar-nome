from flask import render_template, abort, request, jsonify
from config.database import db
from . import storefront
from app.models.store import Store, StoreCustomization
from app.models.product import Product
from app.models.category import Category

@storefront.route('/purchase')
def purchase():
    store = Store.query.filter_by(onboarding_completed=True).first()
        
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
        
        return render_template('/stores/purchase.html', 
            store=store,
            products=products,
            categories=categories,
            customization=customization
        )
