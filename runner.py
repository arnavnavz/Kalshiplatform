"""
Main event loop for the Sharp Mismatch Sports Bot.
Wires together all components and runs periodically.
"""
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import load_config
from kalshi_client import KalshiClient
from odds_client import OddsClient
from models import Market, Game, FairProbabilities
from strategy import (
    compute_fair_probs,
    calc_edge,
    kelly_fraction,
    get_fair_prob_for_team
)
from risk_engine import RiskEngine
from execution import execute_trade

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def setup_logger() -> logging.Logger:
    """Set up main application logger."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler(log_dir / "bot.log")
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger


def market_is_eligible(market: Market, config) -> bool:
    """
    Check if a market passes all eligibility filters.
    
    Args:
        market: Market to check
        config: Configuration object
        
    Returns:
        True if market is eligible, False otherwise
    """
    # Check volume
    if market.volume < config.min_market_volume:
        logger.debug(
            f"Market {market.market_id} filtered: "
            f"volume {market.volume} < {config.min_market_volume}"
        )
        return False
    
    # Check spread
    if market.spread > config.max_spread:
        logger.debug(
            f"Market {market.market_id} filtered: "
            f"spread {market.spread:.4f} > {config.max_spread:.4f}"
        )
        return False
    
    # Check time to start
    time_to_start = (market.start_time - datetime.now()).total_seconds() / 60
    if time_to_start < config.min_time_to_start_minutes:
        logger.debug(
            f"Market {market.market_id} filtered: "
            f"too close to start ({time_to_start:.1f} min < {config.min_time_to_start_minutes} min)"
        )
        return False
    
    return True


def extract_games_from_markets(markets: List[Market]) -> List[Game]:
    """
    Extract unique games from markets.
    
    TODO: This is a simplified implementation. You may need to adjust
    based on actual Kalshi market structure and naming conventions.
    
    Args:
        markets: List of markets
        
    Returns:
        List of unique Game objects
    """
    games_dict: Dict[str, Game] = {}
    
    for market in markets:
        if market.game_id not in games_dict:
            # Parse team names from event_name or title
            # This is a simplified parser - adjust based on actual format
            # Example: "Lakers vs Warriors" or "Lakers to win vs Warriors"
            event_parts = market.event_name.replace(" to win", "").split(" vs ")
            if len(event_parts) == 2:
                team_a, team_b = event_parts[0].strip(), event_parts[1].strip()
            else:
                # Fallback: use team from market
                team_a = market.team
                team_b = "Unknown"
            
            games_dict[market.game_id] = Game(
                game_id=market.game_id,
                team_a=team_a,
                team_b=team_b,
                league=market.league,
                start_time=market.start_time
            )
    
    return list(games_dict.values())


def map_market_to_game_and_team(market: Market) -> Tuple[str, str, str, str]:
    """
    Map a market to its game and team information.
    
    TODO: Adjust this based on actual Kalshi market structure.
    
    Args:
        market: Market object
        
    Returns:
        Tuple of (game_id, team, team_a, team_b)
    """
    # Parse team names from event_name
    event_parts = market.event_name.replace(" to win", "").split(" vs ")
    if len(event_parts) == 2:
        team_a, team_b = event_parts[0].strip(), event_parts[1].strip()
    else:
        team_a = market.team
        team_b = "Unknown"
    
    return market.game_id, market.team, team_a, team_b


def main():
    """Main event loop."""
    logger.info("=" * 60)
    logger.info("Sharp Mismatch Sports Bot Starting")
    logger.info("=" * 60)
    
    try:
        config = load_config()
        logger.info(f"Mode: {config.mode}")
        logger.info(f"Poll interval: {config.poll_interval_seconds}s")
        
        # Initialize clients
        kalshi = KalshiClient(config)
        odds = OddsClient(config)
        risk = RiskEngine(config)
        
        iteration = 0
        
        while True:
            iteration += 1
            logger.info(f"\n--- Iteration {iteration} ---")
            
            try:
                # Get account state
                bankroll = kalshi.get_account_balance()
                positions = kalshi.get_positions()
                risk.update_from_positions(positions, bankroll)
                
                logger.info(f"Bankroll: ${bankroll:.2f}")
                logger.info(f"Open positions: {len(positions)}")
                logger.info(f"Daily risk: ${risk.total_daily_risk:.2f} / ${config.max_daily_risk_pct * bankroll:.2f}")
                
                # Fetch markets
                markets = kalshi.fetch_sports_markets()
                logger.info(f"Fetched {len(markets)} markets")
                
                if not markets:
                    logger.info("No markets available, sleeping...")
                    time.sleep(config.poll_interval_seconds)
                    continue
                
                # Extract games and fetch reference odds
                games = extract_games_from_markets(markets)
                logger.info(f"Extracted {len(games)} unique games")
                
                ref_odds = odds.fetch_reference_odds(games)
                fair_probs = compute_fair_probs(ref_odds)
                
                # Process each market
                trades_executed = 0
                for market in markets:
                    # Filter markets
                    if not market_is_eligible(market, config):
                        continue
                    
                    # Map market to game and team
                    game_id, team, team_a, team_b = map_market_to_game_and_team(market)
                    
                    # Get fair probability
                    if game_id not in fair_probs:
                        logger.debug(f"No fair probabilities for game_id: {game_id}")
                        continue
                    
                    fair_prob = get_fair_prob_for_team(
                        fair_probs, game_id, team, team_a, team_b
                    )
                    kalshi_prob = market.best_yes_price
                    
                    # Calculate edge
                    edge = calc_edge(fair_prob, kalshi_prob)
                    
                    if edge < config.edge_threshold:
                        logger.debug(
                            f"Market {market.market_id}: edge {edge:.4f} < "
                            f"threshold {config.edge_threshold:.4f}"
                        )
                        continue
                    
                    logger.info(
                        f"Found edge opportunity: {market.team} | "
                        f"fair={fair_prob:.4f}, kalshi={kalshi_prob:.4f}, "
                        f"edge={edge:.4f}"
                    )
                    
                    # Calculate Kelly sizing
                    kelly_frac = kelly_fraction(
                        fair_prob, kalshi_prob, config.kelly_factor
                    )
                    raw_stake = kelly_frac * bankroll
                    
                    # Apply risk caps
                    stake = risk.cap_stake(raw_stake, game_id, team, market.league)
                    
                    if stake <= 0:
                        logger.debug(f"Stake capped to 0 for market {market.market_id}")
                        continue
                    
                    # Check risk limits
                    if not risk.can_take_trade(stake, game_id, team, market.league):
                        logger.debug(f"Trade rejected by risk engine for {market.market_id}")
                        continue
                    
                    # Execute trade
                    trade = execute_trade(
                        market=market,
                        stake=stake,
                        kalshi_price=kalshi_prob,
                        fair_prob=fair_prob,
                        edge=edge,
                        config=config,
                        kalshi_client=kalshi,
                        mode=config.mode
                    )
                    
                    if trade:
                        trades_executed += 1
                        # Update risk engine with new position (simplified)
                        # In a real implementation, you'd wait for order confirmation
                        if config.mode == "SHADOW":
                            # For shadow mode, we can simulate position update
                            pass
                
                logger.info(f"Executed {trades_executed} trades this iteration")
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.exception(f"Error in main loop iteration {iteration}: {e}")
            
            # Sleep before next iteration
            logger.info(f"Sleeping for {config.poll_interval_seconds} seconds...")
            time.sleep(config.poll_interval_seconds)
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

