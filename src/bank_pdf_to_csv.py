#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
)}


def money(value: str) -> tuple[float, str | None]:
    value = (value or "").replace(",", "").strip()
    marker = None
    if value.lower().endswith("cr"):
        marker = "Cr"
        value = value[:-2]
    elif value.lower().endswith("dr"):
        marker = "Dr"
        value = value[:-2]
    elif value.lower().endswith("c"):
        marker = "Cr"
        value = value[:-1]
    elif value.lower().endswith("d"):
        marker = "Dr"
        value = value[:-1]
    return float(value), marker


def statement_end_year(text: str) -> int:
    for pattern in (
        r"Statement Date\s*:\s*\d{1,2}\s+\w+\s+(\d{4})",
        r"Statement Period\s*:.+?to\s+\d{1,2}\s+\w+\s+(\d{4})",
    ):
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return int(match.group(1))
    return datetime.now().year


def is_transaction_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3}", (value or "").strip()))


def find_transaction_table(page):
    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "intersection_tolerance": 5,
    }
    tables = page.find_tables(settings)
    for table_obj in tables:
        table = table_obj.extract()
        if not table:
            continue
        header = " ".join((cell or "") for cell in table[0]).lower()
        if all(word in header for word in ("date", "description", "amount", "balance")):
            return table
    return None


def clean_cell(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\n", " ")).strip()


def extract_pdf(pdf_path: Path) -> list[list[str]]:
    with pdfplumber.open(pdf_path) as pdf:
        all_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        year = statement_end_year(all_text)
        rows: list[list[str]] = []

        for page in pdf.pages:
            table = find_transaction_table(page)
            if not table:
                continue

            for raw in table[1:]:
                cells = [clean_cell(cell) for cell in raw]
                if len(cells) < 5 or not is_transaction_date(cells[0]):
                    continue

                day, month_name = cells[0].split()
                month = MONTHS[month_name.lower()]

                amount_cell = cells[2]
                balance_cell = cells[4]
                if len(cells) > 3 and cells[3].lower() in {"cr", "dr", "r"}:
                    amount_cell += cells[3]
                if len(cells) > 5 and cells[5].lower() in {"cr", "dr", "r"}:
                    balance_cell += cells[5]

                amount, amount_marker = money(amount_cell)
                balance, _ = money(balance_cell)
                signed_amount = abs(amount) if amount_marker == "Cr" else -abs(amount)

                rows.append([
                    f"{year:04d}/{month:02d}/{int(day):02d}",
                    f"{signed_amount:.2f}",
                    f"{balance:.2f}",
                    cells[1],
                ])

        return rows


def collect_pdfs(inputs: list[Path]) -> list[Path]:
    pdfs: list[Path] = []
    for item in inputs:
        if item.is_dir():
            pdfs.extend(sorted(item.glob("*.pdf")))
        else:
            pdfs.append(item)
    return pdfs


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert FNB transaction statement PDFs to CSV")
    parser.add_argument("inputs", nargs="+", type=Path, help="PDF files and/or folders")
    parser.add_argument("-o", "--output", type=Path, default=Path("transactions.csv"))
    args = parser.parse_args()

    pdfs = collect_pdfs(args.inputs)
    if not pdfs:
        raise SystemExit("No PDF files found.")

    all_rows: list[list[str]] = []
    for pdf in pdfs:
        extracted = extract_pdf(pdf)
        if not extracted:
            raise SystemExit(
                f"No transaction table found in {pdf}. "
                "This statement may need a bank-specific OCR/layout profile."
            )
        all_rows.extend(extracted)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Date", "Amount", "Balance", "Description"])
        writer.writerows(all_rows)

    print(f"Converted {len(pdfs)} PDF(s) -> {args.output} ({len(all_rows)} transaction rows)")


if __name__ == "__main__":
    main()
