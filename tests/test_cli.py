from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest

from bank_statement_extractor import cli


def assert_amount(expected: str, actual: Decimal) -> None:
    assert Decimal(expected) == actual


def test_parses_positive_amount() -> None:
    line = "01.01.2024 Gehalt Arbeitgeber 1.500,00"

    result = cli.convert_bank_statement(line)

    assert_amount("1500.00", result["in"])
    assert_amount("0.00", result["out"])


def test_parses_negative_amount() -> None:
    line = "05.01.2024 REWE Markt -49,99"

    result = cli.convert_bank_statement(line)

    assert_amount("-49.99", result["out"])
    assert_amount("0.00", result["in"])


def test_accumulates_multiple_transactions() -> None:
    text = "01.01.2024 Gehalt 1.000,00\n05.01.2024 REWE Markt -49,99\n10.01.2024 LIDL -12,49"

    result = cli.convert_bank_statement(text)

    assert_amount("1000.00", result["in"])
    assert_amount("-62.48", result["out"])


@pytest.mark.parametrize(
    "line",
    (
        "31.01.2024 Kontostand/Saldo -200,00",
        "01.01.2024 Freistellungsauftrag 801,00",
        "01.01.2024 Sparer-Pauschbetrag 100,00",
    ),
)
def test_ignores_non_transaction_amount_lines(line: str) -> None:
    result = cli.convert_bank_statement(line)

    assert_amount("0.00", result["in"])
    assert_amount("0.00", result["out"])


def test_non_matching_line_is_ignored() -> None:
    line = "This is not a transaction line"

    result = cli.convert_bank_statement(line)

    assert_amount("0.00", result["in"])
    assert_amount("0.00", result["out"])


def test_categorizes_grocery_transaction() -> None:
    line = "05.01.2024 REWE Markt -49,99"

    result = cli.convert_bank_statement(line)

    assert_amount("-49.99", result["rewe"])


@pytest.mark.parametrize(
    ("description", "category"),
    (
        ("E-CENTER Einkauf", "e-center"),
        ("dm Drogeriemarkt", "dm"),
        ("Rossmann Filiale", "rossmann"),
        ("ALDI SUED", "aldi"),
        ("NORMA SAGT DANKE", "norma"),
        ("Netto Marken-Discount", "netto"),
        ("AMZN Marketplace", "amazon"),
        ("HEM Tankstelle", "hem"),
        ("ARAL", "aral"),
        ("Sparen Tagesgeld", "sparen"),
        ("Versicherungsbeitrag", "versicherung"),
        ("Lebensversicherung", "versicherung"),
        ("Andere Vers.", "versicherung"),
        ("Vers.", "versicherung"),
        ("Krankenversicherungen", "versicherung"),
    ),
)
def test_categorizes_recovered_terms(description: str, category: str) -> None:
    transactions = cli.parse_bank_statement(f"05.01.2024 {description} -10,00")

    assert transactions[0].category == category


def test_does_not_false_positive_on_star() -> None:
    line = "05.01.2024 Sparkasse Duisburg -100,00"

    result = cli.convert_bank_statement(line)

    assert_amount("0.00", result["star"])


def test_categorizes_specific_fuel_merchant_before_generic_term() -> None:
    line = "05.01.2024 Aral Tankstelle -60,00"

    result = cli.convert_bank_statement(line)

    assert_amount("-60.00", result["aral"])
    assert_amount("0.00", result["tank"])


@pytest.mark.parametrize("description", ("Geldmarkt", "Themenladen", "Startguthaben"))
def test_short_category_terms_only_match_whole_words(description: str) -> None:
    transactions = cli.parse_bank_statement(f"05.01.2024 {description} -10,00")

    assert transactions[0].category is None


def test_column_order_is_consistent_across_runs() -> None:
    keys1 = list(cli.GROUPS)
    keys2 = list(cli.GROUPS)

    assert keys1 == keys2
    assert keys1 == ["Grocery", "Shopping", "Fuel", "Order", "Insurance", "Income", "Consumption"]


def test_all_group_categories_have_matchers() -> None:
    grouped_categories = {category for categories in cli.GROUPS.values() for category in categories}

    assert grouped_categories == set(cli.CATEGORY_PATTERNS)


def test_rejects_malformed_date_in_line() -> None:
    line = "1.2.3 Zahlung -50,00"

    result = cli.convert_bank_statement(line)

    assert_amount("0.00", result["in"])
    assert_amount("0.00", result["out"])


def test_accepts_valid_german_date() -> None:
    line = "15.03.2024 Gehalt 2.000,00"

    result = cli.convert_bank_statement(line)

    assert_amount("2000.00", result["in"])


def test_parses_transaction_rows() -> None:
    transactions = cli.parse_bank_statement("01.01.2024 Gehalt Arbeitgeber 1.500,00\n05.01.2024 REWE Markt -49,99")

    assert transactions == [
        cli.Transaction(
            date="01.01.2024",
            name="Gehalt",
            descr="Arbeitgeber",
            amount=Decimal("1500.00"),
            category="gehalt",
            group="Income",
        ),
        cli.Transaction(
            date="05.01.2024", name="REWE", descr="Markt", amount=Decimal("-49.99"), category="rewe", group="Grocery"
        ),
    ]


def test_writes_tsv_rows() -> None:
    output = StringIO()

    cli.write_rows(
        [
            cli.Transaction(
                date="05.01.2024",
                name="REWE",
                descr="Markt",
                amount=Decimal("-49.99"),
                category="rewe",
                group="Grocery",
            )
        ],
        output,
        "tsv",
    )

    assert output.getvalue() == (
        "date\tname\tdescr\tamount\tcategory\tgroup\n05.01.2024\tREWE\tMarkt\t-49.99\trewe\tGrocery\n"
    )


def test_main_extracts_pdf_and_writes_rows(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        cli,
        "extract_text",
        lambda path: "01.01.2024 Gehalt Arbeitgeber 1.500,00\n05.01.2024 REWE Markt -49,99",
    )

    cli.main(["/tmp/statement.pdf"])

    assert capsys.readouterr().out == (
        "date,name,descr,amount,category,group\n01.01.2024,Gehalt,Arbeitgeber,1500.00,gehalt,Income\n05.01.2024,REWE,Markt,-49.99,rewe,Grocery\n"
    )


def test_main_supports_tsv_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "extract_text", lambda path: "05.01.2024 REWE Markt -49,99")

    cli.main(["--format", "tsv", "/tmp/statement.pdf"])

    assert capsys.readouterr().out == (
        "date\tname\tdescr\tamount\tcategory\tgroup\n05.01.2024\tREWE\tMarkt\t-49.99\trewe\tGrocery\n"
    )


def test_extracts_text_from_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.write_bytes(
        b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 68 >>
stream
BT
/F1 12 Tf
72 720 Td
(01.01.2024 Gehalt Arbeitgeber 1.500,00) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000311 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
429
%%EOF
"""
    )

    assert cli.extract_text(pdf_path) == "01.01.2024 Gehalt Arbeitgeber 1.500,00"
