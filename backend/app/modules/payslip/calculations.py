"""Payslip arithmetic + Indian-numbering amount-to-words (F-PAY-09, C-04)."""
import decimal

_TENS = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]


HUNDRED = 100
TWENTY = 20
CRORE = 10**7
LAKH = 10**5
THOUSAND = 10**3


def _convert_hundreds(n: int) -> str:
    if n == 0:
        return ""
    parts = []
    if n >= HUNDRED:
        parts.append(_ONES[n // HUNDRED] + " Hundred")
        n %= HUNDRED
    if n >= TWENTY:
        parts.append(_TENS[n // 10])
        n %= 10
    if n > 0:
        parts.append(_ONES[n])
    return " ".join(parts)


def _two_digit_words(n: int) -> str:
    if n < TWENTY:
        return _ONES[n]
    return _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


MILLION_IN_LAKH = 100  # 1 crore = 100 lakh: used to expand big crores


def _crore_words(crore: int) -> str:
    # Crore itself can exceed 99, so expand it in Indian style recursively.
    crore_rupees = crore
    parts = []
    if crore_rupees >= CRORE:
        parts.append(_crore_words(crore_rupees // CRORE) + " Crore")
        crore_rupees %= CRORE
    if crore_rupees >= MILLION_IN_LAKH:
        parts.append(_convert_hundreds(crore_rupees // MILLION_IN_LAKH) + " Crore Hundred")
        crore_rupees %= MILLION_IN_LAKH
    if crore_rupees:
        parts.append(_two_digit_words(crore_rupees) + " Crore")
    return " ".join(parts)


def amount_to_words_inr(amount: decimal.Decimal) -> str:
    """Indian numbering: crore, lakh, thousand, then hundreds (C-04)."""
    if amount == 0:
        return "Zero Only"
    rupees = int(amount)
    paise = round((amount - rupees) * HUNDRED)
    parts = []
    crore, rem = divmod(rupees, CRORE)
    lakh, rem = divmod(rem, LAKH)
    thousand, rem = divmod(rem, THOUSAND)
    if crore:
        parts.append(_crore_words(crore))
    if lakh:
        parts.append(_two_digit_words(lakh) + " Lakh")
    if thousand:
        parts.append(_convert_hundreds(thousand) + " Thousand")
    if rem:
        parts.append(_convert_hundreds(rem))
    result = " ".join(p for p in parts if p)
    if paise:
        result = (result + " and " + _two_digit_words(paise) + " Paise").strip()
    return (result + " Only").strip()


def calculate_payslip(
    basic: decimal.Decimal,
    other_allowances: decimal.Decimal,
    deductions: list[decimal.Decimal],
) -> dict[str, decimal.Decimal | str]:
    """Gross = Basic + allowances; Net = Gross - deductions; words for Net."""
    gross = basic + other_allowances
    total_deductions = sum(deductions, decimal.Decimal("0"))
    net = gross - total_deductions
    return {
        "gross": gross,
        "total_deductions": total_deductions,
        "net": net,
        "net_in_words": amount_to_words_inr(net),
    }
