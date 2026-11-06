"""Классы предметной области службы доставки"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from delivery.exceptions import InvalidDataError, InvalidStatusError

# Имя: только буквы, слова разделяются одним пробелом или дефисом
NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[ -][^\W\d_]+)*$")
# Мобильный телефон: +79XXXXXXXXX или 89XXXXXXXXX (после удаления
# пробелов, дефисов и скобок)
PHONE_PATTERN = re.compile(r"^(?:\+7|8)(9\d{9})$")
# Госномер автомобиля РФ: А123ВС77 или А123ВС777.
# Используются только 12 русских букв, которые есть и в латинице
PLATE_LETTERS = "АВЕКМНОРСТУХ"
PLATE_PATTERN = re.compile(
    rf"^[{PLATE_LETTERS}]\d{{3}}[{PLATE_LETTERS}]{{2}}\d{{2,3}}$")
TRANSPORT_TYPES = ("car", "scooter", "bike")
PAYMENT_METHODS = ("card", "cash", "sbp")


class Status(Enum):
    """Статус заказа или доставки"""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        """Русское название статуса для вывода на экран"""
        return STATUS_LABELS[self]

    def can_change_to(self, new_status: "Status") -> bool:
        """Можно ли перейти из текущего статуса в новый"""
        return new_status in ALLOWED_TRANSITIONS[self]


STATUS_LABELS = {
    Status.CREATED: "Создан",
    Status.IN_PROGRESS: "В процессе доставки",
    Status.DELIVERED: "Доставлен",
    Status.CANCELLED: "Отменён",
}

# Разрешённые переходы между статусами
ALLOWED_TRANSITIONS = {
    Status.CREATED: (Status.IN_PROGRESS, Status.CANCELLED),
    Status.IN_PROGRESS: (Status.DELIVERED, Status.CANCELLED),
    Status.DELIVERED: (),
    Status.CANCELLED: (),
}


def normalize_name(name: str) -> str:
    """Проверить имя и вернуть его без лишних пробелов

    Допускаются только буквы, пробелы и дефис между словами
    """
    clean_name = " ".join(name.split())
    if not clean_name:
        raise InvalidDataError("Имя не должно быть пустым")
    if not NAME_PATTERN.match(clean_name):
        raise InvalidDataError(
            f"Имя может содержать только буквы, пробелы и дефис: {name}")
    return clean_name


def normalize_phone(phone: str) -> str:
    """Проверить телефон и вернуть его в виде +79XXXXXXXXX

    Допустимы записи +79XXXXXXXXX и 89XXXXXXXXX; пробелы, дефисы
    и скобки игнорируются: +7 (900) 000-00-01
    """
    clean_phone = re.sub(r"[\s\-()]", "", phone)
    match = PHONE_PATTERN.match(clean_phone)
    if match is None:
        raise InvalidDataError(
            f"Некорректный телефон: {phone} "
            f"(нужен формат +79XXXXXXXXX или 89XXXXXXXXX)")
    return "+7" + match.group(1)


def normalize_plate(plate: str) -> str:
    """Проверить госномер автомобиля РФ и вернуть его в верхнем регистре

    Формат: буква, три цифры, две буквы, код региона из 2-3 цифр
    (А123ВС77). Буквы должны быть русскими: АВЕКМНОРСТУХ
    """
    clean_plate = plate.strip().upper()
    if not PLATE_PATTERN.match(clean_plate):
        raise InvalidDataError(
            f"Некорректный госномер: {plate} "
            f"(пример: А123ВС77, буквы русские: {PLATE_LETTERS})")
    # цифры номера 000 и регион 00 не существуют
    if clean_plate[1:4] == "000" or clean_plate[6:8] == "00":
        raise InvalidDataError(f"Некорректный госномер: {plate}")
    return clean_plate


def _change_status(current: Status, new: Status) -> Status:
    """Проверить переход статуса и вернуть новый статус"""
    if not current.can_change_to(new):
        raise InvalidStatusError(
            f"Нельзя перейти из статуса «{current.label}» "
            f"в «{new.label}»"
        )
    return new


class Person(ABC):
    """Абстрактный человек: общие данные клиента и курьера"""

    def __init__(self, name: str, phone: str) -> None:
        self.name = ""
        self.phone = ""
        self.update_contact(name, phone)

    def update_contact(self, name: str, phone: str) -> None:
        """Проверить и изменить имя и телефон"""
        # сначала проверяем оба значения, потом меняем: при ошибке
        # старые данные остаются нетронутыми
        clean_name = normalize_name(name)
        clean_phone = normalize_phone(phone)
        self.name = clean_name
        self.phone = clean_phone

    @abstractmethod
    def describe(self) -> str:
        """Краткое описание человека"""


class Customer(Person):
    """Клиент службы доставки"""

    def __init__(self, customer_id: int, name: str, phone: str) -> None:
        super().__init__(name, phone)
        self.customer_id = customer_id

    def describe(self) -> str:
        return f"Клиент №{self.customer_id}: {self.name}, {self.phone}"


class Courier(Person):
    """Курьер службы доставки"""

    def __init__(self, courier_id: int, name: str, phone: str,
                 license_number: str, is_available: bool = True) -> None:
        super().__init__(name, phone)
        if not license_number.strip():
            raise InvalidDataError("Номер удостоверения не указан")
        self.courier_id = courier_id
        self.license_number = license_number.strip()
        self.is_available = is_available

    def describe(self) -> str:
        state = "свободен" if self.is_available else "занят"
        return f"Курьер №{self.courier_id}: {self.name}, {state}"


@dataclass
class Address:
    """Адрес отправления или получения"""

    city: str
    street: str
    house: str
    apartment: str = ""

    def __post_init__(self) -> None:
        if not (self.city.strip() and self.street.strip()
                and self.house.strip()):
            raise InvalidDataError("Город, улица и дом должны быть указаны")

    def __str__(self) -> str:
        result = f"{self.city}, ул. {self.street}, д. {self.house}"
        if self.apartment:
            result += f", кв. {self.apartment}"
        return result


class Parcel:
    """Посылка, которую необходимо доставить"""

    def __init__(self, parcel_id: int, description: str, weight: float,
                 declared_value: float, is_fragile: bool = False) -> None:
        if not description.strip():
            raise InvalidDataError("Описание посылки не должно быть пустым")
        if weight <= 0:
            raise InvalidDataError("Вес посылки должен быть больше нуля")
        if declared_value < 0:
            raise InvalidDataError("Стоимость не может быть отрицательной")
        self.parcel_id = parcel_id
        self.description = description.strip()
        self.weight = float(weight)
        self.declared_value = float(declared_value)
        self.is_fragile = is_fragile


class Order:
    """Заказ на доставку посылки"""

    def __init__(self, order_id: int, customer: Customer, parcel: Parcel,
                 sender_address: Address, receiver_address: Address,
                 distance: float, status: Status = Status.CREATED) -> None:
        if distance <= 0:
            raise InvalidDataError("Расстояние должно быть больше нуля")
        self.order_id = order_id
        self.customer = customer
        self.parcel = parcel
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.distance = float(distance)
        self.status = status

    def change_status(self, new_status: Status) -> None:
        """Сменить статус с проверкой допустимости перехода"""
        self.status = _change_status(self.status, new_status)

    def __str__(self) -> str:
        return (f"№{self.order_id} | {self.customer.name} | "
                f"{self.parcel.description} | {self.status.label}")


class Transport:
    """Транспорт курьера

    Госномер есть только у автомобиля, для самокатов и велосипедов номер должен быть пустым
    """

    def __init__(self, transport_id: int, transport_type: str,
                 registration_number: str = "") -> None:
        if transport_type not in TRANSPORT_TYPES:
            raise InvalidDataError(
                f"Тип транспорта должен быть одним из: "
                f"{', '.join(TRANSPORT_TYPES)}")
        if transport_type == "car":
            registration_number = normalize_plate(registration_number)
        elif registration_number.strip():
            raise InvalidDataError(
                "Госномер есть только у автомобиля (car)")
        self.transport_id = transport_id
        self.transport_type = transport_type
        self.registration_number = registration_number.strip()


class Delivery:
    """Назначенная доставка заказа"""

    def __init__(self, delivery_id: int, order: Order, courier: Courier,
                 transport: Transport,
                 status: Status = Status.IN_PROGRESS) -> None:
        self.delivery_id = delivery_id
        self.order = order
        self.courier = courier
        self.transport = transport
        self.status = status

    def change_status(self, new_status: Status) -> None:
        """Сменить статус с проверкой допустимости перехода"""
        self.status = _change_status(self.status, new_status)

    def __str__(self) -> str:
        return (f"ID: {self.delivery_id} | Заказ №{self.order.order_id} | "
                f"Курьер: {self.courier.name} | {self.status.label}")


class Tariff:
    """Тариф и правила расчёта стоимости"""

    def __init__(self, tariff_id: int, name: str, price_km: float,
                 min_price: float, express_coefficient: float,
                 fragile_coefficient: float, price_kg: float) -> None:
        if min(price_km, min_price, price_kg) < 0:
            raise InvalidDataError("Цены тарифа не могут быть отрицательными")
        if min(express_coefficient, fragile_coefficient) < 1:
            raise InvalidDataError("Коэффициенты тарифа не меньше 1")
        self.tariff_id = tariff_id
        self.name = name
        self.price_km = price_km
        self.min_price = min_price
        self.express_coefficient = express_coefficient
        self.fragile_coefficient = fragile_coefficient
        self.price_kg = price_kg

    def calculate_price(self, order: Order, is_express: bool = False) -> float:
        """Стоимость = max(минимум, км * цена_км + кг * цена_кг) * коэфф."""
        by_distance = order.distance * self.price_km
        by_weight = order.parcel.weight * self.price_kg
        price = max(self.min_price, by_distance + by_weight)
        if is_express:
            price *= self.express_coefficient
        if order.parcel.is_fragile:
            price *= self.fragile_coefficient
        return round(price, 2)


class Payment:
    """Оплата заказа"""

    def __init__(self, payment_id: int, order: Order, amount: float,
                 payment_method: str, is_paid: bool = False) -> None:
        if amount <= 0:
            raise InvalidDataError("Сумма оплаты должна быть больше нуля")
        if payment_method not in PAYMENT_METHODS:
            raise InvalidDataError(
                f"Способ оплаты должен быть одним из: "
                f"{', '.join(PAYMENT_METHODS)}")
        self.payment_id = payment_id
        self.order = order
        self.amount = float(amount)
        self.payment_method = payment_method
        self.is_paid = is_paid


class Review:
    """Отзыв клиента о доставке"""

    def __init__(self, review_id: int, customer: Customer, delivery: Delivery,
                 rating: int, comment: str) -> None:
        if not 1 <= rating <= 5:
            raise InvalidDataError("Оценка должна быть от 1 до 5")
        self.review_id = review_id
        self.customer = customer
        self.delivery = delivery
        self.rating = rating
        self.comment = comment
