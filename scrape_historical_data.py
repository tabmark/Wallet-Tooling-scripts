#!/usr/bin/env python3
"""
Web scraper for taostats.io delegation data
Uses the same internal API that the website uses
"""

import requests
import json
from datetime import datetime, timedelta

TAOSTATS_API_KEY = "tao-b33d0cd0-e17c-405f-bd44-7effe34e9aac:bf3d3b55"

def scrape_delegation_data(netuid=2, days_back=30):
    """
    Scrape delegation data by reverse-engineering the website's API calls
    """

    print(f"Attempting to scrape delegation data for subnet {netuid}...")
    print(f"Looking back {days_back} days...")

    headers = {
        "Authorization": TAOSTATS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    # Calculate date range
    from datetime import timezone
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    print(f"\nDate range: {start_date.date()} to {end_date.date()}")

    # Try different pagination approaches
    all_transactions = []

    # Approach 1: Paginate backwards in time
    print("\n=== Approach 1: Time-based pagination ===")
    page = 1
    max_pages = 1000  # Safety limit

    while page <= max_pages:
        url = "https://api.taostats.io/api/delegation/v1"
        params = {
            "netuid": netuid,
            "limit": 200,
            "page": page
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 429:
                print(f"  Page {page}: Rate limited, stopping")
                break

            if response.status_code != 200:
                print(f"  Page {page}: Error {response.status_code}")
                break

            data = response.json()
            items = data.get('data', [])

            if not items:
                print(f"  Page {page}: No more data")
                break

            # Check if we've gone past our date range
            oldest_timestamp = items[-1].get('timestamp')
            oldest_date = datetime.fromisoformat(oldest_timestamp.replace('Z', '+00:00'))

            print(f"  Page {page}: {len(items)} items, oldest: {oldest_date.date()}")

            # Filter items within our date range
            for item in items:
                timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                if timestamp >= start_date:
                    all_transactions.append(item)
                else:
                    # We've gone too far back
                    print(f"  Reached target date range at page {page}")
                    return all_transactions

            # Check pagination
            pagination = data.get('pagination', {})
            if not pagination.get('next_page'):
                print(f"  Page {page}: No more pages")
                break

            page += 1

            # Rate limiting
            import time
            time.sleep(0.5)

        except Exception as e:
            print(f"  Page {page}: Error - {e}")
            break

    return all_transactions


def analyze_scraped_data(transactions, spike_dates):
    """
    Analyze scraped transactions against known price spike dates
    """
    from collections import defaultdict

    print(f"\n=== Analysis ===")
    print(f"Total transactions collected: {len(transactions)}")

    if not transactions:
        print("No transactions to analyze")
        return

    # Convert to datetime and sort
    for tx in transactions:
        tx['datetime'] = datetime.fromisoformat(tx['timestamp'].replace('Z', '+00:00'))

    transactions.sort(key=lambda x: x['datetime'])

    print(f"Date range: {transactions[0]['datetime'].date()} to {transactions[-1]['datetime'].date()}")

    # Find wallets that bought before each spike
    RAO_PER_TAO = 1_000_000_000
    MIN_TRANSACTION_SIZE = 3.0

    results = defaultdict(list)

    for spike_date_str in spike_dates:
        from datetime import timezone
        spike_date = datetime.strptime(spike_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        lookback_start = spike_date - timedelta(hours=24)

        print(f"\nSpike on {spike_date.date()}:")
        print(f"  Looking for txs between {lookback_start} and {spike_date}")

        buyers = []
        for tx in transactions:
            if lookback_start <= tx['datetime'] < spike_date:
                if tx['action'] == 'DELEGATE':
                    amount_tao = float(tx['amount']) / RAO_PER_TAO
                    if amount_tao >= MIN_TRANSACTION_SIZE:
                        buyers.append({
                            'wallet': tx['nominator']['ss58'],
                            'amount': amount_tao,
                            'timestamp': tx['datetime'],
                            'price': float(tx.get('alpha_price_in_tao', 0))
                        })

        if buyers:
            print(f"  Found {len(buyers)} wallets:")
            for buyer in buyers[:10]:  # Show first 10
                print(f"    {buyer['wallet'][:30]}... : {buyer['amount']:.2f} TAO")
            results[spike_date_str] = buyers
        else:
            print(f"  No qualifying transactions found")

    return results


if __name__ == "__main__":
    # Subnet 2 price spike dates
    spike_dates = [
        '2026-01-16',
        '2026-01-15',
        '2026-01-10',
        '2026-01-09',
        '2026-01-06',
        '2026-01-03',
        '2026-01-02',
        '2025-12-31',
        '2025-12-30',
        '2025-12-20',
    ]

    # Try to scrape data
    transactions = scrape_delegation_data(netuid=2, days_back=30)

    if transactions:
        # Save to file
        with open('scraped_delegations.json', 'w') as f:
            json.dump(transactions, f, indent=2)
        print(f"\nSaved {len(transactions)} transactions to scraped_delegations.json")

        # Analyze
        results = analyze_scraped_data(transactions, spike_dates)

        # Save results
        if results:
            with open('spike_analysis_results.json', 'w') as f:
                json.dump({k: v for k, v in results.items()}, f, indent=2, default=str)
            print(f"\nSaved analysis to spike_analysis_results.json")
    else:
        print("\nCould not scrape historical data - API limitations apply")
        print("\nThe website uses the same API we're using, which only provides ~15 min of history")
        print("Manual browsing on the website shows the same limitation")
