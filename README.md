# FNB Bank Statement PDF -> CSV

This project converts FNB Easy Account statement PDFs into a transaction CSV that matches the supplied transaction-history format.

```csv
Date,Amount,Balance,Description
```

## Why this approach

The original `vitali84/pdf-to-csv-table-extactor` project is designed primarily for scanned PDFs using image processing and OCR. The supplied FNB statement contains a machine-readable text/table layer, so this implementation uses `pdfplumber` first for better accuracy and lower complexity.

## Convert one PDF

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
python src/bank_pdf_to_csv.py "EASY ACCOUNT 25.pdf" -o transactions.csv
```

## Convert a folder of PDFs

```bash
python src/bank_pdf_to_csv.py ./statements -o transactions.csv
```

## Output convention

- Credits become positive amounts (`199.00`).
- Debits become negative amounts (`-199.00`).
- Balance is stored as the numeric value shown by the bank.
- Core columns match the existing transaction-history CSV so multiple statements can later be merged into one master history.

## Current scope

This first version is tailored to the FNB Easy Account statement layout. Statements whose transaction descriptions are not exposed cleanly in the PDF text layer may need an OCR/layout fallback profile.

## Project structure

```text
PDF2CSV/
├── README.md
├── requirements.txt
├── src/
│   └── bank_pdf_to_csv.py
└── examples/
    └── EASY_ACCOUNT_25_transactions.csv
```
