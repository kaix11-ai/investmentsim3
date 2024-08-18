import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import timedelta
import gc

st.title("Investment Portfolio Simulator")

# Cache the data loading function to avoid reloading it multiple times
@st.cache_data
def load_data():
    # Load the data from the provided link
    df = pd.read_csv(
        'https://raw.githubusercontent.com/kaix11-ai/investmentsim2/main/TQQQ_V6.csv', 
        usecols=['Date', 'Close'],
        parse_dates=['Date'],
        dayfirst=True  # Add this if dates are in day-first format
    )
    return df

# Load the data
df = load_data()


# Ensure the Date column is in datetime format
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Handle any NaT values that might arise from parsing errors
df = df.dropna(subset=['Date'])

# Display date range to verify correct parsing
st.write(f"Data date range: {df['Date'].min().date()} to {df['Date'].max().date()}")

# Calculate the daily return for QQQ and apply 3x leverage
df['Daily Return'] = df['Close'].pct_change().fillna(0)  # Calculate daily return
df['3x Leveraged Return'] = df['Daily Return'] * 3        # Apply 3x leverage

# Initialize the portfolio value
df['Portfolio Value'] = 1000.0  # Starting with an initial investment of $1000

# Calculate the portfolio value using daily compounded returns
for i in range(1, len(df)):
    df.iloc[i, df.columns.get_loc('Portfolio Value')] = df.iloc[i-1, df.columns.get_loc('Portfolio Value')] * (1 + df.iloc[i, df.columns.get_loc('3x Leveraged Return')])

# Set the correct date range based on the data
default_start_date = df['Date'].min().date()
default_end_date = df['Date'].max().date()

# User Inputs with constrained date range
start_date = st.date_input(
    "Investment Start Date", 
    value=default_start_date,
    min_value=default_start_date, 
    max_value=default_end_date
)

end_date = st.date_input(
    "Investment End Date",
    value=default_end_date,
    min_value=start_date,
    max_value=default_end_date
)

initial_investment = st.number_input("Initial Investment Amount", min_value=0.0, step=100.0, value=1000.0)
recurring_amount = st.number_input("Recurring Investment Amount", min_value=0.0, step=100.0, value=0.0)
frequency = st.selectbox("Recurring Investment Frequency", ["Weekly", "Monthly", "Quarterly"])

# Filter the data and adjust the portfolio value according to the selected date range
start_date = pd.Timestamp(start_date)
end_date = pd.Timestamp(end_date)

df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

# Adjust the initial portfolio value based on the user input
df_filtered['Portfolio Value'] = df_filtered['Portfolio Value'] / df_filtered.iloc[0]['Portfolio Value'] * initial_investment

# Plot the portfolio development
st.subheader("Portfolio Value Development Over Time")
plt.figure(figsize=(10, 6), dpi=80)
plt.plot(df_filtered['Date'], df_filtered['Portfolio Value'], label="Portfolio Value")
plt.xlabel("Date")
plt.ylabel("Portfolio Value")
plt.title("Investment Portfolio Value Over Time")
plt.legend()
st.pyplot(plt)

# Display final portfolio metrics
final_value = df_filtered.iloc[-1]['Portfolio Value']
total_investment = initial_investment
st.write(f"Final Portfolio Value: ${final_value:,.2f}")
st.write(f"Total Investment Made: ${total_investment:,.2f}")
st.write(f"Total Portfolio Return: {((final_value - total_investment) / total_investment) * 100:.2f}%")

# Force garbage collection to free up unused memory
del df, df_filtered
gc.collect()
