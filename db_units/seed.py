from datetime import date, datetime, time, timedelta

from logic_units.accounts import full_name, password_hash
from logic_units.catalog import CATEGORIES, COLLECTIONS
from logic_units.orders import PAYMENT_METHODS, STATUSES

WOMEN_SIZES = ("42", "44", "46", "48")
MEN_SIZES = ("46", "48", "50", "52")
SINGLE = ("Единый",)

PRODUCTS = {
    "women": (
        ("W01", "Куртки", "Шерстяной жакет Écru", "Шерсть", "Классика", 28900, None,
         ("Молочный", "Графитовый"), WOMEN_SIZES, ("new", "best"),
         "Укороченный двубортный жакет с широким воротником. Плотная шерсть держит форму, а гладкая подкладка позволяет носить жакет поверх трикотажа."),
        ("W02", "Платья", "Атласное платье Rive", "Шёлк", "Вечерний", 23900, None,
         ("Бордовый", "Чёрный"), WOMEN_SIZES, ("new", "limited"),
         "Платье миди со струящимся подолом и тонкими бретелями. Крой по косой даёт мягкое прилегание без лишних швов."),
        ("W03", "Блузки", "Шёлковая блуза Plissé", "Шёлк", "Классика", 15900, None,
         ("Молочный", "Голубой"), WOMEN_SIZES, ("new",),
         "Матовый шёлк, небольшой воротник и свободный рукав на высоком манжете. Спинка чуть длиннее переда."),
        ("W04", "Юбки", "Плиссированная юбка Sienne", "Шерсть", "Классика", 12900, 15900,
         ("Песочный", "Графитовый"), WOMEN_SIZES, ("sale",),
         "Юбка миди с высоким поясом и глубокими складками из тонкой костюмной шерсти. Молния спрятана в боковом шве."),
        ("W05", "Джинсы", "Прямые джинсы Minuit", "Деним", "Повседневный", 11900, None,
         ("Тёмно-синий",), WOMEN_SIZES, ("best",),
         "Прямые джинсы с высокой посадкой, пятью карманами и контрастной строчкой. Плотный деним без эластана."),
        ("W06", "Платья", "Трикотажное платье Ligne", "Вискоза", "Повседневный", 16900, 19900,
         ("Чёрный", "Бордовый"), WOMEN_SIZES, ("sale",),
         "Приталенное платье в мелкий рубчик с длинным рукавом. Эластичное полотно мягко ложится по фигуре."),
    ),
    "men": (
        ("M01", "Верхняя одежда", "Шерстяное пальто Prado", "Шерсть", "Классика", 38900, None,
         ("Тёмно-коричневый", "Графитовый"), MEN_SIZES, ("new", "best"),
         "Прямое однобортное пальто до колена с прорезными карманами. Внутри — гладкая подкладка и карман для документов."),
        ("M02", "Рубашки", "Рубашка Voile", "Хлопок", "Классика", 10900, None,
         ("Голубой", "Белый"), MEN_SIZES, ("new",),
         "Гладкий поплин с плотным переплетением. Прямой крой, потайное крепление воротника и регулируемые манжеты."),
        ("M03", "Брюки", "Брюки со складками Cadre", "Шерсть", "Классика", 14900, 17900,
         ("Графитовый", "Тёмно-синий"), MEN_SIZES, ("sale",),
         "Брюки из костюмной шерсти с двойной складкой у пояса и прямой стрелкой. Посадка средняя."),
        ("M04", "Обувь", "Кожаные лоферы Arco", "Натуральная кожа", "Классика", 22900, None,
         ("Тёмно-коричневый", "Чёрный"), ("40", "41", "42", "43", "44"), ("best",),
         "Лоферы из гладкой кожи с прошитым мысом. Мягкая кожаная стелька и невысокий каблук."),
        ("M05", "Футболки", "Хлопковая футболка Calme", "Хлопок", "Повседневный", 5900, 7400,
         ("Молочный", "Чёрный"), ("S", "M", "L", "XL"), ("sale",),
         "Базовая футболка из плотного хлопкового джерси. Свободный рукав и уплотнённая горловина."),
        ("M06", "Верхняя одежда", "Замшевый бомбер Dune", "Замша", "Повседневный", 35900, None,
         ("Оливковый", "Коричневый"), MEN_SIZES, ("new", "limited"),
         "Укороченный бомбер из бархатистой замши с металлической молнией. По краю рукавов и по низу — трикотажная резинка."),
    ),
    "accessories": (
        ("A01", "Клатчи", "Кожаный клатч Astre", "Натуральная кожа", "Вечерний", 19800, None,
         ("Бордовый", "Чёрный"), SINGLE, ("new", "best"),
         "Прямоугольный клатч из гладкой кожи с застёжкой из матовой латуни. Внутри одно отделение и карман для карты."),
        ("A02", "Рюкзаки", "Кожаный рюкзак Ligne", "Натуральная кожа", "Повседневный", 27900, None,
         ("Тёмно-коричневый", "Чёрный"), SINGLE, ("best",),
         "Небольшой рюкзак с округлой спинкой, скрытым карманом и регулируемыми лямками."),
        ("A03", "Кошельки", "Складной кошелёк Port", "Натуральная кожа", "Классика", 8900, None,
         ("Чёрный", "Коньячный"), SINGLE, (),
         "Кошелёк из зернистой кожи. Внутри шесть ячеек для карт и отделение для купюр."),
        ("A04", "Ремни", "Кожаный ремень Boucle", "Натуральная кожа", "Классика", 7800, 9800,
         ("Коньячный", "Чёрный"), ("80", "85", "90", "95"), ("sale",),
         "Ремень шириной 30 мм с прямоугольной пряжкой из сатинированной латуни."),
        ("A05", "Очки", "Очки Sillage", "Ацетат", "Повседневный", 12400, None,
         ("Черепаховый", "Чёрный"), SINGLE, ("new",),
         "Очки с плотной прямоугольной оправой из ацетата и дымчатыми линзами."),
        ("A06", "Клатчи", "Овальный клатч Nacre", "Натуральная кожа", "Вечерний", 21600, None,
         ("Молочный",), SINGLE, ("new", "limited"),
         "Овальный клатч с изогнутым швом и потайной молнией. Мягкая кожа сохраняет объём благодаря внутренней вставке."),
    ),
    "jewelry": (
        ("J01", "Кольца", "Кольцо Onde", "Серебро с позолотой", "Вечерний", 13800, None,
         ("Золотой",), ("16", "17", "18"), ("new", "best"),
         "Широкое полированное кольцо с волнообразным контуром. Внутренняя поверхность гладкая, край скруглён."),
        ("J02", "Серьги", "Серьги Aube", "Серебро с позолотой", "Классика", 11900, None,
         ("Золотой", "Серебристый"), SINGLE, ("new",),
         "Небольшие объёмные полукольца с гладкой поверхностью и застёжкой-пусетой."),
        ("J03", "Подвески", "Подвеска Halo", "Жемчуг и серебро", "Вечерний", 15700, None,
         ("Золотой",), ("45 см", "50 см"), ("limited",),
         "Тёмная жемчужина на тонкой цепочке с позолотой. У цепочки два кольца для регулировки длины."),
        ("J04", "Браслеты", "Браслет Nœud", "Серебро", "Повседневный", 10400, None,
         ("Серебристый",), ("S", "M"), (),
         "Открытый браслет из матового серебра с плавным изгибом по центру. Края тщательно отполированы."),
        ("J05", "Часы", "Наручные часы Tempo", "Сталь и кожа", "Классика", 26500, None,
         ("Чёрный",), SINGLE, ("new", "limited"),
         "Кварцевые часы с прямоугольным корпусом, кремовым циферблатом и чёрным кожаным ремешком."),
        ("J06", "Кольца", "Перстень Silex", "Серебро и оникс", "Вечерний", 15600, 18400,
         ("Серебристый",), ("17", "18", "19", "20"), ("sale",),
         "Перстень из сатинированного серебра с плоской овальной вставкой из чёрного оникса."),
    ),
}

