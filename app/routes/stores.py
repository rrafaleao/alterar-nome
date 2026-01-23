from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from config.database import db
from app.models.store import Store
from app.models.user import User
from app.models.store_payment_method import StorePaymentMethod
from app.models.store_shipping_methods import StoreShippingMethod
import uuid
import re
import traceback

registration = Blueprint("registration", __name__, url_prefix="/api/registration")


def generate_slug(name):
    """Gera um slug único baseado no nome da loja"""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    
    # Verifica se o slug já existe e adiciona número se necessário
    original_slug = slug
    counter = 1
    while Store.query.filter_by(slug=slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    return slug


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


# ==================== ETAPA 1: DADOS DA LOJA E CREDENCIAIS ====================

@registration.post('/step1')
def registration_step1():
    """
    Etapa 1: Coleta nome da loja, email e senha
    Cria o usuário e armazena dados temporários na sessão
    """
    try:
        data = request.get_json()
        
        store_name = data.get('store_name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        print(f"\n=== REGISTRO ETAPA 1 ===")
        print(f"Nome da Loja: {store_name}")
        print(f"Email: {email}")
        
        # Validações
        errors = {}
        
        if not store_name:
            errors['store_name'] = 'Nome da loja é obrigatório'
        elif len(store_name) < 3:
            errors['store_name'] = 'Nome da loja deve ter no mínimo 3 caracteres'
        
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
        
        # Gera slug único para a loja
        slug = generate_slug(store_name)
        
        # Armazena dados na sessão para usar nas próximas etapas
        session['registration_data'] = {
            'store_name': store_name,
            'slug': slug,
            'email': email,
            'password_hash': generate_password_hash(password),
            'step': 1
        }
        
        print(f"Slug gerado: {slug}")
        print(f"Dados armazenados na sessão")
        print(f"=== ETAPA 1 CONCLUÍDA ===\n")
        
        return jsonify({
            'success': True,
            'message': 'Etapa 1 concluída com sucesso',
            'data': {
                'store_name': store_name,
                'slug': slug,
                'email': email
            }
        }), 200
        
    except Exception as e:
        print(f"Erro na etapa 1: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao processar dados. Tente novamente.'
        }), 500


# ==================== ETAPA 2: DADOS PESSOAIS/EMPRESA ====================

@registration.post('/step2')
def registration_step2():
    """
    Etapa 2: Coleta nome completo e documento (CPF ou CNPJ)
    Cria o usuário no banco de dados
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
        
        full_name = data.get('full_name', '').strip()
        person_type = data.get('person_type', 'PF')  # PF ou PJ
        cpf = data.get('cpf', '').strip()
        cnpj = data.get('cnpj', '').strip()
        legal_name = data.get('legal_name', '').strip()
        
        print(f"\n=== REGISTRO ETAPA 2 ===")
        print(f"Nome Completo: {full_name}")
        print(f"Tipo: {person_type}")
        
        # Validações
        errors = {}
        
        if not full_name:
            errors['full_name'] = 'Nome completo é obrigatório'
        elif len(full_name) < 3:
            errors['full_name'] = 'Nome deve ter no mínimo 3 caracteres'
        
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
        
        # Cria o usuário
        user = User(
            id=str(uuid.uuid4()),
            email=registration_data['email'],
            password_hash=registration_data['password_hash'],
            full_name=full_name,
            is_seller=True,
            is_active=True
        )
        
        db.session.add(user)
        db.session.flush()  # Garante que o user.id está disponível
        
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
            onboarding_step=2,  # Marca que está na etapa 2
            onboarding_completed=False,
            is_published=False
        )
        
        db.session.add(store)
        db.session.commit()
        
        # Atualiza dados na sessão
        registration_data['user_id'] = user.id
        registration_data['store_id'] = store.id
        registration_data['full_name'] = full_name
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

@registration.post('/step3')
def registration_step3():
    """
    Etapa 3: Configura métodos de pagamento e frete
    Finaliza o onboarding
    """
    try:
        # Verifica se a etapa 2 foi concluída
        registration_data = session.get('registration_data')
        if not registration_data or registration_data.get('step') != 2:
            return jsonify({
                'success': False,
                'error': 'Complete as etapas anteriores primeiro'
            }), 400
        
        data = request.get_json()
        
        payment_methods = data.get('payment_methods', [])  # ['pix', 'credit_card', etc]
        shipping_methods = data.get('shipping_methods', [])  # ['correios', 'fixed', etc]
        
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
                config={}  # Configurações específicas podem ser adicionadas depois
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
                config={}  # Configurações específicas podem ser adicionadas depois
            )
            db.session.add(shipping_method)
            print(f"Método de frete adicionado: {method}")
        
        # Atualiza a loja marcando onboarding como completo
        store = Store.query.get(store_id)
        store.onboarding_step = 3
        store.onboarding_completed = True
        
        db.session.commit()
        
        print(f"Onboarding completo para loja: {store_id}")
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
                'user_id': registration_data['user_id']
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


# ==================== ENDPOINTS AUXILIARES ====================

@registration.get('/status')
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
        'completed': registration_data.get('step', 0) == 3,
        'data': {
            'store_name': registration_data.get('store_name'),
            'email': registration_data.get('email'),
            'slug': registration_data.get('slug')
        }
    }), 200


@registration.post('/cancel')
def registration_cancel():
    """Cancela o registro e limpa a sessão"""
    registration_data = session.get('registration_data')
    
    if registration_data:
        # Se já criou usuário e loja, pode deletar ou marcar como incompleto
        store_id = registration_data.get('store_id')
        if store_id:
            store = Store.query.get(store_id)
            if store and not store.onboarding_completed:
                # Opcional: deletar ou manter como rascunho
                db.session.delete(store)
                db.session.commit()
                print(f"Loja {store_id} deletada - registro cancelado")
    
    session.pop('registration_data', None)
    
    return jsonify({
        'success': True,
        'message': 'Registro cancelado'
    }), 200