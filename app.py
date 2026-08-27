# Import Libraries
import streamlit as st
import numpy_financial as npf
import pandas as pd

# Titles
st.set_page_config(page_title="Loan & Investment Amortization", layout="wide")
st.title("Loan & Investment Amortization Dashboard")

mode = st.sidebar.radio("Input mode", ["Manual entry", "Upload CSV/Excel"])

def build_schedule(loan_amount, annual_rate, years):
    monthly_rate = annual_rate / 100 / 12
    n_periods = int(years * 12)
    payment = -npf.pmt(monthly_rate, n_periods, loan_amount)

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
    return schedule_df, payment

if mode == "Manual entry":
    # Insertable values for loans
    loan_amount = st.number_input("Loan amount", min_value=0.0, value=250000.0)
    annual_rate = st.number_input("Annual interest rate (%)", min_value=0.0, value=5.5)
    years = st.number_input("Term (years)", min_value=1, value=30)

    schedule_df, payment = build_schedule(loan_amount, annual_rate, years)

    st.write(f"Monthly Payment: ${payment:,.2f}")
    st.dataframe(schedule_df)

    total_interest = schedule_df["Interest"].sum()
    total_paid = schedule_df["Payment"].sum()
    payoff_years = len(schedule_df) / 12

    # The 3 titles of information
    col1, col2, col3 = st.columns(3)
    col1.metric("Total interest paid", f"${total_interest:,.2f}")
    col2.metric("Total paid", f"${total_paid:,.2f}")
    col3.metric("Payoff time", f"{payoff_years:.1f} years")

    # Graphs
    st.subheader("Remaining balance over time")
    st.line_chart(schedule_df.set_index("Period")["Balance"])

    st.subheader("Interest vs. principal per payment")
    st.line_chart(schedule_df.set_index("Period")[["Interest", "Principal"]])

    #  CSV Download
    csv_data = schedule_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download schedule as CSV", csv_data, "amortization_schedule.csv", "text/csv")

else:
    uploaded_file = st.sidebar.file_uploader("Upload file", type=["csv", "xlsx"])

    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            loans_df = pd.read_csv(uploaded_file)
        else:
            loans_df = pd.read_excel(uploaded_file)

        st.dataframe(loans_df)

        required_cols = {"loan_amount", "annual_rate", "years"}
        if not required_cols.issubset(loans_df.columns):
            st.error(f"Missing required columns. Need: {', '.join(required_cols)}")
        else:
            summary_rows = []
            balances = {}
            for i, row in loans_df.iterrows():
                loan_schedule, loan_payment = build_schedule(row["loan_amount"], row["annual_rate"], row["years"])
                label = f"Loan {i + 1} (${row['loan_amount']:,.0f})"

                summary_rows.append({
                    "Loan": label,
                    "Monthly payment": loan_payment,
                    "Total interest": loan_schedule["Interest"].sum(),
                    "Payoff (years)": len(loan_schedule) / 12,
                })

                balances[label] = loan_schedule.set_index("Period")["Balance"]

            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df)

            st.subheader("Remaining balance over time (all loans)")
            balance_compare_df = pd.DataFrame(balances)
            st.line_chart(balance_compare_df)