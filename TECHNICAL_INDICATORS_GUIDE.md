# Technical Indicators Guide

## Understanding Your Betting Dashboard Metrics

### 1. **Kalshi Price (23.0%)**
**What it means:** The current market price on Kalshi for the team to win, expressed as a probability.

**How to read it:**
- If Kalshi prices Manchester United at 23%, they're saying there's a 23% chance United wins
- This is what you'd pay to buy a "YES" contract
- Lower price = market thinks team is less likely to win

**What it tells you:** The market's current assessment of the team's chances.

---

### 2. **Reference Odds (-130/380)**
**What it means:** The odds from traditional sportsbooks (like DraftKings, FanDuel, etc.) in American odds format.

**How to read it:**
- **-130** = You need to bet $130 to win $100 (favorite)
- **+380** = You bet $100 to win $380 (underdog)
- The first number is for the first team, second is for the second team

**What it tells you:** What professional sportsbooks think the true probability is.

---

### 3. **Fair Probability (73.1%)**
**What it means:** The "true" probability after removing the bookmaker's margin (vig).

**How to calculate:**
- Convert sportsbook odds to implied probabilities
- Remove the vig (bookmaker's profit margin)
- This gives you the "fair" probability without house edge

**What it tells you:** The actual probability the team should win, based on market consensus from multiple sportsbooks.

---

### 4. **Edge (50.07%)**
**What it means:** The difference between fair probability and Kalshi price. This is your expected value.

**How to calculate:**
- Edge = Fair Probability - Kalshi Price
- Example: 73.1% - 23.0% = 50.07% edge

**What it tells you:**
- **Positive edge (>0%)** = Good bet, Kalshi is undervaluing the team
- **Large edge (>10%)** = Very good bet, significant mispricing
- **Negative edge (<0%)** = Bad bet, Kalshi is overvaluing the team

**In your example:** 50.07% edge means Kalshi is significantly undervaluing Manchester United. If you bet $100, you'd expect to make $50.07 in profit on average.

---

### 5. **Market Volume (7,734)**
**What it means:** Total number of contracts traded in this market.

**How to read it:**
- Higher volume = More liquidity, easier to buy/sell
- Lower volume = Less liquidity, might have wider spreads

**What it tells you:**
- **High volume (>5,000)** = Active market, prices are more reliable
- **Low volume (<1,000)** = Thin market, prices might be less accurate

---

### 6. **Spread (2.00%)**
**What it means:** The difference between the best bid (buy) and ask (sell) prices.

**How to calculate:**
- Spread = Ask Price - Bid Price
- Example: If you can buy at 23% but sell at 21%, spread is 2%

**What it tells you:**
- **Low spread (<3%)** = Tight market, good liquidity
- **High spread (>5%)** = Wide market, might be harder to trade
- Lower spread = Less cost to enter/exit positions

---

### 7. **Recommendation (STRONG BUY)**
**What it means:** The bot's overall recommendation based on all factors.

**Recommendation Levels:**
- **STRONG BUY** = Edge > 15%, very high confidence
- **BUY** = Edge > 10%, good opportunity
- **WEAK BUY** = Edge > 5%, moderate opportunity
- **NO BET** = Edge < 5%, not worth it
- **AVOID** = Negative edge, stay away

**What it tells you:** Quick summary of whether this is a good bet.

---

### 8. **Research Probability (when available)**
**What it means:** AI/statistical analysis of team performance, injuries, matchups, etc.

**What it includes:**
- Team statistics (win rate, recent form)
- Head-to-head history
- Key player injuries
- Home/away performance
- Advanced metrics

**What it tells you:** Whether the research supports the odds-based edge.

---

### 9. **Social Sentiment (when available)**
**What it means:** Public opinion from Twitter, Reddit, and news.

**What it includes:**
- Twitter engagement (likes, retweets)
- Reddit discussions
- News coverage

**What it tells you:**
- If public sentiment aligns with your bet
- Potential market movements based on public opinion
- Whether there's "buzz" around a team

---

## How to Use These Indicators Together

### **The Perfect Bet:**
1. **High Edge (>15%)** - Kalshi significantly undervalues the team
2. **High Volume (>5,000)** - Liquid market, easy to trade
3. **Low Spread (<3%)** - Tight market, low transaction costs
4. **Research Supports** - Statistics and analysis agree with the edge
5. **Social Sentiment Aligns** - Public opinion matches your bet

### **Red Flags:**
- ❌ **Negative Edge** - Kalshi is overvaluing
- ❌ **Very Low Volume** - Market might be unreliable
- ❌ **High Spread (>8%)** - Expensive to trade
- ❌ **Research Contradicts** - Stats don't support the edge

### **Your Example (Manchester United vs Everton):**
- ✅ **Edge: 50.07%** - HUGE edge, Kalshi massively undervalues United
- ✅ **Fair Prob: 73.1%** - Sportsbooks think United has 73% chance
- ⚠️ **Kalshi Price: 23%** - Kalshi only prices at 23% (huge discrepancy!)
- ✅ **Volume: 7,734** - Good liquidity
- ✅ **Spread: 2%** - Tight market
- ✅ **Recommendation: STRONG BUY** - All indicators point to a great bet

**This suggests:** Either Kalshi has a major mispricing, or there's information the sportsbooks have that Kalshi doesn't. The 50% edge is unusually large and worth investigating further with research.

---

## Expected Value Calculation

**If you bet $100 on Manchester United at 23% Kalshi price:**
- You buy 100 contracts at $0.23 each = $23 cost
- If United wins, each contract pays $1.00
- Expected value = (73.1% win prob × $100 payout) - $23 cost = $50.10 profit

**This is why the edge is 50.07%** - you're getting massive value!

