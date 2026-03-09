from flask import render_template, jsonify, session, request
from . import admin
from .decorators import login_required, store_required
from app.models.store import Store, StoreCustomization
from app.models.store_payment_method import StorePaymentMethod
from app.models.store_shipping_methods import StoreShippingMethod
from app.models.user import User
from app.models.store_customer import StoreCustomer
from app.models.store_admin import StoreAdmin
from config.database import db
import uuid
import os
from werkzeug.utils import secure_filename


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


@admin.route('/settings/toggle-publish', methods=['POST'])
@login_required
@store_required
def toggle_store_publish():
    """API para publicar/despublicar a loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        # Alternar status de publicação
        store.is_published = not store.is_published
        db.session.commit()
        
        status = 'publicada' if store.is_published else 'despublicada'
        
        return jsonify({
            'success': True,
            'is_published': store.is_published,
            'message': f'Loja {status} com sucesso!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao alternar publicação da loja: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao alterar status da loja'
        }), 500


# ============================
# APIs de Meios de Pagamento
# ============================

@admin.route('/settings/payment-methods', methods=['GET'])
@login_required
@store_required
def get_payment_methods():
    """API para obter todos os métodos de pagamento da loja"""
    try:
        store_id = session.get('store_id')
        payment_methods = StorePaymentMethod.query.filter_by(store_id=store_id).all()
        
        return jsonify({
            'success': True,
            'data': [pm.to_dict() for pm in payment_methods]
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar métodos de pagamento: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar métodos de pagamento'
        }), 500


@admin.route('/settings/payment-methods/<method>', methods=['PUT'])
@login_required
@store_required
def update_payment_method(method):
    """API para atualizar um método de pagamento"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        # Validar método
        valid_methods = ['pix', 'credit_card', 'debit_card', 'boleto']
        if method not in valid_methods:
            return jsonify({
                'success': False,
                'error': 'Método de pagamento inválido'
            }), 400
        
        # Buscar ou criar método de pagamento
        payment_method = StorePaymentMethod.query.filter_by(
            store_id=store_id,
            method=method
        ).first()
        
        if not payment_method:
            # Criar novo método
            payment_method = StorePaymentMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=data.get('is_enabled', False),
                config=data.get('config', {})
            )
            db.session.add(payment_method)
        else:
            # Atualizar método existente
            if 'is_enabled' in data:
                payment_method.is_enabled = data['is_enabled']
            if 'config' in data:
                payment_method.config = data['config']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': payment_method.to_dict(),
            'message': 'Método de pagamento atualizado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar método de pagamento: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar método de pagamento'
        }), 500


@admin.route('/settings/payment-methods/<method>/toggle', methods=['POST'])
@login_required
@store_required
def toggle_payment_method(method):
    """API para ativar/desativar um método de pagamento"""
    try:
        store_id = session.get('store_id')
        
        # Validar método
        valid_methods = ['pix', 'credit_card', 'debit_card', 'boleto']
        if method not in valid_methods:
            return jsonify({
                'success': False,
                'error': 'Método de pagamento inválido'
            }), 400
        
        # Buscar ou criar método de pagamento
        payment_method = StorePaymentMethod.query.filter_by(
            store_id=store_id,
            method=method
        ).first()
        
        if not payment_method:
            # Criar novo método habilitado
            payment_method = StorePaymentMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=True,
                config={}
            )
            db.session.add(payment_method)
        else:
            # Toggle status
            payment_method.is_enabled = not payment_method.is_enabled
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': payment_method.to_dict(),
            'message': f"Método {'ativado' if payment_method.is_enabled else 'desativado'} com sucesso"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao alternar método de pagamento: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao alternar método de pagamento'
        }), 500


# ============================
# APIs de Meios de Envio
# ============================

