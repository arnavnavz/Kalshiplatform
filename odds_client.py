"""
Reference odds client.
Fetches fair odds from The Odds API.
"""
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
import requests

from config import Config
from models import Game, ReferenceOdds

logger = logging.getLogger(__name__)


class OddsClient:
    """Client for fetching reference odds from The Odds API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_key = os.getenv("THE_ODDS_API_KEY", "")
        self.base_url = "https://api.the-odds-api.com/v4"
        
        if not self.api_key:
            logger.warning("THE_ODDS_API_KEY not set. Will use mock odds.")
    
    def _map_league_to_sport_key(self, league: str) -> Optional[str]:
        """Map our league names to The Odds API sport keys."""
        mapping = {
            "NBA": "basketball_nba",
            "NFL": "americanfootball_nfl",
            "NHL": "icehockey_nhl",
            "MLB": "baseball_mlb",
            "EPL": "soccer_epl",
            "UCL": "soccer_uefa_champs_league",
            "NCAAB": "basketball_ncaab",
            "NCAAF": "americanfootball_ncaaf",
        }
        return mapping.get(league.upper())
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching."""
        # Remove common suffixes and normalize
        name = name.lower().strip()
        
        # Remove common team suffixes
        suffixes = [
            " warriors", " lakers", " clippers", " celtics", " nets", " knicks",
            " 76ers", " sixers", " heat", " magic", " hawks", " hornets",
            " bulls", " cavaliers", " cavs", " mavericks", " mavs", " nuggets",
            " pistons", " rockets", " pacers", " grizzlies", " timberwolves",
            " pelicans", " thunder", " suns", " trail blazers", " blazers",
            " kings", " spurs", " raptors", " jazz", " wizards"
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Remove city prefixes for some teams
        name = name.replace("los angeles ", "").replace("la ", "")
        name = name.replace("new york ", "").replace("ny ", "")
        name = name.replace("golden state", "warriors")
        name = name.replace("philadelphia", "philly")
        
        # Special cases for common team name variations
        if name == "lakers":
            name = "lakers"  # Keep as is, will match via contains check
        elif name == "clippers":
            name = "clippers"
        elif name == "knicks":
            name = "knicks"
        elif name == "nets":
            name = "nets"
        
        return name
    
    def _match_teams(self, kalshi_team: str, odds_team: str) -> bool:
        """Check if two team names match."""
        kalshi_norm = self._normalize_team_name(kalshi_team)
        odds_norm = self._normalize_team_name(odds_team)
        
        # Exact match
        if kalshi_norm == odds_norm:
            return True
        
        # Check if one contains the other (handles "lakers" vs "los angeles lakers")
        if kalshi_norm in odds_norm or odds_norm in kalshi_norm:
            return True
        
        # Check first 3-4 characters match (for abbreviations)
        if len(kalshi_norm) >= 3 and len(odds_norm) >= 3:
            if kalshi_norm[:3] == odds_norm[:3]:
                return True
        
        # Special case: check if normalized names share significant words
        # e.g., "memphis" should match "memphis grizzlies" (already handled by contains)
        # But also handle cases like "lakers" matching "los angeles lakers"
        kalshi_words = set(kalshi_norm.split())
        odds_words = set(odds_norm.split())
        if kalshi_words and odds_words:
            # If they share any significant word (length > 3), consider it a match
            common_words = kalshi_words.intersection(odds_words)
            if common_words and any(len(w) > 3 for w in common_words):
                return True
        
        return False
    
    def _fetch_from_odds_api(self, sport_key: str) -> List[Dict]:
        """Fetch odds from The Odds API for a sport."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h",  # Head-to-head (moneyline)
                "oddsFormat": "american"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Check API usage
            remaining = response.headers.get("x-requests-remaining")
            used = response.headers.get("x-requests-used")
            logger.debug(f"Odds API usage: {used} used, {remaining} remaining")
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching odds from The Odds API: {e}")
            return []
    
    def _find_matching_game(self, game: Game, odds_data: List[Dict]) -> Optional[Dict]:
        """Find matching game in odds data."""
        for event in odds_data:
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            
            # Try to match teams
            team_a_matches = (
                self._match_teams(game.team_a, home_team) or
                self._match_teams(game.team_a, away_team)
            )
            team_b_matches = (
                self._match_teams(game.team_b, home_team) or
                self._match_teams(game.team_b, away_team)
            )
            
            if team_a_matches and team_b_matches:
                return event
        
        return None
    
    def _extract_best_odds(self, event: Dict) -> Optional[tuple[int, int, str, str]]:
        """
        Extract best (most favorable) American odds from bookmakers.
        
        Returns:
            Tuple of (home_odds, away_odds, home_team_name, away_team_name)
        """
        if "bookmakers" not in event or not event["bookmakers"]:
            return None
        
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        home_odds = None
        away_odds = None
        
        for bookmaker in event["bookmakers"]:
            if "markets" not in bookmaker or not bookmaker["markets"]:
                continue
            
            for market in bookmaker["markets"]:
                if market.get("key") != "h2h":
                    continue
                
                outcomes = market.get("outcomes", [])
                if len(outcomes) < 2:
                    continue
                
                # Get best odds for each team across all bookmakers
                for outcome in outcomes:
                    odds = outcome.get("price")
                    name = outcome.get("name", "")
                    
                    # Match to home or away team
                    if self._match_teams(home_team, name):
                        if home_odds is None or odds > home_odds:
                            home_odds = odds
                    elif self._match_teams(away_team, name):
                        if away_odds is None or odds > away_odds:
                            away_odds = odds
        
        if home_odds is not None and away_odds is not None:
            return (home_odds, away_odds, home_team, away_team)
        
        return None
    
    def fetch_reference_odds(self, games: List[Game]) -> Dict[str, ReferenceOdds]:
        """
        Fetch reference odds from The Odds API.
        
        Args:
            games: List of Game objects
            
        Returns:
            Dictionary mapping game_id to ReferenceOdds
        """
        if not self.api_key:
            logger.warning("THE_ODDS_API_KEY not set. Using mock odds.")
            return self._fetch_mock_odds(games)
        
        ref_odds = {}
        
        # Group games by league
        games_by_league = {}
        for game in games:
            league = game.league
            if league not in games_by_league:
                games_by_league[league] = []
            games_by_league[league].append(game)
        
        # Fetch odds for each league
        for league, league_games in games_by_league.items():
            sport_key = self._map_league_to_sport_key(league)
            if not sport_key:
                logger.debug(f"No sport key mapping for league: {league}")
                continue
            
            logger.info(f"Fetching odds for {len(league_games)} {league} games from The Odds API")
            odds_data = self._fetch_from_odds_api(sport_key)
            
            if not odds_data:
                logger.warning(f"No odds data returned for {league}")
                continue
            
            logger.info(f"Received {len(odds_data)} events from The Odds API for {league}")
            
            # Log sample of what we got
            if odds_data:
                sample = odds_data[0]
                logger.debug(f"Sample event: {sample.get('away_team')} @ {sample.get('home_team')} on {sample.get('commence_time')}")
            
            # Match games to odds
            matched_count = 0
            for game in league_games:
                matched_event = self._find_matching_game(game, odds_data)
                
                if matched_event:
                    odds_result = self._extract_best_odds(matched_event)
                    if odds_result:
                        home_odds, away_odds, home_team, away_team = odds_result
                        
                        # Map our team_a/team_b to home/away odds
                        # Match our teams to The Odds API home/away teams
                        if self._match_teams(game.team_a, home_team):
                            # team_a is home team
                            final_team_a_odds = home_odds
                            final_team_b_odds = away_odds
                        elif self._match_teams(game.team_a, away_team):
                            # team_a is away team
                            final_team_a_odds = away_odds
                            final_team_b_odds = home_odds
                        else:
                            # Can't match, try reverse
                            if self._match_teams(game.team_b, home_team):
                                final_team_a_odds = away_odds
                                final_team_b_odds = home_odds
                            else:
                                # Default: assume team_a is home
                                final_team_a_odds = home_odds
                                final_team_b_odds = away_odds
                        
                        ref_odds[game.game_id] = ReferenceOdds(
                            game_id=game.game_id,
                            team_a_american_odds=final_team_a_odds,
                            team_b_american_odds=final_team_b_odds,
                            source="the-odds-api",
                            timestamp=datetime.now()
                        )
                        logger.info(f"✓ Found real odds for {game.team_a} vs {game.team_b}: {final_team_a_odds}/{final_team_b_odds} (from The Odds API)")
                        matched_count += 1
                    else:
                        logger.debug(f"Could not extract odds for {game.team_a} vs {game.team_b} (matched event but no bookmaker data)")
                else:
                    logger.debug(f"Could not match game {game.team_a} vs {game.team_b} in odds data (game may not be available in The Odds API yet)")
            
            logger.info(f"Matched {matched_count}/{len(league_games)} {league} games with real odds")
        
        # Fallback to mock for games without odds
        if len(ref_odds) < len(games):
            logger.info(f"Found odds for {len(ref_odds)}/{len(games)} games. Using mock for rest.")
            for game in games:
                if game.game_id not in ref_odds:
                    ref_odds[game.game_id] = self._generate_mock_odds(game)
        
        return ref_odds
    
    def _fetch_mock_odds(self, games: List[Game]) -> Dict[str, ReferenceOdds]:
        """Generate mock odds as fallback."""
        import random
        logger.debug(f"Generating mock odds for {len(games)} games")
        
        ref_odds = {}
        for game in games:
            ref_odds[game.game_id] = self._generate_mock_odds(game)
        
        return ref_odds
    
    def _generate_mock_odds(self, game: Game) -> ReferenceOdds:
        """Generate mock odds for a game."""
        import random
        
        if random.random() > 0.5:
            team_a_odds = random.randint(-200, -110)
            team_b_odds = random.randint(110, 250)
        else:
            team_a_odds = random.randint(110, 250)
            team_b_odds = random.randint(-200, -110)
        
        return ReferenceOdds(
            game_id=game.game_id,
            team_a_american_odds=team_a_odds,
            team_b_american_odds=team_b_odds,
            source="mock",
            timestamp=datetime.now()
        )

