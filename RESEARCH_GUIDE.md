# Team Research Module Guide

## Overview

The research module analyzes teams, players, and recent performance to provide insights on game outcomes. It enhances betting decisions by considering:

- **Team Records**: Win-loss records, win percentages
- **Recent Form**: Last 5 games performance
- **Home/Away Records**: Performance in different venues
- **Injuries**: Key player availability
- **Head-to-Head**: Historical matchups
- **Offensive/Defensive Stats**: Points scored/allowed

## How It Works

1. **Research Engine** (`research.py`): Main analysis engine that:
   - Fetches team statistics
   - Analyzes key factors
   - Calculates research-based win probabilities
   - Generates detailed reasoning

2. **Team Stats Fetcher** (`team_stats_fetcher.py`): Fetches statistics from various sources

3. **Integration**: Research is automatically included in trade reasoning

## Current Status

The research module is **fully integrated** but currently uses placeholder data. To enable real research:

1. **Add Real Data Sources**: Implement `_fetch_nba_stats()`, `_fetch_nfl_stats()`, etc. in `team_stats_fetcher.py`

2. **Available Data Sources**:
   - **NBA Stats API**: Official NBA API (requires registration)
   - **ESPN API**: Sports data (may require API key)
   - **SportsDataIO**: Comprehensive sports data (paid)
   - **Web Scraping**: Scrape from ESPN, NBA.com, etc.
   - **The Odds API**: Some basic stats available

## Example: Adding NBA Stats

Here's how to add real NBA statistics:

```python
def _fetch_nba_stats(self, team_name: str) -> Optional[TeamStats]:
    """Fetch NBA team statistics from NBA Stats API."""
    try:
        # Example using NBA Stats API
        url = "https://stats.nba.com/stats/teamdashboardbygeneralsplits"
        params = {
            "TeamID": self._get_team_id(team_name),
            "Season": "2024-25",
            "SeasonType": "Regular Season"
        }
        
        response = requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nba.com/"
        })
        
        data = response.json()
        # Parse data and return TeamStats
        # ...
        
    except Exception as e:
        logger.error(f"Failed to fetch NBA stats: {e}")
        return None
```

## Research Output

Research is automatically included in trade logs:

```
Strong edge: Kalshi prices Lakers at 45.0% but fair value is 65.0% (edge: 20.0%). 
Research: Lakers is strongly favored based on research. 
Key factors: Lakers has significantly better record (65.0% vs 45.0%); 
Lakers in better recent form (WWLWW); Lakers playing at home (home advantage). 
Lakers record: 12-5 (70.6%); Warriors record: 8-9 (47.1%). 
Lakers recent: WWLWW; Warriors recent: LWLWL
```

## Next Steps

1. **Choose a Data Source**: Select an API or scraping target
2. **Implement Fetchers**: Add real data fetching logic
3. **Test**: Verify data is being fetched correctly
4. **Enhance Analysis**: Add more sophisticated analysis (player matchups, etc.)

## Configuration

Research is automatically enabled. To disable or configure:

- Modify `research.py` to skip research if needed
- Adjust probability calculations in `_calculate_research_probability()`
- Customize reasoning generation in `_generate_reasoning()`

