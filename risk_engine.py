"""
Risk management engine.
Tracks positions and enforces risk limits.
"""
import logging
from collections import defaultdict
from typing import Dict, List

from config import Config
from models import Position

logger = logging.getLogger(__name__)


class RiskEngine:
    """Manages risk limits and position tracking."""
    
    def __init__(self, config: Config):
        self.config = config
        self.bankroll: float = 0.0
        self.positions: List[Position] = []
        
        # Track exposure by dimension
        self.exposure_by_game: Dict[str, float] = defaultdict(float)
        self.exposure_by_team: Dict[str, float] = defaultdict(float)
        self.exposure_by_league: Dict[str, float] = defaultdict(float)
        self.total_daily_risk: float = 0.0
    
    def update_from_positions(self, positions: List[Position], bankroll: float) -> None:
        """
        Update risk engine with current positions and bankroll.
        
        Args:
            positions: List of current open positions
            bankroll: Current account balance
        """
        self.bankroll = bankroll
        self.positions = positions
        
        # Reset exposure tracking
        self.exposure_by_game.clear()
        self.exposure_by_team.clear()
        self.exposure_by_league.clear()
        self.total_daily_risk = 0.0
        
        # Calculate exposure from positions
        for position in positions:
            # Max loss is the total cost of the position (if it goes to 0)
            max_loss = position.max_loss if position.max_loss > 0 else (
                position.quantity * position.average_price
            )
            
            self.total_daily_risk += max_loss
            self.exposure_by_game[position.game_id] += max_loss
            self.exposure_by_team[position.team] += max_loss
            self.exposure_by_league[position.league] += max_loss
        
        logger.debug(
            f"Risk update: bankroll=${bankroll:.2f}, "
            f"daily_risk=${self.total_daily_risk:.2f}, "
            f"positions={len(positions)}"
        )
    
    def can_take_trade(
        self, 
        stake: float, 
        game_id: str, 
        team: str, 
        league: str
    ) -> bool:
        """
        Check if a trade can be taken given current risk limits.
        
        Args:
            stake: Proposed stake amount
            game_id: Game identifier
            team: Team name
            league: League name
            
        Returns:
            True if trade is allowed, False otherwise
        """
        # Check daily risk limit
        new_daily_risk = self.total_daily_risk + stake
        max_daily_risk = self.config.max_daily_risk_pct * self.bankroll
        if new_daily_risk > max_daily_risk:
            logger.debug(
                f"Trade rejected: Daily risk limit. "
                f"Current: ${self.total_daily_risk:.2f}, "
                f"Proposed: ${stake:.2f}, "
                f"Limit: ${max_daily_risk:.2f}"
            )
            return False
        
        # Check per-game limit
        new_game_exposure = self.exposure_by_game[game_id] + stake
        max_game_exposure = self.config.max_per_game_pct * self.bankroll
        if new_game_exposure > max_game_exposure:
            logger.debug(
                f"Trade rejected: Per-game limit. "
                f"Game: {game_id}, "
                f"Current: ${self.exposure_by_game[game_id]:.2f}, "
                f"Proposed: ${stake:.2f}, "
                f"Limit: ${max_game_exposure:.2f}"
            )
            return False
        
        # Check per-team limit
        new_team_exposure = self.exposure_by_team[team] + stake
        max_team_exposure = self.config.max_per_team_pct * self.bankroll
        if new_team_exposure > max_team_exposure:
            logger.debug(
                f"Trade rejected: Per-team limit. "
                f"Team: {team}, "
                f"Current: ${self.exposure_by_team[team]:.2f}, "
                f"Proposed: ${stake:.2f}, "
                f"Limit: ${max_team_exposure:.2f}"
            )
            return False
        
        return True
    
    def remaining_daily_risk(self) -> float:
        """
        Calculate remaining daily risk capacity.
        
        Returns:
            Remaining risk capacity in dollars
        """
        max_daily_risk = self.config.max_daily_risk_pct * self.bankroll
        return max(0.0, max_daily_risk - self.total_daily_risk)
    
    def cap_stake(
        self, 
        raw_stake: float, 
        game_id: str, 
        team: str, 
        league: str
    ) -> float:
        """
        Apply all risk caps to a raw stake amount.
        
        Args:
            raw_stake: Unconstrained stake amount
            game_id: Game identifier
            team: Team name
            league: League name
            
        Returns:
            Capped stake amount
        """
        # Per-bet cap
        max_per_bet = self.config.max_per_bet_pct * self.bankroll
        stake = min(raw_stake, max_per_bet)
        
        # Daily risk cap
        remaining_daily = self.remaining_daily_risk()
        stake = min(stake, remaining_daily)
        
        # Per-game cap
        max_game = self.config.max_per_game_pct * self.bankroll
        remaining_game = max(0.0, max_game - self.exposure_by_game[game_id])
        stake = min(stake, remaining_game)
        
        # Per-team cap
        max_team = self.config.max_per_team_pct * self.bankroll
        remaining_team = max(0.0, max_team - self.exposure_by_team[team])
        stake = min(stake, remaining_team)
        
        return max(0.0, stake)

