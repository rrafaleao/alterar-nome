from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from config.database import db
import uuid

products = Blueprint("products", __name__, url_prefix="/products")

@products.get('/')
def list_products():
    return render_template('/products/products.html')





@products.get("/new")
def new_product_form():
    return render_template('/products/add_products.html')



@products.get('/delete')
def delete_products():
    return render_template('/products/products.html')

@products.get('/update')
def update():
    return render_template('/products/products.html')