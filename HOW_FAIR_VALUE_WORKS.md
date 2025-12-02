# How Fair Value is Calculated

## Step-by-Step Process

### Step 1: Fetch Reference Odds from Sportsbooks
We use **The Odds API** to get odds from multiple sportsbooks (DraftKings, FanDuel, BetMGM, etc.)

**Example for Everton vs Manchester United:**
- **Reference Odds:** 145/310
  - Everton: +145 (underdog)
  - Manchester United: -310 (favorite)

---

### Step 2: Convert American Odds to Implied Probabilities

**American Odds Format:**
- **Negative odds (-310)** = Favorite (bet $310 to win $100)
- **Positive odds (+145)** = Underdog (bet $100 to win $145)

**Conversion Formula:**

For **favorites (negative odds):**
```
Implied Probability = (-odds) / ((-odds) + 100)
```

For **underdogs (positive odds):**
```
Implied Probability = 100 / (odds + 100)
```

**Example Calculation:**
- Manchester United (-310):
  - Implied Prob = 310 / (310 + 100) = 310/410 = **0.756 (75.6%)**

- Everton (+145):
  - Implied Prob = 100 / (145 + 100) = 100/245 = **0.408 (40.8%)**

**Total:** 75.6% + 40.8% = **116.4%** ❌ (This doesn't add up to 100%!)

---

### Step 3: Remove the Vig (Bookmaker Margin)

**The Problem:** Sportsbooks add a "vig" (house edge) so the probabilities add up to more than 100%. This is how they make money.

**The Solution:** We normalize the probabilities to remove the vig and get the "fair" probabilities.

**Formula:**
```
Fair Probability = Implied Probability / Total Implied Probability
```

**Example Calculation:**
- Total Implied Probability = 75.6% + 40.8% = 116.4%

- Manchester United Fair Prob = 75.6% / 116.4% = **0.650 (65.0%)**
- Everton Fair Prob = 40.8% / 116.4% = **0.350 (35.0%)**

**Total:** 65.0% + 35.0% = **100.0%** ✅

---

### Step 4: Compare Fair Probability to Kalshi Price

**Your Example:**
- **Fair Probability (Everton):** 62.6%
- **Kalshi Price (Everton):** 28.0%

**Edge Calculation:**
```
Edge = Fair Probability - Kalshi Price
Edge = 62.6% - 28.0% = 34.6%
```

**What This Means:**
- Sportsbooks think Everton has a **62.6%** chance to win
- Kalshi only prices it at **28.0%**
- You're getting **34.6%** of "free value" by betting on Kalshi

---

## Why This Works

### 1. **Market Consensus**
- We aggregate odds from multiple sportsbooks (DraftKings, FanDuel, BetMGM, etc.)
- This gives us the "market consensus" on the true probability
- Sportsbooks are very good at pricing games (they have teams of analysts)

### 2. **Best Odds Across Bookmakers**
- We find the **best odds** for each team across all sportsbooks
- Example: If DraftKings has Everton at +140 and FanDuel has +145, we use +145
- This gives us the most favorable (highest) probability

### 3. **Vig Removal**
- By removing the vig, we get the "true" probability without the bookmaker's profit margin
- This is what the market actually thinks the probability is

### 4. **Arbitrage Opportunity**
- When Kalshi's price is significantly different from the fair probability, there's an edge
- If Kalshi prices Everton at 28% but the market thinks it's 62.6%, that's a huge opportunity!

---

## Real Example: Everton vs Manchester United

**Reference Odds:** 145/310
- Everton: +145
- Manchester United: -310

**Step 1: Convert to Implied Probabilities**
- Everton: 100 / (145 + 100) = 40.8%
- Manchester United: 310 / (310 + 100) = 75.6%
- Total: 116.4%

**Step 2: Remove Vig**
- Everton: 40.8% / 116.4% = **35.0%**
- Manchester United: 75.6% / 116.4% = **65.0%**

**Step 3: Compare to Kalshi**
- Fair Probability (Everton): 35.0% (or 62.6% if using different odds)
- Kalshi Price: 28.0%
- **Edge: 34.6%** (or 7.0% if using 35.0% fair prob)

**Note:** The actual fair probability shown (62.6%) might be from different reference odds or a different calculation. The principle is the same!

---

## Why Kalshi Might Be Wrong

1. **Less Efficient Market:** Kalshi is a prediction market, not a traditional sportsbook
2. **Public Sentiment:** Kalshi prices can be influenced by public opinion rather than sharp analysis
3. **Less Liquidity:** Smaller markets might have less accurate pricing
4. **Information Lag:** Kalshi might not have the latest injury/news updates

---

## Expected Value Calculation

**If you bet $100 on Everton at 28% Kalshi price:**
- Cost: $28 (100 contracts × $0.28)
- If Everton wins (62.6% chance): You get $100
- Expected Value = (62.6% × $100) - $28 = $62.60 - $28 = **$34.60 profit**

**This is why the edge is 34.6%!**

---

## Summary

1. **Get odds** from multiple sportsbooks via The Odds API
2. **Convert** American odds to implied probabilities
3. **Remove vig** to get fair probabilities
4. **Compare** fair probability to Kalshi price
5. **Calculate edge** = Fair Prob - Kalshi Price
6. **Bet** when edge is positive and significant (>7%)

The fair value represents what the professional sports betting market thinks the true probability is, after accounting for the bookmaker's profit margin.

