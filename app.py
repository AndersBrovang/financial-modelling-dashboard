# Import Libraries
import streamlit as st
import numpy_financial as npf
import pandas as pd

# Titles
st.set_page_config(page_title="Loan & Investment Amortization", layout="wide")
st.title("Loan & Investment Amortization Dashboard")

# Insertable values for loans
loan_amount = st.number_input("Loan amount", min_value=0.0, value=250000.0)
annual_rate = st.number_input("Annual interest rate (%)", min_value=0.0, value=5.5)
years = st.number_input("Term (years)", min_value=1, value=30)

# Calucations for loans
monthly_rate = annual_rate / 100 / 12
n_periods = years * 12
payment = -npf.pmt(monthly_rate, n_periods, loan_amount)

st.write(f"Monthly Payment: ${payment:,.2f}")

schedule = []
balance = loan_amount

for period in range(1, n_periods + 1):
    interest = balance * monthly_rate
    principal_paid = payment - interest
    balance -= principal_paid

    schedule.append({
        "Period": period,
        "Payment": payment,
        "Interest": interest,
        "Principal": principal_paid,
        "Balance": balance,
    })

schedule_df = pd.DataFrame(schedule)
st.dataframe(schedule_df)