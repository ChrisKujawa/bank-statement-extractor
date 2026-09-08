from __future__ import annotations

import argparse
import csv
import sys
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from re import compile as compile_pattern
from typing import TextIO

from pypdf import PdfReader

TRANSACTION_PATTERN = compile_pattern(
    r"^([0-3][0-9]\.[0-1][0-9]\.[0-9]{4}) (.+) (-?[0-9.]*[0-9]+,[0-9]+)$"
)

CATEGORIES = OrderedDict(
    (category, Decimal("0"))
    for category in (
        "amazon",
        "paypal",
        "tank",
        "rewe",
        "kaufland",
        "edeka",
        "lidl",
        "star",
        "dauerauftrag",
    )
)

GROUPS = OrderedDict(
    (
        ("Grocery", ("rewe", "lidl", "edeka", "kaufland")),
        ("Shopping", ("amazon", "paypal")),
        ("Fuel", ("tank", "star")),
        ("Order", ("dauerauftrag",)),
    )
)

OUT_KEY = "out"
IN_KEY = "in"
IGNORED_TERMS = ("saldo", "freistellungsauftrag", "sparer-pauschbetrag")
DEFAULT_PDF_PATH = Path("/tmp/bank.pdf")


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def convert_bank_statement(text: str) -> dict[str, Decimal]:
    amounts = OrderedDict((category, Decimal("0")) for category in CATEGORIES)
    amounts[OUT_KEY] = Decimal("0")
    amounts[IN_KEY] = Decimal("0")

    for line in text.splitlines():
        match = TRANSACTION_PATTERN.match(line)
        normalized_line = line.lower()
        if match is None or any(term in normalized_line for term in IGNORED_TERMS):
            continue

        value = _parse_german_decimal(match.group(3))
        if value >= 0:
            amounts[IN_KEY] += value
        else:
            amounts[OUT_KEY] += value

        description = match.group(2).lower()
        for category in CATEGORIES:
            if category in description:
                amounts[category] += value
                break

    return amounts


def write_csv(file_name: str, amounts: dict[str, Decimal], output: TextIO) -> None:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("title", IN_KEY, OUT_KEY, *GROUPS.keys()))
    group_totals = (
        _format_decimal(
            sum((amounts.get(category, Decimal("0")) for category in categories), Decimal("0"))
        )
        for categories in GROUPS.values()
    )
    writer.writerow(
        (
            file_name,
            _format_decimal(amounts.get(IN_KEY, Decimal("0"))),
            _format_decimal(amounts.get(OUT_KEY, Decimal("0"))),
            *group_totals,
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Extract categorized CSV data from an ING bank statement PDF."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        default=DEFAULT_PDF_PATH,
        help=f"Path to the statement PDF. Defaults to {DEFAULT_PDF_PATH}.",
    )
    args = parser.parse_args(argv)

    text = extract_text(args.pdf)
    amounts = convert_bank_statement(text)
    write_csv(args.pdf.name, amounts, sys.stdout)


def _parse_german_decimal(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def _format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"
