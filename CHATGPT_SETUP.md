# ChatGPT (OpenAI) API Setup Guide

## Overview

The bot now uses OpenAI's ChatGPT API to provide AI-powered research and analysis on games, teams, and players. This enhances betting decisions with intelligent insights, statistics, and predictions.

## Setup Instructions

### 1. Get OpenAI API Key

1. **Create OpenAI Account**: 
   - Visit https://platform.openai.com/
   - Sign up or log in

2. **Get Your API Key**:
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy your API key (you won't be able to see it again!)

3. **Add Credits**:
   - Go to https://platform.openai.com/account/billing
   - Add payment method and credits
   - Recommended: Start with $10-20 for testing

### 2. Add API Key to Environment

Add your OpenAI API key to `.env.local`:

```bash
OPENAI_API_KEY=sk-your_api_key_here
```

**Important**: Add this to `.env.local` (not `.env`) to keep it secure and out of version control.

### 3. Choose Model (Optional)

You can specify which ChatGPT model to use in `.env.local`:

```bash
OPENAI_MODEL=gpt-4o-mini  # Default: fast and cost-effective
# OR
OPENAI_MODEL=gpt-4o       # More capable, higher cost
# OR
OPENAI_MODEL=gpt-4-turbo  # Latest GPT-4
```

**Model Recommendations**:
- **gpt-4o-mini** (default): Fast, cost-effective, good for most use cases (~$0.15 per 1M input tokens)
- **gpt-4o**: More capable, better reasoning (~$2.50 per 1M input tokens)
- **gpt-4-turbo**: Latest GPT-4, best quality (~$10 per 1M input tokens)

### 4. Verify Setup

Test the integration:

```bash
python3 test_chatgpt.py
```

## How It Works

### Research Process

For each game, the bot:

1. **Fetches Basic Stats**: Gets team records, recent form, etc.
2. **Queries ChatGPT**: Asks ChatGPT to analyze:
   - Recent performance and form (last 5-10 games)
   - Head-to-head records
   - Key players and injuries
   - Team statistics (win-loss, points scored/allowed)
   - Home/away performance
   - Key factors affecting outcome
   - Prediction and reasoning

3. **Enhances Research**: Combines ChatGPT insights with statistical analysis
4. **Includes in Trades**: Research reasoning is automatically added to trade logs

### Example Query

The bot sends queries like:

```
Analyze the upcoming NBA game between Los Angeles Lakers and Golden State Warriors 
scheduled for November 18, 2025 at 7:30 PM.

Please provide a comprehensive analysis including:

1. Recent Performance: Analyze the last 5-10 games for both teams
2. Head-to-Head Record: Historical matchups between these teams
3. Key Players: Identify star players, their current form, and any injury concerns
4. Team Statistics: Win-loss records, points scored/allowed
5. Home/Away Performance: How each team performs at home vs on the road
6. Key Factors: List 3-5 specific factors that could influence the outcome
7. Prediction: Which team is more likely to win and provide clear reasoning
```

### Example Output

Research reasoning in trade logs will include:

```
Strong edge: Kalshi prices Lakers at 45.0% but fair value is 65.0% (edge: 20.0%). 
Research: Lakers is strongly favored based on research. 
Key factors: Lakers has significantly better record (70.6% vs 47.1%); 
Lakers in better recent form (WWLWW); Lakers playing at home (home advantage). 
ChatGPT Analysis: The Los Angeles Lakers have been in excellent form recently, 
winning 8 of their last 10 games. Key player LeBron James is healthy and averaging 
28.5 points per game. The Warriors are struggling on the road with a 3-7 away record. 
The Lakers have won 3 of the last 4 head-to-head matchups. 
Prediction: Lakers should win this game with their home court advantage and 
superior recent form.
```

## API Usage & Costs

### Pricing (as of 2024)

- **gpt-4o-mini**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **gpt-4o**: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- **gpt-4-turbo**: ~$10 per 1M input tokens, ~$30 per 1M output tokens

### Estimated Costs

- **Per game research**: ~500-1000 tokens input, ~1000-2000 tokens output
- **gpt-4o-mini**: ~$0.001-0.002 per game research
- **gpt-4o**: ~$0.015-0.030 per game research

**Example**: With gpt-4o-mini, $10 would cover ~5,000-10,000 game analyses

The bot caches research results to minimize API calls.

## Configuration

The ChatGPT integration is **automatically enabled** when `OPENAI_API_KEY` is set.

If the API key is not set, the bot will:
- Continue to work normally
- Skip ChatGPT research
- Use only statistical analysis
- Log a warning message

## Troubleshooting

### API Key Not Working

1. Verify the key is correct in `.env.local` (should start with `sk-`)
2. Check that you have credits in your OpenAI account
3. Verify the API key hasn't been revoked
4. Check logs for specific error messages

### No Research in Logs

1. Ensure `OPENAI_API_KEY` is set
2. Check that the API key is valid
3. Verify you have credits remaining
4. Check bot logs for errors

### Rate Limiting

If you hit rate limits:
- The bot will log warnings and continue
- Research will be skipped for that game
- The bot will retry on the next iteration
- Consider using gpt-4o-mini for higher rate limits

### High Costs

To reduce costs:
- Use `gpt-4o-mini` model (default)
- Reduce `max_tokens` in `chatgpt_research.py`
- Increase cache duration
- Only research high-value games

## Advanced Configuration

To customize ChatGPT queries, edit `chatgpt_research.py`:

- Modify `_build_query()` to change the research questions
- Adjust `temperature` in `_call_api()` (0.0-2.0, lower = more factual)
- Change `max_tokens` to get longer/shorter analyses
- Change `model` parameter to use different GPT models

## Support

For OpenAI API issues:
- OpenAI API Docs: https://platform.openai.com/docs
- OpenAI Support: https://help.openai.com/
- Status Page: https://status.openai.com/

