from flask import render_template, abort, request, jsonify, session, redirect, url_for
from config.database import db
from . import storefront
from app.models.store import Store
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.address import Address
from .customer_auth import sync_customer_session_for_store
from decimal import Decimal


@storefront.route('/<slug>/checkout')
def checkout_page(slug):
    """Página de checkout/finalização de compra"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    
    if not store:
        abort(404)
    
    customer = sync_customer_session_for_store(store)

    # Redirecionar para login se não estiver logado para esta loja
    if not customer or not customer.is_active:
        # Salvar URL de retorno na sessão
        session['checkout_redirect'] = url_for('storefront.checkout_page', slug=slug)
        return redirect(url_for('storefront.customer_login_page', slug=slug))
    
    # Buscar último endereço do cliente (se houver)
    customer_address = Address.query.filter_by(user_id=customer.id).order_by(Address.created_at.desc()).first()
    
    # Buscar métodos de pagamento habilitados da loja
    payment_methods = [pm for pm in store.payment_methods if pm.is_enabled]
    
    # Buscar métodos de envio habilitados da loja
    shipping_methods = [sm for sm in store.shipping_methods if sm.is_enabled]
    
    # Preparar dados de customização
    customization = {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2'
    }
    
    if store.customization:
        customization['primary_color'] = store.customization.primary_color or '#667eea'
        customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
    
    return render_template(
        'stores/checkout.html',
        store=store,
        customer=customer,
        customer_address=customer_address,
        payment_methods=payment_methods,
        shipping_methods=shipping_methods,
        customization=customization
    )


@storefront.route('/<slug>/checkout/validate-cart', methods=['POST'])
def validate_cart(slug):
    """Valida os itens do carrinho e retorna os dados atualizados"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    
    if not store:
        return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404
    
    try:
        data = request.get_json()
        cart_items = data.get('items', [])
        
        validated_items = []
        total = Decimal('0')
        
        for item in cart_items:
            product = Product.query.filter_by(
                id=item.get('id'),
                store_id=store.id,
                active=True
            ).first()
            
            if product:
                quantity = int(item.get('quantity', 1))
                price = Decimal(str(product.price))
                subtotal = price * quantity
                
                validated_items.append({
                    'id': product.id,
                    'title': product.title,
                    'price': float(price),
                    'quantity': quantity,
                    'subtotal': float(subtotal),
                    'image': product.images[0].url if product.images else None
                })
                total += subtotal
        
        return jsonify({
            'success': True,
            'items': validated_items,
            'total': float(total)
        })
        
    except Exception as e:
        print(f"Erro ao validar carrinho: {e}")
        return jsonify({'success': False, 'error': 'Erro ao validar carrinho'}), 500


