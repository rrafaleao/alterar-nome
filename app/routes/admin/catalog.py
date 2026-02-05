from flask import render_template
from . import admin
from .decorators import login_required, store_required


@admin.route('/products')
@login_required
@store_required
def products_page():
    """Página de produtos"""
    return render_template('admin/products.html')


@admin.route('/categories')
@login_required
@store_required
def categories_page():
    """Página de categorias"""
    return render_template('admin/categories.html')


@admin.route('/stock')
@login_required
@store_required
def stock_page():
    """Página de gestão de estoque"""
    return render_template('admin/stock.html')