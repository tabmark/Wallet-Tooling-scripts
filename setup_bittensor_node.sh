#!/bin/bash
# Bittensor Node Setup Guide
# Run this on Ubuntu 22.04+ or similar Linux distribution

echo "=========================================="
echo "Bittensor Archive Node Setup"
echo "=========================================="

# 1. Install dependencies
echo -e "\n[1/5] Installing dependencies..."
sudo apt update
sudo apt install -y build-essential git clang curl libssl-dev llvm libudev-dev protobuf-compiler

# 2. Install Rust
echo -e "\n[2/5] Installing Rust..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
rustup default stable
rustup update

# 3. Clone Subtensor (Bittensor blockchain node)
echo -e "\n[3/5] Cloning Subtensor repository..."
cd ~
git clone https://github.com/opentensor/subtensor.git
cd subtensor

# 4. Build the node (this takes 20-60 minutes)
echo -e "\n[4/5] Building Subtensor (this will take a while)..."
cargo build --release --features runtime-benchmarks

# 5. Run as archive node
echo -e "\n[5/5] Starting archive node..."
./target/release/node-subtensor \
  --chain raw_spec.json \
  --base-path /tmp/blockchain \
  --sync=full \
  --pruning archive \
  --name "MyBittensorArchiveNode" \
  --rpc-cors all \
  --rpc-methods Unsafe \
  --rpc-external \
  --ws-external

echo "=========================================="
echo "Node started! It will sync blockchain history."
echo "Initial sync may take 24-48 hours."
echo "=========================================="
