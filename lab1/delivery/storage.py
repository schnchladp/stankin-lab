"""Сохранение и загрузка данных в форматах JSON и XML"""

import json
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from delivery.exceptions import DeliveryError, StorageError
from delivery.models import (
    Address, Courier, Customer, Delivery, Order, Parcel, Payment, Review,
    Status, Tariff, Transport
)
from delivery.service import DeliveryService

SECTIONS = {
    "customers": "customer",
    "couriers": "courier",
    "tariffs": "tariff",
    "orders": "order",
    "deliveries": "delivery",
    "payments": "payment",
    "reviews": "review",
}


def _to_int(value: Any) -> int:
    """Целое число из JSON или из текста XML"""
    if isinstance(value, bool):
        raise ValueError(f"ожидалось целое число, а не {value!r}")
    return int(value)


def _to_float(value: Any) -> float:
    return float(value)


def _to_bool(value: Any) -> bool:
    """Логическое значение: true/false (в любом регистре)"""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "false"):
        return text == "true"
    raise ValueError(f"ожидалось true/false, а не {value!r}")


def _to_str(value: Any) -> str:
    return "" if value is None else str(value)


@contextmanager
def _translate_errors(filename: str, kind: str) -> Iterator[None]:
    """Превратить любые ошибки работы с файлом в StorageError"""
    try:
        yield
    except FileNotFoundError:
        raise StorageError(f"Файл {filename} не найден") from None
    except (json.JSONDecodeError, ET.ParseError) as error:
        raise StorageError(
            f"Файл {filename} - некорректный {kind}: {error}") from error
    except OSError as error:
        raise StorageError(
            f"Не удалось прочитать или записать {filename}: {error}"
        ) from error
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise StorageError(
            f"Файл {filename} имеет неверную структуру "
            f"({type(error).__name__}: {error})") from error
    except DeliveryError as error:
        raise StorageError(
            f"В файле {filename} некорректные данные: {error}") from error


