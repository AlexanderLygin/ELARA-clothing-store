from contextlib import closing
from datetime import datetime
import json
import sqlite3

from logic_units.accounts import account_fields, full_name, matches_password, normalized_phone
from logic_units.catalog import CatalogFilter
from logic_units.orders import PAYMENT_METHODS, PAYMENT_STATUSES, STATUSES, STATUS_BY_ROLE
from logic_units.paths import ROOT

PEOPLE_FIELDS = "id, role, surname, name, patronymic, birthday, phone, email, passport"
PRODUCT_FIELDS = """
    p.*, s.name AS subcategory, c.id AS category_id, c.name AS category
"""
PRODUCT_TABLES = """
    products p JOIN subcategories s ON s.id = p.subcategory_id
    JOIN categories c ON c.id = s.category_id
"""
CART_ROWS = """
    SELECT cart.quantity, v.id AS variant_id, v.size, v.color, v.price, v.stock,
           p.id AS product_id, p.sku, p.name, p.image, c.name AS category, s.name AS subcategory
    FROM cart JOIN variants v ON v.id = cart.variant_id
    JOIN products p ON p.id = v.product_id
    JOIN subcategories s ON s.id = p.subcategory_id
    JOIN categories c ON c.id = s.category_id
    WHERE cart.client_id = ?
    ORDER BY cart.rowid
"""


def fold(text):
    return str(text or "").casefold().replace("ё", "е")


def insert_order(db, client_id, customer, phone, created, address, method, items, status, payment):
    total = sum(item["price"] * item["quantity"] for item in items)
    order_id = db.execute(
        """INSERT INTO orders
           (client_id, customer, phone, created_at, total, address, payment_method, payment_status, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, customer, phone, created, total, address, method, payment, status),
    ).lastrowid
    keys = (
        "variant_id", "product_id", "sku", "name", "category", "subcategory", "size", "color",
        "price", "quantity",
    )
    for item in items:
        if status != STATUSES[-1]:
            updated = db.execute(
                "UPDATE variants SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (item["quantity"], item["variant_id"], item["quantity"]),
            )
            if not updated.rowcount:
                raise ValueError(f"Недостаточно на складе: {item['name']}.")
        db.execute(
            """INSERT INTO order_items
               (order_id, variant_id, product_id, sku, name, category, subcategory, size, color, price, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, *(item[k] for k in keys)),
        )
    return order_id


