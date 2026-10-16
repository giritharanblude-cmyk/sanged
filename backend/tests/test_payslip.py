"""Payslip calculation, validation, create/list and lifecycle API tests."""

from decimal import Decimal
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.modules.payslip.calculations import amount_to_words_inr, calculate_payslip


def _create(
    api_client: TestClient,
    overrides: dict[str, object] | None = None,
) -> Response:
    payload: dict[str, object] = {
        "employee_code": "EMP-001",
        "month": "2026-01",
        "total_working_days": 30,
        "days_paid": 30,
        "basic": 5000,
        "other_allowances": 2000,
        "deduction_lines": [{"label": "PF", "amount": 750}],
    }
    payload.update(overrides or {})
    csrf = api_client.cookies.get("csrf_token")
    headers = {"x-csrf-token": csrf} if csrf else None
    response: Response = api_client.post(
        "/api/v1/payslip/payslips",
        json=payload,
        headers=headers,
    )
    return response


def test_payslip_requires_auth(api_client: TestClient) -> None:
    api_client.cookies.set("csrf_token", "test-csrf")
    assert _create(api_client).status_code == HTTPStatus.UNAUTHORIZED


def test_amount_to_words_inr_lakh_and_paise() -> None:
    assert amount_to_words_inr(Decimal("123456.78")) == (
        "One Lakh Twenty Three Thousand Four Hundred Fifty Six "
        "and Seventy Eight Paise Only"
    )


def test_amount_to_words_inr_crore_and_zero() -> None:
    assert amount_to_words_inr(Decimal("125000000")) == "Twelve Crore Fifty Lakh Only"
    assert amount_to_words_inr(Decimal("0")) == "Zero Only"


def test_calculate_payslip_net_math() -> None:
    result = calculate_payslip(
        Decimal("5000"),
        Decimal("2000"),
        [Decimal("750")],
    )
    assert result["gross"] == Decimal("7000")
    assert result["net"] == Decimal("6250")
    assert str(result["net_in_words"]).endswith("Six Thousand Two Hundred Fifty Only")


@pytest.mark.parametrize(
    "overrides",
    [
        {"month": "26-01"},
        {"total_working_days": 32},
        {"basic": -1},
        {"deduction_lines": [{"label": "PF", "amount": -5}]},
    ],
)
def test_payslip_validation_rejects_bad_payloads(
    authenticated_client: TestClient,
    overrides: dict[str, object],
) -> None:
    response = _create(authenticated_client, overrides)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_and_get_payslip_roundtrip(authenticated_client: TestClient) -> None:
    response = _create(authenticated_client)
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["status"] == "draft"
    assert Decimal(str(body["gross"])) == Decimal("7000")
    assert Decimal(str(body["net"])) == Decimal("6250")
    assert body["net_in_words"].endswith("Only")
    line_kinds = {line["kind"] for line in body["lines"]}
    assert {"earning", "deduction"} <= line_kinds

    fetched = authenticated_client.get(f"/api/v1/payslip/payslips/{body['id']}")
    assert fetched.status_code == HTTPStatus.OK
    assert fetched.json()["id"] == body["id"]


def test_list_and_lifecycle(authenticated_client: TestClient) -> None:
    created = _create(authenticated_client)
    payslip_id = created.json()["id"]

    listed = authenticated_client.get("/api/v1/payslip/payslips?month=2026-01")
    assert listed.status_code == HTTPStatus.OK
    assert any(row["id"] == payslip_id for row in listed.json())

    csrf = authenticated_client.cookies.get("csrf_token")
    headers = {"x-csrf-token": csrf} if csrf else None
    generated = authenticated_client.post(
        f"/api/v1/payslip/payslips/{payslip_id}/generate",
        headers=headers,
    )
    assert generated.status_code == HTTPStatus.OK
    assert generated.json()["status"] == "generated"

    sent = authenticated_client.post(
        f"/api/v1/payslip/payslips/{payslip_id}/send",
        headers=headers,
    )
    assert sent.status_code == HTTPStatus.OK
    assert sent.json()["status"] == "sent"

    second_id = _create(authenticated_client, {"employee_code": "EMP-002"}).json()["id"]
    invalid_transition = authenticated_client.post(
        f"/api/v1/payslip/payslips/{second_id}/send",
        headers=headers,
    )
    assert invalid_transition.status_code == HTTPStatus.BAD_REQUEST