DEMO_PEOPLE = (
    ("client", "Волкова", "Алиса", "Романовна", "1998-05-17", "0000000001", "alisa"),
    ("client", "Левин", "Илья", "Павлович", "1994-09-26", "0000000002", "ilya"),
    ("client", "Миронова", "Нина", "Денисовна", "2000-02-11", "0000000003", "nina"),
    ("client", "Савин", "Антон", "Михайлович", "1992-12-08", "0000000004", "anton"),
    ("client", "Рощина", "Вера", "", "1997-07-23", "0000000005", "vera"),
    ("admin", "Орлова", "Софья", "Максимовна", "1995-03-14", "0000000101", "admin"),
    ("director", "Романов", "Артём", "Игоревич", "1989-10-19", "0000000102", "director"),
    ("picker", "Ким", "Марк", "Андреевич", "2001-01-28", "0000000103", "picker"),
    ("courier", "Ветров", "Дамир", "Олегович", "1996-04-21", "0000000104", "courier"),
    ("operator", "Лукина", "Ева", "Викторовна", "2000-08-05", "0000000105", "operator"),
)


def seed_catalog(db):
    for category, (name, groups) in CATEGORIES.items():
        db.execute("INSERT INTO categories VALUES (?, ?)", (category, name))
        db.executemany(
            "INSERT INTO subcategories(category_id, name) VALUES (?, ?)",
            [(category, group) for group in groups],
        )
    db.executemany("INSERT INTO collections VALUES (?, ?)", COLLECTIONS.items())
    for category, products in PRODUCTS.items():
        subcategories = {
            row["name"]: row["id"] for row in db.execute(
                "SELECT id, name FROM subcategories WHERE category_id = ?", (category,)
            )
        }
        for row in products:
            code, group, name, material, style, price, previous, colors, sizes, collections, description = row
            sku = f"EL-{code}"
            product_id = db.execute(
                """INSERT INTO products
                   (sku, subcategory_id, name, description, material, style, image, photo_color)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sku, subcategories[group], name, description, material, style,
                 f"products/{sku}.jpg", colors[0]),
            ).lastrowid
            for color_index, color in enumerate(colors):
                for size_index, size in enumerate(sizes):
                    stock = (product_id + 2 * size_index + color_index) % 7 + 5
                    if color_index == 1 and (product_id + size_index) % 5 == 0:
                        stock = 0
                    db.execute(
                        """INSERT INTO variants (product_id, size, color, price, previous_price, stock)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (product_id, size, color, price * 100, previous * 100 if previous else None, stock),
                    )
            db.executemany(
                "INSERT INTO collection_products VALUES (?, ?)",
                [(collection, product_id) for collection in collections],
            )


