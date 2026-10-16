import os

import pandas as pd
import plotly.express as px
import streamlit as st

from finance_agent import (
    DEFAULT_DATA,
    calculate_totals,
    clean_sheet,
    export_workbook,
    import_workbook,
    make_projection,
)
from insight_agent import generate_budget_observations


st.set_page_config(
    page_title="Ghar Budget",
    page_icon="🏡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f8f6 0%, #eef4f3 100%);
    }
    [data-testid="stMetric"] {
        background: white;
        padding: 18px;
        border-radius: 16px;
        border: 1px solid #e5ece8;
        box-shadow: 0 5px 18px rgba(25, 55, 45, .05);
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 20px;
        background: linear-gradient(120deg, #123d35, #1f7564);
        color: white;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "data" not in st.session_state:
    st.session_state.data = {
        sheet: frame.copy() for sheet, frame in DEFAULT_DATA.items()
    }


def current_data():
    return st.session_state.data


def show_editor(sheet_name: str, key: str):
    """Render one editable table and save its edited values in the session."""
    frame = current_data()[sheet_name]
    edited = st.data_editor(
        frame,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=key,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                min_value=0,
                step=1000,
                format="%.0f",
            )
            for column in frame.columns
            if "Amount" in column or "Balance" in column or "Goal" in column
        },
    )

    limit = 5 if sheet_name == "Income" else 20 if sheet_name == "Expenses" else 2 if sheet_name == "Bank Accounts" else None
    if limit and len(edited) > limit:
        st.warning(f"{sheet_name} is limited to {limit} rows.")
        edited = edited.head(limit)

    st.session_state.data[sheet_name] = clean_sheet(edited, sheet_name)


def show_chart(frame, x, y, title, chart_type="bar"):
    if frame.empty:
        st.info("Add some amounts to see this chart.")
        return

    if chart_type == "pie":
        fig = px.pie(frame, names=x, values=y, hole=0.55, title=title)
    else:
        fig = px.bar(frame, x=x, y=y, title=title, color=x)

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


data = current_data()
metrics = calculate_totals(data)

