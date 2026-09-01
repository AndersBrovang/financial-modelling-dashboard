# Financial Modelling Dashboard
A hands-on project for learning financial modelling by building interactive Streamlit dashboards.

## Goal

Mix programming with financial modelling: input assumptions (or upload a CSV/Excel file), run the model, and explore results through charts instead of spreadsheet cells.

## Models

- [x] **Loan / investment amortization calculator** — time value of money, cash flow schedules
- [x] **DCF valuation model** — projected cash flows, present value, terminal value
- [x] **Simple 3-statement model** — linked income statement, cash flow, and balance sheet

## Getting started

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py                      # Streamlit entry point (all models, one tab each)
requirements.txt            # Python dependencies
sample_loans.csv            # Sample data for the amortization calculator's upload mode
sample_dcf.csv              # Sample data for the DCF model's upload mode
sample_three_statement.csv  # Sample data for the 3-statement model's upload mode
```
