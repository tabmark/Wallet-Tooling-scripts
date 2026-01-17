# Bittensor Subnet Investor Detection Tool

## Overview

This tool analyzes Bittensor subnets to identify wallets that buy into subnets before significant price increases (5% or more).

## Files

- **`subnet_investor_detector.py`** - Main detection script for historical analysis
- **`subnet_realtime_monitor.py`** - Real-time monitoring script (recommended)

## ⚠️ Important Limitations

### API Data Availability

**taostats.io API:**
- Transaction/delegation data is only available for the **last ~15 minutes**
- Historical transaction data beyond this window is not accessible
- This makes retroactive analysis of past price spikes impossible

**tao.app API:**
- Price history data IS available (up to 30+ days)
- Successfully identifies price spikes of 5%+
- Free tier has rate limits

### What This Means

The historical analysis script (`subnet_investor_detector.py`) can:
✅ Identify all historical price spikes
✅ Show when and where 5%+ price increases occurred
❌ **Cannot** fetch transaction data from those historical dates

## Recommended Approach: Real-Time Monitoring

Since historical transaction data isn't available, the best approach is to:

1. **Run the real-time monitor continuously**
2. **Collect data as it happens**
3. **Build a historical database over time**
4. **Analyze patterns as data accumulates**

## Usage

### Option 1: Historical Analysis (Limited by API constraints)

Shows price spikes but cannot fetch historical transactions:

```bash
python3 subnet_investor_detector.py
```

**What it does:**
- Analyzes top 5 subnets by market cap + subnet 2
- Identifies all 5%+ price spikes in the last 30 days
- Attempts to fetch transactions from 24h before each spike
- **Note**: Will show API errors for historical transaction data

### Option 2: Real-Time Monitoring (Recommended)

Collects data in real-time and builds historical database:

```bash
python3 subnet_realtime_monitor.py
```

**What it does:**
- Monitors specified subnets in real-time
- Tracks current prices and transactions
- Detects price changes as they happen
- Identifies wallets buying before price increases
- Saves data to local database for future analysis

## Configuration

Edit the scripts to modify:

```python
# Minimum transaction size to track
MIN_TRANSACTION_SIZE = 3.0  # TAO

# Price increase threshold
PRICE_INCREASE_THRESHOLD = 0.05  # 5%

# Subnets to analyze
SUBNETS_TO_MONITOR = [2, 4, 8, 9, 44, 51, 64, 120]

# Analysis timeframe
ANALYSIS_DAYS = 30
```

## API Keys

The scripts use your provided API keys:

- **taostats.io**: `tao-b33d0cd0-e17c-405f-bd44-7effe34e9aac:bf3d3b55`
- **tao.app**: `5c8f0bf8cb8acee5ad1ae3787e87a84f4b5d1be97d75c11b52c61fee9d99e6ba`

## Results from Latest Run

The script successfully analyzed subnet 2 (DSperse) and found **10 price spikes** in the last 30 days:

| Date       | Price Change | Gain  |
|------------|--------------|-------|
| 2025-12-20 | 0.003225 → 0.003411 TAO | +5.75% |
| 2025-12-30 | 0.003497 → 0.004164 TAO | +19.07% |
| 2025-12-31 | 0.004164 → 0.004950 TAO | +18.90% |
| 2026-01-02 | 0.004866 → 0.005464 TAO | +12.30% |
| 2026-01-03 | 0.005464 → 0.006884 TAO | +25.99% |
| 2026-01-06 | 0.006042 → 0.006437 TAO | +6.54% |
| 2026-01-09 | 0.006407 → 0.006758 TAO | +5.48% |
| 2026-01-10 | 0.006758 → 0.007110 TAO | +5.21% |
| 2026-01-15 | 0.007374 → 0.008118 TAO | +10.08% |
| 2026-01-16 | 0.008118 → 0.008995 TAO | +10.81% |

However, **transaction data from those dates is not available** due to API limitations.

## Future Enhancements

To fully implement this tool:

1. **Set up continuous monitoring** with the real-time script
2. **Store data in a database** (SQLite, PostgreSQL, etc.)
3. **Run analysis on accumulated data** after collecting for days/weeks
4. **Add alerting** for suspicious patterns
5. **Implement machine learning** to predict price movements based on wallet behavior

## Alternative Data Sources

If you need historical transaction data, consider:

- **Running a Bittensor archive node** with full blockchain history
- **Using blockchain explorers** with API access to historical blocks
- **Subscribing to paid data providers** that archive transaction history
- **Building your own data pipeline** by indexing the blockchain directly

## Questions?

The tool is fully functional for:
- ✅ Price spike detection
- ✅ Real-time transaction monitoring
- ✅ Pattern identification (with accumulated data)

Limited by:
- ❌ Historical transaction data (API constraint)
- ❌ Retroactive analysis beyond ~15 minutes
