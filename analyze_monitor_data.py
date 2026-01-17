#!/usr/bin/env python3
"""Query the real-time monitor database for investor patterns"""

import sqlite3
from datetime import datetime

DB_FILE = "subnet_monitor.db"

def analyze_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("="*70)
    print("SUBNET INVESTOR MONITOR - DATABASE ANALYSIS")
    print("="*70)

    # Overall stats
    cursor.execute('SELECT COUNT(*) FROM transactions')
    tx_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM prices')
    price_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM price_spikes')
    spike_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT wallet) FROM wallet_alerts')
    alert_count = cursor.fetchone()[0]

    print(f"\n📊 Overall Statistics:")
    print(f"  Total transactions recorded: {tx_count}")
    print(f"  Total price records: {price_count}")
    print(f"  Price spikes detected: {spike_count}")
    print(f"  Unique wallets flagged: {alert_count}")

    # Transactions by subnet
    cursor.execute('''
        SELECT netuid, COUNT(*) as tx_count, SUM(amount_tao) as total_volume
        FROM transactions
        GROUP BY netuid
        ORDER BY tx_count DESC
    ''')

    print(f"\n📈 Activity by Subnet:")
    for netuid, count, volume in cursor.fetchall():
        print(f"  Subnet {netuid}: {count} transactions, {volume:.2f} TAO volume")

    # Top wallets by frequency
    cursor.execute('''
        SELECT wallet, COUNT(*) as tx_count, SUM(amount_tao) as total_tao,
               MIN(timestamp) as first_tx, MAX(timestamp) as last_tx
        FROM transactions
        GROUP BY wallet
        ORDER BY tx_count DESC
        LIMIT 10
    ''')

    print(f"\n🔥 Most Active Wallets:")
    for wallet, count, total, first, last in cursor.fetchall():
        print(f"  {wallet}")
        print(f"    Transactions: {count}")
        print(f"    Total volume: {total:.2f} TAO")
        print(f"    First tx: {first}")
        print(f"    Last tx: {last}")
        print()

    # Recent large transactions
    cursor.execute('''
        SELECT netuid, wallet, amount_tao, price, timestamp
        FROM transactions
        WHERE amount_tao >= 10
        ORDER BY timestamp DESC
        LIMIT 15
    ''')

    print(f"💰 Recent Large Transactions (≥10 TAO):")
    for netuid, wallet, amount, price, timestamp in cursor.fetchall():
        print(f"  {timestamp}: Subnet {netuid}")
        print(f"    Wallet: {wallet}")
        print(f"    Amount: {amount:.2f} TAO at {price:.6f} TAO/alpha")
        print()

    # Price spikes if any
    if spike_count > 0:
        cursor.execute('''
            SELECT netuid, spike_timestamp, prev_price, new_price, percent_change
            FROM price_spikes
            ORDER BY spike_timestamp DESC
        ''')

        print(f"🚨 Price Spikes Detected:")
        for netuid, timestamp, prev, new, pct in cursor.fetchall():
            print(f"  {timestamp}: Subnet {netuid}")
            print(f"    {prev:.6f} → {new:.6f} TAO ({pct:+.2f}%)")

            # Show wallets that bought before this spike
            cursor.execute('''
                SELECT wa.wallet, wa.amount_tao, wa.buy_price, wa.bought_at
                FROM wallet_alerts wa
                JOIN price_spikes ps ON wa.spike_id = ps.id
                WHERE ps.netuid = ? AND ps.spike_timestamp = ?
                ORDER BY wa.amount_tao DESC
            ''', (netuid, timestamp))

            buyers = cursor.fetchall()
            if buyers:
                print(f"    Wallets that bought before spike:")
                for wallet, amount, buy_price, bought_at in buyers:
                    print(f"      • {wallet[:30]}...")
                    print(f"        {amount:.2f} TAO @ {buy_price:.6f} on {bought_at}")
            print()

    # Time range of data
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM transactions')
    min_time, max_time = cursor.fetchone()

    if min_time and max_time:
        print(f"\n⏰ Data Collection Period:")
        print(f"  From: {min_time}")
        print(f"  To: {max_time}")

    conn.close()

if __name__ == "__main__":
    analyze_database()
