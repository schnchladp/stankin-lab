"""Консольное меню службы курьерской доставки"""

from typing import Callable

from delivery.exceptions import DeliveryError
from delivery.models import (
    PAYMENT_METHODS, TRANSPORT_TYPES, Address, Courier, Customer, Parcel,
    Order, Status, Tariff, Transport
)
from delivery.service import DeliveryService
from delivery.storage import DataStorage

# пункт меню: (подпись, функция-обработчик)
MenuItem = tuple[str, Callable[[], None]]


def ask(prompt: str) -> str:
    """Прочитать строку и убрать пробелы по краям"""
    return input(prompt).strip()


def ask_int(prompt: str) -> int:
    """Прочитать целое число (иначе ValueError)"""
    text = ask(prompt)
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"«{text}» - не целое число") from None


def ask_float(prompt: str) -> float:
    """Прочитать вещественное число, допускается запятая"""
    text = ask(prompt)
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise ValueError(f"«{text}» - не число") from None


def ask_bool(prompt: str) -> bool:
    """Вопрос с ответом «да» или «нет»"""
    answer = ask(prompt + " (да/нет): ").lower()
    if answer in ("да", "д"):
        return True
    if answer in ("нет", "н"):
        return False
    raise ValueError(f"«{answer}» - нужно ответить «да» или «нет»")


def ask_choice(prompt: str, options: tuple[str, ...]) -> str:
    """Выбор одного значения из списка по номеру"""
    for number, option in enumerate(options, start=1):
        print(f"{number}. {option}")
    index = ask_int(prompt)
    if not 1 <= index <= len(options):
        raise ValueError(f"нет варианта с номером {index}")
    return options[index - 1]


def ask_address(title: str) -> Address:
    """Ввести адрес (при пустых полях Address выбросит исключение)"""
    print(title)
    return Address(ask("Город: "), ask("Улица: "), ask("Дом: "),
                   ask("Квартира (можно пропустить): "))


def create_default_service() -> DeliveryService:
    """Новая служба доставки с одним стандартным тарифом"""
    service = DeliveryService("Служба курьерской доставки")
    service.add_tariff(Tariff(1, "Стандарт", 100, 200, 1.5, 1.2, 20))
    return service


