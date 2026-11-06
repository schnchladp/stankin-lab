"""Логика службы доставки: CRUD и правила работы с заказами."""

from typing import Optional, TypeVar

from delivery.exceptions import (
    CourierUnavailableError, DependencyError, DuplicateIdError,
    InvalidDataError, InvalidStatusError, NotFoundError
)
from delivery.models import (
    Address, Courier, Customer, Delivery, Order, Payment, Review, Status,
    Tariff, Transport, normalize_phone
)

T = TypeVar("T")


class DeliveryService:
    """Хранит все объекты и управляет ими (клиенты, курьеры, заказы и тд)"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.customers: list[Customer] = []
        self.couriers: list[Courier] = []
        self.orders: list[Order] = []
        self.deliveries: list[Delivery] = []
        self.tariffs: list[Tariff] = []
        self.payments: list[Payment] = []
        self.reviews: list[Review] = []

    # вспомогательные методы

    @staticmethod
    def _get(items: list[T], attr: str, value: int, title: str) -> T:
        """Найти объект по id или выбросить NotFoundError"""
        for item in items:
            if getattr(item, attr) == value:
                return item
        raise NotFoundError(f"{title} с id={value} не найден(а)")

    @staticmethod
    def _add(items: list[T], item: T, attr: str, title: str) -> None:
        """Добавить объект, если такого id ещё нет"""
        value = getattr(item, attr)
        for existing in items:
            if getattr(existing, attr) == value:
                raise DuplicateIdError(f"{title} с id={value} уже есть")
        items.append(item)

    @staticmethod
    def _check_phone_free(items: list, phone: str, title: str,
                          ignore: object = None) -> None:
        """Телефон должен быть уникален среди клиентов (или курьеров)"""
        for item in items:
            if item is not ignore and item.phone == phone:
                raise DuplicateIdError(f"{title} с телефоном {phone} уже есть")

    @staticmethod
    def next_id(items: list, attr: str) -> int:
        """Следующий свободный id: максимальный + 1"""
        return max((getattr(item, attr) for item in items), default=0) + 1

    # добавление (Create)

    def add_customer(self, item: Customer) -> None:
        self._check_phone_free(self.customers, item.phone, "Клиент")
        self._add(self.customers, item, "customer_id", "Клиент")

    def add_courier(self, item: Courier) -> None:
        self._check_phone_free(self.couriers, item.phone, "Курьер")
        self._add(self.couriers, item, "courier_id", "Курьер")

    def add_order(self, item: Order) -> None:
        self._add(self.orders, item, "order_id", "Заказ")

    def add_delivery(self, item: Delivery) -> None:
        self._add(self.deliveries, item, "delivery_id", "Доставка")

    def add_tariff(self, item: Tariff) -> None:
        self._add(self.tariffs, item, "tariff_id", "Тариф")

    def add_payment(self, item: Payment) -> None:
        self._add(self.payments, item, "payment_id", "Оплата")

    def add_review(self, item: Review) -> None:
        self._add(self.reviews, item, "review_id", "Отзыв")

    # поиск

    def get_customer(self, item_id: int) -> Customer:
        return self._get(self.customers, "customer_id", item_id, "Клиент")

    def get_courier(self, item_id: int) -> Courier:
        return self._get(self.couriers, "courier_id", item_id, "Курьер")

    def get_order(self, item_id: int) -> Order:
        return self._get(self.orders, "order_id", item_id, "Заказ")

    def get_delivery(self, item_id: int) -> Delivery:
        return self._get(self.deliveries, "delivery_id", item_id, "Доставка")

    def get_tariff(self, item_id: int) -> Tariff:
        return self._get(self.tariffs, "tariff_id", item_id, "Тариф")

    def orders_by_status(self, status: Status) -> list[Order]:
        """Все заказы с заданным статусом"""
        return [order for order in self.orders if order.status is status]

    def available_couriers(self) -> list[Courier]:
        """Все свободные курьеры"""
        return [courier for courier in self.couriers if courier.is_available]

    def courier_rating(self, courier_id: int) -> Optional[float]:
        """Средняя оценка курьера по отзывам (None, если отзывов нет)"""
        self.get_courier(courier_id)
        marks = [review.rating for review in self.reviews
                 if review.delivery.courier.courier_id == courier_id]
        return round(sum(marks) / len(marks), 2) if marks else None

    # изменение

    def update_customer(self, item_id: int, name: str, phone: str) -> None:
        customer = self.get_customer(item_id)
        self._check_phone_free(self.customers, normalize_phone(phone),
                               "Клиент", ignore=customer)
        customer.update_contact(name, phone)

    def update_courier(self, item_id: int, name: str, phone: str) -> None:
        courier = self.get_courier(item_id)
        self._check_phone_free(self.couriers, normalize_phone(phone),
                               "Курьер", ignore=courier)
        courier.update_contact(name, phone)

    def set_courier_available(self, item_id: int, available: bool) -> None:
        """Вручную сменить доступность курьера"""
        courier = self.get_courier(item_id)
        if available and self._has_active_delivery(courier):
            raise DependencyError("Курьер сейчас выполняет доставку")
        courier.is_available = available

    def update_order(self, item_id: int, receiver: Address,
                     distance: float) -> None:
        """Изменить адрес получателя и расстояние (только новый заказ)"""
        order = self.get_order(item_id)
        if order.status is not Status.CREATED:
            raise InvalidStatusError(
                f"Менять можно только новый заказ, а сейчас: "
                f"{order.status.label}")
        if distance <= 0:
            raise InvalidDataError("Расстояние должно быть больше нуля")
        order.receiver_address = receiver
        order.distance = float(distance)

    def cancel_order(self, item_id: int) -> None:
        """Отменить заказ, на который ещё не назначен курьер"""
        self.get_order(item_id).change_status(Status.CANCELLED)

    # удаление

    def delete_customer(self, item_id: int) -> None:
        customer = self.get_customer(item_id)
        if any(o.customer is customer for o in self.orders):
            raise DependencyError("У клиента есть заказы, удалять нельзя")
        self.customers.remove(customer)

    def delete_courier(self, item_id: int) -> None:
        courier = self.get_courier(item_id)
        if any(d.courier is courier for d in self.deliveries):
            raise DependencyError("С курьером связаны доставки")
        self.couriers.remove(courier)

    def delete_order(self, item_id: int) -> None:
        order = self.get_order(item_id)
        if any(d.order is order for d in self.deliveries):
            raise DependencyError("На заказ назначена доставка")
        if any(p.order is order for p in self.payments):
            raise DependencyError("Заказ оплачен, удалять нельзя")
        self.orders.remove(order)

    def delete_delivery(self, item_id: int) -> None:
        delivery = self.get_delivery(item_id)
        if delivery.status is Status.IN_PROGRESS:
            raise DependencyError("Нельзя удалить активную доставку")
        if any(r.delivery is delivery for r in self.reviews):
            raise DependencyError("На доставку есть отзыв")
        self.deliveries.remove(delivery)

    # операции

    def _has_active_delivery(self, courier: Courier) -> bool:
        return any(d.courier is courier and d.status is Status.IN_PROGRESS
                   for d in self.deliveries)

    def assign_courier(self, delivery_id: int, order_id: int,
                       courier_id: int, transport: Transport) -> Delivery:
        """Назначить курьера на заказ: заказ уходит в доставку"""
        order = self.get_order(order_id)
        courier = self.get_courier(courier_id)
        if order.status is not Status.CREATED:
            raise InvalidStatusError(
                f"Курьера можно назначить только на новый заказ, "
                f"а сейчас: {order.status.label}")
        if not courier.is_available:
            raise CourierUnavailableError(
                f"Курьер {courier.name} сейчас занят")
        delivery = Delivery(delivery_id, order, courier, transport)
        self.add_delivery(delivery)  # проверка дубликата id до изменений
        order.change_status(Status.IN_PROGRESS)
        courier.is_available = False
        return delivery

    def change_delivery_status(self, delivery_id: int,
                               new_status: Status) -> None:
        """Завершить или отменить доставку; заказ и курьер обновляются"""
        delivery = self.get_delivery(delivery_id)
        delivery.change_status(new_status)
        delivery.order.change_status(new_status)
        delivery.courier.is_available = True

    def calculate_price(self, order_id: int, tariff_id: int,
                        express: bool = False) -> float:
        """Рассчитать стоимость доставки заказа по тарифу"""
        order = self.get_order(order_id)
        return self.get_tariff(tariff_id).calculate_price(order, express)

    def pay_order(self, payment_id: int, order_id: int, tariff_id: int,
                  method: str, express: bool = False) -> Payment:
        """Создать оплату заказа"""
        order = self.get_order(order_id)
        if order.status is Status.CANCELLED:
            raise InvalidStatusError("Заказ отменён, оплата невозможна")
        if any(p.order is order for p in self.payments):
            raise InvalidDataError("Этот заказ уже оплачен")
        amount = self.calculate_price(order_id, tariff_id, express)
        payment = Payment(payment_id, order, amount, method, True)
        self.add_payment(payment)
        return payment

    def leave_review(self, review_id: int, customer_id: int,
                     delivery_id: int, rating: int, comment: str) -> Review:
        """Оставить отзыв: только владелец заказа и только после доставки"""
        customer = self.get_customer(customer_id)
        delivery = self.get_delivery(delivery_id)
        if delivery.order.customer is not customer:
            raise InvalidDataError("Это не доставка данного клиента")
        if delivery.status is not Status.DELIVERED:
            raise InvalidStatusError("Отзыв можно оставить после доставки")
        review = Review(review_id, customer, delivery, rating, comment)
        self.add_review(review)
        return review
