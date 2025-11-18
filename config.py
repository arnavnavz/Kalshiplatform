"""
Configuration management for the Sharp Mismatch Sports Bot.
Loads settings from environment variables with sensible defaults.
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# Load environment variables from .env file
# Try .env.local first (for secrets), then .env (for defaults)
load_dotenv(".env.local")  # Load local overrides first
load_dotenv()  # Then load .env (will not override .env.local values)


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
        # Support both KALSHI_API_KEY/KALSHI_API_SECRET and KALSHI_API_KEY_ID/KALSHI_PRIVATE_KEY
        api_key = os.getenv("KALSHI_API_KEY") or os.getenv("KALSHI_API_KEY_ID", "")
        api_secret = os.getenv("KALSHI_API_SECRET") or os.getenv("KALSHI_PRIVATE_KEY", "")
        
        # If secret is empty or too short, try reading from .env file directly (for multi-line keys)
        if not api_secret or len(api_secret) < 100:
            try:
                env_path = Path(".env")
                if env_path.exists():
                    with open(env_path, 'r') as f:
                        content = f.read()
                        # Extract multi-line secret - capture until next variable or end of file
                        # Look for KALSHI_API_SECRET= and capture everything until next variable or EOF
                        pattern = r'KALSHI_API_SECRET=(.*?)(?=\n[A-Z][A-Z_]*=|$)'
                        match = re.search(pattern, content, re.DOTALL)
                        if match:
                            api_secret = match.group(1).strip()
                            # Remove quotes if present
                            if api_secret.startswith('"') and api_secret.endswith('"'):
                                api_secret = api_secret[1:-1]
                            elif api_secret.startswith("'") and api_secret.endswith("'"):
                                api_secret = api_secret[1:-1]
                            # Clean up any extra whitespace/newlines
                            api_secret = api_secret.strip()
            except Exception:
                pass
        
        return cls(
            kalshi_api_key=api_key,
            kalshi_api_secret=api_secret,
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

