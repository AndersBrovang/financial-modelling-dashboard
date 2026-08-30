# Financial Modelling Dashboard
A hands-on project for learning financial modelling by building interactive Streamlit dashboards.

## Goal

Mix programming with financial modelling: input assumptions (or upload a CSV/Excel file), run the model, and explore results through charts instead of spreadsheet cells.

## Models

- [x] **Loan / investment amortization calculator** — time value of money, cash flow schedules
- [x] **DCF valuation model** — projected cash flows, present value, terminal value
- [ ] Simple 3-statement model

## Getting started

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py              # Streamlit entry point
requirements.txt    # Python dependencies
sample_loans.csv    # Example upload for the amortization calculator
sample_dcf.csv      # Example upload for the DCF valuation model
```
