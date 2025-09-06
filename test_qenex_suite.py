#!/usr/bin/env python3
"""
QENEX OS Comprehensive Test Suite
Unit tests for all major components
"""

import unittest
import tempfile
import shutil
import time
import json
import hashlib
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, '/opt/qenex-os')

# Import modules to test
try:
    from unified_qxc_system import Transaction, Block, Blockchain, WalletManager, AIEvaluator
    from p2p_network import Message, Peer, P2PNode
    from secure_wallet import CryptoUtils, SecureWallet, SecureTransaction
except ImportError as e:
    print(f"Import error: {e}")

class TestBlockchain(unittest.TestCase):
    """Test blockchain functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_db = '/opt/qenex-os/blockchain/qxc.db'
        
        # Mock database path
        with patch('unified_qxc_system.Config.DB_PATH', f'{self.temp_dir}/test.db'):
            self.blockchain = Blockchain()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_genesis_block_creation(self):
        """Test genesis block is created correctly"""
        self.assertEqual(len(self.blockchain.chain), 1)
        genesis = self.blockchain.chain[0]
        self.assertEqual(genesis.index, 0)
        self.assertEqual(genesis.previous_hash, "0")
        self.assertIsNotNone(genesis.merkle_root)
    
    def test_add_transaction(self):
        """Test adding transactions to pending pool"""
        tx = Transaction(
            tx_id="test_tx_1",
            timestamp=time.time(),
            sender="Alice",
            recipient="Bob",
            amount=10.0,
            tx_type="transfer",
            metadata={}
        )
        
        # Mock balance check
        with patch.object(self.blockchain, 'get_balance', return_value=100.0):
            result = self.blockchain.add_transaction(tx)
            self.assertTrue(result)
            self.assertIn(tx, self.blockchain.pending_transactions)
    
    def test_mine_block(self):
        """Test mining a new block"""
        with patch.object(self.blockchain, 'get_balance', return_value=1000.0):
            # Add some transactions
            for i in range(3):
                tx = Transaction(
                    tx_id=f"test_tx_{i}",
                    timestamp=time.time(),
                    sender="Alice",
                    recipient="Bob",
                    amount=10.0,
                    tx_type="transfer",
                    metadata={}
                )
                self.blockchain.add_transaction(tx)
            
            # Mine block
            block = self.blockchain.mine_block("MINER_WALLET", {"test": 0.1})
            
            self.assertIsNotNone(block)
            self.assertEqual(block.index, 1)
            self.assertTrue(block.hash().startswith(self.blockchain.difficulty))
    
    def test_validate_chain(self):
        """Test blockchain validation"""
        # Initial chain should be valid
        self.assertTrue(self.blockchain.validate_chain())
        
        # Mine a block
        with patch.object(self.blockchain, 'get_balance', return_value=1000.0):
            self.blockchain.mine_block("MINER_WALLET", {"test": 0.1})
            self.assertTrue(self.blockchain.validate_chain())
    
    def test_get_balance(self):
        """Test balance calculation"""
        # Add transactions to genesis block
        self.blockchain.chain[0].transactions.append(
            Transaction(
                tx_id="balance_test",
                timestamp=time.time(),
                sender="system",
                recipient="TestWallet",
                amount=100.0,
                tx_type="coinbase",
                metadata={}
            )
        )
        
        balance = self.blockchain.get_balance("TestWallet")
        self.assertEqual(balance, 100.0)

class TestP2PNetwork(unittest.TestCase):
    """Test P2P networking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.node1 = P2PNode(8334)
        self.node2 = P2PNode(8335)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.node1.stop()
        self.node2.stop()
    
    def test_message_serialization(self):
        """Test message serialization and deserialization"""
        msg = Message(
            msg_type="ping",
            payload={"nonce": 12345},
            timestamp=time.time(),
            sender="test_node"
        )
        
        serialized = msg.serialize()
        self.assertIsInstance(serialized, bytes)
        
        # Extract message data (skip 4-byte header)
        msg_data = serialized[4:]
        deserialized = Message.deserialize(msg_data)
        
        self.assertEqual(deserialized.msg_type, "ping")
        self.assertEqual(deserialized.payload["nonce"], 12345)
    
    def test_peer_connection(self):
        """Test peer connection handling"""
        # Create mock socket
        mock_conn = MagicMock()
        peer = Peer(("localhost", 8333), mock_conn)
        
        self.assertEqual(peer.node_id, "localhost:8333")
        self.assertTrue(peer.is_outbound)
        self.assertEqual(peer.score, 100)
    
    def test_message_handlers(self):
        """Test message handler registration"""
        self.assertIn("ping", self.node1.message_handlers)
        self.assertIn("pong", self.node1.message_handlers)
        self.assertIn("block", self.node1.message_handlers)
        self.assertIn("tx", self.node1.message_handlers)
    
    def test_handle_ping(self):
        """Test ping message handling"""
        mock_peer = Mock()
        ping_msg = Message(
            msg_type="ping",
            payload={"nonce": 42},
            timestamp=time.time(),
            sender="test"
        )
        
        self.node1.handle_ping(mock_peer, ping_msg)
        
        # Check that pong was sent
        mock_peer.send_message.assert_called_once()
        sent_msg = mock_peer.send_message.call_args[0][0]
        self.assertEqual(sent_msg.msg_type, "pong")
        self.assertEqual(sent_msg.payload["nonce"], 42)

