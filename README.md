# Sharp Mismatch Sports Bot

A Python-based sports betting bot for Kalshi that implements a rules-based "Sharp Mismatch" strategy. The bot identifies markets where Kalshi's implied probability is significantly worse than reference "fair" probabilities and places bets using fractional Kelly sizing with strict risk limits.

## Strategy Overview

The **Sharp Mismatch Sports Bot** works by:

1. **Fetching markets** from Kalshi's API
2. **Comparing odds** with reference odds from external sources (e.g., Vegas lines)
3. **Identifying edges** where Kalshi's price is significantly below fair value
4. **Sizing bets** using fractional Kelly criterion with multiple risk caps
5. **Executing trades** in either SHADOW (paper trading) or LIVE mode

### Entry Rules

- Only considers LONG YES trades (no shorts)
- Requires edge ≥ `EDGE_THRESHOLD` (default 7 percentage points)
- Markets must pass liquidity checks (volume, spread)
- Markets must have sufficient time before game start

### Risk Management

- **Per-bet cap**: Maximum stake per individual trade
- **Per-game cap**: Maximum exposure per game
- **Per-team cap**: Maximum exposure per team
- **Daily risk cap**: Maximum total risk per day
- **Fractional Kelly**: Uses a fraction of full Kelly (default 25%) for safety

## Setup

### Prerequisites

- Python 3.11+
- pip

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file from the example:
```bash
cp .env.example .env
```

4. Edit `.env` with your configuration:
```env
# Kalshi API Configuration (required for LIVE mode)
KALSHI_API_KEY=your_api_key_here
KALSHI_API_SECRET=your_api_secret_here
KALSHI_BASE_URL=https://api.demo.kalshi.com/trade-api/v2

# Bot Mode: SHADOW (paper trading) or LIVE (real orders)
MODE=SHADOW

# Polling Configuration
POLL_INTERVAL_SECONDS=60

# Strategy Parameters
EDGE_THRESHOLD=0.07
KELLY_FACTOR=0.25
MAX_PER_BET_PCT=0.02
MAX_PER_GAME_PCT=0.05
MAX_DAILY_RISK_PCT=0.10
MAX_PER_TEAM_PCT=0.08

# Market Filtering
MIN_MARKET_VOLUME=2000
MAX_SPREAD=0.08
MIN_TIME_TO_START_MINUTES=5
SLIPPAGE_TOLERANCE=0.02
```

## Usage

### SHADOW Mode (Paper Trading)

**Recommended for testing and development.**

SHADOW mode logs all hypothetical trades without placing real orders. This allows you to:
- Test the strategy logic
- Review trade decisions
- Backtest paper P&L

To run in SHADOW mode:

```bash
MODE=SHADOW python runner.py
```

Or set `MODE=SHADOW` in your `.env` file and run:
```bash
python runner.py
```

Shadow trades are logged to `logs/shadow_trades.log` with detailed information including:
- Timestamp
- Market ID
- Game ID and team
- Fair probability vs Kalshi probability
- Edge
- Stake amount
- Intended limit price

### LIVE Mode (Real Trading)

**⚠️ WARNING: LIVE mode places real orders with real money. Use with extreme caution.**

Before using LIVE mode:

1. **Test thoroughly in SHADOW mode first**
2. **Verify your API keys are correct**
3. **Start with small position sizes**
4. **Monitor closely**

To run in LIVE mode:

```bash
MODE=LIVE python runner.py
```

Or set `MODE=LIVE` in your `.env` file.

**Requirements for LIVE mode:**
- Valid `KALSHI_API_KEY` and `KALSHI_API_SECRET` in `.env`
- Sufficient account balance
- API access enabled on your Kalshi account

### Web Dashboard

The project includes a Streamlit web dashboard for monitoring bot activity, viewing trades, and tracking performance.

**To launch the dashboard:**

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

**Dashboard Features:**
- 📈 **Trading Metrics**: Total trades, stake, average edge, and more
- 📊 **Edge Distribution**: Visual chart of trade edges
- 📋 **Recent Trades Table**: Detailed view of all shadow/live trades
- ⚙️ **Configuration Display**: View current bot settings and risk limits
- 📝 **Bot Activity Log**: Recent bot log entries
- 📥 **CSV Export**: Download trade history as CSV

**Note:** The dashboard reads from log files, so make sure the bot has been run at least once to generate logs. The dashboard updates automatically when you refresh the page.

## Configuration

### Strategy Parameters

