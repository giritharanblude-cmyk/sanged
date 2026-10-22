"""API tests for the currently wired Employees, Inventory, Bills and Company routes."""

from decimal import Decimal
from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.kernel.models import AuditLog, Bill, CompanyProfile, Employee, StockItem, StockMovement

EXPECTED_LEDGER_QUANTITY = 22


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    assert token
    return {"x-csrf-token": token}


def test_create_employee_then_soft_delete(
    authenticated_client: TestClient, db: Session
) -> None:
    response = authenticated_client.post(
        "/api/v1/employees",
        json={
            "employee_code": "EMP-010",
            "name": "Asha Nair",
            "designation": "Designer",
            "email": "asha@example.com",
            "salary": 48000,
        },
        headers=_csrf_headers(authenticated_client),
    )
    assert response.status_code == HTTPStatus.OK
    employee_id = response.json()["id"]

    listed = authenticated_client.get("/api/v1/employees")
    assert any(row["code"] == "EMP-010" for row in listed.json())

    deleted = authenticated_client.delete(
        f"/api/v1/employees/{employee_id}",
        headers=_csrf_headers(authenticated_client),
    )
    assert deleted.status_code == HTTPStatus.OK
    after = authenticated_client.get("/api/v1/employees")
    assert not any(row["code"] == "EMP-010" for row in after.json())

    audit_actions = {
        row.action
        for row in db.query(AuditLog).filter(AuditLog.entity == "employee").all()
    }
    assert {"create", "delete"} <= audit_actions
    assert db.query(Employee).filter_by(id=employee_id).one().deleted_at is not None


def test_duplicate_employee_code_returns_conflict(
    authenticated_client: TestClient,
) -> None:
    payload = {"employee_code": "EMP-DUP", "name": "First"}
    headers = _csrf_headers(authenticated_client)
    authenticated_client.post("/api/v1/employees", json=payload, headers=headers)
    duplicate = authenticated_client.post(
        "/api/v1/employees",
        json={**payload, "name": "Second"},
        headers=headers,
    )
    assert duplicate.status_code == HTTPStatus.CONFLICT


def test_inventory_list_aggregates_ledger_quantity(
    authenticated_client: TestClient, db: Session
) -> None:
    item = StockItem(sku="SKU-1", name="Alpha Widget", category="tools", unit="pcs")
    db.add(item)
    db.flush()
    db.add_all(
        [
            StockMovement(item_id=item.id, kind="in", qty=25, reason="purchase"),
            StockMovement(item_id=item.id, kind="out", qty=5, reason="issue"),
            StockMovement(item_id=item.id, kind="in", qty=2, reason="return"),
        ]
    )
    db.commit()

    listed = authenticated_client.get("/api/v1/inventory/items")
    rows = {row["sku"]: row for row in listed.json()}
    assert rows["SKU-1"]["quantity"] == EXPECTED_LEDGER_QUANTITY


def test_bills_list_and_missing_bill_return_not_found(
    authenticated_client: TestClient, db: Session
) -> None:
    db.add(Bill(vendor="Acme", total=Decimal("199.50"), status="draft"))
    db.commit()

    listed = authenticated_client.get("/api/v1/bills")
    assert listed.status_code == HTTPStatus.OK
    assert any(row["vendor"] == "Acme" for row in listed.json())

    missing_id = "00000000-0000-0000-0000-000000000000"
    missing = authenticated_client.get(f"/api/v1/bills/{missing_id}")
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_company_profile_upsert_and_get(
    authenticated_client: TestClient, db: Session
) -> None:
    empty = authenticated_client.get("/api/v1/company/profile")
    assert empty.status_code == HTTPStatus.OK

    updated = authenticated_client.put(
        "/api/v1/company/profile",
        json={
            "legal_name": "Blude TechX LLP",
            "gstin": "33AAFCB1234A1Z5",
            "pf_applicable": False,
        },
        headers=_csrf_headers(authenticated_client),
    )
    assert updated.status_code == HTTPStatus.OK

    profile = authenticated_client.get("/api/v1/company/profile").json()
    assert profile["legal_name"] == "Blude TechX LLP"
    assert profile["pf_applicable"] is False
    assert db.query(CompanyProfile).count() == 1
    assert db.query(AuditLog).filter_by(entity="company_profile").count() > 0