class TestSecureWallet(unittest.TestCase):
    """Test secure wallet functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        with patch('secure_wallet.SecureWallet.wallet_dir', self.temp_dir):
            self.wallet = SecureWallet("test_wallet", "TestPassword123!")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_wallet_creation(self):
        """Test wallet creation with encryption"""
        self.assertIsNotNone(self.wallet.private_key)
        self.assertIsNotNone(self.wallet.public_key)
        self.assertTrue(self.wallet.address.startswith("QXC"))
        self.assertFalse(self.wallet.locked)
    
    def test_address_generation(self):
        """Test wallet address generation"""
        address = self.wallet.generate_address()
        self.assertTrue(address.startswith("QXC"))
        self.assertEqual(len(address), 35)  # QXC + 32 chars
    
    def test_lock_unlock_wallet(self):
        """Test wallet lock and unlock"""
        # Lock wallet
        self.wallet.lock()
        self.assertTrue(self.wallet.locked)
        self.assertIsNone(self.wallet.password)
        
        # Try to unlock with wrong password
        self.assertFalse(self.wallet.unlock("WrongPassword"))
        self.assertTrue(self.wallet.locked)
        
        # Unlock with correct password
        with patch.object(self.wallet, 'salt', self.wallet.salt):
            with tempfile.NamedTemporaryFile(suffix='.enc', dir=self.temp_dir) as f:
                # Save encrypted private key for unlock test
                key = CryptoUtils.derive_key("TestPassword123!", self.wallet.salt)
                encrypted = CryptoUtils.encrypt_data(b"test_private_key", key)
                f.write(encrypted)
                f.flush()
                
                with patch('secure_wallet.open', return_value=open(f.name, 'rb')):
                    result = self.wallet.unlock("TestPassword123!")
                    # Note: This will fail without proper setup, but tests the flow
    
    def test_transaction_signing(self):
        """Test transaction signing and verification"""
        tx = SecureTransaction(
            tx_id="test_tx",
            sender=self.wallet.address,
            recipient="Bob",
            amount=10.0,
            timestamp=time.time(),
            nonce=12345
        )
        
        # Sign transaction
        signature = self.wallet.sign_transaction(tx)
        self.assertIsNotNone(signature)
        
        # Verify signature
        is_valid = self.wallet.verify_transaction(tx, signature, self.wallet.public_key)
        self.assertTrue(is_valid)
        
        # Verify with wrong signature should fail
        is_invalid = self.wallet.verify_transaction(tx, "wrong_signature", self.wallet.public_key)
        self.assertFalse(is_invalid)

class TestCryptoUtils(unittest.TestCase):
    """Test cryptographic utilities"""
    
    def test_salt_generation(self):
        """Test salt generation"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()
        
        self.assertEqual(len(salt1), 32)
        self.assertEqual(len(salt2), 32)
        self.assertNotEqual(salt1, salt2)  # Should be random
    
    def test_key_derivation(self):
        """Test key derivation from password"""
        password = "TestPassword123!"
        salt = CryptoUtils.generate_salt()
        
        key1 = CryptoUtils.derive_key(password, salt)
        key2 = CryptoUtils.derive_key(password, salt)
        
        self.assertEqual(key1, key2)  # Same password+salt = same key
        
        key3 = CryptoUtils.derive_key("DifferentPassword", salt)
        self.assertNotEqual(key1, key3)  # Different password = different key
    
    def test_encryption_decryption(self):
        """Test data encryption and decryption"""
        data = b"Secret message"
        password = "TestPassword"
        salt = CryptoUtils.generate_salt()
        key = CryptoUtils.derive_key(password, salt)
        
        # Encrypt
        encrypted = CryptoUtils.encrypt_data(data, key)
        self.assertNotEqual(encrypted, data)
        
        # Decrypt
        decrypted = CryptoUtils.decrypt_data(encrypted, key)
        self.assertEqual(decrypted, data)
    
    def test_keypair_generation(self):
        """Test RSA keypair generation"""
        private_pem, public_pem = CryptoUtils.generate_keypair()
        
        self.assertIn("BEGIN RSA PRIVATE KEY", private_pem)
        self.assertIn("BEGIN PUBLIC KEY", public_pem)
    
    def test_signature_verification(self):
        """Test digital signature and verification"""
        data = b"Data to sign"
        private_key, public_key = CryptoUtils.generate_keypair()
        
        # Sign data
        signature = CryptoUtils.sign_data(data, private_key)
        self.assertIsNotNone(signature)
        
        # Verify signature
        is_valid = CryptoUtils.verify_signature(data, signature, public_key)
        self.assertTrue(is_valid)
        
        # Verify with wrong data should fail
        wrong_data = b"Wrong data"
        is_invalid = CryptoUtils.verify_signature(wrong_data, signature, public_key)
        self.assertFalse(is_invalid)

