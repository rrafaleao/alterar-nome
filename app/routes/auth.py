from flask import Blueprint, render_template, jsonify
from config.database import db

auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.get('/login')
def create_store_form():
    """Exibe o formulário para criar uma nova loja"""
    return render_template('/auth/login.html')

@auth.get('/register')
def register():
    """Exibe o formulário para criar uma nova loja"""
    return render_template('/auth/register.html')