-- Habilita o uso de UTF8
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- USERS
CREATE TABLE users (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name VARCHAR(255),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_seller BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email)
);

-- STORES
CREATE TABLE stores (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  owner_id CHAR(36) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  logo_url TEXT,
  is_published BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE (owner_id, slug),
  INDEX idx_stores_slug (slug),
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

-- STORE CUSTOMIZATIONS
CREATE TABLE store_customizations (
  store_id CHAR(36) PRIMARY KEY,
  primary_color VARCHAR(7),
  secondary_color VARCHAR(7),
  theme JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

-- CATEGORIES
CREATE TABLE categories (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  store_id CHAR(36) NOT NULL,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  parent_id CHAR(36),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE (store_id, slug),
  INDEX idx_categories_store (store_id),
  FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- PRODUCTS
CREATE TABLE products (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  store_id CHAR(36) NOT NULL,
  category_id CHAR(36),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  sku VARCHAR(255),
  price DECIMAL(12,2) NOT NULL CHECK (price >= 0),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_products_store (store_id),
  FULLTEXT INDEX idx_products_title_fulltext (title, description),
  FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- PRODUCT IMAGES
CREATE TABLE product_images (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  product_id CHAR(36) NOT NULL,
  url TEXT NOT NULL,
  position INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- PRODUCT STOCK
CREATE TABLE product_stocks (
  product_id CHAR(36) PRIMARY KEY,
  quantity INT NOT NULL DEFAULT 0,
  reserved_quantity INT NOT NULL DEFAULT 0,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- CARTS
CREATE TABLE carts (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  user_id CHAR(36),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_cart_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- CART ITEMS
CREATE TABLE cart_items (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  cart_id CHAR(36),
  product_id CHAR(36),
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(12,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);

-- ADDRESSES
CREATE TABLE addresses (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  user_id CHAR(36),
  line1 TEXT,
  line2 TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ORDER STATUS ENUM
CREATE TABLE order_status_enum (
  status ENUM('pending','paid','shipped','delivered','cancelled','refunded')
);

-- ORDERS
CREATE TABLE orders (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  store_id CHAR(36) NOT NULL,
  user_id CHAR(36),
  total_amount DECIMAL(12,2) NOT NULL,
  status ENUM('pending','paid','shipped','delivered','cancelled','refunded') DEFAULT 'pending',
  shipping_address_id CHAR(36),
  placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  metadata JSON,
  INDEX idx_orders_user (user_id),
  INDEX idx_orders_store_status (store_id, status),
  FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (shipping_address_id) REFERENCES addresses(id)
);

-- ORDER ITEMS
CREATE TABLE order_items (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  order_id CHAR(36) NOT NULL,
  product_id CHAR(36),
  title VARCHAR(255) NOT NULL,
  sku VARCHAR(255),
  unit_price DECIMAL(12,2) NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  total_price DECIMAL(12,2) AS (unit_price * quantity),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- PAYMENTS
CREATE TABLE payments (
  id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  order_id CHAR(36) UNIQUE,
  method VARCHAR(255),
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('created','authorized','captured','failed','refunded') DEFAULT 'created',
  payment_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

SET FOREIGN_KEY_CHECKS = 1;
