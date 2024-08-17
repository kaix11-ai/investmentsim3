import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import gc

st.title("Investment Portfolio Simulator")

# Cache the data loading function to avoid reloading it multiple times
@st.cache_data
def load_data():
    # Load the data from the provided link
    df = pd.read_csv(
        'https://raw.githubusercontent.com/kaix11-ai/investmentsim2/main/TQQQ_V6.csv', 
        usecols=['Date', 'Close'],
        parse_dates=['Date']
    )
    return df

# Load the data
df = load_data()

# Ensure the Date column is in datetime format
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Handle any NaT values that might arise from parsing errors
df = df.dropna(subset=['Date'])

# Calculate the daily return and apply 3x leverage
df['Daily Return'] = df['Close'].pct_change().fillna(0)  # Calculate daily return
df['3x Leveraged Return'] = df['Daily Return'] * 3        # Apply 3x leverage

# Check if the DataFrame is not empty after processing
if df.empty:
    st.error("The DataFrame is empty. Please check the CSV file and ensure it contains valid data.")
else:
    # Set default parameters
    default_start_date = df['Date'].min().date()
    default_end_date = df['Date'].max().date()
    default_initial_investment = 1000.0
    default_recurring_investment = 0.0

    # User Inputs
    start_date = st.date_input(
        "Investment Start Date", 
        value=default_start_date,
        min_value=df['Date'].min().date(), 
        max_value=df['Date'].max().date()
    )

    end_date = st.date_input(
        "Investment End Date",
        value=default_end_date,
        min_value=start_date,
        max_value=df['Date'].max().date()
    )

    initial_investment = st.number_input("Initial Investment Amount", min_value=0.0, step=100.0, value=default_initial_investment)
    recurring_amount = st.number_input("Recurring Investment Amount", min_value=0.0, step=100.0, value=default_recurring_investment)
    frequency = st.selectbox("Recurring Investment Frequency", ["Weekly", "Monthly", "Quarterly"])

    # Optional Conditional Investment
    use_condition = st.checkbox("Use Conditional Investment?")
    condition_percentage = 0
    if use_condition:
        condition_percentage = st.slider("Investment Condition (if close is below X% of last 90 days close)", min_value=0, max_value=100, value=10)

    frequency_days = {'Weekly': 7, 'Monthly': 30, 'Quarterly': 90}[frequency]

    # Convert start_date and end_date to pd.Timestamp for accurate comparison
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    # Filter the data and create a copy to avoid SettingWithCopyWarning
    df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

    # Check if the filtered data is empty
    if df_filtered.empty:
        st.error("No data available for the selected date range.")
    else:
        # Calculate the 90-day low for the condition
        df_filtered['90_day_low'] = df_filtered['Close'].rolling(window=90, min_periods=1).min()

        # Initialize variables for the investment simulation
        portfolio_value = initial_investment
        recurring_investment_total = 0
        investment_dates = []
        portfolio_values = []
        current_date = start_date

        # Simulate the investment strategy
        while current_date <= end_date:
            # Find the closest previous trading day if the current date is not in the data
            closest_date = df_filtered[df_filtered['Date'] <= current_date]['Date'].max()
            
            # Ensure that closest_date is valid
            if pd.isna(closest_date):
                st.warning(f"No trading data available for the selected date range. Current date: {current_date}")
                break

            # Get the row corresponding to the closest available date
            row = df_filtered[df_filtered['Date'] == closest_date].iloc[0]

            # Update portfolio value based on the compounded daily 3x leveraged return
            portfolio_value *= (1 + row['3x Leveraged Return'])

            # Track the portfolio value and date
            investment_dates.append(row['Date'])
            portfolio_values.append(portfolio_value)

            # Move to the next investment date
            current_date += timedelta(days=frequency_days)

            # Regular investment based on frequency
            if recurring_amount > 0:
                portfolio_value += recurring_amount  # Add the recurring amount directly to the portfolio value
                recurring_investment_total += recurring_amount

            # Conditional investment if enabled
            if use_condition and row['Close'] < (1 - condition_percentage / 100) * row['90_day_low']:
                portfolio_value += recurring_amount  # Add the recurring amount directly to the portfolio value
                recurring_investment_total += recurring_amount

        # Calculate total portfolio return and investment period length
        total_investment = initial_investment + recurring_investment_total
        total_return = ((portfolio_value - total_investment) / total_investment) * 100 if total_investment != 0 else 0
        investment_period_length = (end_date - start_date).days

        # Check if there are any values to plot
        if investment_dates and portfolio_values:
            # Plot the portfolio development
            st.subheader("Portfolio Value Development Over Time")
            plt.figure(figsize=(10, 6), dpi=80)  # Use a lower DPI for less memory usage
            plt.plot(investment_dates, portfolio_values, label="Portfolio Value")
            plt.xlabel("Date")
            plt.ylabel("Portfolio Value")
            plt.title("Investment Portfolio Value Over Time")
            plt.legend()
            st.pyplot(plt)

            # Display final portfolio metrics
            st.write(f"Final Portfolio Value: ${portfolio_value:,.2f}")
            st.write(f"Total Investment Made: ${total_investment:,.2f}, of which ${recurring_investment_total:,.2f} was recurring and ${initial_investment:,.2f} was initial investment.")
            st.write(f"Total Portfolio Return: {total_return:.2f}%")
            st.write(f"Investment Period Length: {investment_period_length} days")
        else:
            st.error("No data to display in the chart. Please check the investment conditions and date range.")

        # Force garbage collection to free up unused memory
        del df, df_filtered
        gc.collect()
