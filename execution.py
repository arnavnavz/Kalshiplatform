"""
Trade execution layer.
Handles SHADOW and LIVE mode order placement.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from models import Market, Trade
from kalshi_client import KalshiClient
from research import GameResearch

logger = logging.getLogger(__name__)


def setup_shadow_logging() -> logging.Logger:
    """Set up logging for shadow trades."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    shadow_logger = logging.getLogger("shadow_trades")
    shadow_logger.setLevel(logging.INFO)
    
    # File handler for shadow trades
    file_handler = logging.FileHandler(log_dir / "shadow_trades.log")
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    
    # Avoid duplicate handlers
    if not shadow_logger.handlers:
        shadow_logger.addHandler(file_handler)
    
    return shadow_logger


def execute_trade(
    market: Market,
    stake: float,
    kalshi_price: float,
    fair_prob: float,
    edge: float,
    config: Config,
    kalshi_client: KalshiClient,
    mode: str,
    opponent: str = None,
    game_time: datetime = None,
    research: GameResearch = None
) -> Optional[Trade]:
    """
    Execute a trade (SHADOW or LIVE mode).
    
    Args:
        market: Market to trade
        stake: Stake amount in dollars
        kalshi_price: Kalshi market price
        fair_prob: Fair probability
        edge: Calculated edge
        config: Configuration
        kalshi_client: Kalshi client instance
        mode: "SHADOW" or "LIVE"
        
    Returns:
        Trade object if executed, None otherwise
    """
    # Calculate limit price with slippage tolerance
    max_price = min(1.0, kalshi_price + config.slippage_tolerance)
    
    # Calculate quantity (number of contracts)
    # Each contract costs the price and pays $1 if it wins
    quantity = int(stake / max_price)
    
    if quantity <= 0:
        logger.warning(f"Stake ${stake:.2f} too small for price {max_price:.4f}")
        return None
    
    if mode == "SHADOW":
        # Log shadow trade
        shadow_logger = setup_shadow_logging()
        
        trade = Trade(
            timestamp=datetime.now(),
            market_id=market.market_id,
            game_id=market.game_id,
            team=market.team,
            league=market.league,
            fair_prob=fair_prob,
            kalshi_prob=kalshi_price,
            edge=edge,
            stake=stake,
            quantity=quantity,
            limit_price=max_price,
            mode="SHADOW",
            order_id=None
        )
        
        # Extract opponent and game time if not provided
        if opponent is None:
            # Parse from event_name (e.g., "Sacramento vs Memphis Winner?")
            if " vs " in market.event_name:
                parts = market.event_name.replace(" Winner?", "").split(" vs ")
                if market.team in parts[0]:
                    opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
                elif market.team in parts[1]:
                    opponent = parts[0].strip()
                else:
                    # Try to match by abbreviation or use the other team
                    opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
            else:
                opponent = "Unknown"
        
        if game_time is None:
            game_time = market.start_time
        
        # Format game time in Eastern timezone
        from pytz import timezone
        import pytz
        
        if game_time:
            # Convert to Eastern time
            if game_time.tzinfo is None:
                # Assume UTC if no timezone info
                game_time = pytz.utc.localize(game_time)
            
            eastern = timezone('US/Eastern')
            game_time_et = game_time.astimezone(eastern)
            game_time_str = game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
            
            # Calculate time until game
            now_utc = datetime.now(pytz.utc) if game_time.tzinfo else datetime.now()
            if game_time.tzinfo:
                time_diff = (game_time - now_utc).total_seconds() / 3600  # hours
            else:
                time_diff = (game_time - datetime.now()).total_seconds() / 3600
            
            if time_diff > 24:
                time_until_game = f"{time_diff/24:.1f} days"
            elif time_diff > 1:
                time_until_game = f"{time_diff:.1f} hours"
            elif time_diff > 0:
                time_until_game = f"{time_diff*60:.0f} minutes"
            else:
                time_until_game = "Game started"
        else:
            game_time_str = "Unknown"
            time_until_game = "Unknown"
        
        # Generate reasoning for the trade
        edge_pct = edge * 100
        kalshi_pct = kalshi_price * 100
        fair_pct = fair_prob * 100
        
        # Base reasoning from edge
        if edge > 0.20:
            conviction = "HIGH"
            base_reasoning = f"Strong edge: Kalshi prices {market.team} at {kalshi_pct:.1f}% but fair value is {fair_pct:.1f}% (edge: {edge_pct:.1f}%)"
        elif edge > 0.10:
            conviction = "MEDIUM"
            base_reasoning = f"Good edge: Kalshi prices {market.team} at {kalshi_pct:.1f}% vs fair value {fair_pct:.1f}% (edge: {edge_pct:.1f}%)"
        else:
            conviction = "LOW"
            base_reasoning = f"Moderate edge: Kalshi prices {market.team} at {kalshi_pct:.1f}% vs fair value {fair_pct:.1f}% (edge: {edge_pct:.1f}%)"
        
        # Add research-based reasoning if available
        if research and research.reasoning:
            reasoning = f"{base_reasoning}. Research: {research.reasoning}"
        else:
            reasoning = base_reasoning
        
        # Ensure opponent and game_time are set (should never be None at this point)
        if opponent is None:
            opponent = "Unknown"
            logger.warning(f"Opponent was None for market {market.market_id}, using Unknown")
        
        if game_time_str is None or game_time_str == "Unknown":
            logger.warning(f"Game time was None/Unknown for market {market.market_id}")
            game_time_str = "Unknown"
            time_until_game = "Unknown"
        
        # Log detailed trade information with game details
        shadow_logger.info(
            f"SHADOW TRADE | "
            f"market_id={market.market_id} | "
            f"game_id={market.game_id} | "
            f"team={market.team} | "
            f"opponent={opponent} | "
            f"league={market.league} | "
            f"game_time_et={game_time_str} | "
            f"time_until_game={time_until_game} | "
            f"fair_prob={fair_prob:.4f} | "
            f"kalshi_prob={kalshi_price:.4f} | "
            f"edge={edge:.4f} | "
            f"conviction={conviction} | "
            f"reasoning={reasoning} | "
            f"stake=${stake:.2f} | "
            f"quantity={quantity} | "
            f"limit_price={max_price:.4f}"
        )
        
        logger.info(
            f"SHADOW: Would buy {quantity} YES @ {max_price:.4f} "
            f"for ${stake:.2f} on {market.team} vs {opponent} "
            f"({market.league}, {time_until_game} until game) (edge={edge:.4f})"
        )
        
        return trade
    
    elif mode == "LIVE":
        # Place real order
        logger.warning(f"LIVE MODE: Placing real order on {market.market_id}")
        
        try:
            order_id = kalshi_client.place_yes_order(
                market_id=market.market_id,
                price=max_price,
                size=quantity
            )
            
            trade = Trade(
                timestamp=datetime.now(),
                market_id=market.market_id,
                game_id=market.game_id,
                team=market.team,
                league=market.league,
                fair_prob=fair_prob,
                kalshi_prob=kalshi_price,
                edge=edge,
                stake=stake,
                quantity=quantity,
                limit_price=max_price,
                mode="LIVE",
                order_id=order_id
            )
            
            logger.info(
                f"LIVE: Placed order {order_id} - "
                f"{quantity} YES @ {max_price:.4f} "
                f"for ${stake:.2f} on {market.team}"
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Failed to place LIVE order: {e}", exc_info=True)
            return None
    
    else:
        logger.error(f"Invalid mode: {mode}")
        return None