st.markdown(
    """
    <div class="hero">
        <h1>🏡 Ghar Budget</h1>
        <p>One clear view of your household income, spending, and savings plan.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Active agent: Household Finance Assistant · PKR · Data stays in this app session unless exported.")
st.caption("This starter app stores data in the current browser session. Export your workbook to keep a copy.")

with st.sidebar:
    st.header("Your workspace")
    st.write("Use Excel to upload or download your budget.")
    uploaded = st.file_uploader(
        "Upload a budget workbook",
        type=["xlsx"],
        help="Expected sheets: Income, Expenses, Budget, Bank Accounts.",
    )

    if uploaded and st.button("Import workbook", use_container_width=True):
        try:
            st.session_state.data = import_workbook(uploaded)
            st.success("Workbook imported.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not import workbook: {exc}")

    st.download_button(
        "Download current workbook",
        data=export_workbook(data),
        file_name="ghar_budget.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    if st.button("Reset to blank starter data", use_container_width=True):
        st.session_state.data = {
            sheet: frame.copy() for sheet, frame in DEFAULT_DATA.items()
        }
        st.rerun()

tab_names = [
    "Overview",
    "Income",
    "Expenses",
    "Monthly Budget",
    "Bank Accounts",
    "5-Year Savings",
    "AI Insights",
]
tabs = st.tabs(tab_names)

with tabs[0]:
    st.subheader("Monthly overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", f"PKR {metrics['income']:,.0f}")
    c2.metric("Expenses", f"PKR {metrics['expenses']:,.0f}")
    c3.metric("Estimated savings", f"PKR {metrics['monthly_savings']:,.0f}")
    c4.metric("Combined bank balance", f"PKR {metrics['bank_balance']:,.0f}")

    left, right = st.columns(2)
    with left:
        chart_data = pd.DataFrame({
            "Type": ["Income", "Expenses", "Savings"],
            "PKR": [
                metrics["income"],
                metrics["expenses"],
                max(0, metrics["monthly_savings"]),
            ],
        })
        show_chart(chart_data, "Type", "PKR", "Monthly cash flow")
    with right:
        expenses = data["Expenses"]
        if not expenses.empty:
            show_chart(
                expenses,
                "Category",
                "Monthly Amount (PKR)",
                "Expenses by category",
                "pie",
            )

with tabs[1]:
    st.subheader("Income")
    st.caption("Add up to five monthly income sources.")
    show_editor("Income", "income_editor")
    show_chart(
        data["Income"],
        "Source",
        "Monthly Amount (PKR)",
        "Income sources",
    )

with tabs[2]:
    st.subheader("Expenses")
    st.caption("Add up to twenty monthly expense entries.")
    show_editor("Expenses", "expenses_editor")
    show_chart(
        data["Expenses"],
        "Category",
        "Monthly Amount (PKR)",
        "Monthly expenses",
    )

with tabs[3]:
    st.subheader("Monthly budget and savings plan")
    st.caption(
        "Enter the planned amount and savings goal for each category. "
        "Compare the plan with actual expenses below."
    )
    show_editor("Budget", "budget_editor")

    comparison = data["Budget"].merge(
        data["Expenses"].groupby("Category", as_index=False)[
            "Monthly Amount (PKR)"
        ].sum().rename(columns={"Monthly Amount (PKR)": "Actual (PKR)"}),
        on="Category",
        how="left",
    )
    if not comparison.empty:
        comparison["Actual (PKR)"] = comparison["Actual (PKR)"].fillna(0)
        st.dataframe(comparison, use_container_width=True, hide_index=True)
        show_chart(
            comparison,
            "Category",
            "Planned Amount (PKR)",
            "Planned budget by category",
        )

    st.metric("Planned monthly budget", f"PKR {metrics['planned']:,.0f}")
    st.metric("Estimated actual monthly savings", f"PKR {metrics['monthly_savings']:,.0f}")

with tabs[4]:
    st.subheader("Bank accounts")
    st.caption("Track up to two account balances and update the date whenever you check them.")
    show_editor("Bank Accounts", "banks_editor")
    show_chart(
        data["Bank Accounts"],
        "Account",
        "Balance (PKR)",
        "Current balances",
    )
    st.info("Balances are manually entered snapshots. This starter app does not connect to banks.")

with tabs[5]:
    st.subheader("Five-year savings projection")
    st.caption("A simple estimate based on your current monthly income and expenses.")
    annual_rate = st.slider(
        "Assumed annual growth rate (%)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.5,
        help="Set to 0% for savings without assumed investment growth.",
    )
    monthly_savings = max(0, metrics["monthly_savings"])
    projection = make_projection(monthly_savings, annual_rate)
    st.metric("Estimated monthly contribution", f"PKR {monthly_savings:,.0f}")
    st.dataframe(projection, use_container_width=True, hide_index=True)
    show_chart(
        projection,
        "Year",
        "Projected savings (PKR)",
        "Projected savings over five years",
    )
    st.caption("This is a planning estimate, not a guarantee or investment recommendation.")

with tabs[6]:
    st.subheader("AI budgeting observations")
    st.caption("Groq receives monthly totals and budget categories, not bank names or account details.")
    st.write("Add your Groq API key in Streamlit Cloud secrets to enable AI summaries.")

    if st.button("Generate AI observations", type="primary"):
        try:
            with st.spinner("Household Finance Assistant is reviewing the summary..."):
                observations = generate_budget_observations(
                    metrics,
                    data["Budget"].to_dict(orient="records"),
                )
            st.markdown(observations)
        except Exception as exc:
            st.error(str(exc))

    if not os.getenv("GROQ_API_KEY") and "GROQ_API_KEY" not in st.secrets:
        st.info("AI is optional. The budgeting tools and projection work without it.")
