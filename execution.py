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
    mode: str
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
        
        # Log detailed trade information
        shadow_logger.info(
            f"SHADOW TRADE | "
            f"market_id={market.market_id} | "
            f"game_id={market.game_id} | "
            f"team={market.team} | "
            f"league={market.league} | "
            f"fair_prob={fair_prob:.4f} | "
            f"kalshi_prob={kalshi_price:.4f} | "
            f"edge={edge:.4f} | "
            f"stake=${stake:.2f} | "
            f"quantity={quantity} | "
            f"limit_price={max_price:.4f}"
        )
        
        logger.info(
            f"SHADOW: Would buy {quantity} YES @ {max_price:.4f} "
            f"for ${stake:.2f} on {market.team} (edge={edge:.4f})"
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

