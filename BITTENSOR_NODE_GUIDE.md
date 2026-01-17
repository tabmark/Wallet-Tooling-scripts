# Running a Bittensor Node for Historical Data Access

## Why Run Your Own Node?

Running a Bittensor archive node gives you **complete access** to blockchain history, bypassing all API limitations.

### ✅ What You Get

**Full Blockchain Access:**
- ✅ Every transaction since genesis
- ✅ All delegation/staking events
- ✅ Every block and extrinsic
- ✅ No rate limits
- ✅ No paid API tier needed
- ✅ Query any historical date

**For Your Use Case:**
- Find ALL wallets that bought before the 10 price spikes
- Analyze patterns across weeks/months
- Export unlimited historical data
- Run complex queries on your own schedule

### ❌ API Limitations (What You Avoid)

**Free Tier APIs (taostats.io, tao.app):**
- ❌ Only 24 hours of transaction history
- ❌ Rate limiting
- ❌ No bulk exports
- ❌ Can't query arbitrary dates

**Paid Tier APIs:**
- 💰 Monthly subscription costs
- 🔒 Still have some rate limits
- 📊 Limited query flexibility

## Requirements

### Hardware

**Minimum (Full Node):**
```
CPU: 4 cores
RAM: 8 GB
Storage: 100 GB SSD
Network: 10 Mbps
```

**Recommended (Archive Node):**
```
CPU: 8 cores (or better)
RAM: 32 GB
Storage: 1 TB NVMe SSD
Network: 100 Mbps
```

**Estimated Costs:**
- **VPS (DigitalOcean/AWS):** $40-80/month
- **Dedicated Server:** $50-150/month
- **Home Server:** One-time hardware cost

### Software

- Ubuntu 22.04+ (or similar Linux)
- Rust toolchain
- 200+ GB free disk space (grows over time)

## Setup Process

### Option 1: Quick Setup Script

```bash
# Download and run setup script
wget https://raw.githubusercontent.com/tabmark/Wallet-Tooling-scripts/main/setup_bittensor_node.sh
chmod +x setup_bittensor_node.sh
./setup_bittensor_node.sh
```

### Option 2: Manual Setup

#### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y build-essential git clang curl libssl-dev llvm libudev-dev protobuf-compiler
```

#### 2. Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
rustup default stable
rustup update
```

#### 3. Clone Subtensor

```bash
cd ~
git clone https://github.com/opentensor/subtensor.git
cd subtensor
```

#### 4. Build (20-60 minutes)

```bash
cargo build --release --features runtime-benchmarks
```

#### 5. Run Archive Node

```bash
./target/release/node-subtensor \
  --chain raw_spec.json \
  --base-path /data/bittensor \
  --sync=full \
  --pruning archive \
  --name "MyArchiveNode" \
  --rpc-cors all \
  --rpc-methods Unsafe \
  --rpc-external \
  --ws-external
```

**Important Flags:**
- `--pruning archive` - Keep ALL historical data
- `--ws-external` - Allow external connections
- `--rpc-external` - Enable RPC queries

### 6. Wait for Sync

**Initial sync time:** 24-48 hours
- Downloads entire blockchain history
- Verifies all blocks
- Builds indices

**Monitor progress:**
```bash
# Check logs
tail -f /data/bittensor/chains/bittensor/subtensor.log

# Or use polkadot.js UI
# Connect to ws://YOUR_IP:9944
```

## Querying Your Node

### Install Python Dependencies

```bash
pip install substrate-interface
```

### Query Historical Data

```python
from substrateinterface import SubstrateInterface

# Connect to your node
substrate = SubstrateInterface(
    url="ws://127.0.0.1:9944",  # Your node
    ss58_format=42
)

# Get delegation events for subnet 2 on Jan 15
block_hash = substrate.get_block_hash(7323032)  # Jan 15 block
events = substrate.get_events(block_hash)

for event in events:
    if event.value['module_id'] == 'SubtensorModule':
        print(event.value)
```

### Using the Query Script

```bash
# Edit query_bittensor_node.py with your spike dates
python3 query_bittensor_node.py
```

This will:
1. Connect to your local node
2. Find blocks for each spike date
3. Query all delegation events 24h before
4. Identify wallets that bought in
5. Save results to JSON

## Data You Can Extract

### Delegation Events

```python
{
  "block": 7323032,
  "timestamp": "2026-01-15T00:00:00",
  "event": "StakeAdded",
  "netuid": 2,
  "coldkey": "5HEo565WAy4Dbq3Sv271xJFPrch48dNbz9esuJpVKVbnvP2h",
  "hotkey": "5FDJf2BwQTfq...",
  "amount": 5000000000  // 5 TAO in rao
}
```

