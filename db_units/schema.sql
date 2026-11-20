CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS subcategories (
    id INTEGER PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES categories(id),
    name TEXT NOT NULL,
    UNIQUE (category_id, name)
);

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('client', 'admin', 'director', 'picker', 'courier', 'operator')),
    surname TEXT NOT NULL,
    name TEXT NOT NULL,
    patronymic TEXT NOT NULL DEFAULT '',
    birthday TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    passport TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    subcategory_id INTEGER NOT NULL REFERENCES subcategories(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    material TEXT NOT NULL,
    style TEXT NOT NULL,
    image TEXT NOT NULL DEFAULT '',
    photo_color TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS collection_products (
    collection_id TEXT NOT NULL REFERENCES collections(id),
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    PRIMARY KEY (collection_id, product_id)
);

CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size TEXT NOT NULL,
    color TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    previous_price INTEGER CHECK (previous_price > price),
    UNIQUE (product_id, size, color)
);

CREATE TABLE IF NOT EXISTS favorites (
    client_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    added_at TEXT NOT NULL,
    PRIMARY KEY (client_id, product_id)
);

CREATE TABLE IF NOT EXISTS cart (
    client_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    variant_id INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (client_id, variant_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    customer TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    total INTEGER NOT NULL CHECK (total >= 0),
    address TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES variants(id) ON DELETE SET NULL,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    size TEXT NOT NULL,
    color TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS products_subcategory ON products(subcategory_id);
CREATE INDEX IF NOT EXISTS orders_client ON orders(client_id);
CREATE INDEX IF NOT EXISTS orders_date ON orders(created_at);
CREATE INDEX IF NOT EXISTS order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS order_items_variant ON order_items(variant_id);
CREATE INDEX IF NOT EXISTS order_items_product ON order_items(product_id);
