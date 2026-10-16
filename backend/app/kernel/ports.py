"""Port interfaces for cross-module communication (D-ARCH-01).

Protocol classes: modules talk through these seams, never through each other's
tables. doc/architecture 3.4.
"""
from typing import Any, Protocol


class EmployeeDirectoryPort(Protocol):
    def get_employee(self, employee_code: str) -> dict[str, Any] | None: ...
    def list_employees(self) -> list[dict[str, Any]]: ...


class CompanyProfilePort(Protocol):
    def get_profile(self) -> dict[str, Any]: ...


class BillIntakePort(Protocol):
    def submit_draft(
        self, file_id: str, source: str, meta: dict[str, Any] | None = None
    ) -> str: ...


class PdfPort(Protocol):
    def generate_pdf(self, html: str) -> bytes: ...


class FileStoragePort(Protocol):
    def upload(self, data: bytes, mime: str, key: str) -> str: ...
    def download(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> None: ...


class SequencePort(Protocol):
    def next_serial(self, series: str, fy: str | None = None) -> str: ...


class MailPort(Protocol):
    def send(self, to: str, subject: str, body: str, attachment: bytes | None = None) -> bool: ...


class InboundChannelPort(Protocol):
    def submit_draft(
        self, file_id: str, source: str, meta: dict[str, Any] | None = None
    ) -> str: ...


class MessagingPort(Protocol):
    def send_reply(self, to: str, message: str) -> bool: ...


class ExtractionPort(Protocol):
    def extract(self, file_path: str) -> dict[str, Any]: ...
