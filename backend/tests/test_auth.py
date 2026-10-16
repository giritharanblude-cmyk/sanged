"""Authentication API tests for V-AUTH-01..06."""

import re
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.kernel import models
from app.kernel.auth import lock_ttl_seconds
from tests.factories import make_user

PASSWORD = "correct-horse-1"
OTP_MAX_ATTEMPTS = 5


def _otp_from_messages(messages: list[str]) -> str:
    codes: list[str] = re.findall(r"code is: (\d{6})", "\n".join(messages))
    assert codes, "email adapter should deliver the test OTP"
    return codes[-1]


def _login(api_client: TestClient, email_outbox: list[str]) -> str:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK
    return _otp_from_messages(email_outbox)


def _csrf_headers(api_client: TestClient) -> dict[str, str]:
    token = api_client.cookies.get("csrf_token")
    assert token
    return {"x-csrf-token": token}


def test_health_open_but_protected_routes_blocked(api_client: TestClient) -> None:
    """V-AUTH-06: protected endpoints reject requests without a session."""
    paths = (
        "/api/v1/payslip/payslips",
        "/api/v1/employees/employees",
        "/api/v1/bills/bills",
        "/api/v1/inventory/items",
        "/api/v1/auth/me",
    )
    for path in paths:
        response = api_client.get(path)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, path


def test_correct_password_alone_does_not_create_session(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """V-AUTH-01: password success only issues an OTP."""
    make_user(db)
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK
    assert "session" not in response.cookies
    assert response.json()["message"]
    code = _otp_from_messages(email_outbox)
    assert code not in response.text


def test_wrong_password_is_rejected(api_client: TestClient, db: Session) -> None:
    make_user(db)
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "incorrect-password"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "invalid_credentials"


def test_login_otp_me_and_logout_flow(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """V-AUTH-01, V-AUTH-05, V-AUTH-06: login, /me and session revocation."""
    make_user(db)
    code = _login(api_client, email_outbox)
    verified = api_client.post(
        "/api/v1/auth/verify-otp",
        json={"username": "admin", "otp": code},
    )
    assert verified.status_code == HTTPStatus.OK
    assert api_client.cookies.get("session")
    assert api_client.cookies.get("csrf_token")

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == HTTPStatus.OK
    assert me.json() == {"username": "admin", "role": "master"}

    denied_without_csrf = api_client.post("/api/v1/auth/logout")
    assert denied_without_csrf.status_code == HTTPStatus.FORBIDDEN
    logged_out = api_client.post("/api/v1/auth/logout", headers=_csrf_headers(api_client))
    assert logged_out.status_code == HTTPStatus.OK
    assert api_client.get("/api/v1/auth/me").status_code == HTTPStatus.UNAUTHORIZED


def test_reused_otp_is_rejected(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """V-AUTH-02: a consumed OTP cannot create another session."""
    make_user(db)
    code = _login(api_client, email_outbox)
    payload = {"username": "admin", "otp": code}
    assert api_client.post("/api/v1/auth/verify-otp", json=payload).status_code == HTTPStatus.OK
    reused = api_client.post("/api/v1/auth/verify-otp", json=payload)
    assert reused.status_code == HTTPStatus.UNAUTHORIZED


def test_expired_otp_is_rejected(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """V-AUTH-02: expired challenges do not create sessions."""
    make_user(db)
    code = _login(api_client, email_outbox)
    challenge = db.query(models.OtpChallenge).one()
    challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    response = api_client.post(
        "/api/v1/auth/verify-otp",
        json={"username": "admin", "otp": code},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "otp_expired"


def test_sixth_incorrect_otp_attempt_is_rejected(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """V-AUTH-02: a challenge is locked after five wrong codes."""
    make_user(db)
    code = _login(api_client, email_outbox)
    wrong_code = "000000" if code != "000000" else "000001"
    payload = {"username": "admin", "otp": wrong_code}
    for _ in range(OTP_MAX_ATTEMPTS):
        response = api_client.post("/api/v1/auth/verify-otp", json=payload)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    sixth = api_client.post("/api/v1/auth/verify-otp", json=payload)
    assert sixth.status_code == HTTPStatus.UNAUTHORIZED
    assert sixth.json()["code"] == "otp_locked"


def test_otp_resend_cooldown(api_client: TestClient, db: Session) -> None:
    """F-AUTH-02: a second login OTP request within 60 seconds is throttled."""
    make_user(db)
    payload = {"username": "admin", "password": PASSWORD}
    assert api_client.post("/api/v1/auth/login", json=payload).status_code == HTTPStatus.OK
    again = api_client.post("/api/v1/auth/login", json=payload)
    assert again.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert again.json()["code"] == "otp_cooldown"


def test_account_lockout_after_failed_logins(api_client: TestClient, db: Session) -> None:
    """V-AUTH-04: failed logins create a Redis-backed temporary account lock."""
    make_user(db)
    payload = {"username": "admin", "password": "incorrect-password"}
    for _ in range(OTP_MAX_ATTEMPTS):
        api_client.post("/api/v1/auth/login", json=payload)

    locked = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert locked.status_code == HTTPStatus.LOCKED
    assert locked.json()["code"] == "account_locked"
    assert lock_ttl_seconds("admin") > 0


def test_password_change_requires_valid_otp(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> None:
    """F-AUTH-03, V-AUTH-03: invalid and valid OTP password changes."""
    make_user(db)
    login_code = _login(api_client, email_outbox)
    assert (
        api_client.post(
            "/api/v1/auth/verify-otp",
            json={"username": "admin", "otp": login_code},
        ).status_code
        == HTTPStatus.OK
    )
    headers = _csrf_headers(api_client)
    api_client.post("/api/v1/auth/change-password/init", headers=headers)
    change_code = _otp_from_messages(email_outbox)
    wrong_code = "000000" if change_code != "000000" else "000001"

    invalid = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": PASSWORD,
            "new_password": "brand-new-pass-1",
            "otp": wrong_code,
        },
    )
    assert invalid.status_code == HTTPStatus.UNAUTHORIZED

    changed = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": PASSWORD,
            "new_password": "brand-new-pass-1",
            "otp": change_code,
        },
    )
    assert changed.status_code == HTTPStatus.OK
    assert db.query(models.AuditLog).filter_by(action="password_change").count() > 0
