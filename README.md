# DeFi Platform

Automated Market Maker (AMM) implementation with liquidity pools.

## Features

### Core Functionality
- **Token Swaps** - Exchange tokens using constant product formula
- **Liquidity Pools** - Provide liquidity and earn fees
- **LP Tokens** - Receive shares representing pool ownership
- **Fee Distribution** - Automatic fee collection (0.3% default)

## Architecture

```
     ┌──────────────┐
     │ Liquidity    │
     │    Pool      │
     │  X × Y = K   │
     └──────┬───────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼───┐      ┌────▼────┐
│ Swap  │      │Add/Remove│
│Tokens │      │Liquidity │
└───────┘      └─────────┘
```

## AMM Mathematics

### Constant Product Formula
```
x × y = k

Where:
- x = Reserve of token A
- y = Reserve of token B
- k = Constant product
```

### Swap Calculation
```python
output = (input × reserve_out) / (reserve_in + input)
```

### Price Impact
```python
price_impact = 1 - (reserve_out / (reserve_in + input))
```

## Usage

### Initialize Platform
```python
from defi import DeFiPlatform

defi = DeFiPlatform()
```

### Create Pool
```python
pool_id = defi.create_pool("ETH", "USDC", fee_rate=0.003)
```

### Add Liquidity
```python
lp_tokens = defi.add_liquidity(
    user_id=1,
    token_a="ETH",
    token_b="USDC",
    amount_a=10,
    amount_b=20000
)
```

### Swap Tokens
```python
usdc_received = defi.swap(
    user_id=1,
    token_in="ETH",
    token_out="USDC",
    amount_in=1
)
```

## Pool Statistics

```python
stats = defi.get_pool_stats("ETH-USDC")
# Returns:
{
    "reserve_a": 100,
    "reserve_b": 200000,
    "total_shares": 1414.21,
    "price_a": 2000,
    "price_b": 0.0005,
    "tvl": 400000
}
```

## Security

- Balance validation before operations
- Slippage protection mechanisms
- Atomic transaction processing
- Integer overflow prevention

## Configuration

```python
config = {
    "min_liquidity": 0.001,
    "max_slippage": 0.05,
    "default_fee": 0.003
}
```

## License

MIT