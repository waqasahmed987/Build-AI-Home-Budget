from datetime import date
from io import BytesIO

import pandas as pd


SHEETS = {
    "Income": ["Source", "Monthly Amount (PKR)"],
    "Expenses": ["Category", "Description", "Monthly Amount (PKR)"],
    "Budget": ["Category", "Planned Amount (PKR)", "Savings Goal (PKR)"],
    "Bank Accounts": ["Account", "Bank", "Balance (PKR)", "As of"],
}

DEFAULT_DATA = {
    "Income": pd.DataFrame(
        [["Salary", 0], ["Other income", 0]],
        columns=SHEETS["Income"],
    ),
    "Expenses": pd.DataFrame(
        [
            ["Housing", "Rent / mortgage", 0],
            ["Utilities", "Electricity, gas, water", 0],
            ["Groceries", "Food and household", 0],
            ["Transport", "Fuel / fares", 0],
        ],
        columns=SHEETS["Expenses"],
    ),
    "Budget": pd.DataFrame(
        [
            ["Housing", 0, 0],
            ["Utilities", 0, 0],
            ["Groceries", 0, 0],
            ["Transport", 0, 0],
            ["Healthcare", 0, 0],
            ["Education", 0, 0],
            ["Other", 0, 0],
        ],
        columns=SHEETS["Budget"],
    ),
    "Bank Accounts": pd.DataFrame(
        [
            ["Account 1", "", 0, date.today()],
            ["Account 2", "", 0, date.today()],
        ],
        columns=SHEETS["Bank Accounts"],
    ),
}


def clean_sheet(frame: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Normalize imported or edited data to the expected columns and limits."""
    columns = SHEETS[sheet_name]
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]

    for column in columns:
        if column not in frame.columns:
            frame[column] = 0 if "Amount" in column or "Balance" in column or "Goal" in column else ""

    frame = frame[columns].dropna(how="all").reset_index(drop=True)

    amount_columns = [
        column for column in columns
        if "Amount" in column or "Balance" in column or "Goal" in column
    ]
    for column in amount_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
        frame[column] = frame[column].clip(lower=0)

    for column in columns:
        if column not in amount_columns:
            frame[column] = frame[column].fillna("")

    if sheet_name == "Income":
        frame = frame.head(5)
    elif sheet_name == "Expenses":
        frame = frame.head(20)
    elif sheet_name == "Bank Accounts":
        frame = frame.head(2)

    return frame


def calculate_totals(data: dict[str, pd.DataFrame]) -> dict[str, float]:
    income = float(data["Income"]["Monthly Amount (PKR)"].sum())
    expenses = float(data["Expenses"]["Monthly Amount (PKR)"].sum())
    planned = float(data["Budget"]["Planned Amount (PKR)"].sum())
    bank_balance = float(data["Bank Accounts"]["Balance (PKR)"].sum())

    return {
        "income": income,
        "expenses": expenses,
        "planned": planned,
        "monthly_savings": income - expenses,
        "bank_balance": bank_balance,
    }


def make_projection(monthly_savings: float, annual_return_pct: float) -> pd.DataFrame:
    """Estimate savings for 5 years with monthly contributions and optional growth."""
    balance = 0.0
    monthly_rate = max(annual_return_pct, 0) / 100 / 12
    rows = []

    for year in range(1, 6):
        for _ in range(12):
            balance = balance * (1 + monthly_rate) + monthly_savings

        rows.append({
            "Year": year,
            "Projected savings (PKR)": round(balance),
        })

    return pd.DataFrame(rows)


def export_workbook(data: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name in SHEETS:
            data[sheet_name].to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

    return output.getvalue()


def import_workbook(uploaded_file) -> dict[str, pd.DataFrame]:
    workbook = pd.ExcelFile(uploaded_file)
    aliases = {
        "income": "Income",
        "expenses": "Expenses",
        "budget": "Budget",
        "bank accounts": "Bank Accounts",
        "banks": "Bank Accounts",
    }
    imported_data = {}

    for expected_sheet in SHEETS:
        matching_sheet = next(
            (
                name for name in workbook.sheet_names
                if aliases.get(name.strip().lower()) == expected_sheet
            ),
            None,
        )

        if matching_sheet:
            frame = pd.read_excel(workbook, sheet_name=matching_sheet)
            imported_data[expected_sheet] = clean_sheet(frame, expected_sheet)
        else:
            imported_data[expected_sheet] = DEFAULT_DATA[expected_sheet].copy()

    return imported_data
