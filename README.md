# bank-statement-extractor
Tool to extract and categorize data from bank statements, specialized to ING Bank DE.

## Usage

Install the package locally:

```bash
python -m pip install -e .
```

Extract a statement as CSV:

```bash
bank-statement-extractor /path/to/bank.pdf
```

If no path is provided, the tool reads `/tmp/bank.pdf`.

The output has one row for the input file:

```csv
title,in,out,Grocery,Shopping,Fuel,Order
bank.pdf,1500.00,-62.48,-62.48,0.00,0.00,0.00
```

## Development

Install test dependencies and run the test suite:

```bash
python -m pip install -e '.[test]'
python -m pytest
```
