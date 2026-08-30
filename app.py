# Import Libraries
import streamlit as st
import numpy_financial as npf
import pandas as pd

# Titles
st.set_page_config(page_title="Financial Modelling Dashboard", layout="wide")

model = st.sidebar.radio("Model", ["Loan / Investment Amortization", "DCF Valuation"])


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


def build_dcf(starting_cf, growth_rate, discount_rate, years):
    g = growth_rate / 100
    r = discount_rate / 100

    rows = []
    cash_flow = starting_cf

    for year in range(1, int(years) + 1):
        cash_flow = cash_flow * (1 + g)
        present_value = cash_flow / (1 + r) ** year

        rows.append({
            "Year": year,
            "Cash Flow": cash_flow,
            "Present Value": present_value,
        })

    dcf_df = pd.DataFrame(rows)
    return dcf_df


def terminal_value(last_cash_flow, terminal_growth, discount_rate, years):
    g = terminal_growth / 100
    r = discount_rate / 100

    if r <= g:
        return None

    tv = last_cash_flow * (1 + g) / (r - g)
    pv_tv = tv / (1 + r) ** years
    return pv_tv


if model == "Loan / Investment Amortization":
    st.title("Loan & Investment Amortization Dashboard")

    mode = st.sidebar.radio("Input mode", ["Manual entry", "Upload CSV/Excel"])

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

else:
    st.title("DCF Valuation Model")

    mode = st.sidebar.radio("Input mode", ["Manual entry", "Upload CSV/Excel"])

    if mode == "Manual entry":
        # Insertable values for the DCF
        starting_cf = st.number_input("Starting cash flow ($)", min_value=0.0, value=1_000_000.0)
        growth_rate = st.number_input("Growth rate (%)", value=8.0)
        discount_rate = st.number_input("Discount rate (%)", min_value=0.01, value=10.0)
        years = st.number_input("Years to project", min_value=1, value=5)
        include_terminal = st.checkbox("Include terminal value", value=True)

        terminal_growth = None
        if include_terminal:
            terminal_growth = st.number_input("Terminal growth rate (%)", value=2.5)

        dcf_df = build_dcf(starting_cf, growth_rate, discount_rate, years)

        pv_cash_flows = dcf_df["Present Value"].sum()

        pv_tv = None
        if include_terminal:
            pv_tv = terminal_value(dcf_df["Cash Flow"].iloc[-1], terminal_growth, discount_rate, years)
            if pv_tv is None:
                st.warning("Terminal growth rate must be lower than the discount rate. Skipping terminal value.")

        total_valuation = pv_cash_flows + (pv_tv or 0)

        st.dataframe(dcf_df)

        # The 3 titles of information
        col1, col2, col3 = st.columns(3)
        col1.metric("PV of projected cash flows", f"${pv_cash_flows:,.0f}")
        col2.metric("PV of terminal value", f"${pv_tv:,.0f}" if pv_tv else "N/A")
        col3.metric("Estimated value today", f"${total_valuation:,.0f}")

        # Graphs
        st.subheader("Projected cash flows over time")
        st.bar_chart(dcf_df.set_index("Year")["Cash Flow"])

        st.subheader("Present value by year")
        st.bar_chart(dcf_df.set_index("Year")["Present Value"])

        # CSV Download
        csv_data = dcf_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download projection as CSV", csv_data, "dcf_projection.csv", "text/csv")

    else:
        uploaded_file = st.sidebar.file_uploader("Upload file", type=["csv", "xlsx"])

        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                scenarios_df = pd.read_csv(uploaded_file)
            else:
                scenarios_df = pd.read_excel(uploaded_file)

            st.dataframe(scenarios_df)

            required_cols = {"starting_cash_flow", "growth_rate", "discount_rate", "years"}
            if not required_cols.issubset(scenarios_df.columns):
                st.error(f"Missing required columns. Need: {', '.join(required_cols)}")
            else:
                has_terminal_col = "terminal_growth_rate" in scenarios_df.columns

                summary_rows = []
                cash_flows = {}
                for i, row in scenarios_df.iterrows():
                    scenario_df = build_dcf(row["starting_cash_flow"], row["growth_rate"], row["discount_rate"], row["years"])
                    label = f"Scenario {i + 1} (${row['starting_cash_flow']:,.0f})"

                    pv_cash_flows = scenario_df["Present Value"].sum()

                    pv_tv = None
                    if has_terminal_col and pd.notna(row["terminal_growth_rate"]):
                        pv_tv = terminal_value(scenario_df["Cash Flow"].iloc[-1], row["terminal_growth_rate"], row["discount_rate"], row["years"])

                    summary_rows.append({
                        "Scenario": label,
                        "PV of cash flows": pv_cash_flows,
                        "PV of terminal value": pv_tv if pv_tv is not None else 0,
                        "Total valuation": pv_cash_flows + (pv_tv or 0),
                    })

                    cash_flows[label] = scenario_df.set_index("Year")["Cash Flow"]

                summary_df = pd.DataFrame(summary_rows)
                st.dataframe(summary_df)

                st.subheader("Projected cash flows over time (all scenarios)")
                cash_flow_compare_df = pd.DataFrame(cash_flows)
                st.line_chart(cash_flow_compare_df)
