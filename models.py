"""
Data models for markets, games, odds, and positions.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Market:
    """Represents a Kalshi sports market."""
    market_id: str
    event_name: str
    game_id: str  # Identifier to map to external odds
    league: str  # e.g., "NBA", "NFL", "UCL"
    team: str  # The side we'd be betting on (e.g., "Lakers", "Team A")
    best_yes_price: float  # Best available YES price (0-1)
    best_no_price: float  # Best available NO price (0-1)
    volume: int  # Market volume
    spread: float  # ask - bid (in price units, 0-1)
    start_time: datetime  # Game start time
    settlement_time: datetime  # Market settlement time
    title: str  # Full market title for display
    
    @property
    def bid(self) -> float:
        """Bid price (best YES price)."""
        return self.best_yes_price
    
    @property
    def ask(self) -> float:
        """Ask price (1 - best NO price)."""
        return 1.0 - self.best_no_price


@dataclass
class Game:
    """Represents a sports game/event."""
    game_id: str
    team_a: str
    team_b: str
    league: str
    start_time: datetime


@dataclass
class ReferenceOdds:
    """Reference odds from external source (e.g., Vegas)."""
    game_id: str
    team_a_american_odds: int  # American odds format (e.g., -150, +200)
    team_b_american_odds: int
    source: str = "mock"  # Source of the odds (e.g., "mock", "the-odds-api", etc.)
    timestamp: Optional[datetime] = None


@dataclass
class FairProbabilities:
    """Fair probabilities after removing vig."""
    game_id: str
    team_a_fair_prob: float  # 0-1
    team_b_fair_prob: float  # 0-1


@dataclass
class Position:
    """Represents an open position in a market."""
    market_id: str
    game_id: str
    team: str
    league: str
    quantity: int  # Number of contracts
    average_price: float  # Average fill price (0-1)
    current_yes_price: float  # Current market YES price
    unrealized_pnl: float  # Unrealized P&L
    max_loss: float  # Worst-case loss if position goes to 0


@dataclass
class Trade:
    """Represents a trade execution (or shadow trade)."""
    timestamp: datetime
    market_id: str
    game_id: str
    team: str
    league: str
    fair_prob: float
    kalshi_prob: float
    edge: float
    stake: float  # Dollar amount
    quantity: int  # Number of contracts
    limit_price: float
    mode: str  # "SHADOW" or "LIVE"
    order_id: Optional[str] = None  # Kalshi order ID if LIVE

