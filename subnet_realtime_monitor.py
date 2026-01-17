#!/usr/bin/env python3
"""
Bittensor Subnet Real-Time Investor Monitor

This script monitors subnets in real-time, tracking prices and transactions.
When a price increase of 5%+ is detected, it identifies wallets that bought
in the previous 24 hours.

Since historical transaction data is limited, this script collects data
as it happens and stores it for later analysis.
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import List, Dict
import time
import sqlite3

# API Configuration
TAOSTATS_API_KEY = "tao-b33d0cd0-e17c-405f-bd44-7effe34e9aac:bf3d3b55"
TAO_APP_API_KEY = "5c8f0bf8cb8acee5ad1ae3787e87a84f4b5d1be97d75c11b52c61fee9d99e6ba"

# Configuration
MIN_TRANSACTION_SIZE = 3.0  # TAO
PRICE_INCREASE_THRESHOLD = 0.05  # 5%
RAO_PER_TAO = 1_000_000_000
CHECK_INTERVAL_SECONDS = 300  # Check every 5 minutes
SUBNETS_TO_MONITOR = [2, 4, 8, 9, 44]  # Add more as needed

# Database file
DB_FILE = "subnet_monitor.db"

class SubnetRealtimeMonitor:
    def __init__(self):
        self.taostats_headers = {"Authorization": TAOSTATS_API_KEY}
        self.tao_app_headers = {"X-API-Key": TAO_APP_API_KEY}
        self.taostats_base = "https://api.taostats.io/api"
        self.tao_app_base = "https://api.tao.app/api/beta"

        # In-memory price history (last 24 hours)
        self.price_history = defaultdict(lambda: deque(maxlen=288))  # 24h at 5min intervals

        # Initialize database
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for storing transactions and price data"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Prices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                netuid INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                price REAL NOT NULL,
                UNIQUE(netuid, timestamp)
            )
        ''')

        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                netuid INTEGER NOT NULL,
                wallet TEXT NOT NULL,
                amount_tao REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                action TEXT NOT NULL,
                UNIQUE(netuid, wallet, timestamp, action)
            )
        ''')

        # Price spikes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_spikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                netuid INTEGER NOT NULL,
                spike_timestamp DATETIME NOT NULL,
                prev_price REAL NOT NULL,
                new_price REAL NOT NULL,
                percent_change REAL NOT NULL,
                detected_at DATETIME NOT NULL,
                UNIQUE(netuid, spike_timestamp)
            )
        ''')

        # Wallet alerts table (wallets that bought before spike)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spike_id INTEGER NOT NULL,
                wallet TEXT NOT NULL,
                bought_at DATETIME NOT NULL,
                amount_tao REAL NOT NULL,
                buy_price REAL NOT NULL,
                FOREIGN KEY (spike_id) REFERENCES price_spikes(id),
                UNIQUE(spike_id, wallet, bought_at)
            )
        ''')

        conn.commit()
        conn.close()

        print(f"Database initialized: {DB_FILE}")

    def get_current_price(self, netuid: int) -> float:
        """Get current price for a subnet"""
        url = f"{self.tao_app_base}/analytics/subnets/info/{netuid}"
        try:
            response = requests.get(url, headers=self.tao_app_headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('price', 0.0)
        except Exception as e:
            print(f"  Error fetching price for netuid {netuid}: {e}")
            return 0.0

    def get_recent_transactions(self, netuid: int) -> List[Dict]:
        """Get all recent transactions for a subnet"""
        transactions = []
        url = f"{self.taostats_base}/delegation/v1"
        params = {"netuid": netuid, "limit": 200, "page": 1}

        try:
            response = requests.get(url, headers=self.taostats_headers,
                                  params=params, timeout=10)

            if response.status_code == 429:
                print(f"  Rate limited for netuid {netuid}")
                return transactions

            response.raise_for_status()
            data = response.json()

            for item in data.get('data', []):
                timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))

                # Only process DELEGATE actions
                if item['action'] == 'DELEGATE':
                    amount_tao = float(item['amount']) / RAO_PER_TAO

                    if amount_tao >= MIN_TRANSACTION_SIZE:
                        transactions.append({
                            'wallet': item['nominator']['ss58'],
                            'amount_tao': amount_tao,
                            'timestamp': timestamp,
                            'price': float(item['alpha_price_in_tao']),
                            'action': 'DELEGATE'
                        })

        except Exception as e:
            print(f"  Error fetching transactions for netuid {netuid}: {e}")

        return transactions

    def store_price(self, netuid: int, price: float, timestamp: datetime):
        """Store price in database"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO prices (netuid, timestamp, price) VALUES (?, ?, ?)',
                (netuid, timestamp.isoformat(), price)
            )
            conn.commit()
        except Exception as e:
            print(f"  Error storing price: {e}")
        finally:
            conn.close()

    def store_transaction(self, netuid: int, tx: Dict):
        """Store transaction in database"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT OR IGNORE INTO transactions
                   (netuid, wallet, amount_tao, price, timestamp, action)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (netuid, tx['wallet'], tx['amount_tao'], tx['price'],
                 tx['timestamp'].isoformat(), tx['action'])
            )
            conn.commit()
        except Exception as e:
            print(f"  Error storing transaction: {e}")
        finally:
            conn.close()

    def check_for_price_spike(self, netuid: int, current_price: float, timestamp: datetime):
        """Check if current price represents a spike compared to recent history"""
        history = self.price_history[netuid]

        if len(history) < 2:
            return None

        # Get price from ~5-10 minutes ago
        prev_price = history[-2][1] if len(history) >= 2 else history[0][1]

        price_change = (current_price - prev_price) / prev_price

        if price_change >= PRICE_INCREASE_THRESHOLD:
            return {
                'netuid': netuid,
                'timestamp': timestamp,
                'prev_price': prev_price,
                'new_price': current_price,
                'percent_change': price_change * 100
            }

        return None

    def record_price_spike(self, spike: Dict) -> int:
        """Record a price spike and return its ID"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT OR IGNORE INTO price_spikes
                   (netuid, spike_timestamp, prev_price, new_price, percent_change, detected_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (spike['netuid'], spike['timestamp'].isoformat(),
                 spike['prev_price'], spike['new_price'],
                 spike['percent_change'], datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Get the spike ID
            cursor.execute(
                'SELECT id FROM price_spikes WHERE netuid = ? AND spike_timestamp = ?',
                (spike['netuid'], spike['timestamp'].isoformat())
            )
            spike_id = cursor.fetchone()[0]

            return spike_id

        except Exception as e:
            print(f"  Error recording spike: {e}")
            return None
        finally:
            conn.close()

    def find_prescient_buyers(self, netuid: int, spike_time: datetime):
        """Find wallets that bought in the 24 hours before a spike"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        lookback_time = spike_time - timedelta(hours=24)

        cursor.execute(
            '''SELECT wallet, amount_tao, price, timestamp
               FROM transactions
               WHERE netuid = ? AND timestamp >= ? AND timestamp < ?
               ORDER BY timestamp DESC''',
            (netuid, lookback_time.isoformat(), spike_time.isoformat())
        )

        buyers = cursor.fetchall()
        conn.close()

        return [{
            'wallet': row[0],
            'amount_tao': row[1],
            'price': row[2],
            'timestamp': datetime.fromisoformat(row[3])
        } for row in buyers]

    def monitor_cycle(self):
        """Run one monitoring cycle"""
        timestamp = datetime.now(timezone.utc)

        print(f"\n{'='*70}")
        print(f"Monitoring Cycle: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print('='*70)

        for netuid in SUBNETS_TO_MONITOR:
            print(f"\nSubnet {netuid}:")

            # Get current price
            price = self.get_current_price(netuid)
            if price > 0:
                print(f"  Current price: {price:.6f} TAO")

                # Store price
                self.store_price(netuid, price, timestamp)

                # Add to in-memory history
                self.price_history[netuid].append((timestamp, price))

                # Check for price spike
                spike = self.check_for_price_spike(netuid, price, timestamp)

                if spike:
                    print(f"\n  🚨 PRICE SPIKE DETECTED! 🚨")
                    print(f"  {spike['prev_price']:.6f} → {spike['new_price']:.6f} TAO "
                          f"({spike['percent_change']:+.2f}%)")

                    # Record spike
                    spike_id = self.record_price_spike(spike)

                    if spike_id:
                        # Find buyers from last 24 hours
                        buyers = self.find_prescient_buyers(netuid, timestamp)

                        if buyers:
                            print(f"\n  Found {len(buyers)} wallet(s) that bought in the last 24h:")

                            # Store alerts
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()

                            for buyer in buyers:
                                print(f"    • {buyer['wallet']}: {buyer['amount_tao']:.2f} TAO "
                                      f"at {buyer['price']:.6f}")

                                cursor.execute(
                                    '''INSERT OR IGNORE INTO wallet_alerts
                                       (spike_id, wallet, bought_at, amount_tao, buy_price)
                                       VALUES (?, ?, ?, ?, ?)''',
                                    (spike_id, buyer['wallet'],
                                     buyer['timestamp'].isoformat(),
                                     buyer['amount_tao'], buyer['price'])
                                )

                            conn.commit()
                            conn.close()
                        else:
                            print(f"  No qualifying buyers found in the last 24h")

            # Get recent transactions
            transactions = self.get_recent_transactions(netuid)
            print(f"  Recent transactions: {len(transactions)} (≥{MIN_TRANSACTION_SIZE} TAO)")

            # Store transactions
            for tx in transactions:
                self.store_transaction(netuid, tx)

            time.sleep(1)  # Rate limiting between subnets

    def show_statistics(self):
        """Show statistics from the database"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print(f"\n{'='*70}")
        print("DATABASE STATISTICS")
        print('='*70)

        # Price spikes
        cursor.execute('SELECT COUNT(*) FROM price_spikes')
        spike_count = cursor.fetchone()[0]
        print(f"\nTotal price spikes detected: {spike_count}")

        if spike_count > 0:
            cursor.execute('''
                SELECT netuid, COUNT(*) as spike_count
                FROM price_spikes
                GROUP BY netuid
                ORDER BY spike_count DESC
            ''')
            print("\nSpikes by subnet:")
            for row in cursor.fetchall():
                print(f"  Netuid {row[0]}: {row[1]} spike(s)")

        # Wallet alerts
        cursor.execute('SELECT COUNT(DISTINCT wallet) FROM wallet_alerts')
        unique_wallets = cursor.fetchone()[0]
        print(f"\nUnique wallets flagged: {unique_wallets}")

        if unique_wallets > 0:
            cursor.execute('''
                SELECT wallet, COUNT(*) as alert_count, SUM(amount_tao) as total_tao
                FROM wallet_alerts
                GROUP BY wallet
                ORDER BY alert_count DESC
                LIMIT 10
            ''')
            print("\nTop wallets (by frequency):")
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"  {i}. {row[0]}: {row[1]} spike(s), {row[2]:.2f} TAO total")

        conn.close()

    def run(self, cycles: int = None):
        """Run the monitor (cycles=None for infinite)"""
        print("="*70)
        print("BITTENSOR SUBNET REAL-TIME INVESTOR MONITOR")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  • Monitoring subnets: {SUBNETS_TO_MONITOR}")
        print(f"  • Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        print(f"  • Min transaction size: {MIN_TRANSACTION_SIZE} TAO")
        print(f"  • Price spike threshold: {PRICE_INCREASE_THRESHOLD*100}%")
        print(f"  • Database: {DB_FILE}")
        print(f"\nPress Ctrl+C to stop")

        cycle_count = 0

        try:
            while True:
                self.monitor_cycle()

                cycle_count += 1

                if cycles and cycle_count >= cycles:
                    break

                # Show stats every 10 cycles
                if cycle_count % 10 == 0:
                    self.show_statistics()

                print(f"\nWaiting {CHECK_INTERVAL_SECONDS} seconds until next check...")
                time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            self.show_statistics()
            print("\nData saved to:", DB_FILE)

if __name__ == "__main__":
    monitor = SubnetRealtimeMonitor()
    monitor.run()  # Run indefinitely (or specify cycles=N for testing)