@storefront.route('/<slug>/checkout/process', methods=['POST'])
def process_checkout(slug):
    """Processa a finalização da compra"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    
    if not store:
        return jsonify({'success': False, 'error': 'Loja não encontrada'}), 404
    
    customer = sync_customer_session_for_store(store)

    if not customer or not customer.is_active:
        return jsonify({'success': False, 'error': 'Você precisa estar logado para finalizar a compra', 'redirect': url_for('storefront.customer_login_page', slug=slug)}), 401
    
    try:
        data = request.get_json()
        
        # Dados de entrega
        shipping_data = data.get('shipping', {})
        shipping_method = shipping_data.get('method')
        
        # Dados de pagamento
        payment_data = data.get('payment', {})
        payment_method = payment_data.get('method')
        
        # Itens do carrinho
        cart_items = data.get('items', [])
        
        if not cart_items:
            return jsonify({'success': False, 'error': 'Carrinho vazio'}), 400
        
        if not payment_method:
            return jsonify({'success': False, 'error': 'Método de pagamento não selecionado'}), 400
        
        # Validar e calcular total
        total = Decimal('0')
        order_items_data = []
        
        for item in cart_items:
            product = Product.query.filter_by(
                id=item.get('id'),
                store_id=store.id,
                active=True
            ).first()
            
            if not product:
                return jsonify({
                    'success': False, 
                    'error': f'Produto não encontrado ou indisponível'
                }), 400
            
            quantity = int(item.get('quantity', 1))
            price = Decimal(str(product.price))
            subtotal = price * quantity
            total += subtotal
            
            order_items_data.append({
                'product': product,
                'quantity': quantity,
                'price': price
            })
        
        # Calcular frete
        shipping_cost = Decimal('0')
        if shipping_method == 'fixed':
            # Buscar config do método de envio
            for sm in store.shipping_methods:
                if sm.method == 'fixed' and sm.is_enabled and sm.config:
                    shipping_cost = Decimal(str(sm.config.get('price', 0)))
                    break
        elif shipping_method == 'pickup':
            shipping_cost = Decimal('0')
        
        total_with_shipping = total + shipping_cost
        
        # Criar o endereço de entrega
        address_data = shipping_data.get('address', {})
        shipping_address = None
        shipping_address_id = None
        
        if shipping_method != 'pickup' and address_data:
            shipping_address = Address(
                user_id=customer.id,
                cep=address_data.get('cep', ''),
                street=address_data.get('street', ''),
                number=address_data.get('number', ''),
                complement=address_data.get('complement', ''),
                neighborhood=address_data.get('neighborhood', ''),
                city=address_data.get('city', ''),
                state=address_data.get('state', '')
            )
            db.session.add(shipping_address)
            db.session.flush()  # Para obter o ID do endereço
            shipping_address_id = shipping_address.id
        
        # Criar o pedido
        order = Order(
            store_id=store.id,
            user_id=customer.id,
            total_amount=total_with_shipping,
            status='pending',
            shipping_address_id=shipping_address_id,
            shipping_method=shipping_method,
            shipping_cost=shipping_cost
        )
        db.session.add(order)
        db.session.flush()  # Para obter o ID do pedido
        
        # Criar itens do pedido
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product'].id,
                title=item_data['product'].title,
                sku=item_data['product'].sku,
                unit_price=item_data['price'],
                quantity=item_data['quantity']
            )
            db.session.add(order_item)
        
        # Criar registro de pagamento
        payment = Payment(
            order_id=order.id,
            method=payment_method,
            amount=total_with_shipping,
            status='created',
            payment_data={
                'method_details': payment_data
            }
        )
        db.session.add(payment)
        
        # Processar pagamento (simulação)
        payment_result = process_payment(payment_method, total_with_shipping, payment_data)
        
        if payment_result['success']:
            payment.status = 'authorized'
            order.status = 'paid'
        else:
            payment.status = 'failed'
            order.status = 'cancelled'
        
        db.session.commit()
        
        if payment_result['success']:
            return jsonify({
                'success': True,
                'order_id': order.id,
                'message': 'Pedido realizado com sucesso!',
                'payment_info': payment_result.get('info', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': payment_result.get('error', 'Falha no pagamento')
            }), 400
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao processar checkout: {e}")
        return jsonify({'success': False, 'error': 'Erro ao processar pedido'}), 500


def process_payment(method, amount, payment_data):
    """
    Processa o pagamento baseado no método selecionado.
    Por enquanto é uma simulação - em produção integraria com gateways reais.
    """
    if method == 'pix':
        # Simulação de geração de PIX
        import uuid
        pix_code = f"00020126580014BR.GOV.BCB.PIX0136{uuid.uuid4()}5204000053039865802BR5913LOJA EXEMPLO6008BRASILIA62070503***6304"
        return {
            'success': True,
            'info': {
                'type': 'pix',
                'pix_code': pix_code,
                'message': 'Escaneie o QR Code ou copie o código PIX para pagar'
            }
        }
    
    elif method == 'credit_card':
        # Simulação - em produção usaria Stripe, PagSeguro, etc
        card_number = payment_data.get('card_number', '')
        # Validação básica
        if len(card_number.replace(' ', '')) < 13:
            return {'success': False, 'error': 'Número do cartão inválido'}
        
        return {
            'success': True,
            'info': {
                'type': 'credit_card',
                'message': 'Pagamento aprovado!'
            }
        }
    
    elif method == 'debit_card':
        card_number = payment_data.get('card_number', '')
        if len(card_number.replace(' ', '')) < 13:
            return {'success': False, 'error': 'Número do cartão inválido'}
        
        return {
            'success': True,
            'info': {
                'type': 'debit_card',
                'message': 'Pagamento aprovado!'
            }
        }
    
    elif method == 'boleto':
        # Simulação de geração de boleto
        import random
        boleto_code = ''.join([str(random.randint(0, 9)) for _ in range(47)])
        return {
            'success': True,
            'info': {
                'type': 'boleto',
                'boleto_code': boleto_code,
                'message': 'Boleto gerado! Pague até a data de vencimento.'
            }
        }
    
    return {'success': False, 'error': 'Método de pagamento não suportado'}


@storefront.route('/<slug>/order/<order_id>')
def order_confirmation(slug, order_id):
    """Página de confirmação do pedido"""
    store = Store.query.filter_by(slug=slug, onboarding_completed=True).first()
    
    if not store:
        abort(404)
    
    order = Order.query.filter_by(id=order_id, store_id=store.id).first()
    
    if not order:
        abort(404)
    
    # Preparar dados de customização
    customization = {
        'primary_color': '#667eea',
        'secondary_color': '#764ba2'
    }
    
    if store.customization:
        customization['primary_color'] = store.customization.primary_color or '#667eea'
        customization['secondary_color'] = store.customization.secondary_color or '#764ba2'
    
    return render_template(
        'stores/order_confirmation.html',
        store=store,
        order=order,
        customization=customization
    )
