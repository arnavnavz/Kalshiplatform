"""
Configuration management for the Sharp Mismatch Sports Bot.
Loads settings from environment variables with sensible defaults.
"""
import os
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Main configuration object with all bot settings."""
    
    # Kalshi API Configuration
    kalshi_api_key: str
    kalshi_api_secret: str
    kalshi_base_url: str
    
    # Bot Mode
    mode: Literal["SHADOW", "LIVE"]
    
    # Polling Configuration
    poll_interval_seconds: int
    
    # Strategy Parameters
    edge_threshold: float
    kelly_factor: float
    max_per_bet_pct: float
    max_per_game_pct: float
    max_daily_risk_pct: float
    max_per_team_pct: float
    
    # Market Filtering
    min_market_volume: int
    max_spread: float
    min_time_to_start_minutes: int
    slippage_tolerance: float
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            kalshi_api_key=os.getenv("KALSHI_API_KEY", ""),
            kalshi_api_secret=os.getenv("KALSHI_API_SECRET", ""),
            kalshi_base_url=os.getenv(
                "KALSHI_BASE_URL", 
                "https://api.demo.kalshi.com/trade-api/v2"
            ),
            mode=os.getenv("MODE", "SHADOW").upper(),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
            edge_threshold=float(os.getenv("EDGE_THRESHOLD", "0.07")),
            kelly_factor=float(os.getenv("KELLY_FACTOR", "0.25")),
            max_per_bet_pct=float(os.getenv("MAX_PER_BET_PCT", "0.02")),
            max_per_game_pct=float(os.getenv("MAX_PER_GAME_PCT", "0.05")),
            max_daily_risk_pct=float(os.getenv("MAX_DAILY_RISK_PCT", "0.10")),
            max_per_team_pct=float(os.getenv("MAX_PER_TEAM_PCT", "0.08")),
            min_market_volume=int(os.getenv("MIN_MARKET_VOLUME", "2000")),
            max_spread=float(os.getenv("MAX_SPREAD", "0.08")),
            min_time_to_start_minutes=int(os.getenv("MIN_TIME_TO_START_MINUTES", "5")),
            slippage_tolerance=float(os.getenv("SLIPPAGE_TOLERANCE", "0.02")),
        )
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.mode not in ("SHADOW", "LIVE"):
            raise ValueError(f"Invalid MODE: {self.mode}. Must be SHADOW or LIVE")
        
        if self.mode == "LIVE":
            if not self.kalshi_api_key or not self.kalshi_api_secret:
                raise ValueError("KALSHI_API_KEY and KALSHI_API_SECRET required for LIVE mode")
        
        if not 0 < self.edge_threshold < 1:
            raise ValueError("EDGE_THRESHOLD must be between 0 and 1")
        
        if not 0 < self.kelly_factor <= 1:
            raise ValueError("KELLY_FACTOR must be between 0 and 1")
        
        if not 0 < self.max_per_bet_pct <= 1:
            raise ValueError("MAX_PER_BET_PCT must be between 0 and 1")
        
        if not 0 < self.max_daily_risk_pct <= 1:
            raise ValueError("MAX_DAILY_RISK_PCT must be between 0 and 1")


def load_config() -> Config:
    """Load and validate configuration."""
    config = Config.from_env()
    config.validate()
    return config

