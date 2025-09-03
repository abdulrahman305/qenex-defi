const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Initialize provider and contracts
const provider = new ethers.providers.JsonRpcProvider(process.env.MAINNET_RPC_URL);

// Load contract ABIs and addresses
const contracts = {
  token: new ethers.Contract(
    process.env.QXC_TOKEN_ADDRESS,
    require('./abis/QXCToken.json'),
    provider
  ),
  staking: new ethers.Contract(
    process.env.QXC_STAKING_ADDRESS,
    require('./abis/QXCStaking.json'),
    provider
  )
};

// Routes
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Token endpoints
app.get('/api/token/info', async (req, res) => {
  try {
    const [name, symbol, decimals, totalSupply] = await Promise.all([
      contracts.token.name(),
      contracts.token.symbol(),
      contracts.token.decimals(),
      contracts.token.totalSupply()
    ]);
    
    res.json({
      name,
      symbol,
      decimals: decimals.toString(),
      totalSupply: ethers.utils.formatEther(totalSupply),
      address: process.env.QXC_TOKEN_ADDRESS
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/token/balance/:address', async (req, res) => {
  try {
    const balance = await contracts.token.balanceOf(req.params.address);
    res.json({ 
      address: req.params.address,
      balance: ethers.utils.formatEther(balance)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Staking endpoints
app.get('/api/staking/info', async (req, res) => {
  try {
    const [totalStaked, rewardRate, apr] = await Promise.all([
      contracts.staking.totalStaked(),
      contracts.staking.rewardRate(),
      contracts.staking.APR()
    ]);
    
    res.json({
      totalStaked: ethers.utils.formatEther(totalStaked),
      rewardRate: ethers.utils.formatEther(rewardRate),
      apr: apr.toString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/staking/user/:address', async (req, res) => {
  try {
    const [staked, rewards] = await Promise.all([
      contracts.staking.stakes(req.params.address),
      contracts.staking.calculateReward(req.params.address)
    ]);
    
    res.json({
      address: req.params.address,
      staked: ethers.utils.formatEther(staked.amount || 0),
      rewards: ethers.utils.formatEther(rewards)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Price endpoint (mock)
app.get('/api/token/price', (req, res) => {
  res.json({
    usd: 1.25,
    eth: 0.0005,
    btc: 0.00003,
    change24h: 5.2
  });
});

// Market data endpoint
app.get('/api/market/stats', (req, res) => {
  res.json({
    marketCap: 1903875,
    volume24h: 125000,
    circulatingSupply: 1525.30,
    holders: 1250,
    transactions24h: 3500
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// Start server
app.listen(PORT, () => {
  console.log(`QXC Token API running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});