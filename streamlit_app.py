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

# Calculate the 90-day moving average
df['90_day_avg'] = df['Close'].rolling(window=90, min_periods=1).mean()

# Initialize the portfolio value
df['Portfolio Value'] = 0.0  # Will accumulate investments

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

# Conditional Investment
use_conditional_investment = st.checkbox("Use Conditional Investment?")
conditional_investment_amount = 0.0
percentage_decrease = 0.0

if use_conditional_investment:
    conditional_investment_amount = st.number_input("Conditional Investment Amount", min_value=0.0, step=100.0, value=500.0)
    percentage_decrease = st.slider("Percentage Decrease in QQQ compared to Last 90 Days Average", min_value=0, max_value=100, value=10)

# Convert start_date and end_date to pd.Timestamp for accurate filtering
start_date = pd.Timestamp(start_date)
end_date = pd.Timestamp(end_date)

# Filter the data according to the selected date range
df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

# Initialize the portfolio value with the initial investment
df_filtered.at[df_filtered.index[0], 'Portfolio Value'] = initial_investment

# Set the frequency in days
frequency_days = {'Weekly': 7, 'Monthly': 30, 'Quarterly': 90}[frequency]
current_date = start_date + timedelta(days=frequency_days)

# Track total investments
recurring_investment_total = 0.0
recurring_investment_count = 0
conditional_investment_total = 0.0
conditional_investment_count = 0

# Simulate the portfolio value over time, including recurring and conditional investments
for i in range(1, len(df_filtered)):
    # Compound the portfolio value with the 3x leveraged return
    df_filtered.iloc[i, df_filtered.columns.get_loc('Portfolio Value')] = (
        df_filtered.iloc[i-1, df_filtered.columns.get_loc('Portfolio Value')] * 
        (1 + df_filtered.iloc[i, df_filtered.columns.get_loc('3x Leveraged Return')])
    )
    
    # Add recurring investments on the specified dates
    if df_filtered.iloc[i]['Date'] >= current_date:
        df_filtered.iloc[i, df_filtered.columns.get_loc('Portfolio Value')] += recurring_amount
        recurring_investment_total += recurring_amount
        recurring_investment_count += 1
        current_date += timedelta(days=frequency_days)

    # Apply conditional investments based on the specified criteria
    if use_conditional_investment:
        if df_filtered.iloc[i]['Close'] < (1 - percentage_decrease / 100) * df_filtered.iloc[i]['90_day_avg']:
            df_filtered.iloc[i, df_filtered.columns.get_loc('Portfolio Value')] += conditional_investment_amount
            conditional_investment_total += conditional_investment_amount
            conditional_investment_count += 1

# Plot the portfolio development
st.subheader("Portfolio Value Development Over Time")
plt.figure(figsize=(10, 6), dpi=80)
plt.plot(df_filtered['Date'], df_filtered['Portfolio Value'], label="Portfolio Value")
plt.xlabel("Date")
plt.ylabel("Portfolio Value")
plt.title("Investment Portfolio Value Over Time")
plt.legend()
st.pyplot(plt)

# Calculate and display final portfolio metrics
final_value = df_filtered.iloc[-1]['Portfolio Value']
total_investment = initial_investment + recurring_investment_total + conditional_investment_total
investment_period_days = (end_date - start_date).days

st.write(f"Final Portfolio Value: ${final_value:,.2f}")
st.write(f"Total Investment Made: ${total_investment:,.2f}")
st.write(f"Total Portfolio Return: {((final_value - total_investment) / total_investment) * 100:.2f}%")
st.write(f"Initial Investment: ${initial_investment:,.2f}")
st.write(f"Total Recurring Investment: ${recurring_investment_total:,.2f} ({recurring_investment_count} times)")
st.write(f"Total Conditional Investment: ${conditional_investment_total:,.2f} ({conditional_investment_count} times)")
st.write(f"Investment Period: {investment_period_days} days")

# Force garbage collection to free up unused memory
del df, df_filtered
gc.collect()
