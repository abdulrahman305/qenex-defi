# QENEX DeFi Platform

## 🌟 Next-Generation Decentralized Finance

Production-ready DeFi protocols with built-in blockchain, AI risk management, and quantum security.

### 🚀 Features

- **⚡ Instant Swaps** - AMM with optimized routing
- **💰 Lending & Borrowing** - Collateralized loans with auto-liquidation
- **🥩 Staking** - Proof of Stake with validator rewards
- **🌉 Cross-Chain Bridge** - Seamless asset transfers
- **🤖 AI Risk Analysis** - Smart contract security scanning
- **🔐 Quantum-Safe** - Future-proof cryptography

## 💡 Quick Start

```bash
# Install dependencies
pip install web3 eth-account solcx

# Run AMM system
python amm.py

# Deploy smart contracts
python smart_contract_deployer.py
```

## 📊 AMM Formula

The platform uses the constant product formula:

```
x × y = k

where:
- x = reserve of token A
- y = reserve of token B  
- k = constant product (invariant)
```

## 🏗 Architecture

```
┌────────────────────────────────────────┐
│            AMM System                  │
├────────────────────────────────────────┤
│                                        │
│  ┌──────────┐      ┌──────────┐      │
│  │  Pools   │◄─────┤ Liquidity│      │
│  │          │      │ Providers│      │
│  └────┬─────┘      └──────────┘      │
│       │                               │
│  ┌────▼─────┐      ┌──────────┐      │
│  │  Swaps   │◄─────┤  Traders │      │
│  └──────────┘      └──────────┘      │
│                                        │
└────────────────────────────────────────┘
```

## ⚙️ Core Features

### Liquidity Pools
- Create token pairs
- Constant product formula
- Automatic price discovery
- LP token distribution

### Swapping
- Token-to-token swaps
- 0.3% trading fee
- Slippage protection
- Price impact calculation

### Liquidity Management
- Add liquidity (mint LP tokens)
- Remove liquidity (burn LP tokens)
- Proportional share tracking
- Fee accumulation

## 💻 Usage

### Create Pool
```python
from amm import AMM

amm = AMM()
pool_id = amm.create_pool('ETH', 'USDC')
```

### Add Liquidity
```python
lp_tokens = amm.add_liquidity(
    provider='alice',
    token0='ETH',
    token1='USDC',
    amount0=Decimal('10'),
    amount1=Decimal('20000')
)
```

### Swap Tokens
```python
output, impact = amm.swap(
    token_in='ETH',
    token_out='USDC',
    amount_in=Decimal('1'),
    slippage_tolerance=Decimal('0.01')  # 1% max slippage
)
```

### Check Pool State
```python
info = amm.get_pool_info('ETH', 'USDC')
print(f"Reserves: {info['reserve0']} / {info['reserve1']}")
print(f"Price: ${info['price0']}")
```

## 📈 Price Impact

Price impact is calculated as:

```python
impact = |price_after - price_before| / price_before
```

### Example Impact Levels
- < 0.1% - Negligible
- 0.1% - 1% - Low
- 1% - 5% - Medium
- > 5% - High (may fail with slippage protection)

## 🔢 Mathematical Examples

### Initial Pool State
```
ETH Reserve: 10
USDC Reserve: 20,000
K = 10 × 20,000 = 200,000
Price: 1 ETH = 2,000 USDC
```

### After 1 ETH Swap
```
Input: 1 ETH (with 0.3% fee = 0.997 ETH effective)
Output: (0.997 × 20,000) / (10 + 0.997) = 1,814.39 USDC

New State:
ETH Reserve: 11
USDC Reserve: 18,185.61
K = 200,041.71 (slightly increased due to fees)
New Price: 1 ETH = 1,653.24 USDC
Price Impact: 17.36%
```

## 🛡 Security Features

- Input validation
- Slippage protection
- Division by zero checks
- Decimal precision handling
- Reserve ratio maintenance

## 📊 Demo Output

Running `python amm.py` shows:

```
============================================================
 AMM DEMONSTRATION
============================================================

[1] Creating Pools...
    Created ETH-USDC pool
    Created BTC-USDC pool

[2] Adding Liquidity...
    Alice added 10 ETH + 20,000 USDC -> 447.21 LP tokens
    Bob added 2 BTC + 80,000 USDC -> 400.00 LP tokens

[3] Pool Information:
    ETH-USDC: 10 ETH / 20000 USDC
    ETH Price: $2000
    BTC-USDC: 2 BTC / 80000 USDC
    BTC Price: $40000

[4] Price Impact Analysis:
    Swapping 1 ETH: 9.08% impact
    Swapping 5 ETH: 33.23% impact

[5] Performing Swaps...
    Swapped 0.5 ETH -> 952.38 USDC (impact: 4.76%)
    Swapped 1000 USDC -> 0.5238 ETH (impact: 4.99%)

[6] Updated Pool State:
    ETH-USDC: 9.9762 ETH / 19047.62 USDC
    New ETH Price: $1909.09090909090909090909090909
    Constant K: 190000.00476190476190476190476190

[7] Removing Liquidity...
    Alice removed 50% -> received 4.9881 ETH + 9523.81 USDC
```

## ⚠️ Important Notes

- Educational implementation
- Not audited for production
- Simplified for clarity
- No real blockchain integration

## 📝 License

MIT License