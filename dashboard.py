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
import subprocess
import sys
import logging

from config import load_config

# Set up logger
logger = logging.getLogger(__name__)

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


def fetch_all_games_analysis() -> List[Dict]:
    """Fetch all upcoming games with analysis by importing analysis functions."""
    try:
        from kalshi_client import KalshiClient
        from odds_client import OddsClient
        from models import Market, Game, ReferenceOdds
        from strategy import calc_edge, american_to_implied_prob, remove_vig
        # Skip research import - research is loaded on-demand when game is selected
        from pytz import timezone, utc
        import signal
        
        config = load_config()
        kalshi = KalshiClient(config)
        odds_client = OddsClient(config)
        # Research engine is NOT initialized here - it's loaded on-demand in show_detailed_breakdown()
        
        # Target leagues
        target_leagues = ["EPL", "NBA", "NFL", "UCL", "La Liga"]
        league_names = {
            "EPL": ["EPL", "Premier League", "English Premier League"],
            "NBA": ["NBA"],
            "NFL": ["NFL"],
            "UCL": ["UCL", "Champions League", "UEFA Champions League"],
            "La Liga": ["La Liga", "LaLiga", "Spanish La Liga"]
        }
        
        # Fetch markets with error handling
        try:
            markets = kalshi.fetch_sports_markets()
            if not markets:
                # Don't use st.warning in cached function - return empty list
                return []
        except Exception as e:
            # Don't use st.error in cached function - return empty list
            return []
        
        # Filter for target leagues and next 5 days
        now = datetime.now(utc)
        cutoff = now + timedelta(days=5)
        
        filtered_markets = []
        for market in markets:
            # Check league
            league_match = False
            for target_league in target_leagues:
                if any(alias.lower() in market.league.lower() for alias in league_names.get(target_league, [target_league])):
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
        
        # Group markets by game
        games_dict = {}
        for market in filtered_markets:
            game_id = market.game_id
            if game_id not in games_dict:
                games_dict[game_id] = []
            games_dict[game_id].append(market)
        
        # Create games list
        games_list = []
        for game_id, markets_list in games_dict.items():
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
        
        # Fetch reference odds with error handling (limit to avoid timeout)
        ref_odds_dict = {}
        if games_list:
            try:
                # Limit to first 50 games to avoid timeout
                games_to_fetch = games_list[:50] if len(games_list) > 50 else games_list
                ref_odds_dict = odds_client.fetch_reference_odds(games_to_fetch)
            except Exception as e:
                # Silently continue without reference odds (don't use st.warning in cached function)
                ref_odds_dict = {}
        
        # Analyze each game - limit to first 100 to avoid timeout
        analyses = []
        games_items = list(games_dict.items())[:100]
        for game_id, markets_list in games_items:
            ref_odds = ref_odds_dict.get(game_id)
            
            # Analyze all markets for this game and pick the best one
            # For each game, we might have multiple markets (one for each team)
            # We want to show the market with the best edge for either team
            market_analyses = []
            
            for market in markets_list:
                # Analyze each market (there may be multiple markets per game - one for each team)
                # Determine opponent from event name
                opponent = "Unknown"
                if " vs " in market.event_name:
                    parts = market.event_name.replace(" Winner?", "").split(" vs ")
                    if market.team in parts[0]:
                        opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
                    else:
                        opponent = parts[0].strip() if len(parts) > 0 else "Unknown"
                
                game = Game(
                    game_id=game_id,
                    team_a=market.team,
                    team_b=opponent,
                    league=market.league,
                    start_time=market.start_time
                )
                
                fair_prob = None
                ref_odds_str = "N/A"
                # Use YES price - this is the probability that the team in market.team will win
                kalshi_prob = market.best_yes_price
                
                # Sanity check: if YES price is very low (< 20%), it might be the wrong market
                # Check if there's a better market (higher YES price) for the same game
                if kalshi_prob < 0.20:
                    # Look for other markets in this game with higher YES prices
                    for other_market in markets_list:
                        if other_market.market_id != market.market_id and other_market.best_yes_price > kalshi_prob:
                            # This might be a better market to show
                            # But we'll keep the current one and just note it
                            pass
                
                if ref_odds and ref_odds.source != "mock":
                    p_a_raw = american_to_implied_prob(ref_odds.team_a_american_odds)
                    p_b_raw = american_to_implied_prob(ref_odds.team_b_american_odds)
                    p_a_fair, p_b_fair = remove_vig(p_a_raw, p_b_raw)
                    
                    # Match market.team to the correct team in the game
                    # market.team is the team this market is for (e.g., "Liverpool")
                    # We need to match it to team_a or team_b in the ref_odds
                    # The ref_odds has team_a and team_b, but we need to figure out which is which
                    # Try to match market.team to team_a or team_b
                    market_team_lower = market.team.lower()
                    game_team_a_lower = game.team_a.lower()
                    game_team_b_lower = game.team_b.lower()
                    
                    # Check if market.team matches team_a
                    if (market_team_lower in game_team_a_lower or 
                        game_team_a_lower in market_team_lower or
                        any(word in game_team_a_lower for word in market_team_lower.split() if len(word) > 3)):
                        fair_prob = p_a_fair
                    # Check if market.team matches team_b
                    elif (market_team_lower in game_team_b_lower or 
                          game_team_b_lower in market_team_lower or
                          any(word in game_team_b_lower for word in market_team_lower.split() if len(word) > 3)):
                        fair_prob = p_b_fair
                    else:
                        # Can't match - use average (this shouldn't happen often)
                        fair_prob = (p_a_fair + p_b_fair) / 2
                    
                    ref_odds_str = f"{ref_odds.team_a_american_odds}/{ref_odds.team_b_american_odds}"
                else:
                    fair_prob = kalshi_prob
                
                # Calculate edge for this market
                edge = None
                if fair_prob is not None:
                    edge = fair_prob - kalshi_prob
                
                # Verify we're using the correct market
                # For a team with low YES price (< 30%), make sure we're not accidentally using opponent's market
                # The YES price should match the team we're analyzing
                if kalshi_prob < 0.30 and fair_prob is not None:
                    # If fair_prob is high (> 60%) but Kalshi price is low, this is correct (good edge)
                    # But if fair_prob is also low, we might have the wrong market
                    if fair_prob < 0.40:
                        # Both are low - might be wrong market, skip or flag
                        logger.debug(f"Warning: Low Kalshi price ({kalshi_prob:.1%}) and low fair prob ({fair_prob:.1%}) for {market.team} - might be wrong market")
                
                # Store analysis for this market
                market_analyses.append({
                    'market': market,
                    'opponent': opponent,
                    'game': game,
                    'fair_prob': fair_prob,
                    'kalshi_prob': kalshi_prob,
                    'edge': edge,
                    'ref_odds_str': ref_odds_str if ref_odds else "N/A",
                    'team_a': game.team_a,  # Store for verification
                    'team_b': game.team_b
                })
            
            # Skip research in initial fetch for speed - research is loaded on-demand when game is selected
            # This prevents the dashboard from hanging on ChatGPT API calls (20-30 seconds per game)
            research = None
            research_prob = None
            reasoning = "Research available when you select a game for detailed analysis"
            
            # Find the best market - use best edge (research will be loaded on-demand)
            if market_analyses:
                # Filter out markets with suspiciously low YES prices that don't match fair probability
                # If Kalshi price is very low (< 20%) but fair prob is also low (< 40%), skip it
                valid_analyses = []
                for analysis in market_analyses:
                    kp = analysis['kalshi_prob']
                    fp = analysis['fair_prob']
                    if fp is not None and kp < 0.20 and fp < 0.40:
                        # Suspicious: very low Kalshi price AND low fair prob - might be wrong market
                        continue
                    valid_analyses.append(analysis)
                
                if not valid_analyses:
                    valid_analyses = market_analyses  # Fallback to all if none valid
                
                # Use the market with the best edge
                best_analysis = max(valid_analyses, key=lambda x: x['edge'] if x['edge'] is not None else -999)
                
                market = best_analysis['market']
                opponent = best_analysis['opponent']
                game = best_analysis['game']
                fair_prob = best_analysis['fair_prob']
                kalshi_prob = best_analysis['kalshi_prob']
                edge = best_analysis['edge']
                ref_odds_str = best_analysis['ref_odds_str']
                
                # Verify: market.team should match the team we're showing
                # If market.team doesn't match game.team_a or game.team_b, we have a problem
                if market.team.lower() not in game.team_a.lower() and game.team_a.lower() not in market.team.lower():
                    if market.team.lower() not in game.team_b.lower() and game.team_b.lower() not in market.team.lower():
                        # Team mismatch - log warning but continue
                        logger.warning(f"Team mismatch: market.team={market.team}, game.team_a={game.team_a}, game.team_b={game.team_b}")
                
                # Edge is already calculated above - research will be used in detailed view
                
                # Format game time
                eastern = timezone('US/Eastern')
                if market.start_time.tzinfo is None:
                    market_start = utc.localize(market.start_time)
                else:
                    market_start = market.start_time
                game_time_et = market_start.astimezone(eastern)
                game_time_str = game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
                
                # Time until
                diff = (market_start - now).total_seconds() / 3600
                if diff < 0:
                    time_until = "PAST"
                elif diff < 1:
                    time_until = f"{diff*60:.0f} min"
                elif diff < 24:
                    time_until = f"{diff:.1f} hours"
                else:
                    time_until = f"{diff/24:.1f} days"
                
                # Determine recommendation - PRIORITIZE RESEARCH over edge
                # Without research, we can't make strong recommendations
                recommendation = "NO BET"
                recommendation_reason = ""
                
                # Research is loaded on-demand, so initial recommendations are conservative
                # Only show strong recommendations when research confirms it
                if edge is not None:
                    if edge < -0.10:
                        recommendation = "AVOID"
                        recommendation_reason = f"Negative edge ({edge:.2%}) - Avoid this bet"
                    elif edge > 0.15:
                        # Strong edge, but need research to confirm
                        recommendation = "WEAK BUY"
                        recommendation_reason = f"Strong edge ({edge:.2%}) but research needed - Select game to see research analysis"
                    elif edge > 0.10:
                        recommendation = "WEAK BUY"
                        recommendation_reason = f"Good edge ({edge:.2%}) but research needed - Select game to see research analysis"
                    elif edge > 0.05:
                        recommendation = "NO BET"
                        recommendation_reason = f"Moderate edge ({edge:.2%}) - Select game for research analysis to confirm"
                    else:
                        recommendation = "NO BET"
                        recommendation_reason = f"Edge ({edge:.2%}) below threshold - Select game for research analysis"
                
                analyses.append({
                    'game_id': game_id,
                    'league': market.league,
                    'team': market.team,
                    'opponent': opponent,
                    'game_time': game_time_str,
                    'time_until': time_until,
                    'kalshi_prob': kalshi_prob,
                    'kalshi_price': f"{kalshi_prob:.1%}",
                    'ref_odds': ref_odds_str,
                    'fair_prob': fair_prob,
                    'fair_prob_str': f"{fair_prob:.1%}" if fair_prob else "N/A",
                    'research_prob': research_prob,
                    'research_prob_str': f"{research_prob:.1%}" if research_prob else "N/A",
                    'edge': edge,
                    'edge_str': f"{edge:.2%}" if edge else "N/A",
                    'recommendation': recommendation,
                    'recommendation_reason': recommendation_reason,
                    'reasoning': reasoning,
                    'volume': market.volume,
                    'spread': market.spread
                })
        
        return analyses
    except Exception as e:
        st.error(f"Error fetching games: {e}")
        import traceback
        st.error(traceback.format_exc())
        return []


