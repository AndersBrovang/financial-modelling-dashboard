# Import Libraries
import streamlit as st
import numpy_financial as npf
import pandas as pd

# Titles
st.set_page_config(page_title="Financial Modelling Dashboard", layout="wide")
st.title("Financial Modelling Dashboard")

tab_amortization, tab_dcf, tab_three_statement = st.tabs(["Loan & Investment Amortization", "DCF Valuation", "3-Statement Model"])


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

def build_three_statement(
    starting_revenue, growth_rate, gross_margin, opex_pct, da_pct, tax_rate,
    years, starting_debt, interest_rate, annual_debt_repayment, capex_pct,
    starting_cash, starting_ppe, starting_equity,
):
    g = growth_rate / 100
    gm = gross_margin / 100
    opex_p = opex_pct / 100
    da_p = da_pct / 100
    tax = tax_rate / 100
    r = interest_rate / 100
    
    rows = []
    revenue = starting_revenue
    debt = starting_debt
    cash = starting_cash
    ppe = starting_ppe
    equity = starting_equity
    capex_p = capex_pct / 100
    
    for year in range(1, years + 1):
    # --- Income statement ---
        revenue = revenue * (1 + g)
        cogs = revenue * (1 - gm)
        gross_profit = revenue - cogs
        opex = revenue * opex_p
        ebitda = gross_profit - opex
        da = revenue * da_p
        ebit = ebitda - da
        interest_expense = debt * r
        ebt = ebit - interest_expense
        tax_expense = ebt * tax if ebt > 0 else 0
        net_income = ebt - tax_expense
        
        # --- Debt roll-forward (after interest_expense is already computed) ---
        repayment = min(annual_debt_repayment, debt)   # can't repay more than what's left
        debt = debt - repayment

        # --- Cash flow statement ---
        capex = revenue * capex_p
        change_in_cash = net_income + da - capex - repayment
        cash = cash + change_in_cash
        
        # --- Balance sheet roll-forward ---
        ppe = ppe + capex - da
        equity = equity + net_income

        # --- Balance check ---
        assets = cash + ppe
        liab_and_equity = debt + equity
        balances = abs(assets - liab_and_equity) < 0.01

        rows.append({
            "Year": year, "Revenue": revenue, "Net Income": net_income,
            "Cash": cash, "PP&E": ppe, "Debt": debt, "Equity": equity,
            "Assets": assets, "Liabilities + Equity": liab_and_equity, "Balances?": balances,
        })

    return pd.DataFrame(rows)


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
                
with tab_three_statement:
    ts_mode = st.radio("Input mode", ["Manual entry", "Upload CSV/Excel"], horizontal=True, key="ts_mode")

    if ts_mode == "Manual entry":
        st.subheader("Income statement assumptions")
        col1, col2, col3 = st.columns(3)
        starting_revenue = col1.number_input("Starting revenue ($)", min_value=0.0, value=1000000.0)
        growth_rate = col2.number_input("Revenue growth rate (%)", value=10.0)
        years = col3.number_input("Years to project", min_value=1, value=5, key="ts_years")

        col1, col2, col3 = st.columns(3)
        gross_margin = col1.number_input("Gross margin (%)", min_value=0.0, max_value=100.0, value=40.0)
        opex_pct = col2.number_input("Opex (% of revenue)", min_value=0.0, value=15.0)
        da_pct = col3.number_input("D&A (% of revenue)", min_value=0.0, value=5.0)

        col1, col2 = st.columns(2)
        tax_rate = col1.number_input("Tax rate (%)", min_value=0.0, max_value=100.0, value=21.0)
        capex_pct = col2.number_input("Capex (% of revenue)", min_value=0.0, value=6.0)

        st.subheader("Debt assumptions")
        col1, col2, col3 = st.columns(3)
        starting_debt = col1.number_input("Starting debt ($)", min_value=0.0, value=500000.0)
        interest_rate = col2.number_input("Interest rate (%)", min_value=0.0, value=6.0)
        annual_debt_repayment = col3.number_input("Annual debt repayment ($)", min_value=0.0, value=50000.0)

        st.subheader("Starting balance sheet")
        col1, col2, col3 = st.columns(3)
        starting_cash = col1.number_input("Starting cash ($)", min_value=0.0, value=200000.0)
        starting_ppe = col2.number_input("Starting PP&E ($)", min_value=0.0, value=800000.0)
        starting_equity = col3.number_input("Starting equity ($)", min_value=0.0, value=500000.0)

        statements_df = build_three_statement(
            starting_revenue, growth_rate, gross_margin, opex_pct, da_pct, tax_rate,
            years, starting_debt, interest_rate, annual_debt_repayment, capex_pct,
            starting_cash, starting_ppe, starting_equity,
        )

        st.dataframe(statements_df)

        if not statements_df["Balances?"].all():
            st.error("Balance sheet doesn't balance in at least one year — check your assumptions.")

        ending_cash = statements_df["Cash"].iloc[-1]
        ending_equity = statements_df["Equity"].iloc[-1]
        total_net_income = statements_df["Net Income"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Ending cash", f"${ending_cash:,.2f}")
        col2.metric("Ending equity", f"${ending_equity:,.2f}")
        col3.metric("Total net income", f"${total_net_income:,.2f}")

        # Graphs
        st.subheader("Revenue & net income over time")
        st.line_chart(statements_df.set_index("Year")[["Revenue", "Net Income"]])

        st.subheader("Balance sheet composition over time")
        st.bar_chart(statements_df.set_index("Year")[["Cash", "PP&E", "Debt", "Equity"]])

        # CSV Download
        csv_data = statements_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download statements as CSV", csv_data, "three_statement_model.csv", "text/csv", key="ts_download")

    else:
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"], key="ts_upload")

        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                scenarios_df = pd.read_csv(uploaded_file)
            else:
                scenarios_df = pd.read_excel(uploaded_file)

            st.dataframe(scenarios_df)

            required_cols = {
                "starting_revenue", "growth_rate", "gross_margin", "opex_pct", "da_pct", "tax_rate",
                "years", "starting_debt", "interest_rate", "annual_debt_repayment", "capex_pct",
                "starting_cash", "starting_ppe", "starting_equity",
            }
            if scenarios_df.empty:
                st.error("Uploaded file has no rows.")
            elif not required_cols.issubset(scenarios_df.columns):
                st.error(f"Missing required columns. Need: {', '.join(sorted(required_cols))}")
            else:
                summary_rows = []
                cash_series = {}
                for i, row in scenarios_df.iterrows():
                    scenario_df = build_three_statement(
                        row["starting_revenue"], row["growth_rate"], row["gross_margin"], row["opex_pct"],
                        row["da_pct"], row["tax_rate"], int(row["years"]), row["starting_debt"],
                        row["interest_rate"], row["annual_debt_repayment"], row["capex_pct"],
                        row["starting_cash"], row["starting_ppe"], row["starting_equity"],
                    )
                    label = f"Scenario {i + 1} (${row['starting_revenue']:,.0f})"

                    summary_rows.append({
                        "Scenario": label,
                        "Ending cash": scenario_df["Cash"].iloc[-1],
                        "Ending equity": scenario_df["Equity"].iloc[-1],
                        "Balances every year?": bool(scenario_df["Balances?"].all()),
                    })

                    cash_series[label] = scenario_df.set_index("Year")["Cash"]

                summary_df = pd.DataFrame(summary_rows)
                st.dataframe(summary_df)

                st.subheader("Cash over time (all scenarios)")
                cash_compare_df = pd.DataFrame(cash_series)
                st.line_chart(cash_compare_df)
