# Perplexity Pro API Setup Guide

## Overview

The bot now uses Perplexity Pro API to provide AI-powered research and analysis on games, teams, and players. This enhances betting decisions with real-time insights, statistics, and predictions.

## Setup Instructions

### 1. Get Perplexity Pro API Key

1. **Subscribe to Perplexity Pro**: 
   - Visit https://www.perplexity.ai/
   - Subscribe to Perplexity Pro (includes $5 in monthly API credits)

2. **Get Your API Key**:
   - Go to https://www.perplexity.ai/settings/api
   - Copy your API key

### 2. Add API Key to Environment

Add your Perplexity API key to `.env.local`:

```bash
PERPLEXITY_API_KEY=your_api_key_here
```

**Important**: Add this to `.env.local` (not `.env`) to keep it secure and out of version control.

### 3. Verify Setup

Test the integration:

```bash
python3 -c "from perplexity_research import PerplexityResearcher; print('Perplexity module loaded successfully')"
```

## How It Works

### Research Process

For each game, the bot:

1. **Fetches Basic Stats**: Gets team records, recent form, etc.
2. **Queries Perplexity AI**: Asks Perplexity to analyze:
   - Recent performance and form
   - Head-to-head records
   - Key players and injuries
   - Team statistics
   - Home/away performance
   - Prediction and reasoning

3. **Enhances Research**: Combines Perplexity insights with statistical analysis
4. **Includes in Trades**: Research reasoning is automatically added to trade logs

### Example Query

The bot sends queries like:

```
Analyze the upcoming NBA game between Los Angeles Lakers and Golden State Warriors 
scheduled for November 18, 2025 at 7:30 PM.

Please provide:
1. Recent performance and form for both teams (last 5-10 games)
2. Head-to-head record and recent matchups
3. Key players and their current status (injuries, form)
4. Team statistics (win-loss record, points scored/allowed, etc.)
5. Home/away performance if applicable
6. Any other relevant factors that could affect the outcome
7. Your prediction on which team is more likely to win and why
```

### Example Output

Research reasoning in trade logs will include:

```
Strong edge: Kalshi prices Lakers at 45.0% but fair value is 65.0% (edge: 20.0%). 
Research: Lakers is strongly favored based on research. 
Key factors: Lakers has significantly better record (70.6% vs 47.1%); 
Lakers in better recent form (WWLWW); Lakers playing at home (home advantage). 
Perplexity AI Analysis: The Los Angeles Lakers have been in excellent form recently, 
winning 8 of their last 10 games. Key player LeBron James is healthy and averaging 
28.5 points per game. The Warriors are struggling on the road with a 3-7 away record. 
The Lakers have won 3 of the last 4 head-to-head matchups. Prediction: Lakers should 
win this game with their home court advantage and superior recent form.
```

## API Usage & Costs

- **Perplexity Pro**: Includes $5 in monthly API credits
- **Cost per Query**: Approximately $0.001-0.01 per game research (varies by query length)
- **Estimated Usage**: ~500-5000 game analyses per month with $5 credit

The bot caches research results to minimize API calls.

## Configuration

The Perplexity integration is **automatically enabled** when `PERPLEXITY_API_KEY` is set.

If the API key is not set, the bot will:
- Continue to work normally
- Skip Perplexity research
- Use only statistical analysis
- Log a warning message

## Troubleshooting

### API Key Not Working

1. Verify the key is correct in `.env.local`
2. Check that you have an active Perplexity Pro subscription
3. Verify API credits are available
4. Check logs for specific error messages

### No Research in Logs

1. Ensure `PERPLEXITY_API_KEY` is set
2. Check that the API key is valid
3. Verify you have API credits remaining
4. Check bot logs for errors

### Rate Limiting

If you hit rate limits:
- The bot will log warnings and continue
- Research will be skipped for that game
- The bot will retry on the next iteration

## Advanced Configuration

To customize Perplexity queries, edit `perplexity_research.py`:

- Modify `_build_query()` to change the research questions
- Adjust `temperature` in `_call_api()` for more/less creative responses
- Change `max_tokens` to get longer/shorter analyses

## Support

For Perplexity API issues:
- Perplexity API Docs: https://docs.perplexity.ai/
- Perplexity Support: https://www.perplexity.ai/help

