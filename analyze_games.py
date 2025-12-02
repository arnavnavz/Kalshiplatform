"""
Comprehensive game analysis script.
Shows all upcoming games with odds, research, and betting recommendations.
"""
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pytz import timezone, utc

from config import load_config
from kalshi_client import KalshiClient
from odds_client import OddsClient
from models import Market, Game, ReferenceOdds
from strategy import calc_edge
from research import ResearchEngine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# League mappings
LEAGUE_NAMES = {
    "EPL": ["EPL", "Premier League", "English Premier League"],
    "NBA": ["NBA"],
    "NFL": ["NFL"],
    "UCL": ["UCL", "Champions League", "UEFA Champions League"],
    "La Liga": ["La Liga", "LaLiga", "Spanish La Liga"]
}

def format_time_until(start_time: datetime) -> str:
    """Format time until game start."""
    now = datetime.now(utc) if start_time.tzinfo else datetime.now()
    if start_time.tzinfo and not now.tzinfo:
        now = utc.localize(now)
    elif not start_time.tzinfo and now.tzinfo:
        start_time = utc.localize(start_time)
    
    diff = (start_time - now).total_seconds() / 3600  # hours
    
    if diff < 0:
        return "PAST"
    elif diff < 1:
        return f"{diff*60:.0f} min"
    elif diff < 24:
        return f"{diff:.1f} hours"
    else:
        return f"{diff/24:.1f} days"

def format_game_time(start_time: datetime) -> str:
    """Format game time in Eastern Time."""
    eastern = timezone('US/Eastern')
    
    if start_time.tzinfo is None:
        start_time = utc.localize(start_time)
    
    game_time_et = start_time.astimezone(eastern)
    return game_time_et.strftime("%Y-%m-%d %I:%M %p ET")

