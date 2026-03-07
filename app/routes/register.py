from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from config.database import db
from app.models.store import Store
from app.models.user import User
from app.models.store_payment_method import StorePaymentMethod
from app.models.store_shipping_methods import StoreShippingMethod
from app.models.store import StoreCustomization
from app.models.store_customer import StoreCustomer
from app.models.store_admin import StoreAdmin
import uuid
import re
import traceback
import os

registration = Blueprint("registration", __name__, url_prefix="/registration")

# Configuração de upload
UPLOAD_FOLDER = 'static/uploads/logos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_slug(slug):
    """Valida se o slug contém apenas caracteres permitidos"""
    pattern = r'^[a-z0-9-]+$'
    return re.match(pattern, slug) is not None


def validate_phone(phone):
    """Validação básica de telefone brasileiro"""
    phone = re.sub(r'\D', '', phone)
    return len(phone) in [10, 11]  # (11) 98888-8888 ou (11) 8888-8888


def validate_cpf(cpf):
    """Validação básica de CPF (apenas formato)"""
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11


def validate_cnpj(cnpj):
    """Validação básica de CNPJ (apenas formato)"""
    cnpj = re.sub(r'\D', '', cnpj)
    return len(cnpj) == 14


def validate_email(email):
    """Validação básica de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_hex_color(color):
    """Valida cor hexadecimal"""
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return re.match(pattern, color) is not None


# ==================== ROTA PARA EXIBIR O HTML ====================

@registration.route('/', methods=['GET'])
def show_registration_form():
    """
    Exibe o formulário HTML de registro
    Rota: GET /registration/
    """
    return render_template('registration.html')


# ==================== ETAPA 1: DADOS DA LOJA E CREDENCIAIS ====================

@registration.route('/step1', methods=['POST'])
def registration_step1():
    """
    Etapa 1: Coleta nome da loja, URL/slug, email e senha
    Armazena dados temporários na sessão
    Rota: POST /registration/step1
    """
    try:
        data = request.get_json()
        
        store_name = data.get('store_name', '').strip()
        store_url = data.get('store_url', '').strip().lower()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        print(f"\n=== REGISTRO ETAPA 1 ===")
        print(f"Nome da Loja: {store_name}")
        print(f"URL da Loja: {store_url}")
        print(f"Email: {email}")
        
        # Validações
        errors = {}
        
        if not store_name:
            errors['store_name'] = 'Nome da loja é obrigatório'
        elif len(store_name) < 3:
            errors['store_name'] = 'Nome da loja deve ter no mínimo 3 caracteres'
        
        if not store_url:
            errors['store_url'] = 'URL da loja é obrigatória'
        elif len(store_url) < 3:
            errors['store_url'] = 'URL deve ter no mínimo 3 caracteres'
        elif not validate_slug(store_url):
            errors['store_url'] = 'URL deve conter apenas letras minúsculas, números e hífens'
        elif Store.query.filter_by(slug=store_url).first():
            errors['store_url'] = 'Esta URL já está em uso. Escolha outra.'
        
        if not email:
            errors['email'] = 'Email é obrigatório'
        elif not validate_email(email):
            errors['email'] = 'Email inválido'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Este email já está cadastrado'
        
        if not password:
            errors['password'] = 'Senha é obrigatória'
        elif len(password) < 8:
            errors['password'] = 'Senha deve ter no mínimo 8 caracteres'
        
        if password != confirm_password:
            errors['confirm_password'] = 'As senhas não coincidem'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Armazena dados na sessão para usar nas próximas etapas
        session['registration_data'] = {
            'store_name': store_name,
            'slug': store_url,
            'email': email,
            'password_hash': generate_password_hash(password),
            'step': 1
        }
        
        print(f"Slug/URL: {store_url}")
        print(f"Dados armazenados na sessão")
        print(f"=== ETAPA 1 CONCLUÍDA ===\n")
        
        return jsonify({
            'success': True,
            'message': 'Etapa 1 concluída com sucesso',
            'data': {
                'store_name': store_name,
                'slug': store_url,
                'email': email
            }
        }), 200
        
    except Exception as e:
        print(f"Erro na etapa 1: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar dados. Tente novamente.'
        }), 500


# ==================== ETAPA 2: DADOS PESSOAIS/EMPRESA ====================

@registration.route('/step2', methods=['POST'])
def registration_step2():
    """
    Etapa 2: Coleta nome, sobrenome, telefone e documento (CPF ou CNPJ)
    Cria o usuário no banco de dados
    Rota: POST /registration/step2
    """
    try:
        # Verifica se a etapa 1 foi concluída
        registration_data = session.get('registration_data')
        if not registration_data or registration_data.get('step') != 1:
            return jsonify({
                'success': False,
                'error': 'Complete a etapa 1 primeiro'
            }), 400
        
        data = request.get_json()
        
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        person_type = data.get('person_type', 'PF')
        cpf = data.get('cpf', '').strip()
        cnpj = data.get('cnpj', '').strip()
        legal_name = data.get('legal_name', '').strip()
        
        print(f"\n=== REGISTRO ETAPA 2 ===")
        print(f"Nome: {first_name} {last_name}")
        print(f"Telefone: {phone}")
        print(f"Tipo: {person_type}")
        
        # Validações
        errors = {}
        
        if not first_name:
            errors['first_name'] = 'Nome é obrigatório'
        elif len(first_name) < 2:
            errors['first_name'] = 'Nome deve ter no mínimo 2 caracteres'
        
        if not last_name:
            errors['last_name'] = 'Sobrenome é obrigatório'
        elif len(last_name) < 2:
            errors['last_name'] = 'Sobrenome deve ter no mínimo 2 caracteres'
        
        if not phone:
            errors['phone'] = 'Telefone é obrigatório'
        elif not validate_phone(phone):
            errors['phone'] = 'Telefone inválido'
        else:
            phone = re.sub(r'\D', '', phone)
        
        if person_type not in ['PF', 'PJ']:
            errors['person_type'] = 'Tipo de pessoa inválido'
        
        if person_type == 'PF':
            if not cpf:
                errors['cpf'] = 'CPF é obrigatório'
            elif not validate_cpf(cpf):
                errors['cpf'] = 'CPF inválido'
            else:
                cpf = re.sub(r'\D', '', cpf)
        
        if person_type == 'PJ':
            if not cnpj:
                errors['cnpj'] = 'CNPJ é obrigatório'
            elif not validate_cnpj(cnpj):
                errors['cnpj'] = 'CNPJ inválido'
            else:
                cnpj = re.sub(r'\D', '', cnpj)
            
            if not legal_name:
                errors['legal_name'] = 'Razão social é obrigatória'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Monta nome completo
        full_name = f"{first_name} {last_name}"
        
        # Cria o usuário
        user = User(
            id=str(uuid.uuid4()),
            email=registration_data['email'],
            password_hash=registration_data['password_hash'],
            full_name=full_name,
            phone=phone,
            is_seller=True,
            is_active=True
        )
        
        db.session.add(user)
        db.session.flush()
        
        # Cria a loja com dados parciais
        store = Store(
            id=str(uuid.uuid4()),
            owner_id=user.id,
            name=registration_data['store_name'],
            slug=registration_data['slug'],
            person_type=person_type,
            cpf=cpf if person_type == 'PF' else None,
            cnpj=cnpj if person_type == 'PJ' else None,
            legal_name=legal_name if person_type == 'PJ' else None,
            onboarding_step=2,
            onboarding_completed=False,
            is_published=False
        )
        
        db.session.add(store)
        db.session.commit()
        
        # Atualiza dados na sessão
        registration_data['user_id'] = user.id
        registration_data['store_id'] = store.id
        registration_data['full_name'] = full_name
        registration_data['phone'] = phone
        registration_data['person_type'] = person_type
        registration_data['step'] = 2
        session['registration_data'] = registration_data
        
        print(f"Usuário criado: {user.id}")
        print(f"Loja criada: {store.id}")
        print(f"=== ETAPA 2 CONCLUÍDA ===\n")
        
        return jsonify({
            'success': True,
            'message': 'Etapa 2 concluída com sucesso',
            'data': {
                'user_id': user.id,
                'store_id': store.id,
                'full_name': full_name
            }
        }), 200
        
    except Exception as e:
        print(f"Erro na etapa 2: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar dados. Tente novamente.'
        }), 500


# ==================== ETAPA 3: MEIOS DE PAGAMENTO E FRETE ====================

@registration.route('/step3', methods=['POST'])
def registration_step3():
    """
    Etapa 3: Configura métodos de pagamento e frete
    Rota: POST /registration/step3
    """
    try:
        registration_data = session.get('registration_data')
        if not registration_data or registration_data.get('step') != 2:
            return jsonify({
                'success': False,
                'error': 'Complete as etapas anteriores primeiro'
            }), 400
        
        data = request.get_json()
        
        payment_methods = data.get('payment_methods', [])
        shipping_methods = data.get('shipping_methods', [])
        
        print(f"\n=== REGISTRO ETAPA 3 ===")
        print(f"Meios de Pagamento: {payment_methods}")
        print(f"Meios de Frete: {shipping_methods}")
        
        # Validações
        errors = {}
        
        valid_payment_methods = ['pix', 'credit_card', 'debit_card', 'boleto']
        valid_shipping_methods = ['correios', 'fixed', 'pickup', 'custom']
        
        if not payment_methods:
            errors['payment_methods'] = 'Selecione pelo menos um método de pagamento'
        else:
            for method in payment_methods:
                if method not in valid_payment_methods:
                    errors['payment_methods'] = f'Método de pagamento inválido: {method}'
                    break
        
        if not shipping_methods:
            errors['shipping_methods'] = 'Selecione pelo menos um método de frete'
        else:
            for method in shipping_methods:
                if method not in valid_shipping_methods:
                    errors['shipping_methods'] = f'Método de frete inválido: {method}'
                    break
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        store_id = registration_data['store_id']
        
        # Adiciona métodos de pagamento
        for method in payment_methods:
            payment_method = StorePaymentMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=True,
                config={}
            )
            db.session.add(payment_method)
            print(f"Método de pagamento adicionado: {method}")
        
        # Adiciona métodos de frete
        for method in shipping_methods:
            shipping_method = StoreShippingMethod(
                id=str(uuid.uuid4()),
                store_id=store_id,
                method=method,
                is_enabled=True,
                config={}
            )
            db.session.add(shipping_method)
            print(f"Método de frete adicionado: {method}")
        
        # Atualiza a loja
        store = Store.query.get(store_id)
        store.onboarding_step = 3
        
        db.session.commit()
        
        # Atualiza sessão
        registration_data['step'] = 3
        session['registration_data'] = registration_data
        
        print(f"Etapa 3 concluída para loja: {store_id}")
        print(f"=== ETAPA 3 CONCLUÍDA ===\n")
        
        return jsonify({
            'success': True,
            'message': 'Etapa 3 concluída com sucesso!',
            'data': {
                'store_id': store_id
            }
        }), 200
        
    except Exception as e:
        print(f"Erro na etapa 3: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar dados. Tente novamente.'
        }), 500


# ==================== ETAPA 4: PERSONALIZAÇÃO DA LOJA ====================

@registration.route('/step4', methods=['POST'])
def registration_step4():
    """
    Etapa 4: Personalização visual (layout, logo, cores)
    Finaliza o onboarding
    Rota: POST /registration/step4
    Aceita FormData com arquivo de logo
    """
    try:
        registration_data = session.get('registration_data')
        if not registration_data or registration_data.get('step') != 3:
            return jsonify({
                'success': False,
                'error': 'Complete as etapas anteriores primeiro'
            }), 400
        
        # Aceita tanto JSON quanto FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            layout_template = request.form.get('layout_template', 'default')
            primary_color = request.form.get('primary_color', '#667eea')
            secondary_color = request.form.get('secondary_color', '#764ba2')
        else:
            data = request.get_json() or {}
            layout_template = data.get('layout_template', 'default')
            primary_color = data.get('primary_color', '#667eea')
            secondary_color = data.get('secondary_color', '#764ba2')
        
        logo_url = ''
        
        # Processa upload de logo se enviado
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                ext = file.filename.rsplit('.', 1)[1].lower()
                store_id = registration_data['store_id']
                filename = f"{store_id}_{uuid.uuid4().hex[:8]}.{ext}"
                
                # Criar pasta de logos se não existir
                upload_folder = os.path.join('app', 'static', 'uploads', 'logos')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Salvar arquivo
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                logo_url = f"/static/uploads/logos/{filename}"
                print(f"Logo salvo: {logo_url}")
        
        print(f"\n=== REGISTRO ETAPA 4 ===")
        print(f"Template: {layout_template}")
        print(f"Cor Primária: {primary_color}")
        print(f"Cor Secundária: {secondary_color}")
        print(f"Logo URL: {logo_url}")
        
        # Validações
        errors = {}
        
        valid_templates = ['default', 'modern', 'minimal', 'colorful', 'elegant']
        
        if layout_template not in valid_templates:
            errors['layout_template'] = 'Template inválido'
        
        if not validate_hex_color(primary_color):
            errors['primary_color'] = 'Cor primária inválida (use formato #RRGGBB)'
        
        if not validate_hex_color(secondary_color):
            errors['secondary_color'] = 'Cor secundária inválida (use formato #RRGGBB)'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        store_id = registration_data['store_id']
        store = Store.query.get(store_id)
        
        # Cria customização da loja (incluindo logo se fornecido)
        customization = StoreCustomization(
            store_id=store_id,
            logo=logo_url if logo_url else None,
            primary_color=primary_color,
            secondary_color=secondary_color,
            theme={
                'template': layout_template,
                'font_family': 'default',
                'layout': layout_template
            }
        )
        
        db.session.add(customization)
        
        # Marca onboarding como completo
        store.onboarding_step = 4
        store.onboarding_completed = True
        
        # Cria store_customer para o owner (para poder ser admin)
        owner_customer = StoreCustomer(
            id=str(uuid.uuid4()),
            store_id=store_id,
            email=registration_data['email'],
            password_hash=registration_data['password_hash'],
            full_name=registration_data.get('full_name', ''),
            phone=registration_data.get('phone'),
            is_active=True
        )
        db.session.add(owner_customer)
        db.session.flush()
        
        # Cria store_admin para o owner
        store_admin = StoreAdmin(
            id=str(uuid.uuid4()),
            store_id=store_id,
            customer_id=owner_customer.id,
            role='owner'
        )
        db.session.add(store_admin)
        
        db.session.commit()
        
        print(f"Customização criada para loja: {store_id}")
        print(f"Onboarding completo!")
        print(f"=== REGISTRO FINALIZADO ===\n")
        
        # Limpa dados da sessão
        session.pop('registration_data', None)
        
        return jsonify({
            'success': True,
            'message': 'Registro concluído com sucesso!',
            'data': {
                'store_id': store_id,
                'store_name': store.name,
                'slug': store.slug,
                'user_id': registration_data['user_id'],
                'store_url': f"/{store.slug}"
            }
        }), 200
        
    except Exception as e:
        print(f"Erro na etapa 4: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar dados. Tente novamente.'
        }), 500


# ==================== UPLOAD DE LOGO ====================

@registration.route('/upload-logo', methods=['POST'])
def upload_logo():
    """
    Upload de logo da loja
    Rota: POST /registration/upload-logo
    """
    try:
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
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF ou WEBP'
            }), 400
        
        # Gera nome único para o arquivo
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Cria pasta se não existir
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Salva arquivo
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # URL pública do arquivo
        logo_url = f"/static/uploads/logos/{unique_filename}"
        
        print(f"Logo uploaded: {logo_url}")
        
        return jsonify({
            'success': True,
            'logo_url': logo_url
        }), 200
        
    except Exception as e:
        print(f"Erro no upload: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erro ao fazer upload. Tente novamente.'
        }), 500


# ==================== ENDPOINTS AUXILIARES ====================

@registration.route('/status', methods=['GET'])
def registration_status():
    """Retorna o status atual do registro"""
    registration_data = session.get('registration_data')
    
    if not registration_data:
        return jsonify({
            'success': True,
            'current_step': 0,
            'completed': False
        }), 200
    
    return jsonify({
        'success': True,
        'current_step': registration_data.get('step', 0),
        'completed': registration_data.get('step', 0) == 4,
        'data': {
            'store_name': registration_data.get('store_name'),
            'email': registration_data.get('email'),
            'slug': registration_data.get('slug')
        }
    }), 200


@registration.route('/cancel', methods=['POST'])
def registration_cancel():
    """Cancela o registro e limpa a sessão"""
    registration_data = session.get('registration_data')
    
    if registration_data:
        store_id = registration_data.get('store_id')
        if store_id:
            store = Store.query.get(store_id)
            if store and not store.onboarding_completed:
                db.session.delete(store)
                db.session.commit()
                print(f"Loja {store_id} deletada - registro cancelado")
    
    session.pop('registration_data', None)
    
    return jsonify({
        'success': True,
        'message': 'Registro cancelado'
    }), 200