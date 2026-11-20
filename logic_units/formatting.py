from datetime import datetime


def rubles(kopecks):
    rubles, remainder = divmod(int(kopecks), 100)
    main = f"{rubles:,}".replace(",", "\u202f")
    fraction = f",{remainder:02}" if remainder else ""
    return f"{main}{fraction}\u00a0₽"


def display_date(iso, with_time=False):
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def counted(number, one, few, many):
    word = many
    if not 11 <= number % 100 <= 14:
        if number % 10 == 1:
            word = one
        elif 2 <= number % 10 <= 4:
            word = few
    return f"{number} {word}"
