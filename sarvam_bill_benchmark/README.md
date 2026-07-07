# Sarvam AI Electricity Bill Benchmark

This is a clean, modular, and production-quality benchmark project designed to evaluate whether **Sarvam AI** can accurately extract structured information from multilingual Indian electricity bills.

This project is built from scratch with standard Python dependencies.

---

## Folder Structure

```text
sarvam_bill_benchmark/
├── bills/              # Drop all electricity bills here regardless of language or format
├── outputs/            # One JSON output file per bill, plus consolidated summary reports
├── app/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── sarvam_client.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── extraction_service.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── bill_prompt.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── extraction.py
│   └── utils/
│       ├── __init__.py
│       ├── pdf_utils.py
│       └── logging_config.py
├── tests/
│   ├── __init__.py
│   └── test_benchmark.py
├── .env
├── requirements.txt
├── extract_bill.py     # CLI script to extract data from a single bill
├── benchmark.py        # Runner script to batch process bills in the bills/ directory
├── json_to_excel.py    # Utility to aggregate JSON outputs into a formatted Excel sheet
├── template.xlsx       # Reference Excel template containing the schema
├── test.xlsx           # Generated consolidated Excel spreadsheet
└── README.md
```

---

## Installation & Setup

### 1. Initialize Python Environment
Navigate to the `sarvam_bill_benchmark` directory:
```bash
cd sarvam_bill_benchmark
```

Create a virtual environment and activate it:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials
Make sure `.env` is set up with your Sarvam subscription key:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
```

---

## Usage Guide

### A. Extract a Single Bill (`extract_bill.py`)
Run the standalone CLI script to process any single PDF or image file. By default, the language is auto-detected:
```bash
python extract_bill.py --file "/path/to/your/bill.pdf" --output outputs/result.json
```

Or you can optionally force a specific BCP-47 language code via `--lang`:
```bash
python extract_bill.py --file "/path/to/your/bill.pdf" --lang gu-IN --output outputs/result.json
```

*Language Options*: If omitted, language is auto-detected. Supported codes: `en-IN` (English), `hi-IN` (Hindi), `gu-IN` (Gujarati), `mr-IN` (Marathi), `te-IN` (Telugu), `ta-IN` (Tamil), `kn-IN` (Kannada), `bn-IN` (Bengali), `pa-IN` (Punjabi).

---

### B. Run Folder Benchmarks (`benchmark.py`)
Place all electricity bills directly under the `bills/` folder.

Run the benchmark runner script to iterate over all files in the bills directory:
```bash
python benchmark.py --bills-dir bills --output-dir outputs
```

#### CLI Options:
*   `--bills-dir` / `-b`: Directory containing input bills (default: `bills`).
*   `--output-dir` / `-o`: Directory to save extracted JSONs and logs (default: `outputs`).
*   `--limit` / `-l`: Limit the number of documents to process (e.g., `--limit 5` for quick testing).
*   `--force` / `-f`: Overwrite already processed files (by default, if a JSON file matching the input bill's stem name already exists in the output directory, it is skipped).

This script will:
1. Scan the specified `--bills-dir` directory for supported formats (PDF, PNG, JPG, JPEG, TIFF, BMP, WebP).
2. Skip already processed files to avoid duplicate API calls, unless `--force` is set.
3. Automatically perform dynamic language detection and extraction via Sarvam AI.
4. Clean base64 image dumps to preserve prompt tokens and structure the output.
5. Save individual JSON extraction outputs for each file under `--output-dir`.
6. Pause for 5 seconds between files to respect API rate limits.
7. Export execution summary statistics to `outputs/benchmark_summary.json` and details on failures to `outputs/failed_files.json`.

---

### C. Consolidate JSONs to Excel (`json_to_excel.py`)
Once you have generated the extraction outputs, run the consolidation utility to aggregate all results from the `outputs/` folder into a single, structured Excel sheet:
```bash
python json_to_excel.py
```

This utility will:
1. **Load Existing Edits**: Check if `test.xlsx` already exists in the project root. If found, it loads it to preserve any manual edits you've made. Otherwise, it defaults to the clean schema in `template.xlsx`.
2. **Scan Headers Dynamically**: Scan the active sheet's headers to map Excel column names to corresponding extraction fields.
3. **Map Extracted Data**: Populate the Excel table with details such as Consumer Number, Name, Address, Pincode, Load, Consumed Units, Dates, Net/Total Amounts, and Combined Bill status.
4. **Format & Normalize**: Automatically convert missing/empty values to `"null"` (string) and booleans to native Excel `TRUE`/`FALSE`.
5. **Preserve Manual Edits**: If a cell already contains a manual correction that differs from the newly processed JSON file, the script logs the conflict and preserves your manual edit.
6. **Save Results**: Write the consolidated output back to `test.xlsx` and output a full execution trace to `json_to_excel.log`.

---

## Running Tests
Run unit tests to verify JSON cleaning, base64 filtering, and Pydantic validator components:
```bash
python -m unittest tests/test_benchmark.py
```

