import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import timedelta
import gc
import plotly.graph_objs as go

st.title("Investment Portfolio Simulator")

# Cache the data loading function to avoid reloading it multiple times
@st.cache_data
def load_data():
    # Load the data for QQQ and TLT
    df_qqq = pd.read_csv(
        'https://raw.githubusercontent.com/kaix11-ai/investmentsim2/main/TQQQ_V6.csv', 
        usecols=['Date', 'Close'],
        parse_dates=['Date'],
        dayfirst=True  # Add this if dates are in day-first format
    )
    df_tlt = pd.read_csv(
        'https://raw.githubusercontent.com/kaix11-ai/investmentsim2/main/TLT.csv',
        usecols=['Date', 'Close'],
        parse_dates=['Date'],
        dayfirst=True  # Add this if dates are in day-first format
    )
    return df_qqq, df_tlt

# Load the data
df_qqq, df_tlt = load_data()

# Ensure the Date column is in datetime format
df_qqq['Date'] = pd.to_datetime(df_qqq['Date'], errors='coerce')
df_tlt['Date'] = pd.to_datetime(df_tlt['Date'], errors='coerce')

# Handle any NaT values that might arise from parsing errors
df_qqq = df_qqq.dropna(subset=['Date'])
df_tlt = df_tlt.dropna(subset=['Date'])

# Align the date ranges between QQQ and TLT
common_start_date = max(df_qqq['Date'].min(), df_tlt['Date'].min())
common_end_date = min(df_qqq['Date'].max(), df_tlt['Date'].max())

st.write(f"Data date range: {common_start_date.date()} to {common_end_date.date()}")

# User Inputs
start_date = st.date_input(
    "Investment Start Date", 
    value=common_start_date.date(),
    min_value=common_start_date.date(), 
    max_value=common_end_date.date()
)

end_date = st.date_input(
    "Investment End Date",
    value=common_end_date.date(),
    min_value=start_date,
    max_value=common_end_date.date()
)

initial_investment = st.number_input("Initial Investment Amount", min_value=0.0, step=100.0, value=1000.0)
recurring_amount = st.number_input("Recurring Investment Amount", min_value=0.0, step=100.0, value=0.0)
frequency = st.selectbox("Recurring Investment Frequency", ["Weekly", "Monthly", "Quarterly"])
# Portfolio Composition
qqq_weight = st.slider("Percentage of Portfolio in QQQ", min_value=0, max_value=100, value=50)
tlt_weight = 100 - qqq_weight

# Leverage
qqq_leverage = st.number_input("Leverage for QQQ", min_value=1.0, step=0.5, value=3.0)
tlt_leverage = st.number_input("Leverage for TLT", min_value=1.0, step=0.5, value=1.0)

# Conditional Investment
use_conditional_investment = st.checkbox("Use Conditional Investment?", key="cond_invest_checkbox")
conditional_investment_amount = 0.0
percentage_decrease = 0.0
waiting_weeks = 0

if use_conditional_investment:
    conditional_investment_amount = st.number_input("Conditional Investment Amount", min_value=0.0, step=100.0, value=500.0)
    percentage_decrease = st.slider("Percentage Decrease in QQQ compared to Last 90 Days Average", min_value=0, max_value=100, value=10)
    waiting_weeks = st.number_input("Wait XXX Weeks Before Next Conditional Investment", min_value=0, step=1, value=4)

# Filter the data according to the selected date range
start_date = pd.Timestamp(start_date)
end_date = pd.Timestamp(end_date)

df_qqq = df_qqq[(df_qqq['Date'] >= start_date) & (df_qqq['Date'] <= end_date)].copy()
df_tlt = df_tlt[(df_tlt['Date'] >= start_date) & (df_tlt['Date'] <= end_date)].copy()

# Calculate the daily returns and apply leverage
df_qqq['Daily Return'] = df_qqq['Close'].pct_change().fillna(0)
df_qqq['3x Leveraged Return'] = df_qqq['Daily Return'] * qqq_leverage
df_tlt['Daily Return'] = df_tlt['Close'].pct_change().fillna(0)
df_tlt['3x Leveraged Return'] = df_tlt['Daily Return'] * tlt_leverage

# Calculate the 90-day moving average for conditional investment
df_qqq['90_day_avg'] = df_qqq['Close'].rolling(window=90, min_periods=1).mean()