@admin.route('/settings/shipping-methods', methods=['GET'])
@login_required
@store_required
def get_shipping_methods():
    """API para obter todos os métodos de envio da loja"""
    try:
        store_id = session.get('store_id')
        shipping_methods = StoreShippingMethod.query.filter_by(store_id=store_id).all()
        
        return jsonify({
            'success': True,
            'data': [sm.to_dict() for sm in shipping_methods]
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar métodos de envio: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar métodos de envio'
        }), 500


@admin.route('/settings/shipping-methods/<method>', methods=['PUT'])
@login_required
@store_required
def update_shipping_method(method):
    """API para atualizar um método de envio"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        # Validar método
        valid_methods = ['correios', 'fixed', 'pickup', 'custom']
        if method not in valid_methods:
            return jsonify({
                'success': False,
                'error': 'Método de envio inválido'
            }), 400
        
        # Buscar ou criar método de envio
        shipping_method = StoreShippingMethod.query.filter_by(
            store_id=store_id,
            method=method
        ).first()
        
        if not shipping_method:
            # Criar novo método
            shipping_method = StoreShippingMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=data.get('is_enabled', False),
                config=data.get('config', {})
            )
            db.session.add(shipping_method)
        else:
            # Atualizar método existente
            if 'is_enabled' in data:
                shipping_method.is_enabled = data['is_enabled']
            if 'config' in data:
                shipping_method.config = data['config']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': shipping_method.to_dict(),
            'message': 'Método de envio atualizado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar método de envio: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar método de envio'
        }), 500


@admin.route('/settings/shipping-methods/<method>/toggle', methods=['POST'])
@login_required
@store_required
def toggle_shipping_method(method):
    """API para ativar/desativar um método de envio"""
    try:
        store_id = session.get('store_id')
        
        # Validar método
        valid_methods = ['correios', 'fixed', 'pickup', 'custom']
        if method not in valid_methods:
            return jsonify({
                'success': False,
                'error': 'Método de envio inválido'
            }), 400
        
        # Buscar ou criar método de envio
        shipping_method = StoreShippingMethod.query.filter_by(
            store_id=store_id,
            method=method
        ).first()
        
        if not shipping_method:
            # Criar novo método habilitado
            shipping_method = StoreShippingMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=True,
                config={}
            )
            db.session.add(shipping_method)
        else:
            # Toggle status
            shipping_method.is_enabled = not shipping_method.is_enabled
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': shipping_method.to_dict(),
            'message': f"Método {'ativado' if shipping_method.is_enabled else 'desativado'} com sucesso"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao alternar método de envio: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao alternar método de envio'
        }), 500


# ============================
# APIs de Dados do Negócio
# ============================

@admin.route('/settings/business', methods=['PUT'])
@login_required
@store_required
def update_business_data():
    """API para atualizar dados do negócio"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        data = request.get_json()
        
        # Atualizar dados básicos da loja
        if 'name' in data:
            store.name = data['name']
        if 'slug' in data:
            new_slug = data['slug'].strip().lower()
            # Verificar se o slug já existe em outra loja
            existing = Store.query.filter(Store.slug == new_slug, Store.id != store_id).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Esta URL já está sendo usada por outra loja'
                }), 400
            store.slug = new_slug
        if 'description' in data:
            store.description = data['description']
        if 'person_type' in data and data['person_type'] in ['PF', 'PJ']:
            store.person_type = data['person_type']
        if 'cpf' in data:
            store.cpf = data['cpf'].replace('.', '').replace('-', '') if data['cpf'] else None
        if 'cnpj' in data:
            store.cnpj = data['cnpj'].replace('.', '').replace('/', '').replace('-', '') if data['cnpj'] else None
        if 'legal_name' in data:
            store.legal_name = data['legal_name']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': store.to_dict(),
            'message': 'Dados do negócio atualizados com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar dados do negócio: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar dados do negócio'
        }), 500


