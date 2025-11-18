"""
Reference odds client.
Fetches fair odds from external sources (mocked for now).
"""
import logging
from datetime import datetime
from typing import Dict, List
import random

from config import Config
from models import Game, ReferenceOdds

logger = logging.getLogger(__name__)


class OddsClient:
    """Client for fetching reference odds from external sources."""
    
    def __init__(self, config: Config):
        self.config = config
        # TODO: Add API keys for real odds providers (e.g., The Odds API, etc.)
    
    def fetch_reference_odds(self, games: List[Game]) -> Dict[str, ReferenceOdds]:
        """
        Fetch reference odds for a list of games.
        
        Args:
            games: List of Game objects
            
        Returns:
            Dictionary mapping game_id to ReferenceOdds
        """
        # TODO: Implement real odds fetching from external API
        # For now, return mock odds
        
        logger.debug(f"Fetching reference odds for {len(games)} games (MOCK)")
        
        ref_odds = {}
        for game in games:
            # Generate mock American odds
            # Favorites have negative odds (e.g., -150)
            # Underdogs have positive odds (e.g., +200)
            
            # Randomly assign one team as favorite
            if random.random() > 0.5:
                team_a_odds = random.randint(-200, -110)  # Favorite
                team_b_odds = random.randint(110, 250)    # Underdog
            else:
                team_a_odds = random.randint(110, 250)    # Underdog
                team_b_odds = random.randint(-200, -110)  # Favorite
            
            ref_odds[game.game_id] = ReferenceOdds(
                game_id=game.game_id,
                team_a_american_odds=team_a_odds,
                team_b_american_odds=team_b_odds,
                source="mock",
                timestamp=datetime.now()
            )
        
        return ref_odds
    
    # Example implementation for The Odds API (commented out):
    # def _fetch_from_odds_api(self, games: List[Game]) -> Dict[str, ReferenceOdds]:
    #     """Fetch odds from The Odds API."""
    #     import requests
    #     
    #     api_key = os.getenv("THE_ODDS_API_KEY")
    #     if not api_key:
    #         raise ValueError("THE_ODDS_API_KEY not set")
    #     
    #     ref_odds = {}
    #     for game in games:
    #         # Map league to The Odds API sport key
    #         sport_key = self._map_league_to_sport_key(game.league)
    #         
    #         response = requests.get(
    #             f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
    #             params={
    #                 "apiKey": api_key,
    #                 "regions": "us",
    #                 "markets": "h2h",
    #                 "oddsFormat": "american"
    #             }
    #         )
    #         response.raise_for_status()
    #         data = response.json()
    #         
    #         # Parse response and create ReferenceOdds objects
    #         # This will need to match teams and extract odds
    #         ...
    #     
    #     return ref_odds

