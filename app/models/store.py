from datetime import datetime
from config.database import db

class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.String, primary_key=True)
    owner_id = db.Column(db.String, db.ForeignKey("users.id"))
    slug = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", back_populates="stores")
    customizations = db.relationship(
        "StoreCustomization", back_populates="store", uselist=False
    )
    categories = db.relationship("Category", back_populates="store")
    products = db.relationship("Product", back_populates="store")
    orders = db.relationship("Order", back_populates="store")


class StoreCustomization(db.Model):
    __tablename__ = "store_customizations"

    store_id = db.Column(db.String, db.ForeignKey("stores.id"), primary_key=True)
    primary_color = db.Column(db.String(7))
    secondary_color = db.Column(db.String(7))
    theme = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    store = db.relationship("Store", back_populates="customizations")