def analyze_game(
    market: Market,
    ref_odds: Optional[ReferenceOdds],
    research_engine: ResearchEngine,
    config
) -> Dict:
    """Analyze a single game and return analysis dict."""
    game_id = market.game_id
    
    # Get opponent
    opponent = "Unknown"
    if " vs " in market.event_name:
        parts = market.event_name.replace(" Winner?", "").split(" vs ")
        if market.team in parts[0]:
            opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
        else:
            opponent = parts[0].strip() if len(parts) > 0 else "Unknown"
    
    # Create game object for research
    game = Game(
        game_id=game_id,
        team_a=market.team,
        team_b=opponent,
        league=market.league,
        start_time=market.start_time
    )
    
    # Get reference odds and fair probability
    fair_prob = None
    ref_odds_str = "N/A"
    kalshi_prob = market.best_yes_price
    
    if ref_odds and ref_odds.source != "mock":
        # Compute fair probabilities from reference odds
        from strategy import american_to_implied_prob, remove_vig
        
        p_a_raw = american_to_implied_prob(ref_odds.team_a_american_odds)
        p_b_raw = american_to_implied_prob(ref_odds.team_b_american_odds)
        p_a_fair, p_b_fair = remove_vig(p_a_raw, p_b_raw)
        
        # Match team to get fair probability
        # Try to determine which team is team_a and which is team_b
        # This is a simplified matching - may need improvement
        if market.team.lower() in game.team_a.lower() or game.team_a.lower() in market.team.lower():
            fair_prob = p_a_fair
        elif market.team.lower() in game.team_b.lower() or game.team_b.lower() in market.team.lower():
            fair_prob = p_b_fair
        else:
            # Fallback: use average
            fair_prob = (p_a_fair + p_b_fair) / 2
        
        # Format reference odds
        ref_odds_str = f"{ref_odds.team_a_american_odds}/{ref_odds.team_b_american_odds}"
    else:
        fair_prob = kalshi_prob  # Use Kalshi price as fallback
    
    research = None
    research_prob = None
    reasoning = "No research available"
    
    try:
        research = research_engine.research_game(game)
        if research:
            research_prob = research.research_probability
            if research.reasoning:
                reasoning = research.reasoning[:500]  # Limit length
    except Exception as e:
        logger.debug(f"Research failed for {game_id}: {e}")
    
    # Calculate edge
    edge = None
    if fair_prob is not None:
        if research_prob is not None:
            combined_prob = 0.7 * research_prob + 0.3 * fair_prob
            edge = calc_edge(fair_prob, kalshi_prob, research_prob)
        else:
            edge = fair_prob - kalshi_prob
    
    # Determine recommendation
    recommendation = "NO BET"
    recommendation_reason = ""
    
    if edge is not None:
        if edge > 0.15:
            recommendation = "STRONG BUY"
            recommendation_reason = f"Very high edge ({edge:.2%}). Kalshi significantly undervalues {market.team}."
        elif edge > 0.10:
            recommendation = "BUY"
            recommendation_reason = f"Good edge ({edge:.2%}). Favorable odds on {market.team}."
        elif edge > 0.05:
            recommendation = "WEAK BUY"
            recommendation_reason = f"Moderate edge ({edge:.2%}). Slight value on {market.team}."
        elif edge < -0.10:
            recommendation = "AVOID"
            recommendation_reason = f"Negative edge ({edge:.2%}). Kalshi overvalues {market.team}."
        elif edge < -0.05:
            recommendation = "NO BET"
            recommendation_reason = f"Small negative edge ({edge:.2%}). No clear value."
        else:
            recommendation = "NO BET"
            recommendation_reason = f"Edge too small ({edge:.2%}). Market is efficient."
    else:
        recommendation_reason = "Insufficient data to calculate edge."
    
    # Add research-based reasoning
    if research_prob is not None:
        if research_prob >= 0.55:
            recommendation_reason += f" Research strongly favors {market.team} ({research_prob:.1%} win probability)."
        elif research_prob <= 0.45:
            recommendation_reason += f" Research does not favor {market.team} ({research_prob:.1%} win probability)."
    
    return {
        "game_id": game_id,
        "league": market.league,
        "team": market.team,
        "opponent": opponent,
        "game_time": format_game_time(market.start_time),
        "time_until": format_time_until(market.start_time),
        "kalshi_prob": kalshi_prob,
        "kalshi_price": f"{kalshi_prob:.1%}",
        "ref_odds": ref_odds_str,
        "fair_prob": fair_prob,
        "fair_prob_str": f"{fair_prob:.1%}" if fair_prob else "N/A",
        "research_prob": research_prob,
        "research_prob_str": f"{research_prob:.1%}" if research_prob else "N/A",
        "edge": edge,
        "edge_str": f"{edge:.2%}" if edge else "N/A",
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "reasoning": reasoning,
        "volume": market.volume,
        "spread": market.spread
    }