def show_detailed_breakdown(game_data: Dict):
    """Show detailed breakdown for a selected game."""
    st.markdown("---")
    st.subheader(f"📊 Detailed Analysis: {game_data['team']} vs {game_data['opponent']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**League:** {game_data['league']}")
        st.markdown(f"**Game Time:** {game_data['game_time']} ({game_data['time_until']})")
        st.markdown(f"**Recommendation:** {game_data['recommendation']}")
        if game_data.get('recommendation_reason'):
            st.info(f"💡 {game_data['recommendation_reason']}")
        st.markdown(f"**Edge:** {game_data['edge_str']}")
    
    with col2:
        st.markdown(f"**Kalshi Price:** {game_data['kalshi_price']}")
        st.markdown(f"**Reference Odds:** {game_data['ref_odds']}")
        st.markdown(f"**Fair Probability:** {game_data['fair_prob_str']}")
        st.markdown(f"**Market Volume:** {game_data['volume']:,}")
        st.markdown(f"**Spread:** {game_data['spread']:.2%}")
    
    # Odds Arbitrage Analysis
    st.markdown("### 💰 Odds Arbitrage Analysis")
    if game_data.get('fair_prob') and game_data.get('kalshi_prob'):
        fair_prob = game_data['fair_prob']
        kalshi_prob = game_data['kalshi_prob']
        edge = game_data.get('edge', 0)
        research_prob = game_data.get('research_prob')
        
        if edge > 0:
            st.info(f"ℹ️ **Potential Arbitrage Opportunity**")
            st.markdown(f"- Kalshi price for {game_data['team']}: {kalshi_prob:.1%}")
            st.markdown(f"- Fair value from reference odds: {fair_prob:.1%}")
            st.markdown(f"- **Edge:** {edge:.2%}")
            
            if research_prob is None:
                st.warning(f"⚠️ **Research needed** - This edge is based on odds arbitrage only. Select this game to see research analysis and confirm if {game_data['team']} is actually more likely to win.")
            else:
                # Research is available - show if it confirms or contradicts
                team_research_prob = research_prob if game_data['team'] == game_data.get('team_a', game_data['team']) else (1.0 - research_prob)
                if team_research_prob >= 0.5:
                    st.success(f"✅ Research confirms {game_data['team']} is favored ({team_research_prob:.1%} win probability)")
                else:
                    st.error(f"❌ Research contradicts - {game_data['opponent']} is more likely to win ({1.0 - team_research_prob:.1%} vs {team_research_prob:.1%})")
        else:
            st.warning(f"⚠️ No arbitrage opportunity - Kalshi price is fair or overvalued")
    
    # Research & Technical Analysis
    st.markdown("### 📈 Research & Technical Analysis")
    
    # Try to load research from bot's cache or generate on demand
    try:
        from research import ResearchEngine
        from models import Game
        from pytz import timezone, utc
        
        research_engine = ResearchEngine()
        
        # Parse the game time from the game_data
        game_time_str = game_data.get('game_time', '')
        try:
            # Try to parse the game time string
            from dateutil import parser as date_parser
            if game_time_str and game_time_str != 'N/A':
                # Parse "2025-11-24 06:00 PM ET" format
                game_time = date_parser.parse(game_time_str.replace(' ET', ''))
            else:
                game_time = datetime.now()
        except:
            game_time = datetime.now()
        
        # Ensure we use the correct team names from game_data
        team_a = game_data['team']
        team_b = game_data['opponent']
        
        game = Game(
            game_id=game_data['game_id'],
            team_a=team_a,
            team_b=team_b,
            league=game_data['league'],
            start_time=game_time
        )
        
        with st.spinner("Loading detailed research (this may take 20-30 seconds for ChatGPT analysis)..."):
            research = research_engine.research_game(game)
            
            if research and research.reasoning:
                # Research Probability - Show prominently at top for BOTH teams
                if research.research_probability is not None:
                    st.markdown("#### 🎯 Research-Based Win Probability")
                    col_prob1, col_prob2 = st.columns(2)
                    
                    with col_prob1:
                        # Research prob is for team_a
                        team_a_prob = research.research_probability
                        team_b_prob = 1.0 - research.research_probability
                        st.metric(f"{team_a} Win Probability", f"{team_a_prob:.1%}")
                    
                    with col_prob2:
                        st.metric(f"{team_b} Win Probability", f"{team_b_prob:.1%}")
                    
                    # Show which team research favors and update recommendation
                    edge = game_data.get('edge', 0)
                    research_favors_team_a = team_a_prob > team_b_prob
                    research_favors_team_b = team_b_prob > team_a_prob
                    
                    if research_favors_team_a:
                        st.success(f"✅ **Research favors {team_a}** ({team_a_prob:.1%} vs {team_b_prob:.1%})")
                        # Check if edge aligns with research
                        if edge > 0.05:
                            st.success(f"✅ **RECOMMENDATION: Bet on {team_a}** - Research confirms strong edge ({edge:.2%})")
                        elif edge > 0:
                            st.info(f"ℹ️ **Consider betting on {team_a}** - Research favors them, moderate edge ({edge:.2%})")
                        else:
                            st.warning(f"⚠️ Research favors {team_a} but edge is negative ({edge:.2%}) - Consider avoiding")
                    elif research_favors_team_b:
                        st.success(f"✅ **Research favors {team_b}** ({team_b_prob:.1%} vs {team_a_prob:.1%})")
                        # If research favors opponent, check if we should bet on them instead
                        if edge < 0:
                            # Negative edge means we should bet on opponent
                            st.success(f"✅ **RECOMMENDATION: Bet on {team_b}** - Research confirms they're favored")
                        else:
                            st.warning(f"⚠️ Research favors {team_b}, but edge calculation suggests {team_a}. Review carefully.")
                    else:
                        st.info("Research indicates a close match")
                    
                    st.markdown("---")
                
                # Parse ChatGPT reasoning to extract team-specific stats
                reasoning_text = research.reasoning
                import re
                
                # Extract team-specific sections and stats from ChatGPT analysis
                team_a_name = team_a
                team_b_name = team_b
                
                # Function to extract team statistics and analysis
                def extract_team_stats_from_text(text, team_name, other_team_name):
                    """Extract team statistics from ChatGPT analysis text."""
                    stats = {}
                    text_lower = text.lower()
                    team_lower = team_name.lower()
                    other_lower = other_team_name.lower()
                    
                    # Find section for this team
                    team_pattern = rf"{re.escape(team_lower)}[:\-]?\s*\n(.*?)(?=\n\s*(?:{re.escape(other_lower)}|\d+\.|$))"
                    match = re.search(team_pattern, text, re.IGNORECASE | re.DOTALL)
                    team_section = match.group(1) if match else ""
                    
                    # If no match, try finding paragraphs with team name
                    if not team_section:
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if team_lower in para.lower() and len(para) > 50:
                                team_section += para + "\n\n"
                    
                    # Extract specific stats from the section
                    # Win percentage
                    win_pct_match = re.search(r'win\s*(?:percentage|rate|%|pct)[:\-]?\s*(\d+(?:\.\d+)?)\s*%', team_section, re.IGNORECASE)
                    if win_pct_match:
                        stats['win_percentage'] = float(win_pct_match.group(1)) / 100.0
                    
                    # Record (wins-losses)
                    record_match = re.search(r'(\d+)\s*(?:wins?|w)\s*[,\-]\s*(\d+)\s*(?:losses?|loss|l)', team_section, re.IGNORECASE)
                    if record_match:
                        stats['wins'] = int(record_match.group(1))
                        stats['losses'] = int(record_match.group(2))
                    
                    # Points/Goals per game
                    points_match = re.search(r'(?:points|goals?)\s*(?:scored|per\s*game|pg)[:\-]?\s*(\d+(?:\.\d+)?)', team_section, re.IGNORECASE)
                    if points_match:
                        stats['points_per_game'] = float(points_match.group(1))
                    
                    # Points allowed per game
                    allowed_match = re.search(r'(?:points|goals?)\s*(?:allowed|conceded|against)[:\-]?\s*(\d+(?:\.\d+)?)', team_section, re.IGNORECASE)
                    if allowed_match:
                        stats['points_allowed_per_game'] = float(allowed_match.group(1))
                    
                    # Recent form
                    form_match = re.search(r'(?:form|last\s*\d+\s*games?)[:\-]?\s*([WDL\s,]+)', team_section, re.IGNORECASE)
                    if form_match:
                        stats['recent_form'] = form_match.group(1).strip()
                    
                    # Injuries
                    injury_match = re.search(r'injur(?:y|ies)[:\-]?\s*([^.\n]+)', team_section, re.IGNORECASE)
                    if injury_match:
                        injuries_text = injury_match.group(1)
                        stats['injuries'] = [i.strip() for i in injuries_text.split(',') if i.strip()]
                    
                    return stats, team_section
                
                team_a_stats_dict, team_a_section = extract_team_stats_from_text(reasoning_text, team_a_name, team_b_name)
                team_b_stats_dict, team_b_section = extract_team_stats_from_text(reasoning_text, team_b_name, team_a_name)
                
                # Team Statistics
                st.markdown("#### 📊 Team Statistics & Performance")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**{team_a_name}**")
                    # Show extracted stats from ChatGPT
                    if team_a_stats_dict:
                        if 'win_percentage' in team_a_stats_dict:
                            st.metric("Win Rate", f"{team_a_stats_dict['win_percentage']:.1%}")
                        if 'wins' in team_a_stats_dict and 'losses' in team_a_stats_dict:
                            st.metric("Record", f"{team_a_stats_dict['wins']}-{team_a_stats_dict['losses']}")
                        if 'recent_form' in team_a_stats_dict:
                            st.markdown(f"**Recent Form:** {team_a_stats_dict['recent_form']}")
                        if 'points_per_game' in team_a_stats_dict:
                            st.metric("Points/Game", f"{team_a_stats_dict['points_per_game']:.1f}")
                        if 'points_allowed_per_game' in team_a_stats_dict:
                            st.metric("Points Allowed/Game", f"{team_a_stats_dict['points_allowed_per_game']:.1f}")
                        if 'injuries' in team_a_stats_dict and team_a_stats_dict['injuries']:
                            st.warning(f"**Injuries:** {', '.join(team_a_stats_dict['injuries'])}")
                    elif research.team_a_stats:
                        # Fallback to research stats
                        stats = research.team_a_stats
                        if stats.win_percentage:
                            st.metric("Win Rate", f"{stats.win_percentage:.1%}")
                        if stats.wins is not None and stats.losses is not None:
                            st.metric("Record", f"{stats.wins}-{stats.losses}")
                    
                    # Show ChatGPT analysis for this team
                    if team_a_section:
                        with st.expander(f"📋 {team_a_name} Detailed Analysis", expanded=True):
                            section_clean = team_a_section.strip()
                            section_clean = re.sub(r'\n{3,}', '\n\n', section_clean)
                            if len(section_clean) > 1500:
                                section_clean = section_clean[:1500] + "..."
                            st.markdown(section_clean)
                
                with col2:
                    st.markdown(f"**{team_b_name}**")
                    # Show extracted stats from ChatGPT
                    if team_b_stats_dict:
                        if 'win_percentage' in team_b_stats_dict:
                            st.metric("Win Rate", f"{team_b_stats_dict['win_percentage']:.1%}")
                        if 'wins' in team_b_stats_dict and 'losses' in team_b_stats_dict:
                            st.metric("Record", f"{team_b_stats_dict['wins']}-{team_b_stats_dict['losses']}")
                        if 'recent_form' in team_b_stats_dict:
                            st.markdown(f"**Recent Form:** {team_b_stats_dict['recent_form']}")
                        if 'points_per_game' in team_b_stats_dict:
                            st.metric("Points/Game", f"{team_b_stats_dict['points_per_game']:.1f}")
                        if 'points_allowed_per_game' in team_b_stats_dict:
                            st.metric("Points Allowed/Game", f"{team_b_stats_dict['points_allowed_per_game']:.1f}")
                        if 'injuries' in team_b_stats_dict and team_b_stats_dict['injuries']:
                            st.warning(f"**Injuries:** {', '.join(team_b_stats_dict['injuries'])}")
                    elif research.team_b_stats:
                        # Fallback to research stats
                        stats = research.team_b_stats
                        if stats.win_percentage:
                            st.metric("Win Rate", f"{stats.win_percentage:.1%}")
                        if stats.wins is not None and stats.losses is not None:
                            st.metric("Record", f"{stats.wins}-{stats.losses}")
                    
                    # Show ChatGPT analysis for this team
                    if team_b_section:
                        with st.expander(f"📋 {team_b_name} Detailed Analysis", expanded=True):
                            section_clean = team_b_section.strip()
                            section_clean = re.sub(r'\n{3,}', '\n\n', section_clean)
                            if len(section_clean) > 1500:
                                section_clean = section_clean[:1500] + "..."
                            st.markdown(section_clean)
                
                st.markdown("---")
                
                # Head-to-Head
                if research.head_to_head:
                    st.markdown("#### 📈 Head-to-Head History")
                    st.markdown(research.head_to_head)
                    st.markdown("---")
                
                # Key Factors
                if research.key_factors and len(research.key_factors) > 0:
                    st.markdown("#### 🔑 Key Factors Affecting Outcome")
                    for i, factor in enumerate(research.key_factors, 1):
                        # Clean up factor text if it has markdown formatting issues
                        factor_clean = factor.strip().lstrip('123456789.-•* ').strip()
                        if factor_clean:
                            st.markdown(f"**{i}. {factor_clean}**")
                    st.markdown("---")
                
                # Detailed Reasoning - Show full ChatGPT analysis
                if research.reasoning:
                    st.markdown("#### 📝 Comprehensive Analysis & Reasoning")
                    # Parse and display the reasoning in a more structured way
                    reasoning_text = research.reasoning
                    
                    # Remove the WIN_PROB tag if present
                    reasoning_text = re.sub(r'\[WIN_PROB:[\d.]+\]\s*', '', reasoning_text)
                    
                    # Try to parse and structure the analysis better
                    # Look for numbered sections (1., 2., etc.) and format them
                    lines = reasoning_text.split('\n')
                    structured_sections = []
                    current_section = []
                    current_title = None
                    
                    for line in lines:
                        line = line.strip()
                        # Check if this is a section header (starts with number or is a team name)
                        if re.match(r'^\d+\.', line) or (line and line[0].isupper() and len(line) < 50 and ':' in line):
                            if current_section:
                                structured_sections.append((current_title, '\n'.join(current_section)))
                            current_title = line
                            current_section = []
                        elif line:
                            current_section.append(line)
                    
                    if current_section:
                        structured_sections.append((current_title, '\n'.join(current_section)))
                    
                    # Display structured sections
                    if structured_sections:
                        for title, content in structured_sections:
                            if title:
                                st.markdown(f"**{title}**")
                            st.markdown(content)
                            st.markdown("")
                    else:
                        # Fallback: display as-is
                        st.markdown(reasoning_text)
                    
                    # Also show in expandable for easier reading
                    with st.expander("📖 View Full Raw Analysis", expanded=False):
                        st.markdown(reasoning_text)
            else:
                st.warning("Research is still being generated. Please wait a moment and refresh, or the bot will process this game soon.")
                if game_data.get('reasoning') and game_data['reasoning'] != "Research available when bot analyzes":
                    st.markdown("#### Basic Analysis")
                    st.markdown(game_data['reasoning'])
    except Exception as e:
        st.error(f"Error loading research: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        if game_data.get('reasoning') and game_data['reasoning'] != "Research available when bot analyzes":
            st.markdown("#### Basic Analysis")
            st.markdown(game_data['reasoning'])
    
    # Social Sentiment
    st.markdown("### 📱 Social Sentiment Analysis")
    try:
        from social_sentiment import SocialSentimentAnalyzer
        
        sentiment_analyzer = SocialSentimentAnalyzer()
        with st.spinner("Analyzing social sentiment..."):
            sentiment = sentiment_analyzer.analyze_game_sentiment(
                game_data['team'],
                game_data['opponent'],
                game_data['league']
            )
            
            if sentiment.get('sources'):
                st.success(f"✅ Analyzed: {', '.join(sentiment['sources'])}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(f"{game_data['team']} Sentiment", 
                             f"{sentiment.get('team_a_sentiment', 0):.1%}" if sentiment.get('team_a_sentiment') else "N/A")
                with col2:
                    st.metric(f"{game_data['opponent']} Sentiment",
                             f"{sentiment.get('team_b_sentiment', 0):.1%}" if sentiment.get('team_b_sentiment') else "N/A")
                
                if sentiment.get('overall_sentiment'):
                    st.info(f"**Overall:** {sentiment['overall_sentiment']}")
                
                # Show sample tweets/posts
                if sentiment.get('tweets'):
                    with st.expander("Recent Tweets"):
                        for tweet in sentiment['tweets'][:3]:
                            st.markdown(f"- {tweet.get('text', '')[:100]}...")
                
                if sentiment.get('reddit_posts'):
                    with st.expander("Reddit Discussions"):
                        for post in sentiment['reddit_posts'][:3]:
                            st.markdown(f"- [{post.get('title', '')}]({post.get('url', '')})")
                
                if sentiment.get('news_articles'):
                    with st.expander("News Articles"):
                        for article in sentiment['news_articles'][:3]:
                            st.markdown(f"- [{article.get('title', '')}]({article.get('url', '')})")
            else:
                st.warning("⚠️ Social sentiment analysis requires API keys. See setup instructions below.")
                with st.expander("Setup Social Sentiment APIs"):
                    st.markdown("""
                    **To enable social sentiment analysis, add these to your `.env.local`:**
                    
                    1. **Twitter API (X API):**
                       - Get Bearer Token from: https://developer.twitter.com/
                       - Add: `TWITTER_BEARER_TOKEN=your_token`
                    
                    2. **Reddit API (Optional - works without auth for basic):**
                       - Get credentials from: https://www.reddit.com/prefs/apps
                       - Add: `REDDIT_CLIENT_ID=your_id` and `REDDIT_CLIENT_SECRET=your_secret`
                    
                    3. **News API (Optional):**
                       - Get key from: https://newsapi.org/
                       - Add: `NEWS_API_KEY=your_key`
                    """)
    except Exception as e:
        st.warning(f"Social sentiment analysis unavailable: {e}")


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
    
    # All Upcoming Games section
    st.subheader("🎮 All Upcoming Games (Next 5 Days)")
    
    # Add refresh button and filter
    col_refresh, col_filter = st.columns([1, 4])
    with col_refresh:
        refresh_games = st.button("🔄 Refresh", type="primary")
    
    # Cache the games analysis
    @st.cache_data(ttl=60)  # Cache for 1 minute (faster refresh)
    def get_cached_games():
        return fetch_all_games_analysis()
    
    if refresh_games:
        # Clear cache and refetch
        get_cached_games.clear()
    
    try:
        with st.spinner("Fetching and analyzing games..."):
            all_games = get_cached_games()
    except Exception as e:
        st.error(f"Error loading games: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        all_games = []
    
    if all_games:
        # Filter options
        with col_filter:
            filter_rec = st.selectbox(
                "Filter by Recommendation:",
                ["All", "STRONG BUY", "BUY", "WEAK BUY", "NO BET", "AVOID"],
                key="rec_filter"
            )
        
        # Apply filter
        filtered_games = all_games
        if filter_rec != "All":
            filtered_games = [g for g in all_games if g['recommendation'] == filter_rec]
        # Sort by edge (best bets first)
        all_games_sorted = sorted(filtered_games, key=lambda x: x.get('edge', -999) if x.get('edge') is not None else -999, reverse=True)
        
        # Create DataFrame
        games_data = []
        for game in all_games_sorted:
            # Determine which team to bet on
            # If we have research, use that. Otherwise, use edge but note it's preliminary
            research_prob = game.get('research_prob')
            if research_prob is not None:
                # Research probability is for team_a (game['team'])
                # If research_prob > 0.5, research favors game['team']
                # If research_prob < 0.5, research favors opponent
                if research_prob >= 0.5:
                    team_to_bet = game['team']
                    bet_direction = "YES"
                else:
                    team_to_bet = game['opponent']
                    bet_direction = "YES"
            else:
                # No research yet - use edge but note it's preliminary
                team_to_bet = game['team'] if game.get('edge', 0) > 0 else game['opponent']
                bet_direction = "YES" if game.get('edge', 0) > 0 else "NO"
            
            games_data.append({
                'Matchup': f"{game['team']} vs {game['opponent']}",
                'Team to Bet': f"{team_to_bet} ({bet_direction})",
                'League': game['league'],
                'Game Time (ET)': game['game_time'],
                'Time Until': game['time_until'],
                'Kalshi Price': game['kalshi_price'],
                'Ref Odds': game['ref_odds'],
                'Fair Prob': game['fair_prob_str'],
                'Research Prob': game['research_prob_str'],
                'Edge': game['edge_str'],
                'Recommendation': game['recommendation'],
                'Volume': f"{game['volume']:,}",
                'Spread': f"{game['spread']:.2%}",
                # Store full game data for detailed view
                '_game_data': game
            })
        
        # Extract game data for display (remove internal _game_data)
        display_data = [{k: v for k, v in g.items() if k != '_game_data'} for g in games_data]
        games_df = pd.DataFrame(display_data)
        
        # Add color coding to recommendation column
        def color_recommendation(val):
            if val == 'STRONG BUY':
                return 'background-color: #d4edda; color: #155724; font-weight: bold'
            elif val == 'BUY':
                return 'background-color: #d1ecf1; color: #0c5460'
            elif val == 'WEAK BUY':
                return 'background-color: #fff3cd; color: #856404'
            elif val == 'AVOID':
                return 'background-color: #f8d7da; color: #721c24'
            else:
                return ''
        
        # Style the dataframe
        styled_df = games_df.style.map(color_recommendation, subset=['Recommendation'])
        st.dataframe(styled_df, width='stretch', hide_index=True)
        
        # Game selection for detailed view
        st.markdown("### 🔍 View Detailed Analysis")
        
        # Group games by matchup to avoid duplicates
        matchup_dict = {}
        for g in games_data:
            matchup_key = f"{g['_game_data']['team']} vs {g['_game_data']['opponent']}"
            # Keep the one with better edge if duplicate
            if matchup_key not in matchup_dict:
                matchup_dict[matchup_key] = g
            else:
                # Compare edges and keep the better one
                current_edge = g['_game_data'].get('edge', -999)
                existing_edge = matchup_dict[matchup_key]['_game_data'].get('edge', -999)
                if current_edge > existing_edge:
                    matchup_dict[matchup_key] = g
        
        # Create dropdown options - show research-based recommendation
        game_options = []
        game_data_list = []
        for matchup, g in matchup_dict.items():
            rec = g['_game_data']['recommendation']
            team = g['_game_data']['team']
            opponent = g['_game_data']['opponent']
            edge = g['_game_data'].get('edge', 0)
            research_prob = g['_game_data'].get('research_prob')
            rec_reason = g['_game_data'].get('recommendation_reason', '')
            
            # Show research probability if available
            if research_prob is not None:
                team_prob = research_prob if team == g['_game_data'].get('team_a', team) else (1.0 - research_prob)
                opp_prob = 1.0 - team_prob
                if rec_reason:
                    game_options.append(f"{matchup} - {rec} ({rec_reason[:60]}...)")
                else:
                    game_options.append(f"{matchup} - {rec} (Research: {team_prob:.0%} vs {opp_prob:.0%})")
            elif edge:
                game_options.append(f"{matchup} - {rec} (Edge: {edge:.1%})")
            else:
                game_options.append(f"{matchup} - {rec}")
            game_data_list.append(g['_game_data'])
        
        selected_game = st.selectbox("Select a game to see detailed breakdown:", game_options, key="game_selector")
        
        if selected_game:
            selected_idx = game_options.index(selected_game)
            if selected_idx < len(game_data_list):
                show_detailed_breakdown(game_data_list[selected_idx])
        
        # Summary stats (use all games, not filtered)
        strong_buys = sum(1 for g in all_games if g['recommendation'] == 'STRONG BUY')
        buys = sum(1 for g in all_games if g['recommendation'] == 'BUY')
        weak_buys = sum(1 for g in all_games if g['recommendation'] == 'WEAK BUY')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Games", len(all_games))
        with col2:
            st.metric("🟢 Strong Buys", strong_buys)
        with col3:
            st.metric("🔵 Buys", buys)
        with col4:
            st.metric("🟡 Weak Buys", weak_buys)
    else:
        st.info("No games found. Make sure the bot can connect to Kalshi API and fetch markets.")
    
    st.markdown("---")
    
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
        st.dataframe(trades_df, width='stretch', hide_index=True)
        
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

