#!/usr/bin/env python3
"""
Bittensor Subnet Investor Detection Tool

Finds wallets that buy into subnets 1 day before price increases of 5% or more.
Uses tao.app API for price history and taostats.io API for transaction data.
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple
import time

# API Configuration
TAOSTATS_API_KEY = "tao-b33d0cd0-e17c-405f-bd44-7effe34e9aac:bf3d3b55"
TAO_APP_API_KEY = "5c8f0bf8cb8acee5ad1ae3787e87a84f4b5d1be97d75c11b52c61fee9d99e6ba"

# Constants
MIN_TRANSACTION_SIZE = 3.0  # TAO
PRICE_INCREASE_THRESHOLD = 0.05  # 5%
RAO_PER_TAO = 1_000_000_000

class SubnetInvestorDetector:
    def __init__(self):
        self.taostats_headers = {"Authorization": TAOSTATS_API_KEY}
        self.tao_app_headers = {"X-API-Key": TAO_APP_API_KEY}
        self.taostats_base = "https://api.taostats.io/api"
        self.tao_app_base = "https://api.tao.app/api/beta"

    def get_top_subnets(self, limit: int = 10) -> List[Dict]:
        """Get top subnets by market cap (tao_in * price)"""
        print("Fetching subnet information...")
        url = f"{self.tao_app_base}/analytics/subnets/info"

        try:
            response = requests.get(url, headers=self.tao_app_headers, timeout=30)
            response.raise_for_status()
            subnets = response.json()

            # Calculate market cap and sort
            for subnet in subnets:
                subnet['market_cap'] = subnet['tao_in'] * subnet['price']

            subnets.sort(key=lambda x: x['market_cap'], reverse=True)
            top_subnets = subnets[:limit]

            print(f"\nTop {limit} subnets by market cap:")
            for i, subnet in enumerate(top_subnets, 1):
                print(f"  {i}. Netuid {subnet['netuid']}: {subnet['subnet_name']} "
                      f"(Market Cap: {subnet['market_cap']:.2f} TAO, "
                      f"Price: {subnet['price']:.6f} TAO)")

            return top_subnets
        except Exception as e:
            print(f"Error fetching subnets: {e}")
            return []

    def get_price_history(self, netuid: int, days: int = 30) -> List[Dict]:
        """Get historical price data for a subnet"""
        print(f"\nFetching price history for subnet {netuid}...")
        url = f"{self.tao_app_base}/analytics/dynamic-info/aggregated"

        # Use hourly data for better precision
        params = {
            "netuid": str(netuid),
            "interval": "1hour",
            "page_size": days * 24  # hours in the time period
        }

        try:
            # Add delay to avoid rate limits
            time.sleep(2)

            response = requests.get(url, headers=self.tao_app_headers,
                                  params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            price_data = data.get('data', [])
            # Sort by timestamp (oldest first)
            price_data.sort(key=lambda x: x['timestamp'])

            print(f"  Retrieved {len(price_data)} price data points")
            return price_data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"  Rate limited. Waiting 10 seconds...")
                time.sleep(10)
                # Retry once
                try:
                    response = requests.get(url, headers=self.tao_app_headers,
                                          params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    price_data = data.get('data', [])
                    price_data.sort(key=lambda x: x['timestamp'])
                    print(f"  Retrieved {len(price_data)} price data points")
                    return price_data
                except Exception as retry_error:
                    print(f"  Retry failed: {retry_error}")
                    return []
            else:
                print(f"  Error fetching price history: {e}")
                return []
        except Exception as e:
            print(f"  Error fetching price history: {e}")
            return []

    def identify_price_spikes(self, price_history: List[Dict]) -> List[Tuple[datetime, float, float]]:
        """Identify dates where price increased by 5% or more"""
        spikes = []

        # Group by day for daily comparison
        daily_prices = {}
        for item in price_history:
            timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
            date = timestamp.date()
            price = item['price']

            # Keep highest price for each day
            if date not in daily_prices or price > daily_prices[date]:
                daily_prices[date] = price

        # Sort dates
        sorted_dates = sorted(daily_prices.keys())

        # Find spikes
        for i in range(1, len(sorted_dates)):
            prev_date = sorted_dates[i-1]
            curr_date = sorted_dates[i]
            prev_price = daily_prices[prev_date]
            curr_price = daily_prices[curr_date]

            price_change = (curr_price - prev_price) / prev_price

            if price_change >= PRICE_INCREASE_THRESHOLD:
                spikes.append((curr_date, prev_price, curr_price))

        return spikes

    def get_wallet_transactions(self, netuid: int, start_time: datetime,
                               end_time: datetime) -> List[Dict]:
        """Get all delegation and transfer transactions for a subnet in a time range"""
        print(f"  Fetching transactions from {start_time} to {end_time}...")

        transactions = []

        # Get delegation events (staking/buying alpha)
        try:
            url = f"{self.taostats_base}/delegation/v1"
            params = {
                "netuid": netuid,
                "limit": 200,  # Max per page
                "page": 1
            }

            # Fetch multiple pages if needed
            while True:
                response = requests.get(url, headers=self.taostats_headers,
                                      params=params, timeout=30)

                if response.status_code == 429:  # Rate limited
                    print("    Rate limited, waiting...")
                    time.sleep(5)
                    continue

                response.raise_for_status()
                data = response.json()

                items = data.get('data', [])
                if not items:
                    break

                # Filter by time range and DELEGATE action
                for item in items:
                    timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))

                    # Stop if we've gone past our time range
                    if timestamp < start_time:
                        return transactions

                    if start_time <= timestamp <= end_time:
                        if item['action'] == 'DELEGATE':
                            # Convert amount from rao to TAO
                            amount_tao = float(item['amount']) / RAO_PER_TAO

                            if amount_tao >= MIN_TRANSACTION_SIZE:
                                transactions.append({
                                    'wallet': item['nominator']['ss58'],
                                    'amount_tao': amount_tao,
                                    'timestamp': timestamp,
                                    'price': float(item['alpha_price_in_tao']),
                                    'type': 'DELEGATE'
                                })

                # Check pagination
                pagination = data.get('pagination', {})
                if not pagination.get('next_page'):
                    break

                params['page'] = pagination['next_page']
                time.sleep(0.5)  # Be nice to the API

        except Exception as e:
            print(f"    Error fetching delegations: {e}")

        return transactions

    def analyze_subnet(self, netuid: int, subnet_name: str, days: int = 30):
        """Analyze a subnet for prescient investors"""
        print(f"\n{'='*70}")
        print(f"Analyzing Subnet {netuid}: {subnet_name}")
        print('='*70)

        # Get price history
        price_history = self.get_price_history(netuid, days)
        if not price_history:
            print("  No price history available")
            return {}

        # Identify price spikes
        spikes = self.identify_price_spikes(price_history)
        print(f"\nFound {len(spikes)} price spike(s) of 5%+ in the last {days} days:")

        for spike_date, prev_price, curr_price in spikes:
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            print(f"  {spike_date}: {prev_price:.6f} → {curr_price:.6f} TAO "
                  f"({change_pct:+.2f}%)")

        if not spikes:
            print("  No significant price spikes found")
            return {}

        # For each spike, find wallets that bought in the previous 24 hours
        wallet_stats = defaultdict(lambda: {
            'successful_predictions': 0,
            'total_amount': 0.0,
            'transactions': []
        })

        for spike_date, prev_price, curr_price in spikes:
            # Look for transactions in the 24 hours before the spike
            # Make timezone-aware datetime objects
            from datetime import timezone
            spike_datetime = datetime.combine(spike_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            start_time = spike_datetime - timedelta(hours=24)
            end_time = spike_datetime

            print(f"\n  Analyzing transactions before {spike_date} spike...")
            transactions = self.get_wallet_transactions(netuid, start_time, end_time)

            print(f"    Found {len(transactions)} qualifying transactions (≥{MIN_TRANSACTION_SIZE} TAO)")

            for tx in transactions:
                wallet = tx['wallet']
                wallet_stats[wallet]['successful_predictions'] += 1
                wallet_stats[wallet]['total_amount'] += tx['amount_tao']
                wallet_stats[wallet]['transactions'].append({
                    'date': tx['timestamp'].strftime('%Y-%m-%d %H:%M'),
                    'amount': tx['amount_tao'],
                    'price': tx['price'],
                    'spike_date': spike_date.isoformat(),
                    'spike_gain': ((curr_price - prev_price) / prev_price) * 100
                })

        return wallet_stats

    def print_results(self, netuid: int, subnet_name: str, wallet_stats: Dict):
        """Print formatted results for a subnet"""
        if not wallet_stats:
            return

        print(f"\n{'='*70}")
        print(f"RESULTS FOR SUBNET {netuid}: {subnet_name}")
        print('='*70)

        # Sort by success rate, then by frequency
        sorted_wallets = sorted(
            wallet_stats.items(),
            key=lambda x: (x[1]['successful_predictions'], x[1]['total_amount']),
            reverse=True
        )

        print(f"\nFound {len(sorted_wallets)} unique wallet(s) that bought before price spikes:\n")

        for i, (wallet, stats) in enumerate(sorted_wallets, 1):
            frequency = stats['successful_predictions']
            total_amount = stats['total_amount']

            print(f"{i}. Wallet: {wallet}")
            print(f"   Success Rate: {frequency} time(s) bought before price spike")
            print(f"   Total Amount: {total_amount:.2f} TAO")
            print(f"   Transactions:")

            for tx in stats['transactions']:
                print(f"      • {tx['date']}: {tx['amount']:.2f} TAO at {tx['price']:.6f} TAO/alpha")
                print(f"        (Before {tx['spike_date']} spike of +{tx['spike_gain']:.2f}%)")

            print()

    def run(self, analyze_top_n: int = 10, include_subnet_2: bool = True, days: int = 30):
        """Main execution function"""
        print("="*70)
        print("BITTENSOR SUBNET INVESTOR DETECTION TOOL")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  • Minimum transaction size: {MIN_TRANSACTION_SIZE} TAO")
        print(f"  • Price increase threshold: {PRICE_INCREASE_THRESHOLD*100}%")
        print(f"  • Analysis period: Last {days} days")
        print(f"  • Analyzing top {analyze_top_n} subnets by market cap")
        if include_subnet_2:
            print(f"  • Including subnet 2 specifically")

        # Get top subnets
        top_subnets = self.get_top_subnets(limit=analyze_top_n)

        # Add subnet 2 if not in top list
        subnets_to_analyze = top_subnets.copy()
        if include_subnet_2:
            if not any(s['netuid'] == 2 for s in subnets_to_analyze):
                # Fetch subnet 2 info
                print("\nFetching subnet 2 info (specifically requested)...")
                all_subnets_url = f"{self.tao_app_base}/analytics/subnets/info"
                try:
                    response = requests.get(all_subnets_url, headers=self.tao_app_headers, timeout=30)
                    response.raise_for_status()
                    all_subnets = response.json()
                    subnet_2 = next((s for s in all_subnets if s['netuid'] == 2), None)
                    if subnet_2:
                        subnet_2['market_cap'] = subnet_2['tao_in'] * subnet_2['price']
                        subnets_to_analyze.append(subnet_2)
                except Exception as e:
                    print(f"  Error fetching subnet 2: {e}")

        # Analyze each subnet
        all_results = {}
        for subnet in subnets_to_analyze:
            netuid = subnet['netuid']
            name = subnet['subnet_name']
            wallet_stats = self.analyze_subnet(netuid, name, days)
            all_results[netuid] = (name, wallet_stats)

        # Print all results
        print(f"\n\n{'='*70}")
        print("FINAL RESULTS SUMMARY")
        print('='*70)

        for netuid, (name, wallet_stats) in all_results.items():
            self.print_results(netuid, name, wallet_stats)

        print(f"\n{'='*70}")
        print("Analysis complete!")
        print('='*70)

if __name__ == "__main__":
    detector = SubnetInvestorDetector()
    detector.run(
        analyze_top_n=5,  # Analyze top 5 subnets by market cap (to avoid rate limits)
        include_subnet_2=True,  # Always include subnet 2
        days=30  # Look at last 30 days
    )
