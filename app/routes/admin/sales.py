from flask import render_template
from . import admin
from .decorators import login_required, store_required


@admin.route('/orders')
@login_required
@store_required
def orders_page():
    """Página de pedidos"""
    return render_template('admin/orders.html')


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