class Database:
    def __init__(self, path=ROOT / "db_units" / "elara.sqlite3"):
        self.path = str(path)
        self.initialize()

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.create_function("fold", 1, fold, deterministic=True)
        return db

    def initialize(self):
        from db_units.seed import seed_catalog, seed_orders, seed_people

        with closing(self.connect()) as db, db:
            if db.execute("PRAGMA user_version").fetchone()[0] == 1:
                return
            db.executescript((ROOT / "db_units" / "schema.sql").read_text(encoding="utf-8"))
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] == 0:
                seed_catalog(db)
                seed_people(db)
                seed_orders(db, insert_order)
                db.execute("PRAGMA user_version = 1")

    def rows(self, sql, params=()):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute(sql, params)]

    def row(self, sql, params=()):
        with closing(self.connect()) as db:
            result = db.execute(sql, params).fetchone()
            return dict(result) if result else None

    def authenticate(self, phone, password):
        try:
            phone = normalized_phone(phone)
        except ValueError:
            return None
        person = self.row(
            f"SELECT {PEOPLE_FIELDS}, password_hash FROM people WHERE phone = ?", (phone,)
        )
        if person and matches_password(password, person.pop("password_hash")):
            return person
        return None

    def person(self, person_id):
        return self.row(f"SELECT {PEOPLE_FIELDS} FROM people WHERE id = ?", (person_id,))

    def people(self, staff=False, query="", fields=None):
        conditions = ["role " + ("!=" if staff else "=") + " 'client'"]
        params = []
        if query.strip():
            conditions.append(
                """instr(fold(id || ' ' || surname || ' ' || name || ' ' || patronymic
                            || ' ' || phone || ' ' || email), ?) > 0"""
            )
            params.append(fold(query.strip()))
        for column, value in (fields or {}).items():
            if value and column in ("id", "name", "surname", "patronymic", "phone", "email", "role"):
                if column in ("id", "role"):
                    conditions.append(f"{column} = ?")
                    params.append(value)
                else:
                    conditions.append(f"instr(fold({column}), ?) > 0")
                    params.append(fold(value))
        return self.rows(
            f"SELECT {PEOPLE_FIELDS} FROM people WHERE {' AND '.join(conditions)} ORDER BY fold(surname), fold(name)",
            params,
        )

    def save_person(self, values, role="client", person_id=None):
        data = account_fields(values, role, creating=person_id is None)
        try:
            with closing(self.connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                if person_id is not None:
                    current = db.execute("SELECT role FROM people WHERE id = ?", (person_id,)).fetchone()
                    if not current:
                        raise ValueError("Аккаунт уже удалён.")
                    if current["role"] == "admin" and role != "admin":
                        self.check_other_admin(db, person_id)
                    fields = ", ".join(f"{key} = ?" for key in data)
                    db.execute(f"UPDATE people SET {fields} WHERE id = ?", (*data.values(), person_id))
                else:
                    fields = ", ".join(data)
                    marks = ", ".join("?" for _ in data)
                    person_id = db.execute(
                        f"INSERT INTO people ({fields}) VALUES ({marks})", tuple(data.values())
                    ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("Этот телефон или email уже используется.") from exc
        return self.person(person_id)

    @staticmethod
    def check_other_admin(db, person_id):
        if not db.execute(
            "SELECT 1 FROM people WHERE role = 'admin' AND id != ?", (person_id,)
        ).fetchone():
            raise ValueError("В магазине должен остаться хотя бы один администратор.")

    def delete_person(self, person_id):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            person = db.execute("SELECT role FROM people WHERE id = ?", (person_id,)).fetchone()
            if person and person["role"] == "admin":
                self.check_other_admin(db, person_id)
            db.execute("DELETE FROM people WHERE id = ?", (person_id,))

    def products(self, filters=None, favorites_of=None, fields=None, limit=None):
        filters = filters or CatalogFilter()
        fields = fields or {}
        conditions, params = [], []
        exact = {
            "c.id": filters.category, "s.name": filters.subcategory, "p.material": filters.material,
            "p.style": filters.style,
        }
        for column, value in exact.items():
            if value:
                conditions.append(f"{column} = ?")
                params.append(value)
        if filters.query.strip():
            conditions.append(
                """instr(fold(p.sku || ' ' || p.name || ' ' || p.description || ' ' ||
                         p.material || ' ' || p.style || ' ' || s.name || ' ' || c.name), ?) > 0"""
            )
            params.append(fold(filters.query.strip()))
        if filters.collection:
            conditions.append(
                "EXISTS (SELECT 1 FROM collection_products WHERE product_id = p.id AND collection_id = ?)"
            )
            params.append(filters.collection)
        if favorites_of is not None:
            conditions.append("EXISTS (SELECT 1 FROM favorites WHERE product_id = p.id AND client_id = ?)")
            params.append(favorites_of)
        for field in ("name", "material", "style", "sku"):
            if fields.get(field):
                conditions.append(f"instr(fold(p.{field}), ?) > 0")
                params.append(fold(fields[field]))
        if filters.minimum:
            conditions.append("v.price >= ?")
            params.append(filters.minimum)
        if filters.maximum is not None:
            conditions.append("v.price <= ?")
            params.append(filters.maximum)
        if filters.in_stock:
            conditions.append("v.stock > 0")

        orders = {
            "price_up": "price ASC", "price_down": "price DESC",
            "name_up": "fold(p.name) ASC", "name_down": "fold(p.name) DESC",
        }
        order = orders.get(filters.sort, "p.id")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        tail = ""
        if limit:
            tail = "LIMIT ?"
            params.append(limit)
        items = self.rows(
            f"""SELECT {PRODUCT_FIELDS}, MIN(v.price) AS price, MAX(v.price) AS maximum_price,
                       CASE WHEN COUNT(v.previous_price) = COUNT(*) THEN MIN(v.previous_price) END AS previous_price,
                       SUM(v.stock) AS stock, json_group_array(DISTINCT v.color) AS colors
                FROM {PRODUCT_TABLES} JOIN variants v ON v.product_id = p.id
                {where}
                GROUP BY p.id ORDER BY {order}, p.id {tail}""", params,
        )
        for item in items:
            item["colors"] = json.loads(item["colors"])
            if item["photo_color"] in item["colors"]:
                item["colors"].remove(item["photo_color"])
                item["colors"].insert(0, item["photo_color"])
        return items

    def product(self, product_id):
        return self.row(f"SELECT {PRODUCT_FIELDS} FROM {PRODUCT_TABLES} WHERE p.id = ?", (product_id,))

    def variants(self, product_id):
        return self.rows("SELECT * FROM variants WHERE product_id = ? ORDER BY id", (product_id,))

    def product_collections(self, product_id):
        return {
            row["collection_id"] for row in self.rows(
                "SELECT collection_id FROM collection_products WHERE product_id = ?", (product_id,)
            )
        }

    def save_product(self, product, variants, collections, product_id=None):
        required = ("sku", "name", "description", "material", "style")
        if any(not product[key] for key in required) or not variants:
            raise ValueError("Заполни данные товара и добавь хотя бы один вариант.")
        keys = set()
        for variant in variants:
            size, color, price, previous, stock = variant
            key = (fold(size), fold(color))
            if not size or not color or price <= 0 or stock < 0:
                raise ValueError("Проверь размер, цвет, цену и остаток каждого варианта.")
            if previous is not None and previous <= price:
                raise ValueError("Старая цена должна быть больше текущей.")
            if key in keys:
                raise ValueError("Варианты размера и цвета должны быть уникальны.")
            keys.add(key)

        try:
            with closing(self.connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                group = db.execute(
                    "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
                    (product["category_id"], product["subcategory"]),
                ).fetchone()
                if not group:
                    raise ValueError("Выбери категорию и подкатегорию.")
                if product_id is not None:
                    current = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
                    if not current:
                        raise ValueError("Товар уже удалён.")
                values = (*[product[key] for key in required], product["image"], product["photo_color"], group["id"])
                if product_id is None:
                    product_id = db.execute(
                        """INSERT INTO products
                           (sku, name, description, material, style, image, photo_color, subcategory_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", values,
                    ).lastrowid
                else:
                    db.execute(
                        """UPDATE products SET sku = ?, name = ?, description = ?, material = ?,
                           style = ?, image = ?, photo_color = ?, subcategory_id = ? WHERE id = ?""",
                        (*values, product_id),
                    )
                current = {
                    (fold(row["size"]), fold(row["color"])): row["id"]
                    for row in db.execute("SELECT id, size, color FROM variants WHERE product_id = ?", (product_id,))
                }
                for key, variant_id in current.items():
                    if key not in keys:
                        db.execute("DELETE FROM variants WHERE id = ?", (variant_id,))
                for variant in variants:
                    existing_id = current.get((fold(variant[0]), fold(variant[1])))
                    if existing_id is None:
                        db.execute(
                            """INSERT INTO variants (size, color, price, previous_price, stock, product_id)
                               VALUES (?, ?, ?, ?, ?, ?)""", (*variant, product_id),
                        )
                    else:
                        db.execute(
                            """UPDATE variants SET size = ?, color = ?, price = ?, previous_price = ?,
                               stock = ? WHERE id = ?""", (*variant, existing_id),
                        )
                db.execute("DELETE FROM collection_products WHERE product_id = ?", (product_id,))
                db.executemany(
                    "INSERT INTO collection_products VALUES (?, ?)",
                    [(collection, product_id) for collection in collections],
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Такой артикул уже есть. Проверь данные товара.") from exc
        return product_id

    def delete_product(self, product_id):
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def favorites(self, client_id):
        if client_id is None:
            return set()
        return {row["product_id"] for row in self.rows(
            "SELECT product_id FROM favorites WHERE client_id = ?", (client_id,)
        )}

    def toggle_favorite(self, client_id, product_id):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            removed = db.execute(
                "DELETE FROM favorites WHERE client_id = ? AND product_id = ?", (client_id, product_id)
            ).rowcount
            if removed:
                return False
            if not db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
                raise ValueError("Товар уже удалён.")
            db.execute(
                "INSERT INTO favorites VALUES (?, ?, ?)",
                (client_id, product_id, datetime.now().isoformat(timespec="seconds")),
            )
            return True

    def cart(self, client_id):
        return self.rows(CART_ROWS, (client_id,))

    def cart_quantity(self, client_id):
        return self.row(
            "SELECT COALESCE(SUM(quantity), 0) AS count FROM cart WHERE client_id = ?", (client_id,)
        )["count"]

    def set_cart_quantity(self, client_id, variant_id, quantity, add=False):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT quantity FROM cart WHERE client_id = ? AND variant_id = ?", (client_id, variant_id)
            ).fetchone()
            previous = current["quantity"] if current else 0
            if add:
                quantity += previous
            if quantity <= 0:
                db.execute("DELETE FROM cart WHERE client_id = ? AND variant_id = ?", (client_id, variant_id))
                return
            variant = db.execute("SELECT stock FROM variants WHERE id = ?", (variant_id,)).fetchone()
            if not variant:
                raise ValueError("Этот вариант больше недоступен.")
            if quantity > variant["stock"] and quantity > previous:
                raise ValueError(
                    f"В наличии {variant['stock']} шт. В корзине уже {previous} шт."
                )
            db.execute(
                """INSERT INTO cart(client_id, variant_id, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(client_id, variant_id) DO UPDATE SET quantity = excluded.quantity""",
                (client_id, variant_id, quantity),
            )

    def checkout(self, client_id, address, method, shown_items):
        if not address.strip():
            raise ValueError("Укажи адрес доставки.")
        if method not in PAYMENT_METHODS:
            raise ValueError("Выбери способ оплаты.")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            items = db.execute(CART_ROWS, (client_id,)).fetchall()
            if not items:
                raise ValueError("Корзина пуста.")
            keys = ("variant_id", "quantity", "price")
            current = [tuple(item[key] for key in keys) for item in items]
            expected = [tuple(item[key] for key in keys) for item in shown_items]
            if current != expected:
                raise ValueError("Корзина изменилась. Проверь состав и итоговую сумму.")
            person = db.execute(
                "SELECT * FROM people WHERE id = ? AND role = 'client'", (client_id,)
            ).fetchone()
            if not person:
                raise ValueError("Для заказа нужен аккаунт покупателя.")
            order_id = insert_order(
                db, client_id, full_name(person), person["phone"], datetime.now().isoformat(timespec="seconds"),
                address.strip(), method, items, STATUSES[0], PAYMENT_STATUSES[1],
            )
            db.execute("DELETE FROM cart WHERE client_id = ?", (client_id,))
            return order_id

    def orders(self, client_id=None, query="", fields=None):
        conditions, params = [], []
        if client_id is not None:
            conditions.append("client_id = ?")
            params.append(client_id)
        if query.strip():
            conditions.append("instr(fold(id || ' ' || customer || ' ' || phone || ' ' || address), ?) > 0")
            params.append(fold(query.strip()))
        for key, value in (fields or {}).items():
            if not value:
                continue
            if key in ("id", "status", "payment_status"):
                conditions.append(f"{key} = ?")
                params.append(value)
            elif key in ("customer", "phone"):
                conditions.append(f"instr(fold({key}), ?) > 0")
                params.append(fold(value))
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.rows(f"SELECT * FROM orders {where} ORDER BY created_at DESC, id DESC", params)

    def order(self, order_id):
        return self.row("SELECT * FROM orders WHERE id = ?", (order_id,))

    def order_items(self, order_id):
        return self.rows("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,))

    @staticmethod
    def adjust_order_stock(db, order_id, restock):
        for item in db.execute(
            "SELECT variant_id, quantity, name FROM order_items WHERE order_id = ?", (order_id,)
        ):
            if restock:
                db.execute(
                    "UPDATE variants SET stock = stock + ? WHERE id = ?", (item["quantity"], item["variant_id"])
                )
            else:
                updated = db.execute(
                    "UPDATE variants SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (item["quantity"], item["variant_id"], item["quantity"]),
                )
                if not updated.rowcount:
                    raise ValueError(f"Нельзя возобновить заказ: {item['name']} больше нет в наличии.")

    def change_order(self, order_id, role, status, payment=None):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not current:
                raise ValueError("Заказ уже удалён.")
            if role not in STATUS_BY_ROLE or (status != current["status"] and status not in STATUS_BY_ROLE[role]):
                raise ValueError("Твоя должность не позволяет установить этот статус.")
            if payment is not None and (role not in ("admin", "director") or payment not in PAYMENT_STATUSES):
                raise ValueError("Нельзя изменить статус оплаты.")
            cancelled = STATUSES[-1]
            if (status == cancelled) != (current["status"] == cancelled):
                self.adjust_order_stock(db, order_id, restock=status == cancelled)
            db.execute(
                "UPDATE orders SET status = ?, payment_status = COALESCE(?, payment_status) WHERE id = ?",
                (status, payment, order_id),
            )

    def delete_order(self, order_id):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
            if order and order["status"] not in (STATUSES[-1], STATUSES[-2]):
                self.adjust_order_stock(db, order_id, restock=True)
            db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
