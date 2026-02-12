import os
import uuid
from flask import render_template, jsonify, request, session, current_app
from werkzeug.utils import secure_filename
from config.database import db
from . import admin
from .decorators import login_required, store_required
from app.models.store import Store, StoreCustomization


ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}


def allowed_logo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


@admin.route('/layout')
@login_required
@store_required
def layout_page():
    """Página de personalização de layout"""
    return render_template('admin/layout.html')


@admin.route('/menus')
@login_required
@store_required
def menus_page():
    """Página de configuração de menus"""
    return render_template('admin/menus.html')


# ============================
# APIs de Layout / Personalização
# ============================

@admin.route('/api/layout', methods=['GET'])
@login_required
@store_required
def get_layout_data():
    """Retorna dados atuais de personalização da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)

        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        data = {
            'name': store.name,
            'description': store.description or '',
            'slug': store.slug,
            'is_published': store.is_published,
        }

        if store.customization:
            data['logo'] = store.customization.logo or ''
            data['primary_color'] = store.customization.primary_color or '#667eea'
            data['secondary_color'] = store.customization.secondary_color or '#764ba2'
            data['theme'] = store.customization.theme or {}
        else:
            data['logo'] = ''
            data['primary_color'] = '#667eea'
            data['secondary_color'] = '#764ba2'
            data['theme'] = {}

        return jsonify({'success': True, 'data': data}), 200

    except Exception as e:
        print(f"Erro ao buscar layout: {e}")
        return jsonify({'success': False, 'error': 'Erro ao carregar dados'}), 500


@admin.route('/api/layout', methods=['PUT'])
@login_required
@store_required
def update_layout_data():
    """Atualiza dados de personalização (cores, descrição, tema)"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)

        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        data = request.get_json()

        # Atualiza descrição na store
        if 'description' in data:
            store.description = data['description'].strip() if data['description'] else ''

        # Garante que existe customização
        if not store.customization:
            customization = StoreCustomization(store_id=store_id)
            db.session.add(customization)
            db.session.flush()
            store.customization = customization

        cust = store.customization

        if 'primary_color' in data:
            cust.primary_color = data['primary_color']

        if 'secondary_color' in data:
            cust.secondary_color = data['secondary_color']

        if 'theme' in data and isinstance(data['theme'], dict):
            current_theme = cust.theme or {}
            current_theme.update(data['theme'])
            cust.theme = current_theme

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Layout atualizado com sucesso!'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar layout: {e}")
        return jsonify({'success': False, 'error': 'Erro ao salvar alterações'}), 500


@admin.route('/api/layout/logo', methods=['POST'])
@login_required
@store_required
def upload_logo():
    """Faz upload da logo da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)

        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        if 'logo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

        file = request.files['logo']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

        if not allowed_logo_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Use: {", ".join(ALLOWED_LOGO_EXTENSIONS)}'
            }), 400

        # Gera nome único
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{store_id}_{uuid.uuid4().hex[:8]}.{ext}"

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        logo_url = f"/static/uploads/logos/{unique_filename}"

        # Garante que existe customização
        if not store.customization:
            customization = StoreCustomization(store_id=store_id)
            db.session.add(customization)
            db.session.flush()

        # Remove logo antiga se existir
        old_logo = store.customization.logo
        if old_logo:
            old_path = os.path.join(current_app.root_path, old_logo.lstrip('/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        store.customization.logo = logo_url
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Logo atualizada com sucesso!',
            'data': {'logo_url': logo_url}
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao fazer upload da logo: {e}")
        return jsonify({'success': False, 'error': 'Erro ao fazer upload'}), 500


@admin.route('/api/layout/logo', methods=['DELETE'])
@login_required
@store_required
def remove_logo():
    """Remove a logo da loja"""
    try:
        store_id = session.get('store_id')
        store = Store.query.get(store_id)

        if not store:
            return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404

        if store.customization and store.customization.logo:
            old_path = os.path.join(current_app.root_path, store.customization.logo.lstrip('/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

            store.customization.logo = None
            db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Logo removida com sucesso!'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao remover logo: {e}")
        return jsonify({'success': False, 'error': 'Erro ao remover logo'}), 500