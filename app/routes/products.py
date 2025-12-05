from flask import Blueprint, render_template, request, redirect, url_for, flash
from config.database import db
from app.models.product import Product, ProductImage, ProductStock
from app.models.store import Store
from decimal import Decimal, InvalidOperation

products = Blueprint("products", __name__, url_prefix="/products")


@products.get('/')
def list_products():
    return render_template('/products/products.html')


@products.get("/new")
def new_product_form():
    return render_template('/products/add_products.html')


@products.post("/add")
def create_product():
    title = request.form.get("title")
    price_raw = request.form.get("price")
    description = request.form.get("description")
    store_id = request.form.get("store_id")
    image_url = request.form.get("image_url")

    # Validações mínimas
    if not title or not price_raw or not store_id:
        flash("Preencha título, preço e loja.")
        return redirect(url_for("products.new_product_form"))

    # Converter preço para Decimal
    try:
        price = Decimal(price_raw)
        if price < 0:
            raise InvalidOperation()
    except (InvalidOperation, TypeError):
        flash("Preço inválido.")
        return redirect(url_for("products.new_product_form"))

    # Verifica se a loja existe
    store = Store.query.get(store_id)
    if not store:
        flash("Loja não encontrada.")
        return redirect(url_for("products.new_product_form"))

    product = Product(
        title=title,
        price=price,
        description=description,
        store_id=store_id
    )

    try:
        db.session.add(product)
        db.session.flush()   # gera o ID antes do commit

        # Adicionar imagem (se houver)
        if image_url:
            image = ProductImage(
                product_id=product.id,
                url=image_url,
                position=0
            )
            db.session.add(image)

        # Criar estoque padrão
        stock = ProductStock(
            product_id=product.id,
            quantity=0,
            reserved_quantity=0
        )
        db.session.add(stock)

        db.session.commit()
        flash("Produto adicionado com sucesso.")
    except Exception as exc:
        db.session.rollback()
        # Log no console para depuração local
        print("Erro ao adicionar produto:", exc)
        flash("Erro ao adicionar produto. Verifique os logs.")
        return redirect(url_for("products.new_product_form"))

    return redirect(url_for("products.list_products"))


@products.get('/delete')
def delete_products():
    return render_template('/products/products.html')


@products.get('/update')
def update():
    return render_template('/products/products.html')