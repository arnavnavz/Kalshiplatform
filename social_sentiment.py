"""
Social sentiment analysis module.
Scans Twitter, Reddit, and news for team/game sentiment.
"""
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class SocialSentimentAnalyzer:
    """Analyzes social media and news sentiment for teams/games."""
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        
    def analyze_game_sentiment(self, team_a: str, team_b: str, league: str) -> Dict:
        """
        Analyze social sentiment for a game.
        
        Returns:
            Dict with sentiment scores and sources
        """
        result = {
            'team_a_sentiment': None,
            'team_b_sentiment': None,
            'overall_sentiment': None,
            'sources': [],
            'tweets': [],
            'reddit_posts': [],
            'news_articles': []
        }
        
        # Twitter sentiment
        try:
            twitter_data = self._get_twitter_sentiment(team_a, team_b, league)
            if twitter_data:
                result['team_a_sentiment'] = twitter_data.get('team_a_score')
                result['team_b_sentiment'] = twitter_data.get('team_b_score')
                result['tweets'] = twitter_data.get('tweets', [])
                result['sources'].append('Twitter')
        except Exception as e:
            logger.debug(f"Twitter sentiment failed: {e}")
        
        # Reddit sentiment
        try:
            reddit_data = self._get_reddit_sentiment(team_a, team_b, league)
            if reddit_data:
                if result['team_a_sentiment'] is None:
                    result['team_a_sentiment'] = reddit_data.get('team_a_score')
                else:
                    # Average with Twitter
                    result['team_a_sentiment'] = (result['team_a_sentiment'] + reddit_data.get('team_a_score', 0)) / 2
                
                if result['team_b_sentiment'] is None:
                    result['team_b_sentiment'] = reddit_data.get('team_b_score')
                else:
                    result['team_b_sentiment'] = (result['team_b_sentiment'] + reddit_data.get('team_b_score', 0)) / 2
                
                result['reddit_posts'] = reddit_data.get('posts', [])
                result['sources'].append('Reddit')
        except Exception as e:
            logger.debug(f"Reddit sentiment failed: {e}")
        
        # News sentiment
        try:
            news_data = self._get_news_sentiment(team_a, team_b, league)
            if news_data:
                result['news_articles'] = news_data.get('articles', [])
                result['sources'].append('News')
        except Exception as e:
            logger.debug(f"News sentiment failed: {e}")
        
        # Calculate overall sentiment
        if result['team_a_sentiment'] is not None and result['team_b_sentiment'] is not None:
            if result['team_a_sentiment'] > result['team_b_sentiment']:
                result['overall_sentiment'] = f"Favors {team_a}"
            elif result['team_b_sentiment'] > result['team_a_sentiment']:
                result['overall_sentiment'] = f"Favors {team_b}"
            else:
                result['overall_sentiment'] = "Neutral"
        
        return result
    
    def _get_twitter_sentiment(self, team_a: str, team_b: str, league: str) -> Optional[Dict]:
        """Get Twitter sentiment using Twitter API v2."""
        if not self.twitter_bearer_token:
            return None
        
        try:
            headers = {"Authorization": f"Bearer {self.twitter_bearer_token}"}
            
            # Search for team mentions
            query_a = f"{team_a} {league}"
            query_b = f"{team_b} {league}"
            
            # Get recent tweets (last 7 days)
            url = "https://api.twitter.com/2/tweets/search/recent"
            params_a = {
                "query": query_a,
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics,text"
            }
            
            response_a = requests.get(url, headers=headers, params=params_a, timeout=5)
            if response_a.status_code == 200:
                tweets_a = response_a.json().get('data', [])
                # Simple sentiment: positive if more likes/retweets
                score_a = sum(t.get('public_metrics', {}).get('like_count', 0) for t in tweets_a) / max(len(tweets_a), 1)
            else:
                tweets_a = []
                score_a = 0.5  # Neutral
            
            params_b = {
                "query": query_b,
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics,text"
            }
            
            response_b = requests.get(url, headers=headers, params=params_b, timeout=5)
            if response_b.status_code == 200:
                tweets_b = response_b.json().get('data', [])
                score_b = sum(t.get('public_metrics', {}).get('like_count', 0) for t in tweets_b) / max(len(tweets_b), 1)
            else:
                tweets_b = []
                score_b = 0.5
            
            # Normalize scores (0-1 scale)
            max_score = max(score_a, score_b, 1)
            score_a_norm = score_a / max_score if max_score > 0 else 0.5
            score_b_norm = score_b / max_score if max_score > 0 else 0.5
            
            return {
                'team_a_score': score_a_norm,
                'team_b_score': score_b_norm,
                'tweets': tweets_a[:5] + tweets_b[:5]  # Top 5 from each
            }
        except Exception as e:
            logger.debug(f"Twitter API error: {e}")
            return None
    
    def _get_reddit_sentiment(self, team_a: str, team_b: str, league: str) -> Optional[Dict]:
        """Get Reddit sentiment using Reddit API (PRAW)."""
        try:
            import praw
        except ImportError:
            logger.debug("PRAW not installed. Install with: pip install praw")
            return None
        
        if not self.reddit_client_id or not self.reddit_client_secret:
            # Try without auth (limited)
            reddit = praw.Reddit(
                client_id="public_client",
                client_secret=None,
                user_agent="sports-bot/1.0"
            )
        else:
            reddit = praw.Reddit(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent="sports-bot/1.0"
            )
        
        try:
            # Search relevant subreddits
            subreddits = self._get_league_subreddit(league)
            posts_a = []
            posts_b = []
            
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    # Search for team mentions
                    for post in subreddit.search(f"{team_a}", limit=5, sort='hot'):
                        posts_a.append({
                            'title': post.title,
                            'score': post.score,
                            'url': post.url,
                            'created': datetime.fromtimestamp(post.created_utc).isoformat()
                        })
                    
                    for post in subreddit.search(f"{team_b}", limit=5, sort='hot'):
                        posts_b.append({
                            'title': post.title,
                            'score': post.score,
                            'url': post.url,
                            'created': datetime.fromtimestamp(post.created_utc).isoformat()
                        })
                except:
                    continue
            
            # Calculate sentiment scores based on upvotes
            score_a = sum(p['score'] for p in posts_a) / max(len(posts_a), 1) if posts_a else 0.5
            score_b = sum(p['score'] for p in posts_b) / max(len(posts_b), 1) if posts_b else 0.5
            
            # Normalize
            max_score = max(score_a, score_b, 1)
            score_a_norm = score_a / max_score if max_score > 0 else 0.5
            score_b_norm = score_b / max_score if max_score > 0 else 0.5
            
            return {
                'team_a_score': score_a_norm,
                'team_b_score': score_b_norm,
                'posts': posts_a[:3] + posts_b[:3]
            }
        except Exception as e:
            logger.debug(f"Reddit API error: {e}")
            return None
    
    def _get_news_sentiment(self, team_a: str, team_b: str, league: str) -> Optional[Dict]:
        """Get news sentiment using News API."""
        if not self.news_api_key:
            return None
        
        try:
            url = "https://newsapi.org/v2/everything"
            query = f"{team_a} {team_b} {league}"
            params = {
                "q": query,
                "apiKey": self.news_api_key,
                "sortBy": "publishedAt",
                "pageSize": 10,
                "language": "en"
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                articles = response.json().get('articles', [])
                return {
                    'articles': [
                        {
                            'title': a.get('title', ''),
                            'url': a.get('url', ''),
                            'published': a.get('publishedAt', ''),
                            'source': a.get('source', {}).get('name', '')
                        }
                        for a in articles[:5]
                    ]
                }
        except Exception as e:
            logger.debug(f"News API error: {e}")
            return None
        
        return None
    
    def _get_league_subreddit(self, league: str) -> List[str]:
        """Get relevant subreddits for a league."""
        subreddit_map = {
            "NBA": ["nba", "basketball"],
            "NFL": ["nfl", "fantasyfootball"],
            "EPL": ["soccer", "PremierLeague", "football"],
            "UCL": ["soccer", "championsleague"],
            "La Liga": ["soccer", "laliga"],
            "MLB": ["baseball", "mlb"],
            "NHL": ["hockey", "nhl"]
        }
        return subreddit_map.get(league, ["sports"])

