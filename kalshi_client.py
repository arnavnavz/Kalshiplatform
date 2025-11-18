"""
Kalshi API client wrapper.
Handles authentication, requests, and retries.
"""
import time
import base64
import logging
from typing import List, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from config import Config
from models import Market, Position

logger = logging.getLogger(__name__)


class KalshiClient:
    """Client for interacting with Kalshi API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.kalshi_base_url.rstrip('/')
        self.api_key = config.kalshi_api_key
        self.api_secret = config.kalshi_api_secret
        self.session = self._create_session()
        self._private_key = None
        self._exchange_id = None
        
        # Load private key if available
        if self.api_secret and CRYPTO_AVAILABLE:
            try:
                key_content = self.api_secret.strip()
                
                # Handle escaped newlines from .env file
                key_content = key_content.replace('\\n', '\n')
                
                # If headers are missing, add them
                if "BEGIN PRIVATE KEY" not in key_content and "BEGIN RSA PRIVATE KEY" not in key_content:
                    # Remove any existing headers/footers just in case
                    key_content = key_content.replace('-----BEGIN PRIVATE KEY-----', '').replace('-----END PRIVATE KEY-----', '')
                    key_content = key_content.replace('-----BEGIN RSA PRIVATE KEY-----', '').replace('-----END RSA PRIVATE KEY-----', '')
                    key_content = key_content.strip()
                    # Add PEM headers
                    key_content = f"-----BEGIN PRIVATE KEY-----\n{key_content}\n-----END PRIVATE KEY-----"
                
                self._private_key = load_pem_private_key(
                    key_content.encode(),
                    password=None,
                )
                logger.info("Private key loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load private key: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _sign_request(self, method: str, path: str) -> dict:
        """
        Create signed headers for Kalshi API request using RSA-PSS.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            
        Returns:
            Dictionary of headers for authenticated request
        """
        if self.config.mode == "SHADOW" or not self._private_key:
            return {}
        
        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path
        
        try:
            signature = self._private_key.sign(
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            signature_b64 = base64.b64encode(signature).decode()
            
            return {
                'KALSHI-ACCESS-KEY': self.api_key,
                'KALSHI-ACCESS-TIMESTAMP': timestamp,
                'KALSHI-ACCESS-SIGNATURE': signature_b64
            }
        except Exception as e:
            logger.error(f"Error signing request: {e}")
            return {}
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated request to Kalshi API."""
        # In SHADOW mode, we still allow GET requests (read-only) but block POST (orders)
        # This allows us to see real markets and data without placing orders
        if self.config.mode == "SHADOW" and method.upper() == "POST":
            logger.debug(f"SHADOW mode: Would {method} {endpoint} (blocked)")
            return {}
        
        # Ensure endpoint starts with /
        path = endpoint if endpoint.startswith('/') else f'/{endpoint}'
        
        # Get signed headers
        headers = kwargs.pop("headers", {})
        signed_headers = self._sign_request(method, path)
        headers.update(signed_headers)
        headers.setdefault("Content-Type", "application/json")
        
        url = f"{self.base_url}{path}"
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_account_balance(self) -> float:
        """
        Get current account balance (bankroll).
        
        Returns:
            Current cash balance in dollars.
        """
        # Try to fetch real balance if API keys are available
        use_real_api = bool(self.api_key and self.api_secret and self._private_key)
        
        if not use_real_api and self.config.mode == "SHADOW":
            logger.debug("SHADOW mode: No API keys, returning mock balance")
            return 10000.0  # Mock $10k bankroll
        
        try:
            data = self._request("GET", "/portfolio/balance")
            # Kalshi returns balance in cents, convert to dollars
            balance_cents = float(data.get("balance", 0))
            return balance_cents / 100.0
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of Position objects.
        """
        if self.config.mode == "SHADOW":
            logger.debug("SHADOW mode: Returning empty positions")
            return []
        
        try:
            data = self._request("GET", "/portfolio/positions")
            positions = []
            
            for pos_data in data.get("positions", []):
                # Parse position data - adjust field names based on actual API response
                market_ticker = pos_data.get("ticker", pos_data.get("market_id", ""))
                quantity = int(pos_data.get("position", pos_data.get("quantity", 0)))
                
                # Calculate max loss (worst case if position goes to 0)
                avg_price = float(pos_data.get("average_price", 0)) / 100.0  # Convert from cents
                max_loss = quantity * avg_price
                
                positions.append(Position(
                    market_id=market_ticker,
                    game_id=pos_data.get("game_id", ""),
                    team=pos_data.get("team", ""),
                    league=pos_data.get("league", ""),
                    quantity=quantity,
                    average_price=avg_price,
                    current_yes_price=float(pos_data.get("current_yes_price", 0)) / 100.0 if pos_data.get("current_yes_price") else 0.0,
                    unrealized_pnl=float(pos_data.get("unrealized_pnl", 0)) / 100.0 if pos_data.get("unrealized_pnl") else 0.0,
                    max_loss=max_loss
                ))
            
            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def fetch_sports_markets(self) -> List[Market]:
        """
        Fetch all open sports markets.
        
        Returns:
            List of Market objects.
        """
        # Try to fetch real markets if API keys are available
        # Even in SHADOW mode, we can fetch real markets (just won't place orders)
        use_real_api = bool(self.api_key and self.api_secret and self._private_key)
        
        if not use_real_api and self.config.mode == "SHADOW":
            logger.debug("SHADOW mode: No API keys, returning mock markets")
            from datetime import timedelta
            import random
            
            # Generate some mock markets for testing
            mock_markets = []
            teams = [
                ("Lakers", "Warriors", "NBA"),
                ("Chiefs", "Bills", "NFL"),
                ("Man City", "Liverpool", "EPL"),
            ]
            
            for i, (team_a, team_b, league) in enumerate(teams):
                game_id = f"{league}_{team_a}_{team_b}_{i}"
                yes_price = 0.45 + random.uniform(-0.1, 0.1)
                no_price = 1.0 - yes_price
                spread = random.uniform(0.02, 0.10)
                
                mock_markets.append(Market(
                    market_id=f"market_{i}",
                    event_name=f"{team_a} vs {team_b}",
                    game_id=game_id,
                    league=league,
                    team=team_a,
                    best_yes_price=max(0.01, min(0.99, yes_price)),
                    best_no_price=max(0.01, min(0.99, no_price)),
                    volume=random.randint(1000, 10000),
                    spread=spread,
                    start_time=datetime.now() + timedelta(hours=2),
                    settlement_time=datetime.now() + timedelta(hours=4),
                    title=f"{team_a} to win vs {team_b}"
                ))
            
            return mock_markets
        
        try:
            # Fetch simple game markets by querying each sports series
            # Kalshi organizes markets by series (NBA games, NFL games, etc.)
            all_markets = []
            
            # Query for different sports series
            sports_series = [
                "KXNBAGAME",   # NBA games
                "KXNFLGAME",   # NFL games  
                "KXEPLGAME",   # EPL games
                "KXUCLGAME",   # UCL games
                "KXNHLGAME",   # NHL games
                "KXMLBGAME",   # MLB games
            ]
            
            for series_ticker in sports_series:
                try:
                    params = {
                        "status": "open",
                        "limit": 100,
                        "series_ticker": series_ticker
                    }
                    data = self._request("GET", "/markets", params=params)
                    series_markets = data.get("markets", [])
                    all_markets.extend(series_markets)
                    logger.debug(f"Found {len(series_markets)} markets for series {series_ticker}")
                except Exception as e:
                    logger.debug(f"Error fetching series {series_ticker}: {e}")
                    continue
            
            markets = []
            
            for market_data in all_markets:
                # Skip multivariate/combo markets
                ticker = market_data.get("ticker", "")
                if "KXMVENBASINGLEGAME" in ticker or "KXMVEMENTION" in ticker:
                    continue
                
                # Parse market data - adjust field names based on actual API response
                ticker = market_data.get("ticker", market_data.get("market_id", ""))
                title = market_data.get("title", market_data.get("subtitle", ""))
                
                # Prices are in cents (0-100), convert to 0-1
                yes_price_cents = int(market_data.get("yes_bid", market_data.get("yes_price", 50)))
                no_price_cents = int(market_data.get("no_bid", market_data.get("no_price", 50)))
                
                yes_price = yes_price_cents / 100.0
                no_price = no_price_cents / 100.0
                
                # Calculate spread
                yes_ask = int(market_data.get("yes_ask", yes_price_cents)) / 100.0
                spread = yes_ask - yes_price
                
                # Parse event time - Kalshi uses ISO 8601 format (e.g., "2025-11-18T20:00:00Z")
                from dateutil import parser as date_parser
                
                # Try multiple time fields in order of preference
                time_str = (
                    market_data.get("expected_expiration_time") or
                    market_data.get("event_timestamp") or
                    market_data.get("expiration_time") or
                    market_data.get("close_time")
                )
                
                if time_str:
                    try:
                        # Parse ISO format timestamp
                        if isinstance(time_str, str):
                            start_time = date_parser.parse(time_str)
                        elif isinstance(time_str, (int, float)):
                            # Fallback for Unix timestamp
                            start_time = datetime.fromtimestamp(time_str)
                        else:
                            start_time = datetime.now()
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Could not parse time {time_str}: {e}")
                        start_time = datetime.now()
                else:
                    start_time = datetime.now()
                
                # Extract game info from title/event_ticker
                event_ticker = market_data.get("event_ticker", "")
                league = self._extract_league_from_ticker(event_ticker, title)
                
                # Create game_id and team from market data
                game_id, team = self._parse_market_info(market_data, title, event_ticker)
                
                markets.append(Market(
                    market_id=ticker,
                    event_name=title,
                    game_id=game_id,
                    league=league,
                    team=team,
                    best_yes_price=yes_price,
                    best_no_price=no_price,
                    volume=int(market_data.get("volume", 0)),
                    spread=spread,
                    start_time=start_time,
                    settlement_time=start_time,  # Adjust based on actual API
                    title=title
                ))
            
            logger.info(f"Fetched {len(markets)} sports markets from Kalshi")
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            # Fall back to empty list or mock data in case of error
            return []
    
    def _extract_league_from_ticker(self, event_ticker: str, title: str) -> str:
        """Extract league name from ticker or title."""
        ticker_upper = event_ticker.upper()
        title_upper = title.upper()
        
        # Common league abbreviations
        leagues = {
            "NBA": "NBA",
            "NFL": "NFL",
            "NHL": "NHL",
            "MLB": "MLB",
            "EPL": "EPL",
            "UCL": "UCL",
            "NCAAB": "NCAAB",
            "NCAAF": "NCAAF",
        }
        
        for abbrev, full_name in leagues.items():
            if abbrev in ticker_upper or abbrev in title_upper:
                return full_name
        
        return "UNKNOWN"
    
    def _parse_market_info(self, market_data: dict, title: str, event_ticker: str) -> tuple:
        """
        Parse game_id and team from market data.
        
        Returns:
            Tuple of (game_id, team)
        """
        ticker = market_data.get("ticker", "")
        
        # For Kalshi game markets, the ticker format is like:
        # KXNBAGAME-25NOV20SACMEM-SAC (team is last part after final dash)
        # Or: KXNBAGAME-25NOV20SACMEM-MEM
        
        # Extract team from ticker (last part after final dash)
        if "-" in ticker:
            parts = ticker.split("-")
            if len(parts) >= 3:
                # Last part is usually the team abbreviation
                team_abbrev = parts[-1]
                # Game ID is everything except the team
                game_id = "-".join(parts[:-1])
                
                # Try to extract team name from title
                # Title format: "Sacramento vs Memphis Winner?" or "Team A vs Team B Winner?"
                title_lower = title.lower()
                if " vs " in title_lower and "winner" in title_lower:
                    # Extract both teams
                    parts = title_lower.split(" vs ")
                    team_a = parts[0].strip()
                    team_b = parts[1].split(" winner")[0].strip()
                    
                    # Match abbreviation to team name
                    # Common NBA abbreviations: SAC, MEM, ATL, SAS, GSW, LAL, etc.
                    team_abbrev_lower = team_abbrev.lower()
                    
                    # Check if abbreviation matches first few letters of either team
                    if team_abbrev_lower in team_a[:len(team_abbrev)] or team_abbrev_lower == team_a[:3].lower():
                        team = team_a.title()
                    elif team_abbrev_lower in team_b[:len(team_abbrev)] or team_abbrev_lower == team_b[:3].lower():
                        team = team_b.title()
                    else:
                        # Try matching by common abbreviations
                        abbrev_map = {
                            "sac": "sacramento", "mem": "memphis", "atl": "atlanta", 
                            "sas": "san antonio", "gsw": "golden state", "lal": "los angeles",
                            "bos": "boston", "bkn": "brooklyn", "cha": "charlotte",
                            "chi": "chicago", "cle": "cleveland", "dal": "dallas",
                            "den": "denver", "det": "detroit", "hou": "houston",
                            "ind": "indiana", "lac": "la clippers", "mia": "miami",
                            "mil": "milwaukee", "min": "minnesota", "no": "new orleans",
                            "ny": "new york", "okc": "oklahoma city", "orl": "orlando",
                            "phi": "philadelphia", "phx": "phoenix", "por": "portland",
                            "sa": "san antonio", "tor": "toronto", "uta": "utah", "was": "washington"
                        }
                        if team_abbrev_lower in abbrev_map:
                            full_name = abbrev_map[team_abbrev_lower]
                            if full_name in team_a:
                                team = team_a.title()
                            elif full_name in team_b:
                                team = team_b.title()
                            else:
                                team = full_name.title()
                        else:
                            # Default to first team if can't match
                            team = team_a.title()
                else:
                    # Fallback: use abbreviation
                    team = team_abbrev
                
                return game_id, team
        
        # Fallback parsing from title
        title_lower = title.lower()
        if " vs " in title_lower:
            parts = title_lower.split(" vs ")
            team = parts[0].strip().title()
            game_id = event_ticker if event_ticker else f"game_{ticker}"
        else:
            team = "Unknown"
            game_id = event_ticker if event_ticker else f"game_{ticker}"
        
        return game_id, team
    
    def place_yes_order(
        self, 
        market_id: str, 
        price: float, 
        size: int
    ) -> Optional[str]:
        """
        Place a limit order for YES contracts.
        
        Args:
            market_id: Market ticker/identifier
            price: Limit price (0-1)
            size: Number of contracts
            
        Returns:
            Order ID if successful, None otherwise
        """
        if self.config.mode == "SHADOW":
            logger.info(
                f"SHADOW mode: Would place YES order - "
                f"market={market_id}, price={price:.4f}, size={size}"
            )
            return f"shadow_order_{market_id}_{int(time.time())}"
        
        try:
            # Convert price from 0-1 to cents (0-100)
            price_cents = int(price * 100)
            
            data = self._request(
                "POST",
                "/portfolio/orders",
                json={
                    "ticker": market_id,
                    "action": "buy",
                    "side": "yes",
                    "type": "limit",
                    "count": size,
                    "price": price_cents
                }
            )
            
            order_id = data.get("order_id", data.get("order", {}).get("order_id"))
            logger.info(f"Placed order {order_id} for {size} YES @ {price:.4f} on {market_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