@admin.route('/settings/business/logo', methods=['POST'])
@login_required
@store_required
def upload_business_logo():
    """API para fazer upload do logo da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)
        
        if not store:
            return jsonify({
                'success': False,
                'error': 'Loja não encontrada'
            }), 404
        
        if 'logo' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['logo']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar extensão
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': 'Tipo de arquivo não permitido'
            }), 400
        
        # Gerar nome único
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{store_id}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Caminho para salvar
        upload_folder = os.path.join('app', 'static', 'uploads', 'logos')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        
        file.save(filepath)
        
        # Atualizar customização da loja
        logo_url = f"/static/uploads/logos/{filename}"
        
        if not store.customization:
            customization = StoreCustomization(
                store_id=store_id,
                logo=logo_url
            )
            db.session.add(customization)
        else:
            # Remover logo antigo se existir
            if store.customization.logo:
                old_path = os.path.join('app', store.customization.logo.lstrip('/'))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
            store.customization.logo = logo_url
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {'logo_url': logo_url},
            'message': 'Logo atualizado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao fazer upload do logo: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao fazer upload do logo'
        }), 500


# ============================
# APIs de Administradores
# ============================

@admin.route('/settings/admins', methods=['GET'])
@login_required
@store_required
def get_store_admins():
    """API para obter todos os administradores da loja"""
    try:
        store_id = session.get('store_id')
        admins = StoreAdmin.query.filter_by(store_id=store_id).all()
        
        admins_list = []
        for admin_record in admins:
            customer = StoreCustomer.query.get(admin_record.customer_id)
            if customer:
                admins_list.append({
                    'id': admin_record.id,
                    'customer_id': admin_record.customer_id,
                    'email': customer.email,
                    'full_name': customer.full_name,
                    'phone': customer.phone,
                    'role': admin_record.role,
                    'is_active': customer.is_active,
                    'created_at': admin_record.created_at.isoformat() if admin_record.created_at else None,
                    'updated_at': admin_record.updated_at.isoformat() if admin_record.updated_at else None
                })
        
        return jsonify({
            'success': True,
            'data': admins_list
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar administradores: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar administradores'
        }), 500


@admin.route('/settings/admins', methods=['POST'])
@login_required
@store_required
def add_store_admin():
    """API para adicionar um administrador à loja por email"""
    try:
        store_id = session.get('store_id')
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'E-mail é obrigatório'
            }), 400
        
        # Verificar se o email já é admin
        existing_customer = StoreCustomer.query.filter_by(store_id=store_id, email=email).first()
        
        if existing_customer:
            # Verificar se já é admin
            existing_admin = StoreAdmin.query.filter_by(
                store_id=store_id,
                customer_id=existing_customer.id
            ).first()
            
            if existing_admin:
                return jsonify({
                    'success': False,
                    'error': 'Este usuário já é administrador da loja'
                }), 409
            
            # Criar admin para customer existente
            new_admin = StoreAdmin(
                id=str(uuid.uuid4()),
                store_id=store_id,
                customer_id=existing_customer.id,
                role='admin'
            )
            db.session.add(new_admin)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'{existing_customer.full_name or email} foi adicionado como administrador',
                'data': {
                    'id': new_admin.id,
                    'customer_id': existing_customer.id,
                    'email': existing_customer.email,
                    'full_name': existing_customer.full_name,
                    'role': 'admin'
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Usuário não encontrado. O usuário precisa estar cadastrado na loja primeiro.'
            }), 404
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao adicionar administrador: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao adicionar administrador'
        }), 500


@admin.route('/settings/admins/<admin_id>', methods=['DELETE'])
@login_required
@store_required
def remove_store_admin(admin_id):
    """API para remover um administrador da loja"""
    try:
        store_id = session.get('store_id')
        
        admin_record = StoreAdmin.query.filter_by(id=admin_id, store_id=store_id).first()
        
        if not admin_record:
            return jsonify({
                'success': False,
                'error': 'Administrador não encontrado'
            }), 404
        
        # Não permitir remover o owner
        if admin_record.role == 'owner':
            return jsonify({
                'success': False,
                'error': 'Não é possível remover o proprietário da loja'
            }), 403
        
        db.session.delete(admin_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Administrador removido com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao remover administrador: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao remover administrador'
        }), 500