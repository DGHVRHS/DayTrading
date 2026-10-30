import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Day Trading Simulator",
    page_icon="📈",
    layout="wide"
)

# ------------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ------------------------------------------------------------------------------
if "cash" not in st.session_state:
    st.session_state.cash = 100000.00

if "portfolio" not in st.session_state:
    # Format: { "AAPL": {"shares": 10, "avg_price": 180.00} }
    st.session_state.portfolio = {}

if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

if "latest_advice" not in st.session_state:
    st.session_state.latest_advice = None

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def get_live_data(ticker_symbol):
    """Fetch current market price and 1-day intraday history."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            # Fallback for outside market hours or delayed quotes
            data = ticker.history(period="5d", interval="1m")
        if data.empty:
            return None, None
        current_price = data["Close"].iloc[-1]
        return current_price, data
    except Exception:
        return None, None

def calculate_portfolio_value():
    """Calculate total liquidation value of cash + open positions."""
    total_value = st.session_state.cash
    for ticker, info in st.session_state.portfolio.items():
        price, _ = get_live_data(ticker)
        if price:
            total_value += info["shares"] * price
    return total_value

def generate_trade_advice(action, ticker, shares, price, total_portfolio_val):
    """
    Educational Rule Engine: Evaluates trade parameters and outputs
    pedagogical insights on position sizing, risk management, and diversification.
    """
    trade_value = shares * price
    allocation_pct = (trade_value / total_portfolio_val) * 100
    cash_remaining_pct = ((st.session_state.cash - (trade_value if action == "BUY" else -trade_value)) / total_portfolio_val) * 100

    advice = []
    
    if action == "BUY":
        # Position Sizing Rule
        if allocation_pct > 25:
            advice.append(
                f"⚠️ **High Concentration Risk:** This single trade represents **{allocation_pct:.1f}%** of your entire portfolio. "
                "Professional day traders rarely risk more than 1%–5% of total capital on a single trade."
            )
        else:
            advice.append(
                f"✅ **Disciplined Sizing:** Allocation of **{allocation_pct:.1f}%** is within a prudent risk management framework."
            )

        # Liquidity Rule
        if cash_remaining_pct < 10:
            advice.append(
                f"⚠️ **Low Liquidity Alert:** Remaining cash is down to **{cash_remaining_pct:.1f}%**. "
                "Holding minimal cash limits your flexibility to capitalized on sudden intraday market drops."
            )
        
        advice.append(
            f"💡 **Trading Tip:** Set a strict Stop-Loss order (e.g., 1%–2% below ${price:.2f}) to limit downside loss."
        )

    elif action == "SELL":
        if ticker in st.session_state.portfolio:
            avg_buy = st.session_state.portfolio[ticker]["avg_price"]
            pnl = (price - avg_buy) * shares
            pnl_pct = ((price - avg_buy) / avg_buy) * 100

            if pnl > 0:
                advice.append(
                    f"🎉 **Profit Taken:** Realized gain of **${pnl:.2f} (+{pnl_pct:.2f}%)**. "
                    "Locking in profits discipline avoids turning winning trades into losing ones."
                )
            else:
                advice.append(
                    f"🛡️ **Loss Realized:** Realized loss of **${pnl:.2f} ({pnl_pct:.2f}%)**. "
                    "Cutting losses early is an essential survival skill in day trading."
                )
                
    return advice

# ------------------------------------------------------------------------------
# UI SIDEBAR - ORDER PLACEMENT
# ------------------------------------------------------------------------------
st.sidebar.header("🕹️ Order Execution")

symbol_input = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper().strip()
live_price, intraday_df = get_live_data(symbol_input)

if live_price:
    st.sidebar.metric(label=f"Live Price ({symbol_input})", value=f"${live_price:.2f}")
else:
    st.sidebar.error("Invalid ticker or market data unavailable.")

order_type = st.sidebar.radio("Order Type", ["BUY", "SELL"])
quantity = st.sidebar.number_input("Shares Quantity", min_value=1, value=10, step=1)

if st.sidebar.button("Execute Order", type="primary"):
    if not live_price:
        st.sidebar.error("Cannot execute trade without live price data.")
    else:
        cost = live_price * quantity
        total_port_val = calculate_portfolio_value()

        if order_type == "BUY":
            if cost > st.session_state.cash:
                st.sidebar.error("Insufficient cash funds to complete this order!")
            else:
                st.session_state.cash -= cost
                curr_pos = st.session_state.portfolio.get(symbol_input, {"shares": 0, "avg_price": 0.0})
                
                # Calculate Weighted Average Cost
                tot_shares = curr_pos["shares"] + quantity
                new_avg = ((curr_pos["shares"] * curr_pos["avg_price"]) + cost) / tot_shares
                st.session_state.portfolio[symbol_input] = {"shares": tot_shares, "avg_price": new_avg}

                # Generate Feedback
                st.session_state.latest_advice = generate_trade_advice("BUY", symbol_input, quantity, live_price, total_port_val)
                st.session_state.trade_history.append({
                    "Type": "BUY", "Symbol": symbol_input, "Shares": quantity,
                    "Price": f"${live_price:.2f}", "Total": f"${cost:.2f}"
                })
                st.sidebar.success(f"Bought {quantity} shares of {symbol_input}!")

        elif order_type == "SELL":
            curr_pos = st.session_state.portfolio.get(symbol_input, {"shares": 0, "avg_price": 0.0})
            if curr_pos["shares"] < quantity:
                st.sidebar.error("Not enough shares held to complete sell order.")
            else:
                st.session_state.cash += cost
                remaining = curr_pos["shares"] - quantity
                
                # Generate Feedback BEFORE updating portfolio state
                st.session_state.latest_advice = generate_trade_advice("SELL", symbol_input, quantity, live_price, total_port_val)

                if remaining == 0:
                    del st.session_state.portfolio[symbol_input]
                else:
                    st.session_state.portfolio[symbol_input]["shares"] = remaining

                st.session_state.trade_history.append({
                    "Type": "SELL", "Symbol": symbol_input, "Shares": quantity,
                    "Price": f"${live_price:.2f}", "Total": f"${cost:.2f}"
                })
                st.sidebar.success(f"Sold {quantity} shares of {symbol_input}!")

# ------------------------------------------------------------------------------
# MAIN DASHBOARD
# ------------------------------------------------------------------------------
st.title("📊 Educational Day-Trading Simulator")

# Dashboard Header Metrics
port_val = calculate_portfolio_value()
pnl_total = port_val - 100000.00
pnl_pct = (pnl_total / 100000.00) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Available Cash", f"${st.session_state.cash:,.2f}")
col2.metric("Portfolio Value", f"${port_val:,.2f}")
col3.metric("Total Realized/Unrealized P&L", f"${pnl_total:,.2f}", f"{pnl_pct:.2f}%")

st.divider()

# Instant Educational Advice Panel
if st.session_state.latest_advice:
    st.subheader("🎓 Real-Time Trade Coach Feedback")
    with st.container(border=True):
        for line in st.session_state.latest_advice:
            st.markdown(line)

# Ticker Charting
if intraday_df is not None and not intraday_df.empty:
    st.subheader(f"📈 {symbol_input} Intraday Price Chart")
    fig = go.Figure(data=[go.Candlestick(
        x=intraday_df.index,
        open=intraday_df['Open'],
        high=intraday_df['High'],
        low=intraday_df['Low'],
        close=intraday_df['Close']
    )])
    fig.update_layout(xaxis_rangeslider_visible=False, height=380, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

# Positions & Trade Log
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("💼 Active Positions")
    if st.session_state.portfolio:
        pos_data = []
        for sym, details in st.session_state.portfolio.items():
            curr_p, _ = get_live_data(sym)
            curr_p = curr_p if curr_p else details["avg_price"]
            mkt_val = details["shares"] * curr_p
            unrealized = (curr_p - details["avg_price"]) * details["shares"]
            pos_data.append({
                "Symbol": sym,
                "Shares": details["shares"],
                "Avg Price": f"${details['avg_price']:.2f}",
                "Current Price": f"${curr_p:.2f}",
                "Market Value": f"${mkt_val:.2f}",
                "Unrealized P&L": f"${unrealized:.2f}"
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
    else:
        st.info("No open positions.")

with right_col:
    st.subheader("📜 Trade Execution History")
    if st.session_state.trade_history:
        st.dataframe(pd.DataFrame(st.session_state.trade_history)[::-1], use_container_width=True)
    else:
        st.info("No trades executed yet.")
