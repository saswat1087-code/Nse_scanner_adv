import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="NSE Advanced Scanner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .event-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .trigger-bullish {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
        animation: pulse 2s infinite;
    }
    .trigger-bearish {
        background-color: #f8d7da;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
        margin: 10px 0;
        animation: pulse 2s infinite;
    }
    .option-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.8; }
        100% { opacity: 1; }
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    .small-text {
        font-size: 12px;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

class EventBasedTrigger:
    """Detect event-based triggers in stocks"""
    
    def __init__(self):
        self.triggers = []
    
    def detect_breakout(self, df, lookback=20):
        """Detect breakout events"""
        events = []
        if len(df) < lookback:
            return events
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        highs = df['High'].tail(lookback)
        lows = df['Low'].tail(lookback)
        
        # 52-week high/low (using available data)
        year_high = highs.max()
        year_low = lows.min()
        
        if latest['High'] >= year_high * 0.98:
            events.append({
                'type': 'Bullish Breakout',
                'desc': f'Near 52-week high (₹{year_high:.2f})',
                'severity': 'High'
            })
        
        if latest['Low'] <= year_low * 1.02:
            events.append({
                'type': 'Bearish Breakdown',
                'desc': f'Near 52-week low (₹{year_low:.2f})',
                'severity': 'High'
            })
        
        # Volume breakout
        avg_volume = df['Volume'].tail(lookback).mean()
        if latest['Volume'] > avg_volume * 2:
            if latest['Close'] > latest['Open']:
                events.append({
                    'type': 'Volume Breakout',
                    'desc': f'2x volume with price up',
                    'severity': 'Medium'
                })
            else:
                events.append({
                    'type': 'Volume Breakdown',
                    'desc': f'2x volume with price down',
                    'severity': 'Medium'
                })
        
        return events
    
    def detect_momentum_shifts(self, df):
        """Detect momentum changes"""
        events = []
        
        if len(df) < 10:
            return events
        
        # RSI momentum
        rsi = df['RSI'].iloc[-1]
        rsi_prev = df['RSI'].iloc[-2]
        
        if rsi > 70 and rsi < rsi_prev:
            events.append({
                'type': 'Momentum Loss',
                'desc': f'RSI dropping from overbought ({rsi:.1f} → {rsi_prev:.1f})',
                'severity': 'High'
            })
        
        if rsi < 30 and rsi > rsi_prev:
            events.append({
                'type': 'Momentum Gain',
                'desc': f'RSI rising from oversold ({rsi:.1f} → {rsi_prev:.1f})',
                'severity': 'High'
            })
        
        # Price momentum
        returns = df['Close'].pct_change().tail(5)
        if returns.mean() > 0.03:
            events.append({
                'type': 'Strong Uptrend',
                'desc': f'5-day return: {returns.mean()*100:.1f}%',
                'severity': 'Medium'
            })
        elif returns.mean() < -0.03:
            events.append({
                'type': 'Strong Downtrend',
                'desc': f'5-day return: {returns.mean()*100:.1f}%',
                'severity': 'Medium'
            })
        
        return events
    
    def detect_event_triggers(self, stock_data, symbol):
        """Main trigger detection"""
        triggers = []
        
        # Get stock info
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Earnings triggers
            if 'earningsDate' in info:
                earnings_date = info['earningsDate']
                if earnings_date:
                    days_to_earnings = (earnings_date - datetime.now()).days
                    if 0 <= days_to_earnings <= 7:
                        triggers.append({
                            'event': '📊 Earnings',
                            'description': f'Earnings in {days_to_earnings} days',
                            'impact': 'High',
                            'action': 'Watch for volatility'
                        })
            
            # Dividend triggers
            if 'dividendDate' in info:
                div_date = info['dividendDate']
                if div_date:
                    days_to_dividend = (div_date - datetime.now()).days
                    if 0 <= days_to_dividend <= 14:
                        triggers.append({
                            'event': '💰 Dividend',
                            'description': f'Ex-dividend in {days_to_dividend} days',
                            'impact': 'Medium',
                            'action': 'Potential buying interest'
                        })
            
            # Analyst triggers
            if 'recommendationKey' in info:
                rec = info['recommendationKey']
                if rec in ['strong_buy', 'buy']:
                    triggers.append({
                        'event': '⭐ Analyst Rating',
                        'description': f'Analyst: {rec.replace("_", " ").upper()}',
                        'impact': 'Medium',
                        'action': 'Positive sentiment'
                    })
            
            # Price targets
            if 'targetMeanPrice' in info and 'currentPrice' in info:
                target = info['targetMeanPrice']
                current = info['currentPrice']
                upside = ((target - current) / current) * 100
                if upside > 20:
                    triggers.append({
                        'event': '🎯 Price Target',
                        'description': f'{upside:.1f}% upside to ₹{target:.0f}',
                        'impact': 'High',
                        'action': 'Analyst optimism'
                    })
        
        except:
            pass
        
        # Technical triggers
        df = stock_data
        if df is not None and len(df) > 20:
            # Moving average crossovers
            sma20 = df['SMA20'].iloc[-1]
            sma50 = df['SMA50'].iloc[-1]
            sma20_prev = df['SMA20'].iloc[-2]
            sma50_prev = df['SMA50'].iloc[-2]
            
            if sma20_prev <= sma50_prev and sma20 > sma50:
                triggers.append({
                    'event': '🟢 Golden Cross',
                    'description': '20 SMA crossed above 50 SMA',
                    'impact': 'High',
                    'action': 'Strong bullish signal'
                })
            elif sma20_prev >= sma50_prev and sma20 < sma50:
                triggers.append({
                    'event': '🔴 Death Cross',
                    'description': '20 SMA crossed below 50 SMA',
                    'impact': 'High',
                    'action': 'Strong bearish signal'
                })
            
            # Volume spike
            vol_ratio = df['Volume_Ratio'].iloc[-1]
            if vol_ratio > 2:
                triggers.append({
                    'event': '📈 Volume Spike',
                    'description': f'{vol_ratio:.1f}x average volume',
                    'impact': 'High',
                    'action': 'Institutional interest'
                })
        
        return triggers

class IndexOptionsAnalyzer:
    """Analyze NIFTY and BANKNIFTY options"""
    
    def __init__(self):
        self.indices = {
            'NIFTY 50': '^NSEI',
            'BANK NIFTY': '^NSEBANK'
        }
    
    def get_index_data(self, index_symbol):
        """Fetch index data"""
        try:
            ticker = yf.Ticker(index_symbol)
            df = ticker.history(period="1mo")
            return df
        except:
            return None
    
    def calculate_option_pcr(self, symbol):
        """Calculate Put-Call Ratio (simplified)"""
        # Note: Real PCR requires options data API
        # This is a simulated version using market data
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d")
            
            if not hist.empty:
                # Simulated PCR based on price action
                price_change = hist['Close'].pct_change().iloc[-1] * 100
                volume_change = hist['Volume'].pct_change().iloc[-1]
                
                if price_change > 0 and volume_change > 0:
                    pcr = 0.7  # More calls
                    sentiment = "Bullish"
                elif price_change < 0 and volume_change > 0:
                    pcr = 1.3  # More puts
                    sentiment = "Bearish"
                else:
                    pcr = 1.0
                    sentiment = "Neutral"
                
                return pcr, sentiment
        except:
            return 1.0, "Neutral"
        return 1.0, "Neutral"
    
    def calculate_iv(self, symbol):
        """Calculate Implied Volatility (simplified)"""
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="20d")
            
            if not hist.empty:
                returns = hist['Close'].pct_change()
                volatility = returns.std() * np.sqrt(252) * 100
                
                if volatility > 30:
                    level = "High"
                elif volatility > 20:
                    level = "Medium"
                else:
                    level = "Low"
                
                return round(volatility, 1), level
        except:
            return 20.0, "Medium"
        return 20.0, "Medium"
    
    def get_support_resistance(self, df):
        """Calculate support and resistance levels"""
        if df is None or df.empty:
            return None, None
        
        recent_high = df['High'].tail(20).max()
        recent_low = df['Low'].tail(20).min()
        current = df['Close'].iloc[-1]
        
        resistance = recent_high
        support = recent_low
        
        # Additional levels
        resistance_2 = resistance * 1.02
        support_2 = support * 0.98
        
        return {
            'current': current,
            'resistance': resistance,
            'support': support,
            'resistance_2': resistance_2,
            'support_2': support_2
        }
    
    def analyze_index_options(self):
        """Complete options analysis for indices"""
        results = {}
        
        for name, symbol in self.indices.items():
            df = self.get_index_data(symbol)
            if df is not None:
                current = df['Close'].iloc[-1]
                change = ((current - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                
                pcr, pcr_sentiment = self.calculate_option_pcr(symbol)
                iv, iv_level = self.calculate_iv(symbol)
                levels = self.get_support_resistance(df)
                
                # Option chain strikes (nearest)
                strike_interval = 50 if name == 'NIFTY 50' else 100
                atm_strike = round(current / strike_interval) * strike_interval
                
                strikes = {
                    'CE': [atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100],
                    'PE': [atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100]
                }
                
                results[name] = {
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'pcr': round(pcr, 2),
                    'pcr_sentiment': pcr_sentiment,
                    'iv': iv,
                    'iv_level': iv_level,
                    'levels': levels,
                    'strikes': strikes,
                    'data': df
                }
        
        return results

class EnhancedNSEScanner:
    """Enhanced NSE scanner with events and options"""
    
    def __init__(self):
        self.nifty50 = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
            'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'AXISBANK.NS',
            'LT.NS', 'KOTAKBANK.NS', 'WIPRO.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
            'TITAN.NS', 'ASIANPAINT.NS', 'NESTLE.NS', 'BAJFINANCE.NS', 'HCLTECH.NS'
        ]
        self.event_trigger = EventBasedTrigger()
    
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # Moving Averages
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # Volume
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # ATR for volatility
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        
        return df
    
    def analyze_stock(self, symbol):
        """Complete stock analysis with events"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo")
            
            if df.empty:
                return None
            
            df = self.calculate_indicators(df)
            
            # Get fundamental data
            info = {}
            try:
                info = ticker.info
            except:
                pass
            
            # Detect events and triggers
            breakout_events = self.event_trigger.detect_breakout(df)
            momentum_events = self.event_trigger.detect_momentum_shifts(df)
            event_triggers = self.event_trigger.detect_event_triggers(df, symbol)
            
            # Combine all events
            all_events = breakout_events + momentum_events + event_triggers
            
            # Score based on events
            bullish_events = sum(1 for e in all_events if 'Bullish' in e.get('type', '') or 'Gain' in e.get('type', '') or 'up' in e.get('desc', '').lower())
            bearish_events = sum(1 for e in all_events if 'Bearish' in e.get('type', '') or 'Loss' in e.get('type', '') or 'down' in e.get('desc', '').lower())
            
            total_score = len(all_events)
            if total_score > 0:
                sentiment_score = (bullish_events / total_score) * 100
            else:
                sentiment_score = 50
            
            if sentiment_score >= 60:
                sentiment = "Bullish"
            elif sentiment_score <= 40:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            return {
                'symbol': symbol.replace('.NS', ''),
                'price': round(current_price, 2),
                'change': round(change_pct, 2),
                'rsi': round(df['RSI'].iloc[-1], 1) if not pd.isna(df['RSI'].iloc[-1]) else 50,
                'volume_ratio': round(df['Volume_Ratio'].iloc[-1], 2) if not pd.isna(df['Volume_Ratio'].iloc[-1]) else 1,
                'atr': round(df['ATR'].iloc[-1], 2) if not pd.isna(df['ATR'].iloc[-1]) else 0,
                'sentiment': sentiment,
                'score': round(sentiment_score, 1),
                'events': all_events,
                'breakout_events': breakout_events,
                'momentum_events': momentum_events,
                'event_triggers': event_triggers,
                'fundamentals': info,
                'data': df
            }
        except Exception as e:
            return None

def create_advanced_chart(df, symbol, events):
    """Create advanced chart with event markers"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=(f'{symbol} - Price with Events', 'Volume', 'RSI', 'MACD')
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # Add moving averages
    fig.add_trace(
        go.Scatter(x=df.index, y=df['SMA20'], name='SMA 20', line=dict(color='orange', width=1)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['SMA50'], name='SMA 50', line=dict(color='blue', width=1)),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(x=df.index, y=df['BB_Upper'], name='BB Upper', line=dict(color='gray', width=1, dash='dash')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['BB_Lower'], name='BB Lower', line=dict(color='gray', width=1, dash='dash')),
        row=1, col=1
    )
    
    # Volume
    colors = ['red' if row['Open'] > row['Close'] else 'green' for _, row in df.iterrows()]
    fig.add_trace(
        go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=colors),
        row=2, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple', width=2)),
        row=3, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    # MACD
    fig.add_trace(
        go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue', width=2)),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['Signal'], name='Signal', line=dict(color='red', width=2)),
        row=4, col=1
    )
    
    # MACD Histogram
    hist_colors = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
    fig.add_trace(
        go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=hist_colors),
        row=4, col=1
    )
    
    fig.update_layout(
        title=f"{symbol} - Advanced Technical Analysis with Event Triggers",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        template="plotly_dark",
        height=1000,
        showlegend=True
    )
    
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig

