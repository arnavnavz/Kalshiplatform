"""
Perplexity Pro API integration for game research.
Uses Perplexity AI to analyze teams, players, and game outcomes.
"""
import logging
import os
import requests
from typing import Optional, Dict, List
from dataclasses import dataclass
import json

from models import Game
from research import GameResearch

logger = logging.getLogger(__name__)


@dataclass
class PerplexityAnalysis:
    """Analysis result from Perplexity API."""
    summary: str
    key_factors: List[str]
    prediction: Optional[str] = None
    confidence: Optional[str] = None
    sources: List[str] = None
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class PerplexityResearcher:
    """Uses Perplexity Pro API to research games and provide insights."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity researcher.
        
        Args:
            api_key: Perplexity API key (or from PERPLEXITY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set. Perplexity research will be disabled.")
    
    def research_game(self, game: Game) -> Optional[PerplexityAnalysis]:
        """
        Research a game using Perplexity API.
        
        Args:
            game: Game object to research
            
        Returns:
            PerplexityAnalysis with insights, or None if API unavailable
        """
        if not self.api_key:
            return None
        
        try:
            # Construct query for Perplexity
            query = self._build_query(game)
            
            logger.info(f"Querying Perplexity for {game.team_a} vs {game.team_b} ({game.league})")
            
            # Call Perplexity API
            response = self._call_api(query)
            
            if response:
                # Parse response
                analysis = self._parse_response(response, game)
                return analysis
            else:
                logger.warning("No response from Perplexity API")
                return None
                
        except Exception as e:
            logger.error(f"Error researching game with Perplexity: {e}", exc_info=True)
            return None
    
    def _build_query(self, game: Game) -> str:
        """
        Build a research query for Perplexity.
        
        Args:
            game: Game object
            
        Returns:
            Query string
        """
        # Format game time
        game_time_str = game.start_time.strftime("%B %d, %Y at %I:%M %p") if game.start_time else "upcoming"
        current_date = game.start_time.strftime("%Y-%m-%d") if game.start_time else "today"
        
        query = f"""Analyze the upcoming {game.league} match between {game.team_a} and {game.team_b} scheduled for {game_time_str} (current date: {current_date}).

Provide a structured analysis with CURRENT, REAL-TIME data:

**1. {game.team_a} Analysis:**
- Current season record (wins, losses, draws) and league position
- Last 5-10 games: results, goals scored/allowed, form trend
- Home/away record and performance
- Key players: current form, recent goals/assists, injury status
- Recent news: transfers, lineup changes, tactical adjustments

**2. {game.team_b} Analysis:**
- Current season record (wins, losses, draws) and league position
- Last 5-10 games: results, goals scored/allowed, form trend
- Home/away record and performance
- Key players: current form, recent goals/assists, injury status
- Recent news: transfers, lineup changes, tactical adjustments

**3. Head-to-Head Analysis:**
- Historical record between these teams
- Last 5 head-to-head matches: results, scores, trends
- Patterns: which team performs better in this matchup

**4. Key Factors:**
- List 5-7 specific factors that will influence the outcome
- Include statistics to support each factor
- Consider: form, injuries, home advantage, motivation, tactical matchups

**5. Prediction & Win Probability:**
- Which team is more likely to win? (Be specific: {game.team_a} or {game.team_b})
- Provide a win probability percentage for {game.team_a} (format: "WIN_PROB: XX%")
- Clear reasoning based on all factors above

**Format Requirements:**
- Use specific numbers and statistics
- Separate analysis for each team clearly
- Include current season data (2024-25 or 2025-26 season)
- Cite recent games and performances
- Be data-driven, not speculative

