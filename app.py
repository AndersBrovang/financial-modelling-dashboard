import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Loan & Investment Amortization", layout="wide")


def build_schedule(principal: float, annual_rate: float, years: int, extra_payment: float = 0.0) -> pd.DataFrame:
    monthly_rate = annual_rate / 100 / 12
    n_periods = years * 12
    base_payment = -npf.pmt(monthly_rate, n_periods, principal)

    rows = []
    balance = principal
    period = 0
    while balance > 0 and period < n_periods * 2:
        period += 1
        interest = balance * monthly_rate
        principal_paid = min(base_payment - interest + extra_payment, balance)
        payment = principal_paid + interest
        balance = max(balance - principal_paid, 0)
        rows.append(
            {
                "Period": period,
                "Payment": payment,
                "Principal": principal_paid,
                "Interest": interest,
                "Remaining Balance": balance,
            }
        )
        if balance <= 0:
            break

    return pd.DataFrame(rows), base_payment


st.title("Loan & Investment Amortization Dashboard")
st.caption("Enter values manually, or upload a CSV/Excel file to compare multiple loans.")

mode = st.sidebar.radio("Input mode", ["Manual entry", "Upload CSV/Excel"])

if mode == "Manual entry":
    col1, col2 = st.sidebar.columns(2)
    principal = col1.number_input("Loan amount", min_value=0.0, value=250000.0, step=1000.0)
    annual_rate = col2.number_input("Annual interest rate (%)", min_value=0.0, value=5.5, step=0.1)
    years = col1.number_input("Term (years)", min_value=1, value=30, step=1)
    extra_payment = col2.number_input("Extra monthly payment", min_value=0.0, value=0.0, step=50.0)

    schedule, base_payment = build_schedule(principal, annual_rate, int(years), extra_payment)

    total_interest = schedule["Interest"].sum()
    total_paid = schedule["Payment"].sum()
    payoff_years = len(schedule) / 12

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Monthly payment", f"${base_payment + extra_payment:,.2f}")
    m2.metric("Total interest paid", f"${total_interest:,.2f}")
    m3.metric("Total paid", f"${total_paid:,.2f}")
    m4.metric("Payoff time", f"{payoff_years:.1f} years")

    fig_balance = go.Figure()
    fig_balance.add_trace(
        go.Scatter(x=schedule["Period"], y=schedule["Remaining Balance"], mode="lines", name="Balance")
    )
    fig_balance.update_layout(title="Remaining balance over time", xaxis_title="Month", yaxis_title="Balance ($)")
    st.plotly_chart(fig_balance, use_container_width=True)

    fig_split = go.Figure()
    fig_split.add_trace(go.Bar(x=schedule["Period"], y=schedule["Principal"], name="Principal"))
    fig_split.add_trace(go.Bar(x=schedule["Period"], y=schedule["Interest"], name="Interest"))
    fig_split.update_layout(
        barmode="stack", title="Principal vs. interest per payment", xaxis_title="Month", yaxis_title="Amount ($)"
    )
    st.plotly_chart(fig_split, use_container_width=True)

    st.subheader("Amortization schedule")
    st.dataframe(schedule.style.format({"Payment": "${:,.2f}", "Principal": "${:,.2f}", "Interest": "${:,.2f}", "Remaining Balance": "${:,.2f}"}), use_container_width=True)

    csv_bytes = schedule.to_csv(index=False).encode("utf-8")
    st.download_button("Download schedule as CSV", csv_bytes, "amortization_schedule.csv", "text/csv")

else:
    st.sidebar.markdown(
        "Upload a CSV or Excel file with columns: `loan_amount`, `annual_rate`, `years`, `extra_payment` (optional)."
    )
    uploaded = st.sidebar.file_uploader("Upload file", type=["csv", "xlsx", "xls"])

    if uploaded is None:
        st.info("Upload a CSV or Excel file to compare loans side by side.")
    else:
        if uploaded.name.endswith(".csv"):
            loans_df = pd.read_csv(uploaded)
        else:
            loans_df = pd.read_excel(uploaded)

        required_cols = {"loan_amount", "annual_rate", "years"}
        missing = required_cols - set(loans_df.columns.str.lower())
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
        else:
            loans_df.columns = loans_df.columns.str.lower()
            if "extra_payment" not in loans_df.columns:
                loans_df["extra_payment"] = 0.0

            st.subheader("Uploaded loans")
            st.dataframe(loans_df, use_container_width=True)

            summary_rows = []
            fig_compare = go.Figure()
            for i, row in loans_df.iterrows():
                schedule, base_payment = build_schedule(
                    row["loan_amount"], row["annual_rate"], int(row["years"]), row.get("extra_payment", 0.0)
                )
                label = row.get("name", f"Loan {i + 1}")
                summary_rows.append(
                    {
                        "Loan": label,
                        "Monthly payment": base_payment + row.get("extra_payment", 0.0),
                        "Total interest": schedule["Interest"].sum(),
                        "Total paid": schedule["Payment"].sum(),
                        "Payoff (years)": len(schedule) / 12,
                    }
                )
                fig_compare.add_trace(
                    go.Scatter(x=schedule["Period"], y=schedule["Remaining Balance"], mode="lines", name=str(label))
                )

            summary_df = pd.DataFrame(summary_rows)
            st.subheader("Comparison summary")
            st.dataframe(
                summary_df.style.format(
                    {"Monthly payment": "${:,.2f}", "Total interest": "${:,.2f}", "Total paid": "${:,.2f}", "Payoff (years)": "{:.1f}"}
                ),
                use_container_width=True,
            )

            fig_compare.update_layout(
                title="Remaining balance over time (all loans)", xaxis_title="Month", yaxis_title="Balance ($)"
            )
            st.plotly_chart(fig_compare, use_container_width=True)