### Alpha Token Purchases

```python
{
  "event": "AlphaBought",
  "netuid": 2,
  "account": "5HEo565WAy4Dbq3Sv271...",
  "amount": 10000000000,  // 10 TAO
  "price": 0.009002,
  "slippage": 0.0001
}
```

## Query Examples

### Get All Delegations for Subnet 2

```python
# Get all blocks in date range
start_block = 7300000  # Dec 20
end_block = 7337000    # Jan 17

for block_num in range(start_block, end_block):
    block_hash = substrate.get_block_hash(block_num)
    events = substrate.get_events(block_hash)

    for event in events:
        if (event.value['module_id'] == 'SubtensorModule' and
            event.value['event_id'] == 'StakeAdded' and
            event.value['attributes']['netuid'] == 2):
            # Process delegation
            print(event.value)
```

### Find Wallets That Bought Before Each Spike

```python
spike_dates = [
    ('2026-01-16', 7330000, 7337000),  # Block range
    ('2026-01-15', 7323000, 7330000),
    # etc.
]

for date, start, end in spike_dates:
    wallets = {}
    for block in range(start, end):
        events = get_delegation_events(substrate, block, netuid=2)
        # Aggregate by wallet
        for event in events:
            wallet = event['coldkey']
            wallets[wallet] = wallets.get(wallet, 0) + event['amount']

    # Show top buyers
    sorted_wallets = sorted(wallets.items(), key=lambda x: x[1], reverse=True)
    print(f"{date}: {sorted_wallets[:10]}")
```

## Maintenance

### Disk Space

Archive nodes grow over time:
- Current: ~200-300 GB
- Growth: ~50-100 GB/year
- Monitor with: `df -h /data/bittensor`

### Updates

```bash
cd ~/subtensor
git pull
cargo build --release --features runtime-benchmarks
# Restart node
```

### Backup

Only need to backup if you want to preserve your node's state:
```bash
# Stop node first
rsync -av /data/bittensor/ /backup/bittensor/
```

## Troubleshooting

### Node Won't Sync

```bash
# Check logs
journalctl -u subtensor -f

# Verify network connectivity
curl https://bootnode.bittensor.com

# Try different bootnodes
--bootnodes /ip4/...
```

### RPC Connection Failed

```bash
# Ensure ports are open
sudo ufw allow 9944
sudo ufw allow 30333

# Check if node is listening
netstat -tuln | grep 9944
```

### Out of Memory

```bash
# Increase swap space
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Cost Comparison

### Running Your Own Node

**One-Time:**
- Setup time: 4-8 hours
- Hardware: $0 (existing) or $500-2000 (new server)

**Monthly:**
- VPS: $40-80/month
- Electricity (home): ~$10-20/month

### Paid API Alternative

**Monthly:**
- Taostats Pro: Unknown (contact for pricing)
- Tao.app Paid: Unknown (contact for pricing)

**Limitations:**
- Still have rate limits
- Less query flexibility
- Ongoing subscription

## Pros & Cons

### Pros ✅

- Complete data access (all 10 spike dates!)
- No rate limits
- No monthly fees (after setup)
- Full query control
- Can build custom tools
- Contribute to network decentralization

### Cons ❌

- Initial setup complexity
- Hardware/hosting costs
- 24-48 hour sync time
- Requires technical knowledge
- Ongoing maintenance

## Conclusion

**Run your own node if:**
- ✅ You need historical data beyond 24 hours
- ✅ You want to avoid API limitations
- ✅ You have technical experience
- ✅ You prefer one-time cost vs. subscription

**Use API if:**
- ❌ You only need recent data (<24h)
- ❌ You want minimal setup
- ❌ You don't mind rate limits
- ❌ You prefer managed service

## Next Steps

1. **Choose hosting:** VPS, dedicated server, or home
2. **Run setup script:** `./setup_bittensor_node.sh`
3. **Wait for sync:** 24-48 hours
4. **Test queries:** `python3 query_bittensor_node.py`
5. **Analyze data:** Find wallets that bought before spikes!

## Resources

- **Subtensor GitHub:** https://github.com/opentensor/subtensor
- **Bittensor Docs:** https://docs.bittensor.com/
- **Substrate Docs:** https://docs.substrate.io/
- **Python Interface:** https://pypi.org/project/substrate-interface/

---

**Questions?** Check the scripts in this repo:
- `setup_bittensor_node.sh` - Automated setup
- `query_bittensor_node.py` - Query examples
- `subnet_investor_detector.py` - Price spike analysis
