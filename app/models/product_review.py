from datetime import datetime

from config.database import db
from .utils import uuid4_str


class ProductReview(db.Model):
    __tablename__ = "product_reviews"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey("store_customers.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(
        db.Enum("reviewed", "not_received", name="product_review_status"),
        nullable=False,
        default="reviewed",
    )
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = db.relationship("Store", backref=db.backref("product_reviews", lazy="dynamic"))
    customer = db.relationship("StoreCustomer", backref=db.backref("product_reviews", lazy="dynamic"))
    product = db.relationship("Product", backref=db.backref("reviews", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("order_id", "customer_id", "product_id", name="unique_order_customer_product_review"),
        db.Index("idx_product_reviews_store", "store_id"),
        db.Index("idx_product_reviews_product", "product_id"),
        db.Index("idx_product_reviews_customer", "customer_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "status": self.status,
            "rating": int(self.rating) if self.rating is not None else None,
            "comment": self.comment,
            "customer_name": self.customer.full_name if self.customer else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }