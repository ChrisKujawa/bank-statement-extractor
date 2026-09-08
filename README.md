# bank-statement-extractor
Tool to extract and categorize data from bank statements, specialized to ING Bank DE.

## Installation

Install from a local checkout:

```bash
python -m pip install .
```

For development, install it in editable mode:

```bash
python -m pip install -e .
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

The output has one row for the input file:

```csv
title,in,out,Grocery,Shopping,Fuel,Order
bank.pdf,1500.00,-62.48,-62.48,0.00,0.00,0.00
```

If the command is not on your `PATH` after a user install, run it from Python's user script
directory:

```bash
~/.local/bin/bank-statement-extractor /path/to/bank.pdf
```

## Development

Install test dependencies and run the test suite:

```bash
python -m pip install -e '.[test]'
python -m pytest
```