class DeliveryApp:
    """Интерфейс консольного приложения"""

    JSON_FILE = "data/data.json"
    XML_FILE = "data/data.xml"

    def __init__(self) -> None:
        self.service = create_default_service()
        self.storage = DataStorage()

    # общий механизм меню

    def _menu(self, title: str, items: dict[str, MenuItem],
              back: str = "Назад") -> None:
        """Показывать меню, пока пользователь не выберет «назад»"""
        while True:
            print(f"\n--- {title} ---")
            for key, (label, _) in items.items():
                print(f"{key}. {label}")
            print(f"0. {back}")
            choice = ask("Выберите пункт: ")
            if choice == "0":
                return
            if choice in items:
                self._safe_call(items[choice][1])
            else:
                print("Такого пункта меню нет")

    @staticmethod
    def _safe_call(action: Callable[[], None]) -> None:
        """Выполнить действие так, чтобы ошибка не завершила программу"""
        try:
            action()
        except DeliveryError as error:      # наши исключения
            print(f"Ошибка: {error}")
        except ValueError as error:         # неверный ввод числа и т.п.
            print(f"Некорректный ввод: {error}")
        except EOFError:                    # ввод закончился - выходим выше
            raise
        except Exception as error:          # любая непредвиденная ошибка
            print(f"Непредвиденная ошибка: {type(error).__name__}: {error}")

    def run(self) -> None:
        """Главное меню"""
        items: dict[str, MenuItem] = {
            "1": ("Клиенты", self.customers_menu),
            "2": ("Курьеры", self.couriers_menu),
            "3": ("Заказы", self.orders_menu),
            "4": ("Доставки", self.deliveries_menu),
            "5": ("Оплата и тарифы", self.payments_menu),
            "6": ("Отзывы", self.reviews_menu),
            "7": ("Сохранить данные (JSON и XML)", self.save_data),
            "8": ("Загрузить данные из файла (JSON или XML)", self.load_data),
        }
        print("========================================")
        print("       СЛУЖБА КУРЬЕРСКОЙ ДОСТАВКИ")
        print("========================================")
        try:
            self._menu("ГЛАВНОЕ МЕНЮ", items, back="Выход")
        except (EOFError, KeyboardInterrupt):
            print()
        print("До свидания!")

    # клиенты

    def customers_menu(self) -> None:
        self._menu("КЛИЕНТЫ", {
            "1": ("Список", self.list_customers),
            "2": ("Добавить", self.add_customer),
            "3": ("Найти по id", self.find_customer),
            "4": ("Изменить", self.update_customer),
            "5": ("Удалить", self.delete_customer),
        })

    def list_customers(self) -> None:
        if not self.service.customers:
            print("Список клиентов пуст")
        for customer in self.service.customers:
            print(customer.describe())

    def add_customer(self) -> None:
        customer_id = self.service.next_id(
            self.service.customers, "customer_id")
        self.service.add_customer(
            Customer(customer_id, ask("Имя: "), ask("Телефон: ")))
        print(f"Клиент добавлен, id={customer_id}")

    def find_customer(self) -> None:
        print(self.service.get_customer(ask_int("id клиента: ")).describe())

    def update_customer(self) -> None:
        self.service.update_customer(
            ask_int("id клиента: "), ask("Новое имя: "),
            ask("Новый телефон: "))
        print("Данные клиента изменены")

    def delete_customer(self) -> None:
        self.service.delete_customer(ask_int("id клиента: "))
        print("Клиент удалён")

    # курьеры

    def couriers_menu(self) -> None:
        self._menu("КУРЬЕРЫ", {
            "1": ("Список", self.list_couriers),
            "2": ("Добавить", self.add_courier),
            "3": ("Найти по id", self.find_courier),
            "4": ("Изменить имя и телефон", self.update_courier),
            "5": ("Сменить доступность", self.set_courier_available),
            "6": ("Свободные курьеры", self.list_free_couriers),
            "7": ("Удалить", self.delete_courier),
        })

    def list_couriers(self) -> None:
        if not self.service.couriers:
            print("Список курьеров пуст")
        for courier in self.service.couriers:
            print(courier.describe())

    def add_courier(self) -> None:
        courier_id = self.service.next_id(self.service.couriers, "courier_id")
        self.service.add_courier(Courier(
            courier_id, ask("Имя: "), ask("Телефон: "),
            ask("Номер удостоверения: ")))
        print(f"Курьер добавлен, id={courier_id}")

    def find_courier(self) -> None:
        print(self.service.get_courier(ask_int("id курьера: ")).describe())

    def update_courier(self) -> None:
        self.service.update_courier(
            ask_int("id курьера: "), ask("Новое имя: "),
            ask("Новый телефон: "))
        print("Данные курьера изменены")

    def set_courier_available(self) -> None:
        self.service.set_courier_available(
            ask_int("id курьера: "), ask_bool("Курьер доступен"))
        print("Доступность изменена")

    def list_free_couriers(self) -> None:
        free = self.service.available_couriers()
        if not free:
            print("Свободных курьеров нет")
        for courier in free:
            print(courier.describe())

    def delete_courier(self) -> None:
        self.service.delete_courier(ask_int("id курьера: "))
        print("Курьер удалён")

    # заказы

    def orders_menu(self) -> None:
        self._menu("ЗАКАЗЫ", {
            "1": ("Список", self.list_orders),
            "2": ("Создать", self.add_order),
            "3": ("Найти по id", self.find_order),
            "4": ("Изменить адрес получателя", self.update_order),
            "5": ("Отменить заказ", self.cancel_order),
            "6": ("Заказы по статусу", self.orders_by_status),
            "7": ("Удалить", self.delete_order),
        })

    def list_orders(self) -> None:
        if not self.service.orders:
            print("Список заказов пуст")
        for order in self.service.orders:
            print(order)

    def add_order(self) -> None:
        self.list_customers()            # подсказка: какие id есть
        customer = self.service.get_customer(ask_int("id клиента: "))
        parcel = Parcel(
            self.service.next_id(
                [o.parcel for o in self.service.orders], "parcel_id"),
            ask("Описание посылки: "), ask_float("Вес (кг): "),
            ask_float("Объявленная стоимость (руб): "),
            ask_bool("Посылка хрупкая"))
        sender = ask_address("Адрес отправления:")
        receiver = ask_address("Адрес получения:")
        order_id = self.service.next_id(self.service.orders, "order_id")
        self.service.add_order(Order(
            order_id, customer, parcel, sender, receiver,
            ask_float("Расстояние (км): ")))
        print(f"Заказ создан, id={order_id}")

    def find_order(self) -> None:
        order = self.service.get_order(ask_int("id заказа: "))
        print(order)
        print(f"  Откуда: {order.sender_address}")
        print(f"  Куда:   {order.receiver_address}")

    def update_order(self) -> None:
        order_id = ask_int("id заказа: ")
        receiver = ask_address("Новый адрес получения:")
        self.service.update_order(
            order_id, receiver, ask_float("Расстояние (км): "))
        print("Заказ изменён")

    def cancel_order(self) -> None:
        self.service.cancel_order(ask_int("id заказа: "))
        print("Заказ отменён")

    def orders_by_status(self) -> None:
        names = tuple(status.label for status in Status)
        label = ask_choice("Статус: ", names)
        status = list(Status)[names.index(label)]
        found = self.service.orders_by_status(status)
        if not found:
            print("Заказов с таким статусом нет")
        for order in found:
            print(order)

    def delete_order(self) -> None:
        self.service.delete_order(ask_int("id заказа: "))
        print("Заказ удалён")

    # доставки

    def deliveries_menu(self) -> None:
        self._menu("ДОСТАВКИ", {
            "1": ("Список", self.list_deliveries),
            "2": ("Назначить курьера на заказ", self.assign_courier),
            "3": ("Завершить доставку", self.finish_delivery),
            "4": ("Отменить доставку", self.cancel_delivery),
            "5": ("Удалить", self.delete_delivery),
        })

    def list_deliveries(self) -> None:
        if not self.service.deliveries:
            print("Список доставок пуст")
        for delivery in self.service.deliveries:
            print(delivery)

    def assign_courier(self) -> None:
        order_id = ask_int("id заказа: ")
        courier_id = ask_int("id курьера: ")
        transport_id = self.service.next_id(
            [d.transport for d in self.service.deliveries], "transport_id")
        transport_type = ask_choice("Тип транспорта: ", TRANSPORT_TYPES)
        plate = ""
        if transport_type == "car":      # номер есть только у автомобиля
            plate = ask("Госномер в формате А123ВС77 "
                        "(русские буквы АВЕКМНОРСТУХ): ")
        transport = Transport(transport_id, transport_type, plate)
        delivery_id = self.service.next_id(
            self.service.deliveries, "delivery_id")
        self.service.assign_courier(
            delivery_id, order_id, courier_id, transport)
        print(f"Курьер назначен, доставка id={delivery_id}")

    def finish_delivery(self) -> None:
        self.service.change_delivery_status(
            ask_int("id доставки: "), Status.DELIVERED)
        print("Доставка завершена")

    def cancel_delivery(self) -> None:
        self.service.change_delivery_status(
            ask_int("id доставки: "), Status.CANCELLED)
        print("Доставка отменена")

    def delete_delivery(self) -> None:
        self.service.delete_delivery(ask_int("id доставки: "))
        print("Доставка удалена")

    # оплата

    def payments_menu(self) -> None:
        self._menu("ОПЛАТА И ТАРИФЫ", {
            "1": ("Рассчитать стоимость", self.calculate_price),
            "2": ("Оплатить заказ", self.pay_order),
            "3": ("Список оплат", self.list_payments),
        })

    def calculate_price(self) -> None:
        price = self.service.calculate_price(
            ask_int("id заказа: "), 1, ask_bool("Экспресс-доставка"))
        print(f"Стоимость: {price:.2f} руб.")

    def pay_order(self) -> None:
        order_id = ask_int("id заказа: ")
        express = ask_bool("Экспресс-доставка")
        method = ask_choice("Способ оплаты: ", PAYMENT_METHODS)
        payment_id = self.service.next_id(self.service.payments, "payment_id")
        payment = self.service.pay_order(
            payment_id, order_id, 1, method, express)
        print(f"Оплата принята: {payment.amount:.2f} руб.")

    def list_payments(self) -> None:
        if not self.service.payments:
            print("Оплат пока нет")
        for p in self.service.payments:
            print(f"№{p.payment_id} | заказ №{p.order.order_id} | "
                  f"{p.amount:.2f} руб. | {p.payment_method}")

    # отзывы

    def reviews_menu(self) -> None:
        self._menu("ОТЗЫВЫ", {
            "1": ("Оставить отзыв", self.add_review),
            "2": ("Список отзывов", self.list_reviews),
            "3": ("Рейтинг курьера", self.show_rating),
        })

    def add_review(self) -> None:
        review_id = self.service.next_id(self.service.reviews, "review_id")
        self.service.leave_review(
            review_id, ask_int("id клиента: "), ask_int("id доставки: "),
            ask_int("Оценка (1-5): "), ask("Комментарий: "))
        print("Спасибо за отзыв!")

    def list_reviews(self) -> None:
        if not self.service.reviews:
            print("Отзывов пока нет")
        for r in self.service.reviews:
            print(f"№{r.review_id} | {r.customer.name} | "
                  f"доставка {r.delivery.delivery_id} | "
                  f"{r.rating}/5 | {r.comment}")

    def show_rating(self) -> None:
        rating = self.service.courier_rating(ask_int("id курьера: "))
        print("Отзывов нет" if rating is None else f"Рейтинг: {rating}")

    # файлы

    def save_data(self) -> None:
        self.storage.save_json(self.service, self.JSON_FILE)
        self.storage.save_xml(self.service, self.XML_FILE)
        print("Данные сохранены в JSON и XML")

    def load_data(self) -> None:
        if not ask_bool("Текущие данные в программе будут заменены. "
                        "Продолжить"):
            print("Загрузка отменена")
            return
        file_format = ask_choice("Формат: ", ("JSON", "XML"))
        if file_format == "JSON":
            self.service = self.storage.load_json(self.JSON_FILE)
        else:
            self.service = self.storage.load_xml(self.XML_FILE)
        print("Данные загружены")
