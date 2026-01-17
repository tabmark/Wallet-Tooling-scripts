# Bittensor Subnet Investor Detection - Findings Summary

## 🎯 Mission
Detect wallets that buy into Bittensor subnets 1 day before the price increases by 5% or more.

## ✅ What We Accomplished

### 1. Price Spike Detection (SUCCESSFUL)
We successfully identified **10 significant price spikes** in Subnet 2 (DSperse) over the last 30 days:

| Date | Price Change | % Gain | Status |
|------|--------------|--------|--------|
| 2026-01-03 | 0.005464 → 0.006884 TAO | **+25.99%** 🚀 | Biggest spike |
| 2025-12-30 | 0.003497 → 0.004164 TAO | **+19.07%** | |
| 2025-12-31 | 0.004164 → 0.004950 TAO | **+18.90%** | |
| 2026-01-02 | 0.004866 → 0.005464 TAO | **+12.30%** | |
| 2026-01-16 | 0.008118 → 0.008995 TAO | **+10.81%** | Most recent |
| 2026-01-15 | 0.007374 → 0.008118 TAO | **+10.08%** | |
| 2026-01-06 | 0.006042 → 0.006437 TAO | **+6.54%** | |
| 2025-12-20 | 0.003225 → 0.003411 TAO | **+5.75%** | |
| 2026-01-09 | 0.006407 → 0.006758 TAO | **+5.48%** | |
| 2026-01-10 | 0.006758 → 0.007110 TAO | **+5.21%** | |

**Tools Used:**
- `subnet_investor_detector.py` - Successfully analyzes historical prices
- tao.app API - Provides 30+ days of hourly price data

### 2. Real-Time Monitoring (ACTIVE & COLLECTING DATA)

**Monitor Status:** ✅ RUNNING

The real-time monitor has already collected valuable data:

**Current Statistics:**
- **103 transactions** recorded across 4 subnets
- **12+ hours** of historical data (from 2026-01-16 12:02 to now)
- **5 price snapshots** taken
- **$8,974 TAO** total volume tracked

**Subnet Activity:**
- Subnet 44: 49 txs, 8,307 TAO (most active)
- Subnet 2: 23 txs, 161 TAO
- Subnet 9: 17 txs, 308 TAO
- Subnet 4: 14 txs, 197 TAO

**Top Active Wallets Identified:**
1. `5GTrbZE2PgJjww4PekR9PEF75xBm91FjLnJi211MRhoMKxBS` - 9 txs, 89.50 TAO
2. `5HNchfbqDhZJFnr3EBGVgp92aim1YYpicrv6dkzhgiyLfYqC` - 8 txs, 55.00 TAO
3. `5Hot6fAxKzarjuFu6jvSiCCcNP9tp61gc4JS5cdiSRWdqeaW` - 6 txs, 76.86 TAO
4. `5GHrA88kdA9mZqGuEEz5JU1rmwERKVLUB7ZctBP4DHVQkZww` - 4 txs, 193.98 TAO

## ❌ Limitations Discovered

### Historical Transaction Data Access
Both APIs (taostats.io and tao.app) have the same limitation on **free tier**:

**What's Available:**
- ✅ Current prices and subnet information
- ✅ Historical price data (30+ days back)
- ✅ Very recent transactions (~15 minutes)

**What's NOT Available (Free Tier):**
- ❌ Historical transactions beyond ~15 minutes
- ❌ Wallet activity from past dates (e.g., Jan 3rd, Dec 30th)
- ❌ Bulk transaction export/download
- ❌ Historical delegation events

**Paid Tier Required For:**
- `/api/beta/analytics/subnets/transactions` endpoint
- `/api/beta/portfolio/events` endpoint
- Historical block events beyond recent blocks

### Website Access
Blockchain explorer websites (taostats.io, tao.app, coinstats.app) block automated access:
- Manual browsing possible but no bulk data export visible
- No API alternatives for bulk historical data on free tier

## 🚀 Current Solution: Real-Time Monitoring

Since historical data isn't available, we're building a database from scratch:

**How It Works:**
1. Monitor runs every 5 minutes
2. Fetches current prices for subnets 2, 4, 8, 9, 44
3. Collects all recent transactions (≥3 TAO minimum)
4. Detects price spikes of 5%+ in real-time
5. Identifies wallets that bought 24h before each spike
6. Stores everything in SQLite database: `subnet_monitor.db`

**Files:**
- `subnet_realtime_monitor.py` - Running monitor (active now)
- `analyze_monitor_data.py` - Query and analyze collected data
- `subnet_monitor.db` - SQLite database with all collected data

