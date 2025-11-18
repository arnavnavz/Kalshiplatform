"""
Streamlit dashboard for the Sharp Mismatch Sports Bot.
Provides real-time monitoring, trade history, and metrics.
"""
import re
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from config import load_config

# Page configuration
st.set_page_config(
    page_title="Sharp Mismatch Sports Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .trade-positive {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .trade-negative {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    </style>
""", unsafe_allow_html=True)


def parse_shadow_trade_log(log_file: Path) -> List[Dict]:
    """Parse shadow trades from log file."""
    trades = []
    
    if not log_file.exists():
        return trades
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if "SHADOW TRADE" in line:
                    # Parse log line format:
                    # timestamp | SHADOW TRADE | market_id=... | game_id=... | ...
                    parts = line.split('|')
                    if len(parts) < 3:
                        continue
                    
                    trade = {
                        'timestamp': parts[0].strip(),
                        'type': 'SHADOW'
                    }
                    
                    # Extract key-value pairs
                    for part in parts[2:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Try to parse numeric values
                            if key in ['fair_prob', 'kalshi_prob', 'edge', 'stake', 'limit_price']:
                                try:
                                    # Remove currency symbols and commas for stake
                                    if key == 'stake':
                                        clean_value = value.replace('$', '').replace(',', '').strip()
                                        trade[key] = float(clean_value)
                                    else:
                                        trade[key] = float(value)
                                except ValueError:
                                    trade[key] = value
                            elif key == 'quantity':
                                try:
                                    trade[key] = int(value)
                                except ValueError:
                                    trade[key] = value
                            else:
                                trade[key] = value
                    
                    trades.append(trade)
    except Exception as e:
        st.error(f"Error reading log file: {e}")
    
    return trades


def parse_bot_log(log_file: Path) -> List[Dict]:
    """Parse bot activity from main log file."""
    log_entries = []
    
    if not log_file.exists():
        return log_entries
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        log_entries.append({
                            'timestamp': parts[0].strip(),
                            'level': parts[2].strip() if len(parts) > 2 else 'INFO',
                            'message': '|'.join(parts[3:]).strip() if len(parts) > 3 else ''
                        })
    except Exception as e:
        st.error(f"Error reading bot log: {e}")
    
    return log_entries[-100:]  # Last 100 entries


def calculate_metrics(trades: List[Dict]) -> Dict:
    """Calculate trading metrics from trades."""
    if not trades:
        return {
            'total_trades': 0,
            'total_stake': 0.0,
            'avg_edge': 0.0,
            'avg_stake': 0.0,
            'total_quantity': 0
        }
    
    total_trades = len(trades)
    # Safely convert stake to float if it's a string
    total_stake = sum(
        float(t.get('stake', 0)) if isinstance(t.get('stake', 0), (int, float)) 
        else float(str(t.get('stake', 0)).replace('$', '').replace(',', '').strip() or 0)
        for t in trades
    )
    total_quantity = sum(
        int(t.get('quantity', 0)) if isinstance(t.get('quantity', 0), (int, float))
        else int(str(t.get('quantity', 0)).strip() or 0)
        for t in trades
    )
    edges = [
        float(t.get('edge', 0)) if isinstance(t.get('edge', 0), (int, float))
        else float(str(t.get('edge', 0)).strip() or 0)
        for t in trades if 'edge' in t
    ]
    stakes = [
        float(t.get('stake', 0)) if isinstance(t.get('stake', 0), (int, float))
        else float(str(t.get('stake', 0)).replace('$', '').replace(',', '').strip() or 0)
        for t in trades if 'stake' in t
    ]
    
    return {
        'total_trades': total_trades,
        'total_stake': total_stake,
        'avg_edge': sum(edges) / len(edges) if edges else 0.0,
        'avg_stake': sum(stakes) / len(stakes) if stakes else 0.0,
        'total_quantity': total_quantity,
        'max_edge': max(edges) if edges else 0.0,
        'min_edge': min(edges) if edges else 0.0
    }


def main():
    """Main dashboard application."""
    # Header
    st.markdown('<div class="main-header">📊 Sharp Mismatch Sports Bot Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        try:
            config = load_config()
            
            st.subheader("Bot Status")
            mode_color = "🟢" if config.mode == "SHADOW" else "🔴"
            st.write(f"{mode_color} Mode: **{config.mode}**")
            
            st.subheader("Strategy Parameters")
            st.write(f"**Edge Threshold:** {config.edge_threshold:.1%}")
            st.write(f"**Kelly Factor:** {config.kelly_factor:.1%}")
            st.write(f"**Poll Interval:** {config.poll_interval_seconds}s")
            
            st.subheader("Risk Limits")
            st.write(f"**Max Per Bet:** {config.max_per_bet_pct:.1%}")
            st.write(f"**Max Per Game:** {config.max_per_game_pct:.1%}")
            st.write(f"**Max Daily Risk:** {config.max_daily_risk_pct:.1%}")
            st.write(f"**Max Per Team:** {config.max_per_team_pct:.1%}")
            
            st.subheader("Market Filters")
            st.write(f"**Min Volume:** {config.min_market_volume:,}")
            st.write(f"**Max Spread:** {config.max_spread:.1%}")
            st.write(f"**Min Time to Start:** {config.min_time_to_start_minutes} min")
            
        except Exception as e:
            st.error(f"Error loading config: {e}")
    
    # Main content
    log_dir = Path("logs")
    shadow_log = log_dir / "shadow_trades.log"
    bot_log = log_dir / "bot.log"
    
    # Load data
    trades = parse_shadow_trade_log(shadow_log)
    log_entries = parse_bot_log(bot_log)
    metrics = calculate_metrics(trades)
    
    # Metrics row
    st.subheader("📈 Trading Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Trades", metrics['total_trades'])
    with col2:
        st.metric("Total Stake", f"${metrics['total_stake']:,.2f}")
    with col3:
        st.metric("Avg Edge", f"{metrics['avg_edge']:.2%}")
    with col4:
        st.metric("Avg Stake", f"${metrics['avg_stake']:,.2f}")
    with col5:
        st.metric("Total Contracts", f"{metrics['total_quantity']:,}")
    
    # Edge distribution
    if trades:
        st.subheader("📊 Edge Distribution")
        edges = [t.get('edge', 0) for t in trades if 'edge' in t]
        if edges:
            edge_df = pd.DataFrame({'Edge': edges})
            st.bar_chart(edge_df)
    
    # Recent trades table
    st.subheader("📋 Recent Trades")
    
    if trades:
        # Convert to DataFrame for display
        trades_df_data = []
        for trade in trades[-50:]:  # Last 50 trades
            # Format game matchup
            team = trade.get('team', 'Unknown')
            opponent = trade.get('opponent', 'Unknown')
            matchup = f"{team} vs {opponent}" if opponent != 'Unknown' else team
            
            # Format game time - prefer game_time_et if available
            game_time_et = trade.get('game_time_et', '')
            game_time = trade.get('game_time', '')
            time_until = trade.get('time_until_game', '')
            
            # Use ET time if available, otherwise fall back to regular game_time
            if game_time_et:
                game_info = game_time_et
            elif game_time and time_until:
                game_info = f"{game_time} ({time_until})"
            elif time_until:
                game_info = f"In {time_until}"
            elif game_time:
                game_info = game_time
            else:
                game_info = 'N/A'
            
            # Get conviction and reasoning
            conviction = trade.get('conviction', 'N/A')
            reasoning = trade.get('reasoning', 'N/A')
            
            # Get game time in ET
            game_time_et = trade.get('game_time_et', trade.get('game_time', 'N/A'))
            
            trades_df_data.append({
                'Timestamp': trade.get('timestamp', ''),
                'Matchup': matchup,
                'Team Betting': team,  # Which team we're choosing
                'Opponent': opponent if opponent != 'Unknown' else 'N/A',
                'League': trade.get('league', ''),
                'Game Time (ET)': game_time_et,
                'Time Until': time_until if time_until else 'N/A',
                'Conviction': conviction,
                'Reasoning': reasoning[:80] + '...' if len(reasoning) > 80 else reasoning,
                'Fair Prob': f"{trade.get('fair_prob', 0):.2%}" if 'fair_prob' in trade else 'N/A',
                'Kalshi Prob': f"{trade.get('kalshi_prob', 0):.2%}" if 'kalshi_prob' in trade else 'N/A',
                'Edge': f"{trade.get('edge', 0):.2%}" if 'edge' in trade else 'N/A',
                'Stake': f"${trade.get('stake', 0):,.2f}" if 'stake' in trade else 'N/A',
                'Quantity': trade.get('quantity', 0),
                'Price': f"{trade.get('limit_price', 0):.4f}" if 'limit_price' in trade else 'N/A'
            })
        
        trades_df = pd.DataFrame(trades_df_data)
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        
        # Download button
        csv = trades_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Trades CSV",
            data=csv,
            file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No trades found. The bot may not have executed any trades yet, or logs are empty.")
        st.write("**Tip:** Run the bot with `python runner.py` to generate trade logs.")
    
    # Bot activity log
    with st.expander("📝 Recent Bot Activity", expanded=False):
        if log_entries:
            for entry in log_entries[-20:]:  # Last 20 log entries
                level = entry.get('level', 'INFO')
                message = entry.get('message', '')
                timestamp = entry.get('timestamp', '')
                
                if 'ERROR' in level:
                    st.error(f"**{timestamp}** | {message}")
                elif 'WARNING' in level:
                    st.warning(f"**{timestamp}** | {message}")
                else:
                    st.text(f"{timestamp} | {message}")
        else:
            st.info("No bot log entries found.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <p>Sharp Mismatch Sports Bot Dashboard | 
            <a href='https://github.com/arnavnavz/Kalshiplatform' target='_blank'>GitHub</a></p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

