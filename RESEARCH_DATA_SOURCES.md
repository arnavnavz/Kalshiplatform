# Real-Time Research Data Sources

## Problem
ChatGPT's training data is outdated (cutoff dates vary by model). For current sports data, we need real-time sources.

## Recommended Solutions

### 1. **Perplexity API** (Best for Real-Time Web Data)
- **Why**: Has real-time web search capability
- **Cost**: ~$0.001 per request
- **Setup**: 
  ```bash
  # Add to .env.local
  PERPLEXITY_API_KEY=your_key_here
  ```
- **API**: https://www.perplexity.ai/settings/api
- **Note**: You previously had Perplexity setup - we can re-enable it

### 2. **API-Football** (Soccer/Football)
- **Why**: Comprehensive, real-time soccer data
- **Cost**: Free tier available (100 requests/day)
- **Setup**: https://www.api-football.com/
- **Data**: Live scores, fixtures, statistics, injuries, H2H

### 3. **NBA Stats API** (Basketball)
- **Why**: Official NBA data, free
- **Cost**: Free (no API key needed)
- **Setup**: https://www.nba.com/stats
- **Data**: Team stats, player stats, recent games, injuries

### 4. **ESPN API** (Multiple Sports)
- **Why**: Comprehensive sports coverage
- **Cost**: Free (limited) or paid
- **Setup**: https://www.espn.com/apis/devcenter/
- **Data**: Scores, stats, news, injuries

### 5. **SportsDataIO** (All Sports)
- **Why**: Comprehensive, reliable
- **Cost**: Paid (starts at $10/month)
- **Setup**: https://sportsdata.io/
- **Data**: Real-time stats, injuries, schedules

### 6. **The Odds API** (You Already Have This!)
- **Why**: You're already using it for odds
- **Data**: Some basic stats available
- **Enhancement**: Can extract more data from their responses

### 7. **Web Scraping** (Free but requires maintenance)
- **Sources**: ESPN, BBC Sport, team websites
- **Libraries**: BeautifulSoup, Scrapy
- **Pros**: Free, comprehensive
- **Cons**: Breaks when sites change, legal considerations

### 8. **GPT-4o with Web Browsing** (If Available)
- **Why**: Can search the web in real-time
- **Cost**: Higher than regular GPT-4
- **Setup**: Use `gpt-4o` model with browsing enabled

## Quick Implementation Options

### Option A: Re-enable Perplexity (Fastest)
You already have Perplexity setup code. We can:
1. Re-enable Perplexity API integration
2. Use it for real-time web searches
3. Combine with ChatGPT for analysis

### Option B: Add API-Football (Best for Soccer)
1. Sign up at api-football.com
2. Get free API key
3. Integrate into `team_stats_fetcher.py`
4. Fetch real-time stats, injuries, H2H

### Option C: Add NBA Stats API (Best for NBA)
1. No API key needed
2. Integrate into `team_stats_fetcher.py`
3. Fetch real-time NBA stats

### Option D: Hybrid Approach (Recommended)
1. Use Perplexity for real-time web searches
2. Use API-Football for soccer data
3. Use NBA Stats API for basketball
4. Use ChatGPT to analyze the combined data

## Next Steps

Which option would you like to implement? I recommend:
1. **Re-enable Perplexity** (you already have the code)
2. **Add API-Football** for soccer (free tier is good)
3. **Add NBA Stats API** for basketball (free)

This will give you real-time data for the main sports you're betting on.