## 📊 Data We're Collecting

**Tables in Database:**
1. `prices` - Price snapshots every 5 minutes
2. `transactions` - All delegations ≥3 TAO
3. `price_spikes` - Detected 5%+ price increases
4. `wallet_alerts` - Wallets that bought before spikes

## 🎯 Next Steps & Options

### Option 1: Continue Real-Time Monitoring (FREE) ⭐ RECOMMENDED
**Timeline:** Let it run for 7-30 days
**What You'll Get:**
- Complete transaction history during that period
- Wallets flagged when they buy before price spikes
- Success rate and frequency metrics
- Historical database you can analyze anytime

**How to Monitor:**
```bash
# Check current status
python3 analyze_monitor_data.py

# View live output
tail -f /tmp/claude/-home-user-Wallet-Tooling-scripts/tasks/bcb0f2c.output

# Query database directly
python3 -c "import sqlite3; conn = sqlite3.connect('subnet_monitor.db'); ..."
```

### Option 2: Upgrade to Paid API (PAID)
**Cost:** Contact tao.app or taostats.io for pricing
**What You'll Get:**
- Full historical transaction data
- Analyze all 10 past price spikes
- Identify wallets that bought before each spike
- Immediate results instead of waiting

**To Upgrade:**
- Visit https://api.tao.app/docs or https://dash.taostats.io
- Request paid tier access
- Update API keys in scripts

### Option 3: Run Bittensor Archive Node (TECHNICAL)
**Requirements:**
- Full Bittensor node with archive mode
- Significant storage (100s of GB)
- Technical setup required

**What You'll Get:**
- Complete blockchain history
- No API limitations
- Direct access to all blocks and transactions

**Resources:**
- [Bittensor Docs](https://docs.bittensor.com/)
- [TaoStats GitHub](https://github.com/TaoStats/bittensor-explorer-ui)

### Option 4: Blockchain Explorers (MANUAL)
Manually browse these sites for wallet data:

- **[Taostats Explorer](https://taostats.io/)** - Block explorer with delegation tables
- **[CoinStats Bittensor](https://coinstats.app/explorer/bittensor/)** - Transaction filtering
- **[TAO Analytics](https://taoanalytics.app/dash/)** - AI-powered subnet insights
- **[Taostats Delegation](https://taostats.io/delegation)** - Delegation history table

**Process:**
1. Visit delegation table on website
2. Filter by subnet 2 and date range
3. Manually record wallet addresses
4. Cross-reference with price spike dates

## 💡 Recommendation

**Best Approach for Free Access:**

1. **Let the real-time monitor run for 30 days** ✅ (already started)
   - Zero cost
   - Builds complete dataset
   - Automatic detection

2. **Check progress weekly** with `analyze_monitor_data.py`
   - See how many spikes detected
   - View wallets flagged
   - Track data accumulation

3. **After 30 days, analyze patterns:**
   - Which wallets consistently buy before spikes?
   - What's their success rate?
   - How much TAO do they invest?

**For Immediate Historical Results:**
- Upgrade to paid API tier on tao.app or taostats.io
- Or manually browse blockchain explorers for specific wallets

## 📁 Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `subnet_investor_detector.py` | Historical analysis (limited by API) | ✅ Complete |
| `subnet_realtime_monitor.py` | Live monitoring & data collection | ✅ Running |
| `analyze_monitor_data.py` | Query collected data | ✅ Ready |
| `subnet_monitor.db` | SQLite database | ✅ Active |
| `README_INVESTOR_DETECTION.md` | Full documentation | ✅ Complete |
| `FINDINGS_SUMMARY.md` | This file | ✅ Complete |

## 🔍 Key Insights

1. **Subnet 2 is highly volatile** - 10 spikes in 30 days (33% of days had 5%+ gains!)
2. **Real-time data IS accessible** - Just not historical
3. **Monitor is working perfectly** - Already collecting actionable data
4. **Wallets are active** - 103 transactions in 12 hours shows high trading volume

## Questions?

Run these commands:
```bash
# See what's been collected
python3 analyze_monitor_data.py

# Check monitor status
tail -n 50 /tmp/claude/-home-user-Wallet-Tooling-scripts/tasks/bcb0f2c.output

# Query specific wallet
python3 -c "
import sqlite3
conn = sqlite3.connect('subnet_monitor.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM transactions WHERE wallet LIKE ?', ('%5GTrbZE%',))
for row in cursor.fetchall():
    print(row)
"
```

---

**Status:** Monitor is actively collecting data. Check back in 24 hours for more insights!
