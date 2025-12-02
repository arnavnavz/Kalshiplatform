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
    
    # Check time to start - must be in the future
    # Handle timezone-aware vs naive datetime comparison
    from pytz import utc
    now = datetime.now(utc) if market.start_time.tzinfo else datetime.now()
    if market.start_time.tzinfo and not now.tzinfo:
        now = utc.localize(now)
    elif not market.start_time.tzinfo and now.tzinfo:
        market_start = utc.localize(market.start_time)
        time_to_start_minutes = (market_start - now).total_seconds() / 60
    else:
        time_to_start_minutes = (market.start_time - now).total_seconds() / 60
    
    # Filter out past games
    if time_to_start_minutes < 0:
        logger.debug(
            f"Market {market.market_id} filtered: "
            f"game is in the past ({time_to_start_minutes:.1f} minutes ago)"
        )
        return False
    
    # Check minimum time to start
    if time_to_start_minutes < config.min_time_to_start_minutes:
        logger.debug(
            f"Market {market.market_id} filtered: "
            f"too close to start ({time_to_start_minutes:.1f} min < {config.min_time_to_start_minutes} min)"
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
        from research import ResearchEngine
        research = ResearchEngine()
        
        iteration = 0
        
        while True:
            iteration += 1
            logger.info(f"\n--- Iteration {iteration} ---")
            
            try:
                # Get account state (use default in SHADOW mode if auth fails)
                try:
                    bankroll = kalshi.get_account_balance()
                    positions = kalshi.get_positions()
                except Exception as e:
                    if config.mode == "SHADOW":
                        logger.warning(f"Could not authenticate with Kalshi API: {e}")
                        logger.info("Using default bankroll for SHADOW mode: $10,000")
                        bankroll = 10000.0
                        positions = []
                    else:
                        raise
                
                risk.update_from_positions(positions, bankroll)
                
                logger.info(f"Bankroll: ${bankroll:.2f}")
                logger.info(f"Open positions: {len(positions)}")
                logger.info(f"Daily risk: ${risk.total_daily_risk:.2f} / ${config.max_daily_risk_pct * bankroll:.2f}")
                
                # Fetch markets
                markets = kalshi.fetch_sports_markets()
                logger.info(f"Fetched {len(markets)} markets")
                
                if not markets:
                    logger.warning("No markets available - cannot generate trades. Check Kalshi API connection.")
                    logger.info("Sleeping...")
                    time.sleep(config.poll_interval_seconds)
                    continue
                
                # Verify we have real markets (not mock)
                real_markets = [m for m in markets if not m.market_id.startswith("market_")]
                if len(real_markets) < len(markets):
                    logger.warning(f"Found {len(markets) - len(real_markets)} mock markets - these will be skipped")
                    markets = real_markets
                
                if not markets:
                    logger.warning("No real markets available after filtering. Skipping iteration.")
                    time.sleep(config.poll_interval_seconds)
                    continue
                
                # Extract games and fetch reference odds
                games = extract_games_from_markets(markets)
                logger.info(f"Extracted {len(games)} unique games")
                
                ref_odds = odds.fetch_reference_odds(games)
                fair_probs = compute_fair_probs(ref_odds)
                
                # Research games for additional insights
                game_research = {}
                for game in games:
                    try:
                        game_research[game.game_id] = research.research_game(game)
                    except Exception as e:
                        logger.warning(f"Failed to research game {game.game_id}: {e}")
                        game_research[game.game_id] = None
                
                # Process each market
                trades_executed = 0
                for market in markets:
                    # Filter markets
                    if not market_is_eligible(market, config):
                        continue
                    
                    # Map market to game and team
                    game_id, team, team_a, team_b = map_market_to_game_and_team(market)
                    
                    # Determine opponent
                    if team == team_a:
                        opponent = team_b
                    elif team == team_b:
                        opponent = team_a
                    else:
                        # Fallback: parse from event_name
                        if " vs " in market.event_name:
                            parts = market.event_name.replace(" Winner?", "").split(" vs ")
                            if team in parts[0] or team[:3].lower() in parts[0].lower():
                                opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
                            else:
                                opponent = parts[0].strip()
                        else:
                            opponent = "Unknown"
                    
                    # Get fair probability
                    if game_id not in fair_probs:
                        logger.debug(f"No fair probabilities for game_id: {game_id}")
                        continue
                    
                    # Check if we're using real odds (not mock)
                    ref_odds_obj = ref_odds.get(game_id)
                    if ref_odds_obj and ref_odds_obj.source == "mock":
                        logger.debug(f"Skipping {market.team} vs {opponent} - using mock odds, waiting for real odds")
                        continue
                    
                    fair_prob = get_fair_prob_for_team(
                        fair_probs, game_id, team, team_a, team_b
                    )
                    kalshi_prob = market.best_yes_price
                    
                    # Get research for this game to use research-based probability
                    game_research_obj = game_research.get(game_id)
                    research_prob = None
                    if game_research_obj and game_research_obj.research_probability is not None:
                        # Map research probability to the team we're betting on
                        if team == team_a:
                            research_prob = game_research_obj.research_probability
                        else:
                            # Research prob is for team_a, so for team_b it's 1 - prob
                            research_prob = 1.0 - game_research_obj.research_probability
                    
                    # Calculate edge using research probability if available
                    # Get research confidence if available
                    research_confidence = None
                    if game_research_obj and hasattr(game_research_obj, 'confidence'):
                        research_confidence = game_research_obj.confidence
                    
                    edge = calc_edge(fair_prob, kalshi_prob, research_prob, research_confidence)
                    
                    # Require research for all trades - don't trade without comprehensive analysis
                    if not game_research_obj or not game_research_obj.reasoning:
                        logger.debug(
                            f"Market {market.market_id}: Skipping - no research available. "
                            f"Need comprehensive analysis before trading."
                        )
                        continue
                    
                    # Use research-based threshold - require stronger edge when we have research
                    # League-specific edge thresholds (markets have different efficiency)
                    # More efficient markets (NBA) need lower thresholds
                    # Less efficient markets (EPL, UCL) can use higher thresholds
                    league_thresholds = {
                        "NBA": 0.05,      # 5% - more efficient market
                        "NFL": 0.06,      # 6% - efficient but more variance
                        "EPL": 0.08,      # 8% - less efficient, more opportunities
                        "UCL": 0.10,      # 10% - higher variance, need bigger edge
                        "La Liga": 0.08,  # 8% - similar to EPL
                        "NHL": 0.07,      # 7% - moderate efficiency
                        "MLB": 0.07,      # 7% - moderate efficiency
                    }
                    effective_threshold = league_thresholds.get(market.league, config.edge_threshold)
                    
                    # If we have research probability, require it to align with our bet
                    if research_prob is not None:
                        # Research should favor the team we're betting on
                        if research_prob < 0.45:  # Research doesn't favor this team
                            logger.debug(
                                f"Market {market.market_id}: Research probability {research_prob:.2%} "
                                f"doesn't favor {team}. Skipping."
                            )
                            continue
                    
                    if edge < effective_threshold:
                        logger.debug(
                            f"Market {market.market_id}: edge {edge:.4f} < "
                            f"threshold {effective_threshold:.4f}"
                        )
                        continue
                    
                    # Calculate time until game
                    time_until_game = (market.start_time - datetime.now()).total_seconds() / 3600
                    time_str = f"{time_until_game:.1f}h" if time_until_game > 1 else f"{time_until_game*60:.0f}m"
                    
                    # Log comprehensive analysis
                    research_info = ""
                    if research_prob is not None:
                        research_info = f", research_prob={research_prob:.4f}"
                    
                    logger.info(
                        f"Found edge opportunity: {market.team} vs {opponent} ({market.league}) | "
                        f"Game in {time_str} | "
                        f"fair={fair_prob:.4f}{research_info}, kalshi={kalshi_prob:.4f}, "
                        f"edge={edge:.4f}"
                    )
                    
                    if game_research_obj and game_research_obj.reasoning:
                        logger.info(f"Research: {game_research_obj.reasoning[:200]}...")
                    
                    # Calculate Kelly sizing using combined probability (research-weighted)
                    # Use the same combined_prob that was used for edge calculation
                    combined_prob = fair_prob
                    if research_prob is not None:
                        # Use same weighting as calc_edge
                        if research_confidence == "HIGH":
                            research_weight = 0.85
                        elif research_confidence == "MEDIUM":
                            research_weight = 0.70
                        elif research_confidence == "LOW":
                            research_weight = 0.50
                        else:
                            research_weight = 0.70
                        combined_prob = research_weight * research_prob + (1 - research_weight) * fair_prob
                    
                    kelly_frac = kelly_fraction(
                        combined_prob, kalshi_prob, config.kelly_factor, research_confidence
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
                    
                    # Execute trade (research already retrieved above)
                    trade = execute_trade(
                        market=market,
                        stake=stake,
                        kalshi_price=kalshi_prob,
                        fair_prob=combined_prob,  # Use combined research-weighted probability
                        edge=edge,
                        config=config,
                        kalshi_client=kalshi,
                        mode=config.mode,
                        opponent=opponent,
                        game_time=market.start_time,
                        research=game_research_obj
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

