"""R-05: money is serialised as a string, never as a JSON float.

A JSON number cannot represent 0.10 exactly, so every amount on the wire
must be a fixed 2-decimal string. This test pins the wire format for the
four money-bearing endpoints and for the generated OpenAPI schema.
"""
import json
from decimal import Decimal
from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.kernel.models import Bill, BillItem, Employee, StockItem


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    assert token
    return {"x-csrf-token": token}


DECIMAL_PLACES = 2
DOT_COUNT = 1


def _assert_money_string(value: object, label: str) -> None:
    """An amount must be a 2-decimal string, never a JSON number."""
    assert isinstance(value, str), f"{label} is {type(value).__name__} ({value!r}), expected str"
    assert (
        value.count(".") == DOT_COUNT
    ), f"{label} is not a 2-decimal amount: {value!r}"
    whole, _, frac = value.partition(".")
    assert (
        len(frac) == DECIMAL_PLACES
    ), f"{label} is not a 2-decimal amount: {value!r}"
    assert whole.isdigit(), f"{label} is not a 2-decimal amount: {value!r}"
    assert Decimal(value) >= 0


def test_payslip_response_money_is_a_string(
    authenticated_client: TestClient, db: Session
) -> None:
    db.add(Employee(employee_code="EMP-MONEY", name="Money Person", salary=Decimal("48000.50")))
    db.commit()

    created = authenticated_client.post(
        "/api/v1/payslip/payslips",
        json={
            "employee_code": "EMP-MONEY",
            "month": "2026-03",
            "total_working_days": 30,
            "days_paid": 30,
            "basic": 7000.25,
            "other_allowances": 0.1,
            "deduction_lines": [{"label": "PF", "amount": 750}],
        },
        headers=_csrf_headers(authenticated_client),
    )
    assert created.status_code == HTTPStatus.OK, created.text
    body = created.json()

    _assert_money_string(body["gross"], "payslip.gross")
    _assert_money_string(body["total_deductions"], "payslip.total_deductions")
    _assert_money_string(body["net"], "payslip.net")
    for line in body["lines"]:
        _assert_money_string(line["amount"], f"payslip.lines[{line['label']}].amount")

    # 7000.25 + 0.10 - 750.00 = 6250.35, exact only because nothing became a float.
    assert body["gross"] == "7000.35"
    assert body["total_deductions"] == "750.00"
    assert body["net"] == "6250.35"

    listed = authenticated_client.get("/api/v1/payslip/payslips")
    assert listed.status_code == HTTPStatus.OK
    first = listed.json()[0]
    _assert_money_string(first["gross"], "payslip list gross")
    _assert_money_string(first["net"], "payslip list net")

    fetched = authenticated_client.get(f"/api/v1/payslip/payslips/{body['id']}")
    assert fetched.status_code == HTTPStatus.OK
    _assert_money_string(fetched.json()["net"], "payslip detail net")


def test_employee_response_money_is_a_string(
    authenticated_client: TestClient, db: Session
) -> None:
    db.add(Employee(employee_code="EMP-S", name="Salary Person", salary=Decimal("12345.50")))
    db.commit()

    listed = authenticated_client.get("/api/v1/employees")
    assert listed.status_code == HTTPStatus.OK
    row = next(r for r in listed.json() if r["code"] == "EMP-S")
    _assert_money_string(row["salary"], "employee.salary")
    assert row["salary"] == "12345.50"

    fetched = authenticated_client.get(f"/api/v1/employees/{row['id']}")
    assert fetched.status_code == HTTPStatus.OK
    _assert_money_string(fetched.json()["salary"], "employee detail salary")


def test_inventory_response_money_is_a_string(
    authenticated_client: TestClient, db: Session
) -> None:
    db.add(
        StockItem(
            sku="SKU-MONEY",
            name="Money Widget",
            category="tools",
            unit="pcs",
            unit_cost=Decimal("19.99"),
        )
    )
    db.commit()

    listed = authenticated_client.get("/api/v1/inventory/items")
    assert listed.status_code == HTTPStatus.OK
    row = next(r for r in listed.json() if r["sku"] == "SKU-MONEY")
    _assert_money_string(row["unit_cost"], "inventory.unit_cost")
    assert row["unit_cost"] == "19.99"


def test_bills_response_money_is_a_string(
    authenticated_client: TestClient, db: Session
) -> None:
    bill = Bill(vendor="Acme", total=Decimal("199.50"), status="draft")
    db.add(bill)
    db.flush()
    db.add(BillItem(bill_id=bill.id, description="Widgets", amount=Decimal("199.50")))
    db.commit()

    listed = authenticated_client.get("/api/v1/bills")
    assert listed.status_code == HTTPStatus.OK
    row = next(r for r in listed.json() if r["vendor"] == "Acme")
    _assert_money_string(row["total"], "bill.total")
    assert row["total"] == "199.50"

    fetched = authenticated_client.get(f"/api/v1/bills/{row['id']}")
    assert fetched.status_code == HTTPStatus.OK
    detail = fetched.json()
    _assert_money_string(detail["total"], "bill detail total")
    for item in detail["items"]:
        _assert_money_string(item["amount"], "bill item amount")


def test_openapi_declares_money_fields_as_strings(authenticated_client: TestClient) -> None:
    """The generated schema must tell the frontend the amount is a string."""
    schema = authenticated_client.get("/openapi.json").json()
    schemas = schema["components"]["schemas"]

    def money_type(schema_name: str, field: str) -> object:
        return schemas[schema_name]["properties"][field]

    # A string (or string|null) field, never number/integer.
    for schema_name, field in (
        ("PayslipOut", "gross"),
        ("PayslipOut", "total_deductions"),
        ("PayslipOut", "net"),
        ("PayslipLineOut", "amount"),
        ("EmployeeOut", "salary"),
        ("InventoryItemOut", "unit_cost"),
        ("BillSummaryOut", "total"),
        ("BillItemOut", "amount"),
    ):
        node = money_type(schema_name, field)
        rendered = json.dumps(node)
        assert "number" not in rendered, f"{schema_name}.{field} is numeric: {rendered}"
        assert "string" in rendered, f"{schema_name}.{field} is not a string: {rendered}"