# Merge QQQ and TLT data
df_combined = pd.merge(df_qqq[['Date', '3x Leveraged Return', 'Close', '90_day_avg']], df_tlt[['Date', '3x Leveraged Return']], on='Date', suffixes=('_QQQ', '_TLT'))

# Initialize the portfolio value
df_combined['Portfolio Value'] = initial_investment

# Rebalancing and Investment Simulation
current_date = start_date + timedelta(days={'Weekly': 7, 'Monthly': 30, 'Quarterly': 90}[frequency])
last_conditional_investment_date = start_date - timedelta(days=365)  # Initialize far in the past

recurring_investment_total = 0.0
recurring_investment_count = 0
conditional_investment_total = 0.0
conditional_investment_count = 0
conditional_investment_dates = []

for i in range(1, len(df_combined)):
    # Compound the portfolio value with the returns from both QQQ and TLT
    qqq_return = df_combined.iloc[i, df_combined.columns.get_loc('3x Leveraged Return_QQQ')]
    tlt_return = df_combined.iloc[i, df_combined.columns.get_loc('3x Leveraged Return_TLT')]
    
    df_combined.iloc[i, df_combined.columns.get_loc('Portfolio Value')] = (
        df_combined.iloc[i-1, df_combined.columns.get_loc('Portfolio Value')] *
        (1 + (qqq_weight / 100) * qqq_return + (tlt_weight / 100) * tlt_return)
    )
    
    # Rebalancing
    if df_combined.iloc[i]['Date'] >= current_date:
        df_combined.iloc[i, df_combined.columns.get_loc('Portfolio Value')] += recurring_amount
        recurring_investment_total += recurring_amount
        recurring_investment_count += 1
        current_date += timedelta(days={'Weekly': 7, 'Monthly': 30, 'Quarterly': 90}[frequency])
    
    # Conditional Investment
# Conditional Investment
    if use_conditional_investment and (df_combined.iloc[i]['Close'] < (1 - percentage_decrease / 100) * df_combined.iloc[i]['90_day_avg']):
        if (df_combined.iloc[i]['Date'] - last_conditional_investment_date).days >= waiting_weeks * 7:
            df_combined.iloc[i, df_combined.columns.get_loc('Portfolio Value')] += conditional_investment_amount
            conditional_investment_total += conditional_investment_amount
            conditional_investment_count += 1
            conditional_investment_dates.append(df_combined.iloc[i]['Date'])
            last_conditional_investment_date = df_combined.iloc[i]['Date']


# Plot the portfolio development
st.subheader("Portfolio Value Development Over Time")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_combined['Date'], y=df_combined['Portfolio Value'], mode='lines', name='Portfolio Value'))

# Add markers for conditional investments
if conditional_investment_dates:
    fig.add_trace(go.Scatter(
        x=conditional_investment_dates,
        y=df_combined[df_combined['Date'].isin(conditional_investment_dates)]['Portfolio Value'],
        mode='markers',
        marker=dict(size=10, color='red'),
        name='Conditional Investment'
    ))

fig.update_layout(
    title="Investment Portfolio Value Over Time",
    xaxis_title="Date",
    yaxis_title="Portfolio Value",
    showlegend=True,
    height=600,  # Adjust the chart size
    template="plotly_white"
)

st.plotly_chart(fig)

# Calculate and display final portfolio metrics
final_value = df_combined.iloc[-1]['Portfolio Value']
total_investment = initial_investment + recurring_investment_total + conditional_investment_total
investment_period_length = (end_date - start_date).days

st.write(f"Final Portfolio Value: ${final_value:,.2f}")
st.write(f"Total Investment Made: ${total_investment:,.2f}")
st.write(f"Total Portfolio Return: {((final_value - total_investment) / total_investment) * 100:.2f}%")
st.write(f"Investment Period Length: {investment_period_length} days, ({investment_period_length/365:,.2f} years)")
st.write(f"Initial Investment: ${initial_investment:,.2f}")
st.write(f"Total Recurring Investment: ${recurring_investment_total:,.2f} ({recurring_investment_count} times)")
if use_conditional_investment:
    st.write(f"Total Conditional Investment: ${conditional_investment_total:,.2f} ({conditional_investment_count} times)")

# Force garbage collection to free up unused memory
del df_qqq, df_tlt, df_combined
gc.collect()
