"""
Sharp Mismatch Sports Bot strategy logic.
Implements edge calculation and Kelly sizing.
"""
import logging
from typing import Dict

from models import Market, FairProbabilities, ReferenceOdds

logger = logging.getLogger(__name__)


def american_to_implied_prob(odds: int) -> float:
    """
    Convert American odds to raw implied probability.
    
    Args:
        odds: American odds (e.g., -150, +200)
        
    Returns:
        Implied probability (0-1)
    """
    if odds < 0:
        # Favorite: -150 means bet $150 to win $100
        # Implied prob = 150 / (150 + 100) = 0.6
        return (-odds) / ((-odds) + 100)
    else:
        # Underdog: +200 means bet $100 to win $200
        # Implied prob = 100 / (200 + 100) = 0.333
        return 100 / (odds + 100)


def remove_vig(p_a_raw: float, p_b_raw: float) -> tuple[float, float]:
    """
    Remove vig (bookmaker margin) to get fair probabilities.
    
    Args:
        p_a_raw: Raw implied probability for team A
        p_b_raw: Raw implied probability for team B
        
    Returns:
        Tuple of (fair_prob_a, fair_prob_b) that sum to 1.0
    """
    total = p_a_raw + p_b_raw
    if total == 0:
        return 0.5, 0.5
    return p_a_raw / total, p_b_raw / total


def compute_fair_probs(
    ref_odds_dict: Dict[str, ReferenceOdds]
) -> Dict[str, FairProbabilities]:
    """
    Compute fair probabilities from reference odds.
    
    Args:
        ref_odds_dict: Dictionary mapping game_id to ReferenceOdds
        
    Returns:
        Dictionary mapping game_id to FairProbabilities
    """
    fair_probs = {}
    
    for game_id, ref_odds in ref_odds_dict.items():
        # Convert American odds to implied probabilities
        p_a_raw = american_to_implied_prob(ref_odds.team_a_american_odds)
        p_b_raw = american_to_implied_prob(ref_odds.team_b_american_odds)
        
        # Remove vig
        p_a_fair, p_b_fair = remove_vig(p_a_raw, p_b_raw)
        
        fair_probs[game_id] = FairProbabilities(
            game_id=game_id,
            team_a_fair_prob=p_a_fair,
            team_b_fair_prob=p_b_fair
        )
    
    return fair_probs


def calc_edge(
    fair_prob: float, 
    kalshi_price: float, 
    research_prob: float = None,
    research_confidence: str = None
) -> float:
    """
    Calculate edge (expected value) of a trade.
    Uses research probability if available, with dynamic weighting based on confidence.
    
    Args:
        fair_prob: Fair probability from reference odds (0-1)
        kalshi_price: Kalshi market price (0-1)
        research_prob: Research-based probability (0-1), optional
        research_confidence: Research confidence level ("HIGH", "MEDIUM", "LOW"), optional
        
    Returns:
        Edge in probability units (positive = good trade)
    """
    # If we have research probability, use weighted combination
    # Weight depends on research confidence
    if research_prob is not None and 0 < research_prob < 1:
        # Dynamic weighting based on confidence
        if research_confidence == "HIGH":
            # High confidence: trust research more (85% research, 15% odds)
            research_weight = 0.85
        elif research_confidence == "MEDIUM":
            # Medium confidence: balanced (70% research, 30% odds) - default
            research_weight = 0.70
        elif research_confidence == "LOW":
            # Low confidence: trust odds more (50% research, 50% odds)
            research_weight = 0.50
        else:
            # Default to medium if confidence not specified
            research_weight = 0.70
        
        combined_prob = research_weight * research_prob + (1 - research_weight) * fair_prob
        return combined_prob - kalshi_price
    
    # Fallback to odds-based probability
    return fair_prob - kalshi_price


def kelly_fraction(
    fair_prob: float, 
    market_prob: float, 
    kelly_factor: float,
    research_confidence: str = None
) -> float:
    """
    Calculate fractional Kelly bet size with confidence-based adjustment.
    
    For a binary contract paying 1 if event happens:
    - If we buy at price p and true prob is q, expected value = q - p
    - Kelly formula: f = (q - p) / (1 - p)
    - We apply a fractional Kelly factor for safety
    - Confidence level further adjusts the bet size
    
    Args:
        fair_prob: Fair probability (0-1)
        market_prob: Market price (0-1)
        kelly_factor: Fraction of full Kelly to use (0-1)
        research_confidence: Research confidence level ("HIGH", "MEDIUM", "LOW"), optional
        
    Returns:
        Kelly fraction (0-1), representing fraction of bankroll to bet
    """
    if fair_prob <= market_prob:
        return 0.0
    
    # Base Kelly formula for binary contract
    base = (fair_prob - market_prob) / (1.0 - market_prob)
    
    # Apply fractional Kelly factor
    base_kelly = base * kelly_factor
    
    # Adjust based on research confidence
    if research_confidence == "HIGH":
        # High confidence: use full calculated Kelly (no reduction)
        confidence_multiplier = 1.0
    elif research_confidence == "MEDIUM":
        # Medium confidence: reduce by 10%
        confidence_multiplier = 0.9
    elif research_confidence == "LOW":
        # Low confidence: reduce by 30% (be more conservative)
        confidence_multiplier = 0.7
    else:
        # No research: reduce by 20% (be conservative)
        confidence_multiplier = 0.8
    
    return max(0.0, base_kelly * confidence_multiplier)


def get_fair_prob_for_team(
    fair_probs: Dict[str, FairProbabilities],
    game_id: str,
    team: str,
    team_a: str,
    team_b: str
) -> float:
    """
    Get fair probability for a specific team in a game.
    
    Args:
        fair_probs: Dictionary of fair probabilities by game_id
        game_id: Game identifier
        team: Team name we're betting on
        team_a: Name of team A
        team_b: Name of team B
        
    Returns:
        Fair probability for the team (0-1)
    """
    if game_id not in fair_probs:
        logger.warning(f"No fair probabilities found for game_id: {game_id}")
        return 0.5  # Default to neutral
    
    fair = fair_probs[game_id]
    
    # Match team name to team_a or team_b
    # This is a simple matching - may need more sophisticated logic
    if team.lower() in team_a.lower() or team_a.lower() in team.lower():
        return fair.team_a_fair_prob
    elif team.lower() in team_b.lower() or team_b.lower() in team.lower():
        return fair.team_b_fair_prob
    else:
        logger.warning(
            f"Could not match team '{team}' to '{team_a}' or '{team_b}' "
            f"for game_id: {game_id}. Using average."
        )
        return (fair.team_a_fair_prob + fair.team_b_fair_prob) / 2

