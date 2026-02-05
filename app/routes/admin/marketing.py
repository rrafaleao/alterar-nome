from flask import render_template
from . import admin
from .decorators import login_required, store_required


@admin.route('/promotions')
@login_required
@store_required
def promotions_page():
    """Página de promoções"""
    return render_template('admin/promotions.html')


@admin.route('/coupons')
@login_required
@store_required
def coupons_page():
    """Página de cupons de desconto"""
    return render_template('admin/coupons.html')