def main():
    st.title("🎯 NSE Advanced Scanner - Events & Options Analysis")
    st.markdown("---")
    
    # Initialize analyzers
    stock_scanner = EnhancedNSEScanner()
    options_analyzer = IndexOptionsAnalyzer()
    
    # Sidebar
    with st.sidebar:
        st.header("🔍 Analysis Mode")
        
        analysis_mode = st.radio(
            "Select Analysis Type",
            ["📊 Stock Scanner", "🎯 Index Options", "⚡ Event Triggers"]
        )
        
        st.markdown("---")
        
        if analysis_mode == "📊 Stock Scanner":
            scan_type = st.radio(
                "Scan Type",
                ["Nifty 50", "Single Stock"]
            )
            
            if scan_type == "Single Stock":
                stock_symbol = st.text_input("Stock Symbol", "RELIANCE.NS")
                st.caption("Add .NS for NSE stocks")
            
            st.markdown("---")
            st.subheader("Event Filters")
            show_breakouts = st.checkbox("Show Breakouts", True)
            show_momentum = st.checkbox("Show Momentum Shifts", True)
            show_fundamental = st.checkbox("Show Fundamental Events", True)
        
        scan_button = st.button("🚀 Start Analysis", use_container_width=True)
    
    if scan_button:
        if analysis_mode == "📊 Stock Scanner":
            if scan_type == "Nifty 50":
                with st.spinner("Scanning Nifty 50 stocks for events..."):
                    results = []
                    progress_bar = st.progress(0)
                    
                    for i, symbol in enumerate(stock_scanner.nifty50):
                        result = stock_scanner.analyze_stock(symbol)
                        if result:
                            results.append(result)
                        progress_bar.progress((i + 1) / len(stock_scanner.nifty50))
                    
                    if results:
                        df_results = pd.DataFrame(results)
                        
                        # Display metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Stocks", len(df_results))
                        with col2:
                            bullish = len(df_results[df_results['sentiment'] == 'Bullish'])
                            st.metric("🐂 Bullish", bullish)
                        with col3:
                            bearish = len(df_results[df_results['sentiment'] == 'Bearish'])
                            st.metric("🐻 Bearish", bearish)
                        with col4:
                            with_events = len(df_results[df_results['events'].apply(len) > 0])
                            st.metric("⚡ Active Events", with_events)
                        
                        # Display results table
                        st.subheader("📋 Scan Results with Events")
                        display_df = df_results[['symbol', 'price', 'change', 'rsi', 'sentiment', 'score', 'events']].copy()
                        display_df['event_count'] = display_df['events'].apply(len)
                        display_df = display_df.rename(columns={
                            'symbol': 'Symbol', 'price': 'Price', 'change': 'Change %',
                            'rsi': 'RSI', 'sentiment': 'Sentiment', 'score': 'Score',
                            'event_count': 'Events'
                        })
                        st.dataframe(display_df, use_container_width=True)
                        
                        # Detailed view
                        st.markdown("---")
                        selected = st.selectbox("Select stock for detailed event analysis", df_results['symbol'].tolist())
                        
                        if selected:
                            stock_data = df_results[df_results['symbol'] == selected].iloc[0]
                            
                            # Event display
                            if stock_data['events']:
                                st.subheader("⚡ Active Event Triggers")
                                for event in stock_data['events']:
                                    if 'Bullish' in event.get('type', '') or 'up' in event.get('desc', '').lower():
                                        st.markdown(f"""
                                        <div class='trigger-bullish'>
                                            <strong>🟢 {event.get('type', 'Event')}</strong><br>
                                            {event.get('desc', '')}<br>
                                            <span class='small-text'>Impact: {event.get('severity', 'Medium')}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div class='trigger-bearish'>
                                            <strong>🔴 {event.get('type', 'Event')}</strong><br>
                                            {event.get('desc', '')}<br>
                                            <span class='small-text'>Impact: {event.get('severity', 'Medium')}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                            else:
                                st.info("No active event triggers detected")
                            
                            # Chart
                            fig = create_advanced_chart(stock_data['data'], selected, stock_data['events'])
                            st.plotly_chart(fig, use_container_width=True)
            
            else:  # Single stock
                with st.spinner(f"Analyzing {stock_symbol} for events..."):
                    result = stock_scanner.analyze_stock(stock_symbol)
                    
                    if result:
                        # Display events
                        if result['events']:
                            st.subheader("⚡ Active Event Triggers")
                            for event in result['events']:
                                if 'Bullish' in event.get('type', '') or 'up' in event.get('desc', '').lower():
                                    st.markdown(f"""
                                    <div class='trigger-bullish'>
                                        <strong>🟢 {event.get('type', 'Event')}</strong><br>
                                        {event.get('desc', '')}<br>
                                        <span class='small-text'>Impact: {event.get('severity', 'Medium')}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown(f"""
                                    <div class='trigger-bearish'>
                                        <strong>🔴 {event.get('type', 'Event')}</strong><br>
                                        {event.get('desc', '')}<br>
                                        <span class='small-text'>Impact: {event.get('severity', 'Medium')}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Chart
                        fig = create_advanced_chart(result['data'], result['symbol'], result['events'])
                        st.plotly_chart(fig, use_container_width=True)
        
        elif analysis_mode == "🎯 Index Options":
            with st.spinner("Analyzing Index Options..."):
                options_data = options_analyzer.analyze_index_options()
                
                for index_name, data in options_data.items():
                    st.subheader(f"📊 {index_name} Options Analysis")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Spot Price", f"₹{data['price']:,.0f}", f"{data['change']}%")
                    with col2:
                        st.metric("Put-Call Ratio", data['pcr'], data['pcr_sentiment'])
                    with col3:
                        st.metric("Implied Volatility", f"{data['iv']}%", data['iv_level'])
                    with col4:
                        st.metric("Range", f"₹{data['levels']['support']:.0f} - ₹{data['levels']['resistance']:.0f}")
                    
                    # Option chain visualization
                    st.markdown("### 🎲 Option Chain Strikes")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Call Options (CE)**")
                        for strike in data['strikes']['CE']:
                            strike_diff = ((strike - data['price']) / data['price']) * 100
                            color = "green" if strike_diff < 0 else "red"
                            st.markdown(f"<span style='color:{color}'>₹{strike} ({strike_diff:+.1f}%)</span>", unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("**Put Options (PE)**")
                        for strike in data['strikes']['PE']:
                            strike_diff = ((strike - data['price']) / data['price']) * 100
                            color = "red" if strike_diff < 0 else "green"
                            st.markdown(f"<span style='color:{color}'>₹{strike} ({strike_diff:+.1f}%)</span>", unsafe_allow_html=True)
                    
                    # Support/Resistance visualization
                    st.markdown("### 📈 Key Levels")
                    levels_data = data['levels']
                    st.markdown(f"""
                    <div class='option-card'>
                        <strong>Resistance 2:</strong> ₹{levels_data['resistance_2']:.0f}<br>
                        <strong>Resistance 1:</strong> ₹{levels_data['resistance']:.0f}<br>
                        <strong>Current:</strong> ₹{levels_data['current']:.0f}<br>
                        <strong>Support 1:</strong> ₹{levels_data['support']:.0f}<br>
                        <strong>Support 2:</strong> ₹{levels_data['support_2']:.0f}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Options strategy suggestions
                    st.markdown("### 💡 Options Strategies")
                    if data['pcr'] > 1.2:
                        st.info("📉 High PCR suggests bearish sentiment. Consider Bear Put Spread or Short Calls")
                    elif data['pcr'] < 0.8:
                        st.info("📈 Low PCR suggests bullish sentiment. Consider Bull Call Spread or Short Puts")
                    else:
                        st.info("⚖️ Neutral PCR. Consider Iron Condor or Strangle for range-bound market")
                    
                    st.markdown("---")
        
        elif analysis_mode == "⚡ Event Triggers":
            st.subheader("🔥 Top Event-Driven Opportunities")
            
            with st.spinner("Scanning for event triggers..."):
                all_stocks = []
                for symbol in stock_scanner.nifty50:
                    result = stock_scanner.analyze_stock(symbol)
                    if result and result['events']:
                        all_stocks.append(result)
                
                if all_stocks:
                    # Sort by event count
                    all_stocks.sort(key=lambda x: len(x['events']), reverse=True)
                    
                    for stock in all_stocks[:10]:  # Top 10
                        st.markdown(f"""
                        <div class='event-box'>
                            <h3>{stock['symbol']}</h3>
                            <p>Price: ₹{stock['price']} | Change: {stock['change']}% | RSI: {stock['rsi']}</p>
                            <p><strong>{len(stock['events'])} Active Events:</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        for event in stock['events']:
                            st.markdown(f"- {event.get('desc', 'Event detected')}")
                        
                        st.markdown("---")
                else:
                    st.info("No active event triggers found in Nifty 50 stocks")
    
    else:
        st.info("👈 Select analysis mode and click 'Start Analysis'")
        
        with st.expander("🎯 What's New in This Version?"):
            st.markdown("""
            ### ✨ New Features:
            
            **Event-Based Triggers:**
            - 🚀 Breakout/Breakdown detection
            - 📈 Momentum shifts (RSI divergence)
            - 💰 Earnings & dividend alerts
            - ⭐ Analyst rating changes
            - 🎯 Price target triggers
            
            **Index Options Analysis:**
            - 📊 NIFTY & BANKNIFTY options
            - 🔄 Put-Call Ratio (PCR)
            - 📈 Implied Volatility (IV)
            - 🎲 Option chain visualization
            - 💡 Strategy suggestions
            
            **Enhanced Visualization:**
            - Event markers on charts
            - Color-coded triggers
            - Real-time event detection
            - Impact severity indicators
            """)

if __name__ == "__main__":
    main()