- `EDGE_THRESHOLD` (default: 0.07): Minimum edge required to enter a trade (7 percentage points)
- `KELLY_FACTOR` (default: 0.25): Fraction of full Kelly to use (25% = conservative)

### Risk Limits

- `MAX_PER_BET_PCT` (default: 0.02): Maximum stake per trade as % of bankroll (2%)
- `MAX_PER_GAME_PCT` (default: 0.05): Maximum exposure per game (5%)
- `MAX_DAILY_RISK_PCT` (default: 0.10): Maximum total daily risk (10%)
- `MAX_PER_TEAM_PCT` (default: 0.08): Maximum exposure per team (8%)

### Market Filtering

- `MIN_MARKET_VOLUME` (default: 2000): Minimum market volume to trade
- `MAX_SPREAD` (default: 0.08): Maximum spread (8 cents)
- `MIN_TIME_TO_START_MINUTES` (default: 5): Minimum minutes before game start
- `SLIPPAGE_TOLERANCE` (default: 0.02): Maximum price slippage tolerance (2 cents)

### Polling

- `POLL_INTERVAL_SECONDS` (default: 60): How often to check for new opportunities

## Project Structure

```
.
├── config.py              # Configuration management
├── kalshi_client.py       # Kalshi API wrapper
├── odds_client.py         # Reference odds client (mocked)
├── models.py              # Data models
├── strategy.py            # Strategy logic (edge, Kelly)
├── risk_engine.py         # Risk management
├── execution.py           # Trade execution (SHADOW/LIVE)
├── runner.py              # Main event loop
├── dashboard.py           # Streamlit web dashboard
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── README.md              # This file
└── logs/                  # Log files (created automatically)
    ├── bot.log            # Main bot logs
    └── shadow_trades.log  # Shadow trade log
```

## Implementation Status

### ✅ Completed

- Project structure and configuration
- Data models
- Strategy logic (edge calculation, Kelly sizing)
- Risk engine with position tracking
- Execution layer (SHADOW and LIVE modes)
- Main event loop
- Logging

### 🔧 TODO: Real API Integration

The following components currently use mock data and need real API integration:

1. **Kalshi API Client** (`kalshi_client.py`):
   - Real authentication endpoint
   - Real balance endpoint
   - Real positions endpoint
   - Real markets endpoint
   - Real order placement endpoint

2. **Reference Odds Client** (`odds_client.py`):
   - Integrate with real odds provider (e.g., The Odds API, SportsDataIO)
   - Map Kalshi markets to external games
   - Handle odds format conversion

3. **Market Parsing** (`runner.py`):
   - Adjust `extract_games_from_markets()` based on actual Kalshi market structure
   - Adjust `map_market_to_game_and_team()` for proper team matching
   - Handle different market naming conventions

## Logging

The bot creates two log files:

1. **`logs/bot.log`**: Main application log with all operations
2. **`logs/shadow_trades.log`**: Detailed log of all shadow trades (SHADOW mode only)

Logs are automatically created in the `logs/` directory.

## Development Notes

### Market Mapping

The current implementation uses simplified market parsing. You'll need to adjust:
- `extract_games_from_markets()` in `runner.py`
- `map_market_to_game_and_team()` in `runner.py`
- Team name matching in `get_fair_prob_for_team()` in `strategy.py`

These functions assume markets follow patterns like "Team A vs Team B - Team A to win". Actual Kalshi market formats may differ.

### Reference Odds

The current implementation uses mock odds. To integrate real odds:

1. Choose an odds provider (e.g., The Odds API, SportsDataIO)
2. Update `odds_client.py` to fetch real data
3. Implement proper game/market matching logic
4. Handle different leagues and sports

### Testing

Always test in SHADOW mode first. Review `logs/shadow_trades.log` to verify:
- Trades are being identified correctly
- Sizing looks reasonable
- Risk limits are being respected

## Safety Features

- **SHADOW mode by default**: Prevents accidental real trades
- **Multiple risk caps**: Per-bet, per-game, per-team, and daily limits
- **Fractional Kelly**: Uses conservative sizing (default 25% of full Kelly)
- **Market filtering**: Only trades liquid markets with sufficient time
- **Comprehensive logging**: All decisions are logged for review

## Disclaimer

This bot is for educational and research purposes. Sports betting involves risk of financial loss. Always:
- Test thoroughly in SHADOW mode
- Start with small position sizes
- Monitor performance closely
- Understand the risks involved
- Comply with all applicable laws and regulations

## License

This project is provided as-is for educational purposes.

