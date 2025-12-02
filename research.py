"""
Team and player research module.
Analyzes team statistics, recent form, injuries, and other factors
to provide insights on game outcomes.
"""
import logging
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

from models import Game
from team_stats_fetcher import TeamStatsFetcher, TeamStats

logger = logging.getLogger(__name__)


@dataclass
class GameResearch:
    """Research analysis for a specific game."""
    game_id: str
    team_a: str
    team_b: str
    league: str
    team_a_stats: Optional[TeamStats] = None
    team_b_stats: Optional[TeamStats] = None
    head_to_head: Optional[str] = None  # Recent H2H record
    home_team: Optional[str] = None
    key_factors: List[str] = None  # List of key factors affecting outcome
    research_probability: Optional[float] = None  # Research-based win probability for team_a
    reasoning: str = ""  # Detailed reasoning for the prediction
    confidence: Optional[str] = None  # Research confidence level: "HIGH", "MEDIUM", "LOW"
    
    def __post_init__(self):
        if self.key_factors is None:
            self.key_factors = []


class ResearchEngine:
    """Fetches and analyzes team/player data to inform betting decisions."""
    
    def __init__(self):
        """Initialize research engine."""
        self.cache: Dict[str, GameResearch] = {}
        self.cache_ttl = timedelta(hours=6)  # Cache research for 6 hours
        self.stats_fetcher = TeamStatsFetcher()
        self._perplexity = None  # Lazy load Perplexity (preferred - real-time web data)
        self._chatgpt = None  # Lazy load ChatGPT (fallback - outdated training data)
        
    def research_game(self, game: Game) -> GameResearch:
        """
        Research a game and return analysis.
        
        Args:
            game: Game object to research
            
        Returns:
            GameResearch with analysis and reasoning
        """
        # Check cache
        cache_key = f"{game.game_id}_{game.team_a}_{game.team_b}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Cache is still valid (simplified - in production, check timestamp)
            return cached
        
        logger.info(f"Researching game: {game.team_a} vs {game.team_b} ({game.league})")
        
        # Fetch team statistics
        team_a_stats = self.stats_fetcher.fetch_team_stats(game.team_a, game.league)
        team_b_stats = self.stats_fetcher.fetch_team_stats(game.team_b, game.league)
        
        # Determine home team (simplified - would need venue data)
        home_team = self._determine_home_team(game)
        
        # Analyze key factors
        key_factors = self._analyze_key_factors(
            game, team_a_stats, team_b_stats, home_team
        )
        
        # Calculate research-based probability
        research_prob = self._calculate_research_probability(
            game, team_a_stats, team_b_stats, home_team
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            game, team_a_stats, team_b_stats, home_team, key_factors, research_prob
        )
        
        research = GameResearch(
            game_id=game.game_id,
            team_a=game.team_a,
            team_b=game.team_b,
            league=game.league,
            team_a_stats=team_a_stats,
            team_b_stats=team_b_stats,
            home_team=home_team,
            key_factors=key_factors,
            research_probability=research_prob,
            reasoning=reasoning
        )
        
        # Enhance with AI research - prefer Perplexity (real-time web data) over ChatGPT
        # Perplexity has real-time web access, ChatGPT has outdated training data
        try:
            # Try Perplexity first (has real-time web access)
            if self._perplexity is None:
                try:
                    from perplexity_research import PerplexityResearcher
                    self._perplexity = PerplexityResearcher()
                except ImportError:
                    self._perplexity = None
            
            if self._perplexity and self._perplexity.api_key:
                perplexity_analysis = self._perplexity.research_game(game)
                if perplexity_analysis:
                    # Extract win probability from Perplexity if available
                    import re
                    prob_match = re.search(r'\[WIN_PROB:([\d.]+)\]', perplexity_analysis.summary)
                    if prob_match:
                        perplexity_prob = float(prob_match.group(1))
                        # Update research probability with Perplexity's estimate (weighted average)
                        if research.research_probability is not None:
                            # Combine: 70% Perplexity (real-time), 30% statistical
                            research.research_probability = 0.7 * perplexity_prob + 0.3 * research.research_probability
                        else:
                            research.research_probability = perplexity_prob
                        logger.info(f"Perplexity win probability: {perplexity_prob:.2%} for {game.team_a}")
                    
                    research = self._perplexity.enhance_research(research, perplexity_analysis)
                    # Extract confidence from Perplexity analysis
                    if perplexity_analysis.confidence:
                        research.confidence = perplexity_analysis.confidence
                    logger.info(f"Enhanced research with Perplexity AI (real-time) insights for {game.team_a} vs {game.team_b}")
        except Exception as e:
            logger.warning(f"Failed to get Perplexity research: {e}")
        
        # Fallback to ChatGPT if Perplexity not available
        try:
            if self._chatgpt is None:
                from chatgpt_research import ChatGPTResearcher
                self._chatgpt = ChatGPTResearcher()
            
            # Only use ChatGPT if Perplexity didn't provide analysis
            if not (self._perplexity and self._perplexity.api_key):
                chatgpt_analysis = self._chatgpt.research_game(game)
                if chatgpt_analysis:
                    # Extract win probability from ChatGPT if available
                    import re
                    prob_match = re.search(r'\[WIN_PROB:([\d.]+)\]', chatgpt_analysis.summary)
                    if prob_match:
                        chatgpt_prob = float(prob_match.group(1))
                        # Update research probability with ChatGPT's estimate (weighted average)
                        if research.research_probability is not None:
                            # Combine: 60% ChatGPT, 40% statistical
                            research.research_probability = 0.6 * chatgpt_prob + 0.4 * research.research_probability
                        else:
                            research.research_probability = chatgpt_prob
                        logger.info(f"ChatGPT win probability: {chatgpt_prob:.2%} for {game.team_a}")
                    
                    research = self._chatgpt.enhance_research(research, chatgpt_analysis)
                    # Extract confidence from ChatGPT analysis
                    if chatgpt_analysis.confidence and not research.confidence:
                        research.confidence = chatgpt_analysis.confidence
                    logger.info(f"Enhanced research with ChatGPT AI insights for {game.team_a} vs {game.team_b}")
        except Exception as e:
            logger.warning(f"Failed to get ChatGPT research: {e}")
        
        # Cache result
        self.cache[cache_key] = research
        
        return research
    
    
    def _determine_home_team(self, game: Game) -> Optional[str]:
        """
        Determine which team is playing at home.
        
        Args:
            game: Game object
            
        Returns:
            Home team name or None if unknown
        """
        # This would need venue information from Kalshi or another source
        # For now, return None (neutral)
        return None
    
    def _analyze_key_factors(
        self,
        game: Game,
        team_a_stats: TeamStats,
        team_b_stats: TeamStats,
        home_team: Optional[str]
    ) -> List[str]:
        """
        Analyze key factors that could affect the game outcome.
        
        Args:
            game: Game object
            team_a_stats: Statistics for team A
            team_b_stats: Statistics for team B
            home_team: Home team name or None
            
        Returns:
            List of key factors
        """
        factors = []
        
        # Win percentage comparison
        if team_a_stats.win_percentage > team_b_stats.win_percentage + 0.1:
            factors.append(f"{game.team_a} has significantly better record ({team_a_stats.win_percentage:.1%} vs {team_b_stats.win_percentage:.1%})")
        elif team_b_stats.win_percentage > team_a_stats.win_percentage + 0.1:
            factors.append(f"{game.team_b} has significantly better record ({team_b_stats.win_percentage:.1%} vs {team_a_stats.win_percentage:.1%})")
        
        # Recent form
        if team_a_stats.recent_form:
            a_wins = team_a_stats.recent_form.count('W')
            b_wins = team_b_stats.recent_form.count('W') if team_b_stats.recent_form else 0
            if a_wins > b_wins + 1:
                factors.append(f"{game.team_a} in better recent form ({team_a_stats.recent_form})")
            elif b_wins > a_wins + 1:
                factors.append(f"{game.team_b} in better recent form ({team_b_stats.recent_form})")
        
        # Home advantage
        if home_team:
            if home_team == game.team_a:
                factors.append(f"{game.team_a} playing at home (home advantage)")
            elif home_team == game.team_b:
                factors.append(f"{game.team_b} playing at home (home advantage)")
        
        # Injuries
        if team_a_stats.injuries:
            factors.append(f"{game.team_a} has injuries: {', '.join(team_a_stats.injuries)}")
        if team_b_stats.injuries:
            factors.append(f"{game.team_b} has injuries: {', '.join(team_b_stats.injuries)}")
        
        # Offensive/defensive stats
        if team_a_stats.points_per_game > 0 and team_b_stats.points_allowed_per_game > 0:
            if team_a_stats.points_per_game > team_b_stats.points_allowed_per_game + 5:
                factors.append(f"{game.team_a} strong offense vs {game.team_b} weaker defense")
        
        return factors
    
    def _calculate_research_probability(
        self,
        game: Game,
        team_a_stats: TeamStats,
        team_b_stats: TeamStats,
        home_team: Optional[str]
    ) -> float:
        """
        Calculate win probability for team A based on research.
        
        Args:
            game: Game object
            team_a_stats: Statistics for team A
            team_b_stats: Statistics for team B
            home_team: Home team name or None
            
        Returns:
            Win probability for team A (0-1)
        """
        # Start with win percentage
        total_win_pct = team_a_stats.win_percentage + team_b_stats.win_percentage
        if total_win_pct > 0:
            base_prob = team_a_stats.win_percentage / total_win_pct
        else:
            # If no data, default to 50/50
            base_prob = 0.5
        
        # Adjust for home advantage (typically +3-4% for home team)
        if home_team == game.team_a:
            base_prob += 0.04
        elif home_team == game.team_b:
            base_prob -= 0.04
        
        # Adjust for recent form
        if team_a_stats.recent_form:
            a_wins = team_a_stats.recent_form.count('W')
            b_wins = team_b_stats.recent_form.count('W') if team_b_stats.recent_form else 0
            form_diff = (a_wins - b_wins) / 5.0  # Normalize to -1 to 1
            base_prob += form_diff * 0.05  # Max 5% adjustment
        
        # Adjust for injuries (reduce probability if key players out)
        if team_a_stats.injuries:
            base_prob -= len(team_a_stats.injuries) * 0.02  # -2% per injury
        if team_b_stats.injuries:
            base_prob += len(team_b_stats.injuries) * 0.02
        
        # Clamp to reasonable range
        return max(0.2, min(0.8, base_prob))
    
    def _generate_reasoning(
        self,
        game: Game,
        team_a_stats: TeamStats,
        team_b_stats: TeamStats,
        home_team: Optional[str],
        key_factors: List[str],
        research_prob: float
    ) -> str:
        """
        Generate detailed reasoning for the prediction.
        
        Args:
            game: Game object
            team_a_stats: Statistics for team A
            team_b_stats: Statistics for team B
            home_team: Home team name or None
            key_factors: List of key factors
            research_prob: Research-based probability for team A
            
        Returns:
            Detailed reasoning string
        """
        reasoning_parts = []
        
        # Overall assessment
        if research_prob > 0.6:
            favored_team = game.team_a
            confidence = "strongly"
        elif research_prob > 0.55:
            favored_team = game.team_a
            confidence = "slightly"
        elif research_prob < 0.4:
            favored_team = game.team_b
            confidence = "strongly"
        elif research_prob < 0.45:
            favored_team = game.team_b
            confidence = "slightly"
        else:
            reasoning_parts.append("This is a closely matched game with no clear favorite.")
            if key_factors:
                reasoning_parts.append(f"Key factors: {'; '.join(key_factors)}")
            return " ".join(reasoning_parts)
        
        reasoning_parts.append(f"{favored_team} is {confidence} favored based on research.")
        
        # Add key factors
        if key_factors:
            reasoning_parts.append(f"Key factors: {'; '.join(key_factors)}")
        
        # Add record comparison
        if team_a_stats.wins > 0 or team_b_stats.wins > 0:
            reasoning_parts.append(
                f"{game.team_a} record: {team_a_stats.wins}-{team_a_stats.losses} "
                f"({team_a_stats.win_percentage:.1%}); "
                f"{game.team_b} record: {team_b_stats.wins}-{team_b_stats.losses} "
                f"({team_b_stats.win_percentage:.1%})"
            )
        
        # Add recent form
        if team_a_stats.recent_form or team_b_stats.recent_form:
            form_str = f"{game.team_a} recent: {team_a_stats.recent_form or 'N/A'}; "
            form_str += f"{game.team_b} recent: {team_b_stats.recent_form or 'N/A'}"
            reasoning_parts.append(form_str)
        
        return " ".join(reasoning_parts)

