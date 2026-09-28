import argparse
import csv
import sys
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from re import compile as compile_pattern
from typing import TextIO

from pypdf import PdfReader

TRANSACTION_PATTERN = compile_pattern(r"^([0-3][0-9]\.[0-1][0-9]\.[0-9]{4}) (.+) (-?[0-9.]*[0-9]+,[0-9]+)$")

GROUPS = OrderedDict(
    (
        (
            "Grocery",
            (
                "rewe",
                "lidl",
                "edeka",
                "kaufland",
                "e-center",
                "dm",
                "rossmann",
                "aldi",
                "norma",
                "netto",
                "baecker",
            ),
        ),
        (
            "Shopping",
            (
                "amazon",
                "paypal",
                "decathlon",
                "levis",
                "smyths",
                "marykay",
                "baumarkt",
            ),
        ),
        ("Fuel", ("tank", "star", "hem", "aral", "agip", "total")),
        ("Order", ("dauerauftrag", "sparen", "bausparkasse")),
        ("Insurance", ("versicherung",)),
        ("Income", ("gehalt", "lohn", "kindergeld")),
        ("Consumption", ("strom", "wasser", "gas", "telekom", "rundfunk", "stadtreinigung")),
        ("Health", ("apotheke", "arzt")),
        ("Leisure", ("fitness", "restaurant")),
        ("Family", ("kita",)),
        ("Transport", ("bvg",)),
        ("Cash", ("bargeld",)),
    )
)

CATEGORY_PATTERNS = OrderedDict(
    (
        ("rewe", compile_pattern(r"\brewe\b")),
        ("lidl", compile_pattern(r"\blidl\b")),
        ("edeka", compile_pattern(r"\bedeka\b")),
        ("kaufland", compile_pattern(r"\bkaufland\b")),
        ("e-center", compile_pattern(r"\be-center\b")),
        ("dm", compile_pattern(r"\bdm\b")),
        ("rossmann", compile_pattern(r"\brossmann\b")),
        ("aldi", compile_pattern(r"\baldi\b")),
        ("norma", compile_pattern(r"\bnorma\b")),
        ("netto", compile_pattern(r"\bnetto\b")),
        ("amazon", compile_pattern(r"\b(?:amazon|amzn)\b")),
        ("paypal", compile_pattern(r"\bpaypal\b")),
        ("star", compile_pattern(r"\bstar\b")),
        ("hem", compile_pattern(r"\bhem\b")),
        ("aral", compile_pattern(r"\baral\b")),
        ("tank", compile_pattern(r"\btank\w*")),
        ("dauerauftrag", compile_pattern(r"\bdauerauftrag\b")),
        ("sparen", compile_pattern(r"\bsparen\b")),
        ("lohn", compile_pattern(r"\blohn\b")),
        ("gehalt", compile_pattern(r"\bgehalt\b")),
        ("versicherung", compile_pattern(r"\b\w*(vers)(icherung)?\w*")),
        ("strom", compile_pattern(r"\b\w*strom\w*")),
        ("wasser", compile_pattern(r"\b\w*wasser\w*")),
        ("gas", compile_pattern(r"\b\w*gas\w*")),
        ("baecker", compile_pattern(r"\b(?:backstube|backhaus|b[ae]ckerei|boulangerie|stadtbackerei)\w*")),
        ("decathlon", compile_pattern(r"\bdecathlon\b")),
        ("levis", compile_pattern(r"\blevis\b")),
        ("smyths", compile_pattern(r"\bsmyths\b")),
        ("marykay", compile_pattern(r"\bmarykay\b")),
        ("baumarkt", compile_pattern(r"\b(?:hellweg|thomas philipps|pflanzen-koelle|maec geiz)\w*")),
        ("agip", compile_pattern(r"\bagip\b")),
        ("total", compile_pattern(r"\btotal service\b")),
        ("bausparkasse", compile_pattern(r"\b(?:wuestenrot|bausparkasse)\w*")),
        ("kindergeld", compile_pattern(r"\bfamilien\s*kasse\b")),
        ("telekom", compile_pattern(r"\b(?:telekom|vodafone|otelo|klarmobil)\w*")),
        ("rundfunk", compile_pattern(r"\brundfunk\b")),
        ("stadtreinigung", compile_pattern(r"\bstadtreinigung\w*")),
        ("apotheke", compile_pattern(r"\bapotheke\w*")),
        ("arzt", compile_pattern(r"\bdr\.?\s*med\b")),
        ("fitness", compile_pattern(r"\b(?:fitx|fitness)\w*")),
        ("restaurant", compile_pattern(r"\b(?:restaurant\w*|grillhaus|marche|five guys|kinowelt|levy restaurants)\b")),
        ("kita", compile_pattern(r"\bkita\w*")),
        ("bvg", compile_pattern(r"\bbvg\b")),
        ("bargeld", compile_pattern(r"\bbargeldauszahlung\w*")),
    )
)

CATEGORIES = OrderedDict((category, Decimal(0)) for category in CATEGORY_PATTERNS)

OUT_KEY = "out"
IN_KEY = "in"
IGNORED_TERMS = ("saldo", "freistellungsauftrag", "sparer-pauschbetrag")
DEFAULT_PDF_PATH = Path("/tmp/bank.pdf")


@dataclass(frozen=True)
class Transaction:
    date: str
    name: str
    descr: str
    amount: Decimal
    category: str | None
    group: str | None


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_bank_statement(text: str) -> list[Transaction]:
    transactions: list[Transaction] = []

    for line in text.splitlines():
        line = line.strip()
        match = TRANSACTION_PATTERN.match(line)
        normalized_line = line.lower()
        if match is None or any(term in normalized_line for term in IGNORED_TERMS):
            continue

        description = match.group(2)
        name, descr = _split_description(description)
        category = _categorize_description(description)
        group = _find_group(category)
        transactions.append(
            Transaction(
                date=match.group(1),
                name=name,
                descr=descr,
                amount=_parse_german_decimal(match.group(3)),
                category=category,
                group=group,
            )
        )

    return transactions


def write_rows(transactions: list[Transaction], output: TextIO, output_format: str = "csv") -> None:
    writer = csv.writer(output, delimiter=_delimiter(output_format), lineterminator="\n")
    writer.writerow(("date", "name", "descr", "amount", "category", "group"))
    for transaction in transactions:
        writer.writerow(
            (
                transaction.date,
                transaction.name,
                transaction.descr,
                _format_decimal(transaction.amount),
                transaction.category or "",
                transaction.group or "",
            )
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract data from an ING bank statement PDF.")
    parser.add_argument(
        "--format",
        choices=("csv", "tsv"),
        default="csv",
        help="Output format. Defaults to csv.",
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        type=Path,
        default=[DEFAULT_PDF_PATH],
        help=f"Path to statement PDFs. Defaults to {DEFAULT_PDF_PATH}.",
    )
    args = parser.parse_args(argv)

    transactions: list[Transaction] = []
    for pdf_path in args.pdfs:
        transactions.extend(parse_bank_statement(extract_text(pdf_path)))
    write_rows(transactions, sys.stdout, args.format)


def _categorize_description(description: str) -> str | None:
    normalized_description = description.lower()
    for category, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(normalized_description):
            return category
    return None


def _find_group(category: str) -> str | None:
    for group, list in GROUPS.items():
        for group_category in list:
            if group_category == category:
                return group
    return None


def _split_description(description: str) -> tuple[str, str]:
    parts = description.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1].split())


def _delimiter(output_format: str) -> str:
    if output_format == "tsv":
        return "\t"
    return ","


def _parse_german_decimal(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def _format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"
