from dataclasses import dataclass
from datetime import date
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from secrets import token_bytes
import re

ROLES = {
    "client": "Покупатель",
    "admin": "Администратор",
    "director": "Директор",
    "picker": "Сборщик",
    "courier": "Курьер",
    "operator": "Оператор",
}
MANAGERS = ("admin", "director")
PASSWORD_ROUNDS = 310_000


def normalized_phone(value):
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        digits = "7" + digits
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    raise ValueError("Укажи телефон в формате +7 900 123-45-67.")


def password_hash(password):
    salt = token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
    return f"{PASSWORD_ROUNDS}${salt.hex()}${digest.hex()}"


def matches_password(password, encoded):
    rounds, salt, digest = encoded.split("$")
    candidate = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return compare_digest(candidate.hex(), digest)


def account_fields(values, role, creating):
    data = {
        field: values.get(field, "").strip()
        for field in ("surname", "name", "patronymic", "birthday", "email", "passport")
    }
    if not data["surname"] or not data["name"]:
        raise ValueError("Укажи имя и фамилию.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data["email"]):
        raise ValueError("Проверь адрес электронной почты.")
    data["email"] = data["email"].casefold()
    if date.fromisoformat(data["birthday"]) > date.today():
        raise ValueError("Дата рождения не может быть в будущем.")
    data["phone"] = normalized_phone(values.get("phone", ""))
    if role != "client" and not data["passport"]:
        raise ValueError("Укажи паспорт сотрудника.")
    if role == "client":
        data["passport"] = ""
    password = values.get("password", "")
    if creating or password:
        if len(password) < 8 or not password.strip():
            raise ValueError("Пароль должен содержать минимум 8 символов.")
        data["password_hash"] = password_hash(password)
    data["role"] = role
    return data


def full_name(person):
    return " ".join(filter(None, (person["surname"], person["name"], person["patronymic"])))


@dataclass
class Session:
    person: dict | None = None

    @property
    def role(self):
        return self.person["role"] if self.person else None

    @property
    def client_id(self):
        return self.person["id"] if self.role == "client" else None

    @property
    def is_staff(self):
        return self.role is not None and self.role != "client"