def main():
    """Main analysis function."""
    print("\n" + "="*100)
    print("COMPREHENSIVE GAME ANALYSIS - NEXT 5 DAYS")
    print("="*100 + "\n")
    
    # Load config
    config = load_config()
    
    # Initialize clients
    kalshi = KalshiClient(config)
    odds_client = OddsClient(config)
    research_engine = ResearchEngine()
    
    # Target leagues
    target_leagues = ["EPL", "NBA", "NFL", "UCL", "La Liga"]
    
    print(f"Fetching markets for: {', '.join(target_leagues)}")
    print(f"Time range: Next 5 days\n")
    
    # Fetch markets
    try:
        markets = kalshi.fetch_sports_markets()
        logger.info(f"Fetched {len(markets)} total markets")
    except Exception as e:
        logger.error(f"Failed to fetch markets: {e}")
        print(f"ERROR: Failed to fetch markets: {e}")
        return
    
    # Filter for target leagues and next 5 days
    now = datetime.now(utc)
    cutoff = now + timedelta(days=5)
    
    filtered_markets = []
    for market in markets:
        # Check league
        league_match = False
        for target_league in target_leagues:
            if any(alias.lower() in market.league.lower() for alias in LEAGUE_NAMES.get(target_league, [target_league])):
                league_match = True
                break
        
        if not league_match:
            continue
        
        # Check time range
        market_time = market.start_time
        if market_time.tzinfo is None:
            market_time = utc.localize(market_time)
        
        if market_time < now or market_time > cutoff:
            continue
        
        # Skip mock markets
        if market.market_id.startswith("market_"):
            continue
        
        filtered_markets.append(market)
    
    logger.info(f"Filtered to {len(filtered_markets)} markets in target leagues (next 5 days)")
    
    if not filtered_markets:
        print("No games found matching criteria.")
        return
    
    # Group markets by game
    games_dict = {}
    for market in filtered_markets:
        game_id = market.game_id
        if game_id not in games_dict:
            games_dict[game_id] = []
        games_dict[game_id].append(market)
    
    print(f"Found {len(games_dict)} unique games\n")
    
    # Fetch reference odds for all games
    games_list = []
    for game_id, markets_list in games_dict.items():
        # Create a Game object from the first market
        first_market = markets_list[0]
        opponent = "Unknown"
        if " vs " in first_market.event_name:
            parts = first_market.event_name.replace(" Winner?", "").split(" vs ")
            if first_market.team in parts[0]:
                opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
            else:
                opponent = parts[0].strip() if len(parts) > 0 else "Unknown"
        
        game = Game(
            game_id=game_id,
            team_a=first_market.team,
            team_b=opponent,
            league=first_market.league,
            start_time=first_market.start_time
        )
        games_list.append(game)
    
    ref_odds_dict = odds_client.fetch_reference_odds(games_list)
    
    # Analyze each game
    analyses = []
    for game_id, markets_list in games_dict.items():
        # Analyze each market (team) in the game
        for market in markets_list:
            ref_odds = ref_odds_dict.get(game_id)
            analysis = analyze_game(market, ref_odds, research_engine, config)
            analyses.append(analysis)
    
    # Sort by game time
    analyses.sort(key=lambda x: x["time_until"])
    
    # Print results
    print("\n" + "="*100)
    print("GAME ANALYSIS RESULTS")
    print("="*100 + "\n")
    
    current_league = None
    for analysis in analyses:
        # Print league header
        if analysis["league"] != current_league:
            current_league = analysis["league"]
            print(f"\n{'='*100}")
            print(f"  {current_league}")
            print(f"{'='*100}\n")
        
        # Print game details
        print(f"🏀 {analysis['team']} vs {analysis['opponent']}")
        print(f"   Game Time: {analysis['game_time']} ({analysis['time_until']} until game)")
        print(f"   League: {analysis['league']} | Volume: {analysis['volume']:,} | Spread: {analysis['spread']:.2%}")
        print()
        
        # Print odds
        print(f"   📊 ODDS:")
        print(f"      Kalshi Price: {analysis['kalshi_price']}")
        print(f"      Reference Odds: {analysis['ref_odds']}")
        print(f"      Fair Probability: {analysis['fair_prob_str']}")
        if analysis['research_prob']:
            print(f"      Research Probability: {analysis['research_prob_str']}")
        if analysis['edge']:
            print(f"      Edge: {analysis['edge_str']}")
        print()
        
        # Print recommendation
        rec_emoji = "✅" if "BUY" in analysis['recommendation'] else "❌" if analysis['recommendation'] == "AVOID" else "⚪"
        print(f"   {rec_emoji} RECOMMENDATION: {analysis['recommendation']}")
        print(f"      {analysis['recommendation_reason']}")
        print()
        
        # Print reasoning
        if analysis['reasoning'] and analysis['reasoning'] != "No research available":
            print(f"   📝 RESEARCH:")
            # Print first 3 lines of reasoning
            reasoning_lines = analysis['reasoning'].split('\n')[:3]
            for line in reasoning_lines:
                if line.strip():
                    print(f"      {line.strip()}")
            if len(analysis['reasoning'].split('\n')) > 3:
                print(f"      ... (truncated)")
        print()
        print("-" * 100)
        print()
    
    print(f"\n{'='*100}")
    print(f"Total games analyzed: {len(analyses)}")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)

