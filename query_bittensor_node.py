#!/usr/bin/env python3
"""
Query Bittensor node directly for historical delegation data
Requires a running Bittensor archive node
"""

from substrateinterface import SubstrateInterface
from datetime import datetime, timedelta
import json

# Connect to your local node
# Default: ws://127.0.0.1:9944
NODE_URL = "ws://127.0.0.1:9944"

def connect_to_node():
    """Connect to local Bittensor node"""
    try:
        substrate = SubstrateInterface(
            url=NODE_URL,
            ss58_format=42,  # Bittensor format
            type_registry_preset='substrate-node-template'
        )
        print(f"✓ Connected to Bittensor node")
        print(f"  Chain: {substrate.chain}")
        print(f"  Version: {substrate.version}")
        return substrate
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print(f"\nMake sure your node is running:")
        print(f"  ./target/release/node-subtensor --ws-external")
        return None


def get_block_by_timestamp(substrate, target_date):
    """
    Find block number closest to a target date
    Uses binary search for efficiency
    """
    print(f"\nFinding block for date: {target_date}...")

    # Get current block
    current_block = substrate.get_block_number(substrate.get_chain_head())

    # Binary search to find block near target date
    # This is approximate - you may need to adjust
    blocks_per_day = 7200  # ~12 sec per block
    days_ago = (datetime.now() - target_date).days
    estimated_block = current_block - (days_ago * blocks_per_day)

    print(f"  Estimated block: {estimated_block}")
    return estimated_block


def get_delegation_events(substrate, start_block, end_block, netuid=2):
    """
    Get all delegation events between two blocks for a specific subnet
    """
    print(f"\nQuerying delegation events...")
    print(f"  Blocks: {start_block} to {end_block}")
    print(f"  Subnet: {netuid}")

    events = []

    # Query blocks in batches to avoid overwhelming the node
    batch_size = 100
    for block_num in range(start_block, end_block, batch_size):
        batch_end = min(block_num + batch_size, end_block)

        print(f"  Processing blocks {block_num}-{batch_end}...")

        for block in range(block_num, batch_end):
            try:
                # Get block hash
                block_hash = substrate.get_block_hash(block)

                # Get events from this block
                block_events = substrate.get_events(block_hash)

                for event in block_events:
                    # Look for staking/delegation events
                    if event.value['module_id'] == 'SubtensorModule':
                        event_id = event.value['event_id']

                        # Filter for delegation-related events
                        if event_id in ['StakeAdded', 'StakeRemoved', 'AlphaBought']:
                            event_data = event.value['attributes']

                            # Check if it's for our subnet
                            if 'netuid' in event_data and event_data['netuid'] == netuid:

                                # Get block timestamp
                                extrinsics = substrate.get_block(block_hash)['extrinsics']
                                timestamp = None
                                for ext in extrinsics:
                                    if 'Timestamp' in str(ext):
                                        timestamp = ext.value['call']['call_args'][0]['value']
                                        timestamp = datetime.fromtimestamp(timestamp / 1000)
                                        break

                                events.append({
                                    'block': block,
                                    'timestamp': timestamp.isoformat() if timestamp else None,
                                    'event': event_id,
                                    'netuid': netuid,
                                    'data': event_data
                                })

            except Exception as e:
                print(f"    Error at block {block}: {e}")
                continue

    return events


def analyze_wallets_before_spike(substrate, spike_date, netuid=2):
    """
    Find wallets that bought into a subnet 24h before a price spike
    """
    print(f"\n{'='*70}")
    print(f"Analyzing wallets before {spike_date} spike (Subnet {netuid})")
    print('='*70)

    # Get blocks for 24h before spike
    spike_datetime = datetime.combine(spike_date, datetime.min.time())
    start_datetime = spike_datetime - timedelta(hours=24)

    start_block = get_block_by_timestamp(substrate, start_datetime)
    end_block = get_block_by_timestamp(substrate, spike_datetime)

    # Get delegation events
    events = get_delegation_events(substrate, start_block, end_block, netuid)

    print(f"\n✓ Found {len(events)} delegation events")

    # Analyze wallets
    wallets = {}
    for event in events:
        if event['event'] == 'StakeAdded' or event['event'] == 'AlphaBought':
            wallet = event['data'].get('coldkey') or event['data'].get('account')
            amount = event['data'].get('amount', 0)

            if wallet not in wallets:
                wallets[wallet] = {
                    'total_amount': 0,
                    'transactions': []
                }

            wallets[wallet]['total_amount'] += amount
            wallets[wallet]['transactions'].append({
                'block': event['block'],
                'timestamp': event['timestamp'],
                'amount': amount
            })

    # Sort by total amount
    sorted_wallets = sorted(wallets.items(), key=lambda x: x[1]['total_amount'], reverse=True)

    print(f"\n🎯 Top Wallets (24h before spike):")
    for wallet, data in sorted_wallets[:10]:
        tao_amount = data['total_amount'] / 1e9  # Convert from rao to TAO
        print(f"  {wallet}")
        print(f"    Amount: {tao_amount:.2f} TAO")
        print(f"    Transactions: {len(data['transactions'])}")

    return sorted_wallets


def main():
    """Main function to demonstrate node querying"""

    # Connect to node
    substrate = connect_to_node()
    if not substrate:
        return

    # Example: Analyze subnet 2 for Jan 16 spike
    from datetime import date
    spike_dates = [
        date(2026, 1, 16),
        date(2026, 1, 15),
        date(2026, 1, 10),
        # Add more dates as needed
    ]

    results = {}
    for spike_date in spike_dates:
        wallets = analyze_wallets_before_spike(substrate, spike_date, netuid=2)
        results[spike_date.isoformat()] = wallets

    # Save results
    with open('node_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✓ Results saved to node_analysis_results.json")


if __name__ == "__main__":
    # First, install required package:
    # pip install substrate-interface

    main()