Focus on CURRENT data from the most recent games and current season statistics."""
        
        return query
    
    def _call_api(self, query: str) -> Optional[Dict]:
        """
        Call Perplexity API.
        
        Args:
            query: Research query
            
        Returns:
            API response as dict, or None if error
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use correct Perplexity model names
            # Available models: sonar, sonar-pro, sonar-reasoning, sonar-reasoning-pro
            # sonar-pro is better for complex analysis, sonar is faster
            payload = {
                "model": "sonar-pro",  # Pro model for better analysis quality
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert sports analyst. Provide detailed, data-driven analysis with CURRENT statistics from the most recent games and current season. Structure your response clearly with separate sections for each team. Always include specific numbers, records, and recent performance data. End with a clear prediction and win probability in the format: WIN_PROB: XX% for [team name]."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.1,  # Very low temperature for factual, consistent responses
                "max_tokens": 3000  # Increased for more detailed analysis
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"API Error details: {error_detail}")
                    print(f"API Error: {error_detail}")  # Also print for visibility
                except:
                    logger.error(f"API Error response: {e.response.text}")
                    print(f"API Error: {e.response.text}")  # Also print for visibility
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Perplexity API: {e}")
            return None
    
    def _parse_response(self, response: Dict, game: Game) -> PerplexityAnalysis:
        """
        Parse Perplexity API response.
        
        Args:
            response: API response dict
            game: Game object
            
        Returns:
            PerplexityAnalysis object
        """
        try:
            # Extract content from response
            content = ""
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations/sources if available
            sources = []
            if "citations" in response:
                sources = response["citations"]
            elif "choices" in response and len(response["choices"]) > 0:
                # Try to extract from message
                message = response["choices"][0].get("message", {})
                if "citations" in message:
                    sources = message["citations"]
            
            # Parse key factors and prediction from content
            key_factors = self._extract_key_factors(content)
            prediction = self._extract_prediction(content, game)
            confidence = self._extract_confidence(content)
            
            return PerplexityAnalysis(
                summary=content,
                key_factors=key_factors,
                prediction=prediction,
                confidence=confidence,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {e}")
            # Return basic analysis with raw content
            return PerplexityAnalysis(
                summary=content if 'content' in locals() else "Analysis unavailable",
                key_factors=[],
                sources=sources if 'sources' in locals() else []
            )
    
    def _extract_key_factors(self, content: str) -> List[str]:
        """
        Extract key factors from Perplexity response.
        
        Args:
            content: Response content
            
        Returns:
            List of key factors
        """
        factors = []
        
        # Look for numbered lists or bullet points
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # Check for numbered items (1., 2., etc.) or bullets (-, •)
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                line.startswith(('-', '•', '*'))) and len(line) > 10:
                # Clean up the line
                factor = line.lstrip('123456789.-•* ').strip()
                if factor:
                    factors.append(factor)
        
        # If no structured factors found, extract sentences with key terms
        if not factors:
            key_terms = ['win', 'loss', 'injury', 'form', 'record', 'performance', 'advantage']
            sentences = content.split('.')
            for sentence in sentences:
                if any(term in sentence.lower() for term in key_terms) and len(sentence) > 20:
                    factors.append(sentence.strip())
                    if len(factors) >= 5:  # Limit to 5 factors
                        break
        
        return factors[:5]  # Return top 5 factors
    
    def _extract_prediction(self, content: str, game: Game) -> Optional[str]:
        """
        Extract prediction from Perplexity response.
        
        Args:
            content: Response content
            game: Game object
            
        Returns:
            Prediction string or None
        """
        content_lower = content.lower()
        
        # Look for phrases indicating prediction
        for team in [game.team_a, game.team_b]:
            team_lower = team.lower()
            # Check for phrases like "X is likely to win", "X should win", etc.
            patterns = [
                f"{team_lower} is likely to win",
                f"{team_lower} should win",
                f"{team_lower} will win",
                f"{team_lower} is favored",
                f"{team_lower} has the advantage",
                f"favor {team_lower}",
                f"pick {team_lower}"
            ]
            
            for pattern in patterns:
                if pattern in content_lower:
                    # Extract surrounding context
                    idx = content_lower.find(pattern)
                    start = max(0, idx - 100)
                    end = min(len(content), idx + len(pattern) + 200)
                    prediction = content[start:end].strip()
                    return prediction
        
        return None
    
    def _extract_confidence(self, content: str) -> Optional[str]:
        """
        Extract confidence level from response.
        
        Args:
            content: Response content
            
        Returns:
            Confidence level (HIGH, MEDIUM, LOW) or None
        """
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['strongly', 'clearly', 'definitely', 'confident']):
            return "HIGH"
        elif any(word in content_lower for word in ['likely', 'probably', 'should', 'favor']):
            return "MEDIUM"
        elif any(word in content_lower for word in ['possibly', 'might', 'could', 'uncertain']):
            return "LOW"
        
        return None
    
    def enhance_research(self, game_research: GameResearch, perplexity_analysis: PerplexityAnalysis) -> GameResearch:
        """
        Enhance existing research with Perplexity insights.
        
        Args:
            game_research: Existing GameResearch object
            perplexity_analysis: Perplexity analysis
            
        Returns:
            Enhanced GameResearch object
        """
        # Extract win probability from Perplexity if available
        import re
        prob_match = re.search(r'WIN_PROB:\s*(\d+(?:\.\d+)?)\s*%', perplexity_analysis.summary, re.IGNORECASE)
        if prob_match:
            perplexity_prob = float(prob_match.group(1)) / 100.0
            # Update research probability with Perplexity's estimate
            if game_research.research_probability is not None:
                # Weighted: 80% Perplexity (real-time), 20% statistical
                game_research.research_probability = 0.8 * perplexity_prob + 0.2 * game_research.research_probability
            else:
                game_research.research_probability = perplexity_prob
        
        # Add Perplexity factors to key factors (avoid duplicates)
        if perplexity_analysis.key_factors:
            existing_factors = set(game_research.key_factors)
            for factor in perplexity_analysis.key_factors:
                if factor not in existing_factors:
                    game_research.key_factors.append(factor)
        
        # Enhance reasoning with Perplexity summary (full analysis)
        if perplexity_analysis.summary:
            # Use full summary, not truncated
            perplexity_reasoning = f"Perplexity AI Analysis (Real-Time Data): {perplexity_analysis.summary}"
            if perplexity_analysis.prediction:
                perplexity_reasoning += f"\n\nPrediction: {perplexity_analysis.prediction}"
            if perplexity_analysis.confidence:
                perplexity_reasoning += f"\nConfidence: {perplexity_analysis.confidence}"
            
            # Prepend Perplexity analysis (it's more current)
            if game_research.reasoning:
                game_research.reasoning = f"{perplexity_reasoning}\n\n{game_research.reasoning}"
            else:
                game_research.reasoning = perplexity_reasoning
        
        return game_research

