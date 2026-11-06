"""Демонстрация работы программы: обычная работа и все виды ошибок"""

from pathlib import Path
from typing import Callable

from delivery.app import create_default_service
from delivery.exceptions import DeliveryError
from delivery.models import (
    Address, Courier, Customer, Order, Parcel, Status, Transport
)
from delivery.storage import DataStorage


def expect_error(title: str, action: Callable[[], object]) -> None:
    """Выполнить действие, которое должно завершиться ошибкой"""
    try:
        action()
    except DeliveryError as error:
        print(f"[ОШИБКА] {title}: {type(error).__name__}: {error}")
    else:
        print(f"[!!!] {title}: ошибка не возникла")


def main() -> None:
    service = create_default_service()
    home = Address("Москва", "Тверская", "10", "25")
    office = Address("Москва", "Арбат", "15")

    print("--- Нормальная работа ---")
    service.add_customer(Customer(1, "Алина", "+7 900 000-00-01"))
    service.add_customer(Customer(2, "Игорь", "+79000000002"))
    service.add_courier(Courier(1, "Аделина", "+79111111111", "1234567890"))
    service.add_courier(Courier(2, "Петр", "+79222222222", "0987654321"))
    parcel = Parcel(101, "Ваза", 3.5, 2500, True)
    service.add_order(Order(1, service.get_customer(1), parcel,
                            home, office, 5))
    service.add_order(Order(2, service.get_customer(2),
                            Parcel(102, "Документы", 0.3, 0), office, home, 8))
    print("[OK] заказы созданы:", *service.orders, sep="\n     ")

    transport = Transport(1, "car", "А123ВС77")
    delivery = service.assign_courier(1, 1, 1, transport)
    print(f"[OK] курьер назначен: {delivery}")
    print("[OK] свободные курьеры:",
          [c.name for c in service.available_couriers()])
    price = service.calculate_price(1, 1, express=True)
    print(f"[OK] стоимость экспресс-доставки заказа №1: {price} руб.")
    payment = service.pay_order(1, 1, 1, "card", express=True)
    print(f"[OK] оплата принята: {payment.amount} руб.")
    service.change_delivery_status(1, Status.DELIVERED)
    print(f"[OK] доставка завершена: {delivery}")
    service.leave_review(1, 1, 1, 5, "Быстро и аккуратно")
    print("[OK] рейтинг курьера №1:", service.courier_rating(1))

    print("--- Обработка ошибок ---")
    expect_error("пустое имя",
                 lambda: Customer(9, "  ", "+79000000009"))
    expect_error("имя с цифрами",
                 lambda: Customer(9, "Олег2", "+79000000009"))
    expect_error("неверный телефон",
                 lambda: Customer(9, "Олег", "12-34"))
    expect_error("телефон не мобильный (+7495...)",
                 lambda: Customer(9, "Олег", "+74951234567"))
    expect_error("повторный телефон", lambda: service.add_customer(
        Customer(9, "Олег", "89000000001")))
    expect_error("неверный госномер",
                 lambda: Transport(9, "car", "1Фы45"))
    expect_error("номер у велосипеда",
                 lambda: Transport(9, "bike", "А123ВС77"))
    expect_error("отрицательный вес",
                 lambda: Parcel(9, "Коробка", -1, 0))
    expect_error("повторный id", lambda: service.add_customer(
        Customer(1, "Ещё", "+79000000003")))
    expect_error("нет такого заказа", lambda: service.get_order(99))
    service.assign_courier(2, 2, 2, transport)
    service.add_order(Order(3, service.get_customer(1),
                            Parcel(103, "Подарок", 1, 500),
                            home, office, 4))
    expect_error("курьер занят",
                 lambda: service.assign_courier(3, 3, 2, transport))
    expect_error("заказ уже в доставке",
                 lambda: service.assign_courier(4, 2, 1, transport))
    expect_error("повторная доставка завершена",
                 lambda: service.change_delivery_status(1, Status.DELIVERED))
    expect_error("отмена доставленного заказа",
                 lambda: service.cancel_order(1))
    expect_error("повторная оплата",
                 lambda: service.pay_order(2, 1, 1, "cash"))
    expect_error("чужой отзыв",
                 lambda: service.leave_review(2, 2, 1, 4, "Не мой заказ"))
    expect_error("оценка вне диапазона",
                 lambda: service.leave_review(2, 1, 1, 7, "Супер"))
    expect_error("удаление клиента с заказами",
                 lambda: service.delete_customer(1))
    expect_error("удаление заказа с доставкой",
                 lambda: service.delete_order(1))

    print("--- JSON и XML ---")
    storage = DataStorage()
    folder = Path("data/demo")
    folder.mkdir(parents=True, exist_ok=True)

    def path(name: str) -> str:
        return (folder / name).as_posix()

    original = storage.to_dict(service)
    storage.save_json(service, path("data.json"))
    loaded = storage.load_json(path("data.json"))
    print("JSON: записано, прочитано, данные совпадают =",
          storage.to_dict(loaded) == original)
    storage.save_xml(service, path("data.xml"))
    loaded = storage.load_xml(path("data.xml"))
    print("XML:  записано, прочитано, данные совпадают =",
          storage.to_dict(loaded) == original)

    print("--- Повреждённые файлы ---")
    (folder / "bad.json").write_text("{'a': 1}", encoding="utf-8")
    (folder / "bad.xml").write_text("<root><a>", encoding="utf-8")
    (folder / "wrong.json").write_text(
        '{"name": "x", "customers": [{"id": "x"}]}', encoding="utf-8")
    (folder / "dup.json").write_text(
        '{"name": "x", "customers": ['
        '{"id": 1, "name": "А", "phone": "+79000000001"},'
        '{"id": 1, "name": "Б", "phone": "+79000000002"}]}',
        encoding="utf-8")
    expect_error("загрузка bad.json",
                 lambda: storage.load_json(path("bad.json")))
    expect_error("загрузка bad.xml",
                 lambda: storage.load_xml(path("bad.xml")))
    expect_error("загрузка wrong.json",
                 lambda: storage.load_json(path("wrong.json")))
    expect_error("загрузка dup.json",
                 lambda: storage.load_json(path("dup.json")))
    expect_error("файла нет",
                 lambda: storage.load_json(path("none.json")))
    print("Демонстрация завершена, программа дошла до конца.")


if __name__ == "__main__":
    main()
