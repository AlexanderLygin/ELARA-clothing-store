from datetime import date, timedelta

ORDER_SUMS = """
    SELECT o.*, substr(o.created_at, 1, 10) AS day,
           COALESCE((SELECT SUM(i.quantity) FROM order_items i WHERE i.order_id = o.id), 0) AS units,
           CASE WHEN o.payment_status = 'Оплачен' THEN o.total ELSE 0 END AS paid
    FROM orders o WHERE o.status != 'Отменён'
"""
PAID_ITEMS = "SUM(CASE WHEN o.payment_status = 'Оплачен' THEN i.quantity * i.price ELSE 0 END)"
RANGE = "o.created_at >= ? AND o.created_at < date(?, '+1 day')"


class Reports:
    def __init__(self, db):
        self.db = db

    def sales(self, first, last):
        return self.db.rows(
            f"""WITH totals AS ({ORDER_SUMS} AND {RANGE})
                SELECT day AS label, COUNT(*) AS orders, SUM(units) AS units, SUM(paid) AS revenue
                FROM totals GROUP BY day ORDER BY day""",
            (first, last),
        )

    def revenue(self, period, first, last):
        expression = {
            "day": "day",
            "week": "strftime('%Y / %W', created_at)",
            "month": "strftime('%Y-%m', created_at)",
            "year": "strftime('%Y', created_at)",
        }[period]
        return self.db.rows(
            f"""WITH totals AS ({ORDER_SUMS} AND {RANGE})
                SELECT {expression} AS label, SUM(paid) AS revenue, COUNT(*) AS orders,
                       SUM(units) AS units
                FROM totals GROUP BY label ORDER BY label""",
            (first, last),
        )

    def categories(self, first, last):
        return self.db.rows(
            f"""SELECT i.category AS label, i.subcategory, COUNT(DISTINCT o.id) AS orders,
                       SUM(i.quantity) AS units, {PAID_ITEMS} AS revenue
                FROM order_items i JOIN orders o ON o.id = i.order_id
                WHERE o.status != 'Отменён' AND {RANGE}
                GROUP BY i.category, i.subcategory ORDER BY revenue DESC, units DESC""",
            (first, last),
        )

    def daily(self, day):
        return self.db.row(
            f"""WITH totals AS ({ORDER_SUMS} AND {RANGE})
                SELECT COUNT(*) AS orders, COALESCE(SUM(paid), 0) AS revenue,
                       COALESCE(AVG(CASE WHEN payment_status = 'Оплачен' THEN paid END), 0) AS average,
                       COUNT(DISTINCT CASE WHEN client_id IS NULL THEN phone ELSE client_id END) AS clients,
                       COALESCE(SUM(units), 0) AS units,
                       COUNT(CASE WHEN status = 'Новый' THEN 1 END) AS new_orders,
                       COUNT(CASE WHEN status = 'Доставлен' THEN 1 END) AS completed
                FROM totals""",
            (day, day),
        )

    def top(self, limit, days):
        today = date.today()
        return self.db.rows(
            f"""SELECT COALESCE(p.sku, MAX(i.sku)) AS sku,
                       COALESCE(p.name, MAX(i.name)) AS name, MAX(i.category) AS category,
                       COUNT(DISTINCT o.id) AS orders, SUM(i.quantity) AS units, {PAID_ITEMS} AS revenue
                FROM order_items i JOIN orders o ON o.id = i.order_id
                LEFT JOIN products p ON p.id = i.product_id
                WHERE o.status != 'Отменён' AND {RANGE}
                GROUP BY i.product_id, CASE WHEN i.product_id IS NULL THEN i.sku END
                ORDER BY units DESC, revenue DESC, sku LIMIT ?""",
            (today - timedelta(days=days - 1), today, limit),
        )

    def compare(self, skus, first, last):
        if not skus:
            return []
        markers = ", ".join("?" for _ in skus)
        return self.db.rows(
            f"""WITH sales AS (
                    SELECT i.product_id, COUNT(DISTINCT o.id) AS orders, SUM(i.quantity) AS units,
                           {PAID_ITEMS} AS revenue
                    FROM order_items i JOIN orders o ON o.id = i.order_id
                    WHERE o.status != 'Отменён' AND {RANGE}
                    GROUP BY i.product_id
                )
                SELECT p.sku AS label, p.name, COALESCE(sales.orders, 0) AS orders,
                       COALESCE(sales.units, 0) AS units, COALESCE(sales.revenue, 0) AS revenue
                FROM products p LEFT JOIN sales ON sales.product_id = p.id
                WHERE p.sku IN ({markers})
                ORDER BY revenue DESC, units DESC, p.sku""",
            (first, last, *skus),
        )