def seed_people(db):
    for index, person in enumerate(DEMO_PEOPLE, start=1):
        role, surname, name, patronymic, birthday, phone, email = person
        password = "ElaraClient26" if role == "client" else "ElaraStaff26"
        db.execute(
            """INSERT INTO people
               (role, surname, name, patronymic, birthday, phone, email, password_hash, passport)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (role, surname, name, patronymic, birthday, "+7" + phone,
             f"{email}@example.test", password_hash(password),
             f"ДЕМО {index:06}" if role != "client" else ""),
        )


def seed_orders(db, insert_order):
    clients = db.execute("SELECT * FROM people WHERE role = 'client' ORDER BY id").fetchall()
    catalog = db.execute("SELECT id FROM products ORDER BY id").fetchall()
    today = date.today()
    days_back = (0, 0, 0, 1, 2, 3, 4, 5, 5, 7, 8, 9, 11, 13, 13, 15, 17,
                 19, 22, 25, 27, 29, 33, 35, 37, 42, 45, 52)
    addresses = (
        "Москва, ул. Макетная, 4, кв. 12",
        "Москва, пер. Тканевый, 8, кв. 21",
        "Москва, ул. Студийная, 13, кв. 6",
        "Москва, пер. Палитры, 3, кв. 40",
        "Москва, ул. Эскизная, 16, кв. 7",
    )
    for index in reversed(range(len(days_back))):
        client = clients[index % len(clients)]
        created = datetime.combine(
            today - timedelta(days=days_back[index]), time(9 + index % 8, index * 7 % 60)
        )
        recent = (STATUSES[0], STATUSES[1], STATUSES[0], STATUSES[2], STATUSES[3])
        if index < len(recent):
            status = recent[index]
        else:
            status = STATUSES[-1] if index in (8, 18) else STATUSES[-2]
        items = []
        for offset in range(1 + index % 3):
            product_id = catalog[(index * 7 + offset * 5) % len(catalog)]["id"]
            item = db.execute(
                """SELECT v.id AS variant_id, p.id AS product_id, v.size, v.color, v.price,
                          p.sku, p.name, c.name AS category, s.name AS subcategory
                   FROM variants v JOIN products p ON p.id = v.product_id
                   JOIN subcategories s ON s.id = p.subcategory_id
                   JOIN categories c ON c.id = s.category_id
                   WHERE v.product_id = ? AND v.stock >= 2
                   ORDER BY v.stock DESC, v.id LIMIT 1""",
                (product_id,),
            ).fetchone()
            items.append(dict(item) | {"quantity": 2 if index % 5 == 0 else 1})
        insert_order(
            db, client["id"], full_name(client), client["phone"], created.isoformat(timespec="seconds"),
            addresses[index % len(addresses)], PAYMENT_METHODS[index % 3], items,
            status, "Не оплачен" if status == STATUSES[-1] or index % 7 == 0 else "Оплачен",
        )

    now = datetime.now().isoformat(timespec="seconds")
    db.executemany("INSERT INTO favorites VALUES (?, ?, ?)", [(clients[0]["id"], item, now) for item in (1, 2, 13)])
