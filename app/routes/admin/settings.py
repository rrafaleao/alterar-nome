from flask import render_template, jsonify, session
from . import admin
from .decorators import login_required, store_required
from app.models.store import Store


@admin.route('/settings')
@login_required
@store_required
def settings_page():
    """Página principal de configurações"""
    return render_template('admin/settings/index.html')


@admin.route('/settings/payments')
@login_required
@store_required
def payment_methods_page():
    """Página de configuração de meios de pagamento"""
    return render_template('admin/settings/payments.html')


@admin.route('/settings/shipping')
@login_required
@store_required
def shipping_methods_page():
    """Página de configuração de meios de envio"""
    return render_template('admin/settings/shipping.html')


@admin.route('/settings/business')
@login_required
@store_required
def business_data_page():
    """Página de dados do negócio"""
    return render_template('admin/settings/business.html')


@admin.route('/settings/users')
@login_required
@store_required
def users_permissions_page():
    """Página de usuários e permissões"""
    return render_template('admin/settings/users.html')


@admin.route('/settings/domains')
@login_required
@store_required
def domains_page():
    """Página de configuração de domínios"""
    return render_template('admin/settings/domains.html')


# ============================
# APIs de Configurações
# ============================

@admin.route('/settings/store', methods=['GET'])
@login_required
@store_required
def get_store_settings():
    """API para obter configurações da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        store_data = store.to_dict(include_details=True)
        
        return jsonify({
            'success': True,
            'data': store_data
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar configurações: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar configurações'
        }), 500


@admin.route('/my-store')
@login_required
@store_required
def my_store_info():
    """API para obter informações da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        # Contar meios de pagamento e envio ativos
        payment_count = len([pm for pm in store.payment_methods if pm.is_enabled])
        shipping_count = len([sm for sm in store.shipping_methods if sm.is_enabled])
        
        # Obter URL do logo se existir customização
        logo_url = None
        if store.customization and store.customization.logo:
            logo_url = store.customization.logo
        
        return jsonify({
            'success': True,
            'data': {
                'id': store.id,
                'name': store.name,
                'slug': store.slug,
                'description': store.description,
                'logo_url': logo_url,
                'is_published': store.is_published,
                'public_url': f'/{store.slug}',
                'payment_count': payment_count,
                'shipping_count': shipping_count
            }
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar informações da loja: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar loja'
        }), 500