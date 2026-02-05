from flask import render_template
from . import admin
from .decorators import login_required, store_required


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