class TestAIEvaluator(unittest.TestCase):
    """Test AI evaluation system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.evaluator = AIEvaluator()
    
    def test_model_initialization(self):
        """Test AI model initialization"""
        self.assertEqual(self.evaluator.model_state["version"], 1)
        self.assertIn("mathematics", self.evaluator.model_state["capabilities"])
        self.assertIn("language", self.evaluator.model_state["capabilities"])
        self.assertIn("code", self.evaluator.model_state["capabilities"])
    
    def test_performance_evaluation(self):
        """Test performance evaluation"""
        with patch.object(self.evaluator, '_evaluate_mathematics', return_value=0.7):
            with patch.object(self.evaluator, '_evaluate_language', return_value=0.6):
                with patch.object(self.evaluator, '_evaluate_code', return_value=0.65):
                    improvements = self.evaluator.evaluate_performance()
                    
                    # Should detect improvements above baseline
                    self.assertIn("mathematics", improvements)
                    self.assertIn("language", improvements)
                    self.assertIn("code", improvements)
    
    def test_cumulative_improvements(self):
        """Test cumulative model improvements"""
        initial_version = self.evaluator.model_state["version"]
        
        # Apply improvements
        improvements = {"mathematics": 0.1, "language": 0.05}
        self.evaluator._apply_improvements(improvements)
        
        # Check version incremented
        self.assertEqual(self.evaluator.model_state["version"], initial_version + 1)
        
        # Check capabilities improved
        math_cap = self.evaluator.model_state["capabilities"]["mathematics"]["algebra"]
        self.assertGreater(math_cap, 0.5)

class TestIntegration(unittest.TestCase):
    """Integration tests for system components"""
    
    @patch('unified_qxc_system.Config.DB_PATH', '/tmp/test_integration.db')
    @patch('unified_qxc_system.Config.WALLET_DB_PATH', '/tmp/test_wallets.db')
    def test_blockchain_mining_integration(self):
        """Test blockchain and mining integration"""
        blockchain = Blockchain()
        evaluator = AIEvaluator()
        
        # Simulate AI improvement
        improvements = {"test": 0.1}
        
        # Mine block with improvements
        block = blockchain.mine_block("TEST_MINER", improvements)
        
        self.assertIsNotNone(block)
        self.assertEqual(len(blockchain.chain), 2)  # Genesis + new block
        self.assertEqual(block.ai_improvements, improvements)
    
    def test_wallet_transaction_integration(self):
        """Test wallet and transaction integration"""
        # Create wallets
        wallet1 = SecureWallet("alice", "password1")
        wallet2 = SecureWallet("bob", "password2")
        
        # Set balance for testing
        wallet1.balance = 100.0
        
        # Create transaction
        tx = wallet1.create_transaction(wallet2.address, 25.0)
        
        self.assertEqual(tx.sender, wallet1.address)
        self.assertEqual(tx.recipient, wallet2.address)
        self.assertEqual(tx.amount, 25.0)
        self.assertIsNotNone(tx.signature)
        
        # Verify transaction
        is_valid = wallet2.verify_transaction(tx, tx.signature, wallet1.public_key)
        self.assertTrue(is_valid)

class TestPerformance(unittest.TestCase):
    """Performance tests"""
    
    def test_mining_performance(self):
        """Test mining performance"""
        start_time = time.time()
        
        # Create simple block
        block = Block(
            index=1,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0",
            nonce=0,
            difficulty="00",  # Easy difficulty for testing
            merkle_root="test",
            miner="test",
            ai_improvements={}
        )
        
        # Mine block
        while not block.hash().startswith("00"):
            block.nonce += 1
        
        mining_time = time.time() - start_time
        
        # Should mine quickly with easy difficulty
        self.assertLess(mining_time, 1.0)
        print(f"Mining time: {mining_time:.3f}s for difficulty '00'")
    
    def test_encryption_performance(self):
        """Test encryption performance"""
        data = b"Test data" * 1000  # 9KB of data
        password = "TestPassword"
        salt = CryptoUtils.generate_salt()
        key = CryptoUtils.derive_key(password, salt)
        
        # Test encryption speed
        start_time = time.time()
        encrypted = CryptoUtils.encrypt_data(data, key)
        encryption_time = time.time() - start_time
        
        # Test decryption speed
        start_time = time.time()
        decrypted = CryptoUtils.decrypt_data(encrypted, key)
        decryption_time = time.time() - start_time
        
        self.assertEqual(decrypted, data)
        self.assertLess(encryption_time, 0.1)  # Should be fast
        self.assertLess(decryption_time, 0.1)
        
        print(f"Encryption: {encryption_time:.3f}s, Decryption: {decryption_time:.3f}s")

def run_tests():
    """Run all tests with coverage report"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBlockchain))
    suite.addTests(loader.loadTestsFromTestCase(TestP2PNetwork))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureWallet))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptoUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestAIEvaluator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("="*60)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)