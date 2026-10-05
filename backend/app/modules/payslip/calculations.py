import decimal
import re


_UNITS = ["", "Thousand", "Lakh", "Crore"]
_TENS = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]


def _convert_hundreds(n: int) -> str:
    if n == 0:
        return ""
    parts = []
    if n >= 100:
        parts.append(_ONES[n // 100] + " Hundred")
        n %= 100
    if n >= 20:
        parts.append(_TENS[n // 10])
        n %= 10
    if n > 0:
        parts.append(_ONES[n])
    return " ".join(parts)


def amount_to_words_inr(amount: decimal.Decimal) -> str:
    if amount == 0:
        return "Zero"
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    if rupees == 0:
        result = ""
    else:
        parts = []
        n = rupees
        crore = n // 10000000
        n %= 10000000
        lakh = n // 100000
        n %= 100000
        thousand = n // 1000
        n %= 1000
        if crore:
            parts.append(_convert_hundreds(crore) + " Crore")
        if lakh:
            parts.append(_convert_hundreds(lakh) + " Lakh")
        if thousand:
            parts.append(_convert_hundreds(thousand) + " Thousand")
        if n:
            parts.append(_convert_hundreds(n))
        result = " ".join(parts)
    if paise:
        result += f" and {_convert_hundreds(paise)} Paise"
    return result.strip() + " Only"


def calculate_payslip(basic: decimal.Decimal, other_allowances: decimal.Decimal, deductions: list[decimal.Decimal]) -> dict:
    gross = basic + other_allowances
    total_deductions = sum(deductions, decimal.Decimal(0))
    net = gross - total_deductions
    return {
        "gross": gross,
        "total_deductions": total_deductions,
        "net": net,
        "net_in_words": amount_to_words_inr(net),
    }