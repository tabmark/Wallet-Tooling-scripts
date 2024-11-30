import subprocess

# Update the wallet data below: Change 'wallet_name' to your actual wallet name and 
# 'current_staked_balance' to the current staked balance for each of your wallets.
wallet_data = {
    "wallet_name1": 7.267524582,  # Replace with actual wallet and balance
    "wallet_name2": 6.999491562,  # Replace with actual wallet and balance
    # ... Add more wallets as needed ...
}

def unstake_from_wallet(wallet_name, amount):
    # Replace 'put password here' with your actual wallet password.
    password = "put password here"
    
    expect_script = f"""
    spawn btcli stake remove --amount {amount} --wallet.name {wallet_name} --wallet.hotkey {wallet_name}
    expect "Do you want to unstake from the following keys to {wallet_name}:"
    send "y\\r"
    expect "Enter password to unlock key:"
    send "{password}\\r"
    expect "Do you want to unstake:"
    send "y\\r"
    expect eof
    """

    # Running the expect script
    process = subprocess.run(['expect'], input=expect_script, text=True, capture_output=True)
    return process.stdout

# Update this to whatever you want to keep your staked balance at.
target_balance = 7.0

for wallet_name, current_balance in wallet_data.items():
    if current_balance > target_balance:
        amount_to_unstake = current_balance - target_balance
        print(f"Unstaking {amount_to_unstake} from wallet {wallet_name}")
        result = unstake_from_wallet(wallet_name, amount_to_unstake)
        print(result)
