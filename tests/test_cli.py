from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest

from bank_statement_extractor import cli


def assert_amount(expected: str, actual: Decimal) -> None:
    assert Decimal(expected) == actual


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
        ("VISA Muster Backstube", "baecker"),
        ("Stadtbackerei Nord", "baecker"),
        ("Boulangerie Exemple", "baecker"),
        ("VISA Decathlon Filiale", "decathlon"),
        ("VISA Levis Shop Online", "levis"),
        ("VISA Smyths Spielwaren", "smyths"),
        ("VISA Marykay Kosmetik", "marykay"),
        ("VISA Beispiel Baumarkt Hellweg", "baumarkt"),
        ("VISA Agip Service Station", "agip"),
        ("VISA Total Service Station", "total"),
        ("Muster Bausparkasse AG", "bausparkasse"),
        ("Familien kasse Auszahlung", "kindergeld"),
        ("Telekom Rechnung", "telekom"),
        ("Vodafone Vertrag", "telekom"),
        ("Klarmobil Tarif", "telekom"),
        ("Rundfunk Beitrag Service", "rundfunk"),
        ("Stadtreinigung Gebuehr", "stadtreinigung"),
        ("VISA Muster Apotheke", "apotheke"),
        ("Dr. med. Mustermann", "arzt"),
        ("Fitnessstudio Beispiel", "fitness"),
        ("VISA Beispiel Restaurant", "restaurant"),
        ("VISA Grillhaus Muster", "restaurant"),
        ("KITA Gebuehr Beispiel", "kita"),
        ("VISA Nahverkehr BVG", "bvg"),
        ("Bargeldauszahlung Automat", "bargeld"),
    ),
)
def test_categorizes_recovered_terms(description: str, category: str) -> None:
    transactions = cli.parse_bank_statement(f"05.01.2024 {description} -10,00")

    assert transactions[0].category == category


@pytest.mark.parametrize("description", ("Geldmarkt", "Themenladen", "Startguthaben"))
def test_short_category_terms_only_match_whole_words(description: str) -> None:
    transactions = cli.parse_bank_statement(f"05.01.2024 {description} -10,00")

    assert transactions[0].category is None


def test_column_order_is_consistent_across_runs() -> None:
    keys1 = list(cli.GROUPS)
    keys2 = list(cli.GROUPS)

    assert keys1 == keys2
    assert keys1 == [
        "Grocery",
        "Shopping",
        "Fuel",
        "Order",
        "Insurance",
        "Income",
        "Consumption",
        "Health",
        "Leisure",
        "Family",
        "Transport",
        "Cash",
    ]


def test_all_group_categories_have_matchers() -> None:
    grouped_categories = {category for categories in cli.GROUPS.values() for category in categories}

    assert grouped_categories == set(cli.CATEGORY_PATTERNS)


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


def test_parses_transaction_rows_with_whitespaces() -> None:
    transactions = cli.parse_bank_statement(
        "01.01.2024 Lastschrift Amazon\t more, text\t  than usual here 1.500,00\n05.01.2024 REWE Markt -49,99"
    )

    assert transactions[0] == cli.Transaction(
        date="01.01.2024",
        name="Lastschrift",
        descr="Amazon more, text than usual here",
        amount=Decimal("1500.00"),
        category="amazon",
        group="Shopping",
    )

    assert transactions[1] == cli.Transaction(
        date="05.01.2024", name="REWE", descr="Markt", amount=Decimal("-49.99"), category="rewe", group="Grocery"
    )


def test_should_skip_non_bank_statement() -> None:
    transactions = cli.parse_bank_statement("Hallo world ; Foo Bar \n 05.01.2024 REWE Markt -49,99")

    assert transactions == [
        cli.Transaction(
            date="05.01.2024", name="REWE", descr="Markt", amount=Decimal("-49.99"), category="rewe", group="Grocery"
        ),
    ]


def test_should_skip_ignored_terms() -> None:
    transactions = cli.parse_bank_statement("Saldo -01,11 \n 05.01.2024 REWE Markt -49,99")

    assert transactions == [
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
