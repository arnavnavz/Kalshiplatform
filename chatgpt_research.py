"""
OpenAI ChatGPT API integration for game research.
Uses ChatGPT to analyze teams, players, and game outcomes.
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
class ChatGPTAnalysis:
    """Analysis result from ChatGPT API."""
    summary: str
    key_factors: List[str]
    prediction: Optional[str] = None
    confidence: Optional[str] = None
    
    def __post_init__(self):
        if self.key_factors is None:
            self.key_factors = []


class ChatGPTResearcher:
    """Uses OpenAI ChatGPT API to research games and provide insights."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize ChatGPT researcher.
        
        Args:
            api_key: OpenAI API key (or from OPENAI_API_KEY env var)
            model: Model to use (gpt-4o-mini, gpt-4o, gpt-4-turbo, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. ChatGPT research will be disabled.")
    
    def research_game(self, game: Game) -> Optional[ChatGPTAnalysis]:
        """
        Research a game using ChatGPT API.
        
        Args:
            game: Game object to research
            
        Returns:
            ChatGPTAnalysis with insights, or None if API unavailable
        """
        if not self.api_key:
            return None
        
        try:
            # Construct query for ChatGPT
            query = self._build_query(game)
            
            logger.info(f"Querying ChatGPT for {game.team_a} vs {game.team_b} ({game.league})")
            
            # Call OpenAI API
            response = self._call_api(query)
            
            if response:
                # Parse response
                analysis = self._parse_response(response, game)
                return analysis
            else:
                logger.warning("No response from ChatGPT API")
                return None
                
        except Exception as e:
            logger.error(f"Error researching game with ChatGPT: {e}", exc_info=True)
            return None
    
    def _build_query(self, game: Game) -> str:
        """
        Build a research query for ChatGPT.
        
        Args:
            game: Game object
            
        Returns:
            Query string
        """
        # Format game time
        game_time_str = game.start_time.strftime("%B %d, %Y at %I:%M %p") if game.start_time else "upcoming"
        current_date = game.start_time.strftime("%Y-%m-%d") if game.start_time else "today"
        
        query = f"""IMPORTANT: Use web search or your knowledge cutoff to find CURRENT data for {current_date}. Do NOT use outdated data from 2023 or earlier.

Analyze the upcoming {game.league} game between {game.team_a} and {game.team_b} scheduled for {game_time_str}.

Use CURRENT, REAL-TIME data from:
- Recent games (last 5-10 matches)
- Current season statistics
- Latest injury reports
- Recent form and performance trends
- Head-to-head records from recent seasons

Provide a comprehensive technical analysis including:

1. Recent Performance & Form: Analyze the last 5-10 games for both teams with specific statistics:
   - Win-loss record and win percentage
   - Points scored/allowed per game
   - Offensive and defensive efficiency ratings
   - Recent form trend (improving/declining)

2. Head-to-Head Analysis: 
   - Historical matchups and recent results
   - Trends in head-to-head performance
   - Any patterns or advantages

3. Key Players & Injuries:
   - Star players and their current form/statistics
   - Injury reports and player availability
   - Impact of missing key players
   - Player matchups that could be decisive

4. Team Statistics & Technical Indicators:
   - Win-loss records and winning percentage
   - Points scored/allowed per game
   - Offensive and defensive rankings
   - Home/away splits and performance
   - Strength of schedule
   - Recent momentum indicators

5. Advanced Metrics (if available):
   - Offensive/defensive efficiency
   - Pace of play
   - Turnover rates
   - Three-point shooting (for basketball)
   - Any other relevant advanced statistics

6. Key Factors: List 3-5 specific technical factors that could influence the outcome with data to support each

7. Prediction & Win Probability: 
   - Which team is more likely to win
   - Provide a win probability estimate (as a percentage)
   - Clear reasoning based on all the technical indicators above

Be specific with statistics, use current/real data, and provide concrete technical reasons for your analysis. Focus on data-driven insights rather than general observations."""
        
        return query
    
    def _call_api(self, query: str) -> Optional[Dict]:
        """
        Call OpenAI ChatGPT API.
        
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
            
            # Use GPT-4o or GPT-4-turbo if available (they have better knowledge cutoff)
            # GPT-4o has knowledge cutoff of April 2024, GPT-4-turbo is April 2023
            # For real-time data, consider using GPT-4o with web browsing or Perplexity API
            model_to_use = self.model
            if model_to_use == "gpt-4o-mini":
                # Try to use a model with better knowledge cutoff if available
                model_to_use = "gpt-4o"  # Better knowledge cutoff
            
            payload = {
                "model": model_to_use,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert sports analyst with access to current data. Provide detailed, data-driven analysis of sports games with specific statistics, CURRENT information (not data from 2023 or earlier), and clear reasoning. If you don't have current data, clearly state that and use the most recent data available. Focus on real, verifiable statistics and recent performance."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more factual, consistent responses
                "max_tokens": 2500  # Increased for more detailed analysis
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ChatGPT API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"API Error details: {error_detail}")
                except:
                    logger.error(f"API Error response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling ChatGPT API: {e}")
            return None
    
    def _parse_response(self, response: Dict, game: Game) -> ChatGPTAnalysis:
        """
        Parse ChatGPT API response.
        
        Args:
            response: API response dict
            game: Game object
            
        Returns:
            ChatGPTAnalysis object
        """
        try:
            # Extract content from response
            content = ""
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "")
            
            # Parse key factors and prediction from content
            key_factors = self._extract_key_factors(content)
            prediction = self._extract_prediction(content, game)
            confidence = self._extract_confidence(content)
            
            # Try to extract win probability for team_a
            win_prob = self._extract_win_probability(content)
            
            analysis = ChatGPTAnalysis(
                summary=content,
                key_factors=key_factors,
                prediction=prediction,
                confidence=confidence
            )
            
            # Store win probability in a way we can access it
            if win_prob is not None:
                # Store in summary for now, we'll extract it in research.py
                analysis.summary = f"[WIN_PROB:{win_prob:.4f}] " + analysis.summary
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing ChatGPT response: {e}")
            # Return basic analysis with raw content
            return ChatGPTAnalysis(
                summary=content if 'content' in locals() else "Analysis unavailable",
                key_factors=[]
            )
    
    def _extract_key_factors(self, content: str) -> List[str]:
        """
        Extract key factors from ChatGPT response.
        
        Args:
            content: Response content
            
        Returns:
            List of key factors
        """
        factors = []
        
        # Look for numbered lists or bullet points
        lines = content.split('\n')
        in_factors_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if we're in a "Key Factors" section
            if "key factor" in line.lower() or "factor" in line.lower():
                in_factors_section = True
                continue
            
            # Check for numbered items (1., 2., etc.) or bullets (-, •)
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                line.startswith(('-', '•', '*'))) and len(line) > 10:
                # Clean up the line
                factor = line.lstrip('123456789.-•* ').strip()
                if factor and len(factor) > 10:  # Ensure it's substantial
                    factors.append(factor)
                    if len(factors) >= 5:  # Limit to 5 factors
                        break
        
        # If no structured factors found, extract sentences with key terms
        if not factors:
            key_terms = ['win', 'loss', 'injury', 'form', 'record', 'performance', 'advantage', 'strength', 'weakness']
            sentences = content.split('.')
            for sentence in sentences:
                if any(term in sentence.lower() for term in key_terms) and len(sentence) > 20:
                    factors.append(sentence.strip())
                    if len(factors) >= 5:
                        break
        
        return factors[:5]  # Return top 5 factors
    
    def _extract_win_probability(self, content: str) -> Optional[float]:
        """
        Extract win probability from ChatGPT response.
        
        Args:
            content: Response content
            
        Returns:
            Win probability (0-1) or None
        """
        import re
        
        # Look for percentage patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability|likely)',
            r'win\s*probability[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*to\s*win',
            r'probability[:\s]+(\d+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    prob = float(matches[0]) / 100.0
                    if 0 <= prob <= 1:
                        return prob
                except ValueError:
                    continue
        
        return None
    
    def _extract_prediction(self, content: str, game: Game) -> Optional[str]:
        """
        Extract prediction from ChatGPT response.
        
        Args:
            content: Response content
            game: Game object
            
        Returns:
            Prediction string or None
        """
        content_lower = content.lower()
        
        # Look for "Prediction" section
        prediction_section = None
        if "prediction" in content_lower:
            idx = content_lower.find("prediction")
            # Get text after "prediction" (next 500 chars)
            prediction_section = content[idx:idx+500]
        
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
                f"pick {team_lower}",
                f"{team_lower} to win"
            ]
            
            search_text = prediction_section if prediction_section else content_lower
            for pattern in patterns:
                if pattern in search_text:
                    # Extract surrounding context
                    idx = search_text.find(pattern)
                    start = max(0, idx - 100)
                    end = min(len(search_text), idx + len(pattern) + 300)
                    prediction = search_text[start:end].strip()
                    return prediction
        
        # If no specific prediction found, return the prediction section if it exists
        if prediction_section:
            return prediction_section.strip()
        
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
        
        if any(word in content_lower for word in ['strongly', 'clearly', 'definitely', 'confident', 'highly likely']):
            return "HIGH"
        elif any(word in content_lower for word in ['likely', 'probably', 'should', 'favor', 'expected']):
            return "MEDIUM"
        elif any(word in content_lower for word in ['possibly', 'might', 'could', 'uncertain', 'close']):
            return "LOW"
        
        return None
    
    def enhance_research(self, game_research: GameResearch, chatgpt_analysis: ChatGPTAnalysis) -> GameResearch:
        """
        Enhance existing research with ChatGPT insights.
        
        Args:
            game_research: Existing GameResearch object
            chatgpt_analysis: ChatGPT analysis
            
        Returns:
            Enhanced GameResearch object
        """
        # Add ChatGPT factors to key factors
        if chatgpt_analysis.key_factors:
            game_research.key_factors.extend(chatgpt_analysis.key_factors)
        
        # Enhance reasoning with ChatGPT summary
        if chatgpt_analysis.summary:
            chatgpt_reasoning = f"ChatGPT Analysis: {chatgpt_analysis.summary[:800]}"
            if chatgpt_analysis.prediction:
                chatgpt_reasoning += f" Prediction: {chatgpt_analysis.prediction}"
            
            # Append to existing reasoning
            if game_research.reasoning:
                game_research.reasoning += f" {chatgpt_reasoning}"
            else:
                game_research.reasoning = chatgpt_reasoning
        
        return game_research

