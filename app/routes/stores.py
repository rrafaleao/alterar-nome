from flask import Blueprint, render_template, request, redirect, url_for, flash
from config.database import db
from app.models.store import Store
from app.models.user import User
import traceback

stores = Blueprint("stores", __name__, url_prefix="/stores")


@stores.get('/create')
def create_store_form():
    """Exibe o formulário para criar uma nova loja"""
    return render_template('/stores/create_store.html')


@stores.post('/create')
def create_store():
    """Processa a criação de uma nova loja"""
    name = request.form.get("name")
    slug = request.form.get("slug")
    description = request.form.get("description")
    logo_url = request.form.get("logo_url")
    is_published = request.form.get("is_published") == "1"

    print(f"\n=== CRIANDO LOJA ===")
    print(f"Nome: {name}")
    print(f"Slug: {slug}")
    print(f"Descrição: {description}")
    print(f"Logo URL: {logo_url}")
    print(f"Publicada: {is_published}")

    # Validações
    if not name or not slug:
        flash("Nome e slug são obrigatórios.")
        return redirect(url_for("stores.create_store_form"))

    # Cria um usuário padrão se não existir
    user = User.query.filter_by(email="admin@loja.com").first()
    if not user:
        user = User(
            email="admin@loja.com",
            password_hash="hash_temporario",
            full_name="Administrador",
            is_seller=True,
            is_active=True
        )
        db.session.add(user)
        db.session.flush()
        print(f"Usuário criado: {user.id}")

    # Cria a loja
    store = Store(
        owner_id=user.id,
        name=name,
        slug=slug,
        description=description,
        logo_url=logo_url,
        is_published=is_published
    )

    try:
        db.session.add(store)
        db.session.commit()
        print(f"Loja criada com sucesso!")
        print(f"ID: {store.id}")
        print(f"=== FIM ===\n")
        flash(f"Loja '{name}' criada com sucesso! ID: {store.id}")
        return redirect(url_for("stores.list_stores"))
    except Exception as exc:
        print(f"Erro ao criar loja: {exc}")
        traceback.print_exc()
        db.session.rollback()
        flash("Erro ao criar loja. Verifique os logs.")
        return redirect(url_for("stores.create_store_form"))


@stores.get('/list')
def list_stores():
    """Lista todas as lojas"""
    stores_list = Store.query.all()
    print(f"\n=== LISTANDO LOJAS ===")
    for store in stores_list:
        print(f"ID: {store.id} | Nome: {store.name} | Slug: {store.slug}")
    print(f"Total: {len(stores_list)}\n")
    return render_template('/stores/list_store.html', stores=stores_list)
