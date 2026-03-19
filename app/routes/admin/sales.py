from flask import render_template, jsonify, request, session
from . import admin
from .decorators import login_required, store_required
from app.models.store_customer import StoreCustomer
from app.models.order import Order
from config.database import db
from datetime import datetime, timedelta


@admin.route('/orders')
@login_required
@store_required
def orders_page():
    """Página de pedidos"""
    store_id = session.get('store_id')
    
    # Buscar todos os pedidos da loja
    orders = Order.query.filter_by(store_id=store_id).order_by(Order.placed_at.desc()).all()
    
    # Estatísticas
    total_orders = len(orders)
    pending_orders = sum(1 for o in orders if o.status == 'pending')
    paid_orders = sum(1 for o in orders if o.status == 'paid')
    shipped_orders = sum(1 for o in orders if o.status == 'shipped')
    delivered_orders = sum(1 for o in orders if o.status == 'delivered')
    cancelled_orders = sum(1 for o in orders if o.status == 'cancelled')
    
    return render_template(
        'admin/orders.html',
        orders=orders,
        stats={
            'total': total_orders,
            'pending': pending_orders,
            'paid': paid_orders,
            'shipped': shipped_orders,
            'delivered': delivered_orders,
            'cancelled': cancelled_orders
        }
    )


@admin.route('/abandoned-carts')
@login_required
@store_required
def abandoned_carts_page():
    """Página de carrinhos abandonados"""
    return render_template('admin/abandoned_carts.html')


@admin.route('/customers')
@login_required
@store_required
def customers_page():
    """Página de clientes"""
    return render_template('admin/customers.html')


@admin.route('/customers/data', methods=['GET'])
@login_required
@store_required
def customers_data():
    """API para obter dados dos clientes da loja que já realizaram pedidos"""
    try:
        store_id = session.get('store_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str).strip()
        sort = request.args.get('sort', 'recent', type=str)

        # Mostra apenas clientes que tenham ao menos 1 pedido nesta loja
        has_order_in_store = db.session.query(Order.id).filter(
            Order.store_id == store_id,
            Order.user_id == StoreCustomer.id
        ).exists()

        base_query = StoreCustomer.query.filter(
            StoreCustomer.store_id == store_id,
            has_order_in_store
        )

        query = base_query

        # Busca
        if search:
            query = query.filter(
                db.or_(
                    StoreCustomer.full_name.ilike(f'%{search}%'),
                    StoreCustomer.email.ilike(f'%{search}%'),
                    StoreCustomer.phone.ilike(f'%{search}%')
                )
            )

        # Ordenação
        if sort == 'name':
            query = query.order_by(StoreCustomer.full_name.asc())
        elif sort == 'oldest':
            query = query.order_by(StoreCustomer.created_at.asc())
        else:  # recent
            query = query.order_by(StoreCustomer.created_at.desc())

        # Stats
        total_customers = base_query.count()

        now = datetime.utcnow()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = base_query.filter(
            StoreCustomer.created_at >= first_day_of_month
        ).count()

        active_customers = base_query.filter(StoreCustomer.is_active == True).count()

        # Paginação
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        customers = []
        for customer in pagination.items:
            customers.append({
                'id': customer.id,
                'full_name': customer.full_name or 'Sem nome',
                'email': customer.email,
                'phone': customer.phone,
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
            })

        return jsonify({
            'success': True,
            'data': customers,
            'stats': {
                'total': total_customers,
                'new_this_month': new_this_month,
                'active': active_customers,
            },
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            }
        }), 200

    except Exception as e:
        print(f"Erro ao buscar clientes: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar clientes'
        }), 500


@admin.route('/customers/<customer_id>/toggle-active', methods=['POST'])
@login_required
@store_required
def toggle_customer_active(customer_id):
    """Ativa/desativa um cliente"""
    try:
        store_id = session.get('store_id')
        customer = StoreCustomer.query.filter_by(id=customer_id, store_id=store_id).first()

        if not customer:
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404

        customer.is_active = not customer.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Cliente {"ativado" if customer.is_active else "desativado"} com sucesso',
            'is_active': customer.is_active
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao alterar status do cliente: {e}")
        return jsonify({'success': False, 'error': 'Erro ao alterar status'}), 500


@admin.route('/customers/<customer_id>', methods=['DELETE'])
@login_required
@store_required
def delete_customer(customer_id):
    """Remove um cliente da loja"""
    try:
        store_id = session.get('store_id')
        customer = StoreCustomer.query.filter_by(id=customer_id, store_id=store_id).first()

        if not customer:
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404

        db.session.delete(customer)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cliente removido com sucesso'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao remover cliente: {e}")
        return jsonify({'success': False, 'error': 'Erro ao remover cliente'}), 500