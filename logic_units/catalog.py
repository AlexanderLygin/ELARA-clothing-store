from dataclasses import dataclass

CATEGORIES = {
    "women": ("Женское", ("Платья", "Юбки", "Блузки", "Джинсы", "Куртки")),
    "men": ("Мужское", ("Брюки", "Рубашки", "Обувь", "Верхняя одежда", "Футболки")),
    "accessories": (
        "Сумки и аксессуары", ("Клатчи", "Рюкзаки", "Кошельки", "Ремни", "Очки")
    ),
    "jewelry": ("Украшения", ("Кольца", "Серьги", "Подвески", "Браслеты", "Часы")),
}
COLLECTIONS = {
    "new": "Новая коллекция",
    "limited": "Лимитированная серия",
    "sale": "Скидки",
    "best": "Бестселлеры",
}
SORTS = {
    "default": "По умолчанию",
    "price_up": "Сначала дешевле",
    "price_down": "Сначала дороже",
    "name_up": "Название А–Я",
    "name_down": "Название Я–А",
}

COLORS = {
    "Молочный": "#eee4d2",
    "Чёрный": "#262223",
    "Графитовый": "#575355",
    "Тёмно-синий": "#313c55",
    "Бордовый": "#6d2938",
    "Песочный": "#c5a585",
    "Коричневый": "#684233",
    "Коньячный": "#985e3c",
    "Тёмно-коричневый": "#452e29",
    "Голубой": "#aabccf",
    "Оливковый": "#717056",
    "Черепаховый": "#9d6639",
    "Золотой": "#c9a666",
    "Серебристый": "#bfc0bd",
    "Розовое золото": "#c28c7c",
    "Красный": "#9d3441",
    "Белый": "#f6f4ed",
}


@dataclass
class CatalogFilter:
    query: str = ""
    category: str = ""
    subcategory: str = ""
    collection: str = ""
    material: str = ""
    style: str = ""
    minimum: int = 0
    maximum: int | None = None
    in_stock: bool = False
    sort: str = "default"

    def is_filtered(self):
        return bool(
            self.material or self.style or self.minimum
            or self.maximum is not None or self.in_stock
        )
