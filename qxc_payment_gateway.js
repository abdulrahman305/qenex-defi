/**
 * QXC Payment Gateway
 * Accept QXC payments on e-commerce platforms
 */

const { ethers } = require('ethers');
const express = require('express');
const cors = require('cors');

class QXCPaymentGateway {
    constructor(config) {
        this.config = {
            contractAddress: config.contractAddress || '0xb17654f3f068aded95a234de2532b9a478b858bf',
            rpcUrl: config.rpcUrl || 'https://eth-mainnet.public.blastapi.io',
            merchantWallet: config.merchantWallet,
            apiKey: config.apiKey,
            webhookUrl: config.webhookUrl,
            ...config
        };
        
        this.provider = new ethers.JsonRpcProvider(this.config.rpcUrl);
        this.payments = new Map();
        
        // Initialize Express server
        this.app = express();
        this.app.use(cors());
        this.app.use(express.json());
        
        this.setupRoutes();
    }
    
    setupRoutes() {
        // Create payment request
        this.app.post('/api/payments/create', async (req, res) => {
            try {
                const payment = await this.createPayment(req.body);
                res.json(payment);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });
        
        // Verify payment
        this.app.get('/api/payments/:paymentId/verify', async (req, res) => {
            try {
                const status = await this.verifyPayment(req.params.paymentId);
                res.json(status);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });
        
        // Get payment status
        this.app.get('/api/payments/:paymentId', async (req, res) => {
            const payment = this.payments.get(req.params.paymentId);
            if (payment) {
                res.json(payment);
            } else {
                res.status(404).json({ error: 'Payment not found' });
            }
        });
        
        // Webhook for payment confirmations
        this.app.post('/api/webhook/payment', async (req, res) => {
            const { paymentId, txHash } = req.body;
            await this.handlePaymentWebhook(paymentId, txHash);
            res.json({ success: true });
        });
    }
    
    async createPayment(options) {
        const {
            amount,
            currency = 'QXC',
            orderId,
            customerEmail,
            description,
            metadata = {}
        } = options;
        
        // Generate unique payment ID
        const paymentId = this.generatePaymentId();
        
        // Calculate QXC amount if currency is USD
        let qxcAmount = amount;
        if (currency === 'USD') {
            qxcAmount = await this.convertUsdToQxc(amount);
        }
        
        // Create payment object
        const payment = {
            id: paymentId,
            orderId,
            amount: qxcAmount,
            currency: 'QXC',
            originalAmount: amount,
            originalCurrency: currency,
            status: 'pending',
            merchantWallet: this.config.merchantWallet,
            customerEmail,
            description,
            metadata,
            createdAt: new Date().toISOString(),
            expiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 minutes
            paymentUrl: `https://pay.qenex.ai/${paymentId}`,
            qrCode: this.generateQRCode(paymentId, qxcAmount)
        };
        
        this.payments.set(paymentId, payment);
        
        // Set expiration timer
        setTimeout(() => {
            if (this.payments.get(paymentId)?.status === 'pending') {
                payment.status = 'expired';
            }
        }, 30 * 60 * 1000);
        
        return payment;
    }
    
    async verifyPayment(paymentId) {
        const payment = this.payments.get(paymentId);
        if (!payment) {
            throw new Error('Payment not found');
        }
        
        // Check blockchain for payment
        const contract = new ethers.Contract(
            this.config.contractAddress,
            [
                'event Transfer(address indexed from, address indexed to, uint256 value)',
                'function balanceOf(address) view returns (uint256)'
            ],
            this.provider
        );
        
        // Get recent transfers to merchant wallet
        const filter = contract.filters.Transfer(null, this.config.merchantWallet);
        const events = await contract.queryFilter(filter, -100); // Last 100 blocks
        
        // Check for matching payment
        for (const event of events) {
            const amount = ethers.formatEther(event.args.value);
            if (parseFloat(amount) === payment.amount) {
                payment.status = 'confirmed';
                payment.txHash = event.transactionHash;
                payment.confirmedAt = new Date().toISOString();
                
                // Send webhook notification
                await this.sendWebhook(payment);
                
                return payment;
            }
        }
        
        return payment;
    }
    
    async handlePaymentWebhook(paymentId, txHash) {
        const payment = this.payments.get(paymentId);
        if (!payment) return;
        
        // Verify transaction on blockchain
        const tx = await this.provider.getTransaction(txHash);
        if (tx && tx.to?.toLowerCase() === this.config.merchantWallet.toLowerCase()) {
            payment.status = 'confirmed';
            payment.txHash = txHash;
            payment.confirmedAt = new Date().toISOString();
        }
    }
    
    async sendWebhook(payment) {
        if (!this.config.webhookUrl) return;
        
        try {
            const response = await fetch(this.config.webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-QXC-Signature': this.generateSignature(payment)
                },
                body: JSON.stringify({
                    event: 'payment.confirmed',
                    payment
                })
            });
            
            return response.ok;
        } catch (error) {
            console.error('Webhook failed:', error);
            return false;
        }
    }
    
    async convertUsdToQxc(usdAmount) {
        // In production, fetch from price oracle
        const qxcPrice = 0.50; // $0.50 per QXC
        return usdAmount / qxcPrice;
    }
    
    generatePaymentId() {
        return 'pay_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    generateQRCode(paymentId, amount) {
        // Generate QR code data for payment
        const qrData = {
            to: this.config.merchantWallet,
            amount: amount,
            paymentId: paymentId,
            token: 'QXC'
        };
        
        return `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(JSON.stringify(qrData))}`;
    }
    
    generateSignature(data) {
        const crypto = require('crypto');
        return crypto
            .createHmac('sha256', this.config.apiKey)
            .update(JSON.stringify(data))
            .digest('hex');
    }
    
    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`QXC Payment Gateway running on port ${port}`);
        });
    }
}

// WooCommerce Plugin
class WooCommerceQXC {
    constructor(gateway) {
        this.gateway = gateway;
    }
    
    async processPayment(order) {
        const payment = await this.gateway.createPayment({
            amount: order.total,
            currency: order.currency,
            orderId: order.id,
            customerEmail: order.email,
            description: `Order #${order.id}`,
            metadata: {
                platform: 'woocommerce',
                items: order.items
            }
        });
        
        return {
            result: 'success',
            redirect: payment.paymentUrl
        };
    }
}

// Shopify Plugin
class ShopifyQXC {
    constructor(gateway) {
        this.gateway = gateway;
    }
    
    async createCheckout(checkout) {
        const payment = await this.gateway.createPayment({
            amount: checkout.total_price,
            currency: checkout.currency,
            orderId: checkout.id,
            customerEmail: checkout.email,
            description: `Checkout ${checkout.id}`,
            metadata: {
                platform: 'shopify',
                line_items: checkout.line_items
            }
        });
        
        return payment;
    }
}

// Export for use
module.exports = {
    QXCPaymentGateway,
    WooCommerceQXC,
    ShopifyQXC
};

// Example usage
if (require.main === module) {
    const gateway = new QXCPaymentGateway({
        merchantWallet: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb4',
        apiKey: 'qxc_live_key_abc123',
        webhookUrl: 'https://yourstore.com/webhooks/qxc'
    });
    
    gateway.start(3000);
}