class DataStorage:
    """Запись и чтение данных службы доставки в JSON и XML"""

    # объекты -> словарь

    @staticmethod
    def to_dict(service: DeliveryService) -> dict[str, Any]:
        """Собрать все данные службы в обычный словарь"""
        return {
            "name": service.name,
            "customers": [
                {"id": x.customer_id, "name": x.name, "phone": x.phone}
                for x in service.customers],
            "couriers": [
                {"id": x.courier_id, "name": x.name, "phone": x.phone,
                 "license": x.license_number, "available": x.is_available}
                for x in service.couriers],
            "tariffs": [
                {"id": x.tariff_id, "name": x.name, "price_km": x.price_km,
                 "min_price": x.min_price, "price_kg": x.price_kg,
                 "express_coefficient": x.express_coefficient,
                 "fragile_coefficient": x.fragile_coefficient}
                for x in service.tariffs],
            "orders": [
                {"id": x.order_id, "customer_id": x.customer.customer_id,
                 "parcel_id": x.parcel.parcel_id,
                 "description": x.parcel.description,
                 "weight": x.parcel.weight,
                 "declared_value": x.parcel.declared_value,
                 "fragile": x.parcel.is_fragile, "distance": x.distance,
                 "status": x.status.value,
                 "sender": vars(x.sender_address),
                 "receiver": vars(x.receiver_address)}
                for x in service.orders],
            "deliveries": [
                {"id": x.delivery_id, "order_id": x.order.order_id,
                 "courier_id": x.courier.courier_id,
                 "transport": {
                     "id": x.transport.transport_id,
                     "registration_number": x.transport.registration_number,
                     "transport_type": x.transport.transport_type},
                 "status": x.status.value}
                for x in service.deliveries],
            "payments": [
                {"id": x.payment_id, "order_id": x.order.order_id,
                 "amount": x.amount, "method": x.payment_method,
                 "paid": x.is_paid}
                for x in service.payments],
            "reviews": [
                {"id": x.review_id, "customer_id": x.customer.customer_id,
                 "delivery_id": x.delivery.delivery_id,
                 "rating": x.rating, "comment": x.comment}
                for x in service.reviews],
        }

    # словарь -> объекты

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DeliveryService:
        """Восстановить службу доставки из словаря"""
        service = DeliveryService(_to_str(data["name"]))
        for x in data.get("customers", []):
            service.add_customer(Customer(
                _to_int(x["id"]), _to_str(x["name"]), _to_str(x["phone"])))
        for x in data.get("couriers", []):
            service.add_courier(Courier(
                _to_int(x["id"]), _to_str(x["name"]), _to_str(x["phone"]),
                _to_str(x["license"]), _to_bool(x["available"])))
        for x in data.get("tariffs", []):
            service.add_tariff(Tariff(
                _to_int(x["id"]), _to_str(x["name"]),
                _to_float(x["price_km"]), _to_float(x["min_price"]),
                _to_float(x["express_coefficient"]),
                _to_float(x["fragile_coefficient"]),
                _to_float(x["price_kg"])))
        for x in data.get("orders", []):
            parcel = Parcel(
                _to_int(x["parcel_id"]), _to_str(x["description"]),
                _to_float(x["weight"]), _to_float(x["declared_value"]),
                _to_bool(x["fragile"]))
            service.add_order(Order(
                _to_int(x["id"]),
                service.get_customer(_to_int(x["customer_id"])), parcel,
                DataStorage._address(x["sender"]),
                DataStorage._address(x["receiver"]),
                _to_float(x["distance"]), Status(x["status"])))
        for x in data.get("deliveries", []):
            t = x["transport"]
            transport = Transport(
                _to_int(t["id"]), _to_str(t["transport_type"]),
                _to_str(t["registration_number"]))
            service.add_delivery(Delivery(
                _to_int(x["id"]),
                service.get_order(_to_int(x["order_id"])),
                service.get_courier(_to_int(x["courier_id"])),
                transport, Status(x["status"])))
        for x in data.get("payments", []):
            service.add_payment(Payment(
                _to_int(x["id"]),
                service.get_order(_to_int(x["order_id"])),
                _to_float(x["amount"]), _to_str(x["method"]),
                _to_bool(x["paid"])))
        for x in data.get("reviews", []):
            service.add_review(Review(
                _to_int(x["id"]),
                service.get_customer(_to_int(x["customer_id"])),
                service.get_delivery(_to_int(x["delivery_id"])),
                _to_int(x["rating"]), _to_str(x["comment"])))
        return service

    @staticmethod
    def _address(data: dict[str, Any]) -> Address:
        return Address(
            _to_str(data["city"]), _to_str(data["street"]),
            _to_str(data["house"]), _to_str(data.get("apartment", "")))

    # JSON

    def save_json(self, service: DeliveryService, filename: str) -> None:
        with _translate_errors(filename, "JSON"):
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(self.to_dict(service), file,
                          ensure_ascii=False, indent=4)

    def load_json(self, filename: str) -> DeliveryService:
        with _translate_errors(filename, "JSON"):
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
            return self.from_dict(data)

    # XML

    def save_xml(self, service: DeliveryService, filename: str) -> None:
        with _translate_errors(filename, "XML"):
            data = self.to_dict(service)
            root = ET.Element("delivery_service", name=service.name)
            for section, record_name in SECTIONS.items():
                section_element = ET.SubElement(root, section)
                for record in data[section]:
                    element = ET.SubElement(section_element, record_name)
                    self._dict_to_xml(element, record)
            tree = ET.ElementTree(root)
            ET.indent(tree, space="    ")
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            tree.write(filename, encoding="utf-8", xml_declaration=True)

    def load_xml(self, filename: str) -> DeliveryService:
        with _translate_errors(filename, "XML"):
            root = ET.parse(filename).getroot()
            data: dict[str, Any] = {"name": root.get("name", "")}
            for section in SECTIONS:
                data[section] = [self._xml_to_dict(item)
                                 for item in root.findall(f"./{section}/*")]
            return self.from_dict(data)

    @classmethod
    def _dict_to_xml(cls, parent: ET.Element, data: dict[str, Any]) -> None:
        """Записать словарь как вложенные XML-элементы"""
        for key, value in data.items():
            child = ET.SubElement(parent, key)
            if isinstance(value, dict):
                cls._dict_to_xml(child, value)
            elif isinstance(value, bool):
                child.text = "true" if value else "false"
            else:
                child.text = str(value)

    @classmethod
    def _xml_to_dict(cls, element: ET.Element) -> dict[str, Any]:
        """Прочитать XML-элемент в словарь (значения остаются текстом)"""
        result: dict[str, Any] = {}
        for child in element:
            if len(child):
                result[child.tag] = cls._xml_to_dict(child)
            else:
                result[child.tag] = child.text or ""
        return result
