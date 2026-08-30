# Import Libraries
import streamlit as st
import numpy_financial as npf
import pandas as pd

# Titles
st.set_page_config(page_title="Financial Modelling Dashboard", layout="wide")
st.title("Financial Modelling Dashboard")

tab_amortization, tab_dcf = st.tabs(["Loan & Investment Amortization", "DCF Valuation"])


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


def build_dcf(starting_cf, growth_rate, discount_rate, years, include_terminal_value=False):
    g = growth_rate / 100
    r = discount_rate / 100

    schedule = []
    cf = starting_cf
    for year in range(1, years + 1):
        cf = cf * (1 + g)
        pv = cf / (1 + r) ** year
        schedule.append({"Year": year, "Cash Flow": cf, "Present Value": pv})

    schedule_df = pd.DataFrame(schedule)
    pv_of_projection = schedule_df["Present Value"].sum()

    pv_of_terminal = 0
    if include_terminal_value and r > g:
        last_cf = schedule_df["Cash Flow"].iloc[-1]
        terminal_value = last_cf * (1 + g) / (r - g)
        pv_of_terminal = terminal_value / (1 + r) ** years

    total_valuation = pv_of_projection + pv_of_terminal
    return schedule_df, total_valuation, pv_of_terminal


with tab_amortization:
    mode = st.radio("Input mode", ["Manual entry", "Upload CSV/Excel"], horizontal=True, key="amort_mode")

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
        st.download_button("Download schedule as CSV", csv_data, "amortization_schedule.csv", "text/csv", key="amort_download")

    else:
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"], key="amort_upload")

        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                loans_df = pd.read_csv(uploaded_file)
            else:
                loans_df = pd.read_excel(uploaded_file)

            st.dataframe(loans_df)

            required_cols = {"loan_amount", "annual_rate", "years"}
            if loans_df.empty:
                st.error("Uploaded file has no rows.")
            elif not required_cols.issubset(loans_df.columns):
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

with tab_dcf:
    dcf_mode = st.radio("Input mode", ["Manual entry", "Upload CSV/Excel"], horizontal=True, key="dcf_mode")

    if dcf_mode == "Manual entry":
        starting_cf = st.number_input("Starting cash flow ($)", min_value=0.0, value=100000.0)
        growth_rate = st.number_input("Growth rate (%)", value=5.0)
        discount_rate = st.number_input("Discount rate (%)", min_value=0.01, value=10.0)
        years = st.number_input("Years to project", min_value=1, value=5)
        include_terminal_value = st.checkbox("Include terminal value", value=True)

        if include_terminal_value and discount_rate <= growth_rate:
            st.warning("Discount rate must be greater than growth rate to calculate a terminal value — it will be excluded.")

        schedule_df, total_valuation, pv_of_terminal = build_dcf(
            starting_cf, growth_rate, discount_rate, years, include_terminal_value
        )

        st.write(f"Estimated Value Today: ${total_valuation:,.2f}")
        st.dataframe(schedule_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total valuation", f"${total_valuation:,.2f}")
        col2.metric("PV of terminal value", f"${pv_of_terminal:,.2f}")
        col3.metric("Years projected", f"{years}")

        # Graphs
        st.subheader("Projected cash flows over time")
        st.line_chart(schedule_df.set_index("Year")["Cash Flow"])

        st.subheader("Present value breakdown per year")
        st.bar_chart(schedule_df.set_index("Year")["Present Value"])

        # CSV Download
        csv_data = schedule_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download schedule as CSV", csv_data, "dcf_schedule.csv", "text/csv", key="dcf_download")

    else:
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"], key="dcf_upload")

        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                scenarios_df = pd.read_csv(uploaded_file)
            else:
                scenarios_df = pd.read_excel(uploaded_file)

            st.dataframe(scenarios_df)

            required_cols = {"starting_cf", "growth_rate", "discount_rate", "years"}
            if scenarios_df.empty:
                st.error("Uploaded file has no rows.")
            elif not required_cols.issubset(scenarios_df.columns):
                st.error(f"Missing required columns. Need: {', '.join(required_cols)}")
            else:
                summary_rows = []
                cash_flows = {}
                for i, row in scenarios_df.iterrows():
                    if "include_terminal_value" in scenarios_df.columns:
                        include_tv = bool(row["include_terminal_value"])
                    else:
                        include_tv = True

                    scenario_schedule, scenario_valuation, scenario_pv_terminal = build_dcf(
                        row["starting_cf"], row["growth_rate"], row["discount_rate"], int(row["years"]), include_tv
                    )
                    label = f"Scenario {i + 1} (${row['starting_cf']:,.0f})"

                    summary_rows.append({
                        "Scenario": label,
                        "Total valuation": scenario_valuation,
                        "PV of terminal value": scenario_pv_terminal,
                        "Years projected": int(row["years"]),
                    })

                    cash_flows[label] = scenario_schedule.set_index("Year")["Cash Flow"]

                summary_df = pd.DataFrame(summary_rows)
                st.dataframe(summary_df)

                st.subheader("Projected cash flows over time (all scenarios)")
                cash_flow_compare_df = pd.DataFrame(cash_flows)
                st.line_chart(cash_flow_compare_df)
