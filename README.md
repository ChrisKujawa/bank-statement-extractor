# bank-statement-extractor
Tool to extract and categorize data from bank statements, specialized to ING Bank DE.

## Installation

This project uses the [`uv` package manager](https://docs.astral.sh/uv/). Follow the
[official installation guide](https://docs.astral.sh/uv/getting-started/installation/),
then install the command from a local checkout:

```bash
uv tool install .
```

This installs the `bank-statement-extractor` command.

## Usage

Run the CLI with a bank statement PDF:

```bash
bank-statement-extractor /path/to/bank.pdf
```

If no path is provided, the CLI reads `/tmp/bank.pdf`:

```bash
bank-statement-extractor
```

The default output writes one row per extracted transaction:

```csv
date;name;descr;amount;category
01.01.2024;Gehalt;Arbeitgeber;1500,00;
05.01.2024;REWE;Markt;-49,99;rewe
```

To keep the old categorized totals, use the `sum` subcommand:

```bash
bank-statement-extractor sum /path/to/bank.pdf
```

```csv
title;in;out;Grocery;Shopping;Fuel;Order;Insurance
bank.pdf;1500,00;-62,48;-62,48;0,00;0,00;0,00;0,00
```

Both modes support CSV and TSV output. CSV uses `;` as the field separator, TSV uses tabs;
both use `,` as the decimal separator (avoids Google Sheets misreading amounts like `1964.07`
as dates on import):

```bash
bank-statement-extractor --format tsv /path/to/bank.pdf
bank-statement-extractor sum --format tsv /path/to/bank.pdf
```

## Development

The project dependencies are declared in `pyproject.toml` and locked in `uv.lock`.
Create the development environment:

```bash
uv sync
```

Run formatting, type checks, linting, and tests:

```bash
make format
make check
```
