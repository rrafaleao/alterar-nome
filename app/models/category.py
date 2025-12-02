from datetime import datetime
from config.database import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.String, primary_key=True)
    store_id = db.Column(db.String, db.ForeignKey("stores.id"))
    name = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False)
    parent_id = db.Column(db.String, db.ForeignKey("categories.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    store = db.relationship("Store", back_populates="categories")
    children = db.relationship("Category")
    products = db.relationship("Product", back_populates="category")
