/**
 * QXC Mobile Wallet App
 * React Native application for iOS & Android
 */

import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  StatusBar,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ethers } from 'ethers';

const QXC_CONTRACT = '0xb17654f3f068aded95a234de2532b9a478b858bf';
const RPC_URL = 'https://eth-mainnet.public.blastapi.io';

const App = () => {
  const [wallet, setWallet] = useState(null);
  const [balance, setBalance] = useState('0');
  const [miningRewards, setMiningRewards] = useState('0');
  const [refreshing, setRefreshing] = useState(false);
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [activeTab, setActiveTab] = useState('wallet');

  useEffect(() => {
    loadWallet();
  }, []);

  const loadWallet = async () => {
    try {
      const privateKey = await AsyncStorage.getItem('privateKey');
      if (privateKey) {
        const wallet = new ethers.Wallet(privateKey);
        setWallet(wallet);
        await loadBalance(wallet.address);
      }
    } catch (error) {
      console.error('Error loading wallet:', error);
    }
  };

  const createWallet = async () => {
    const newWallet = ethers.Wallet.createRandom();
    await AsyncStorage.setItem('privateKey', newWallet.privateKey);
    setWallet(newWallet);
    Alert.alert('Success', 'New wallet created!');
  };

  const importWallet = async (privateKey) => {
    try {
      const wallet = new ethers.Wallet(privateKey);
      await AsyncStorage.setItem('privateKey', privateKey);
      setWallet(wallet);
      await loadBalance(wallet.address);
      Alert.alert('Success', 'Wallet imported successfully!');
    } catch (error) {
      Alert.alert('Error', 'Invalid private key');
    }
  };

  const loadBalance = async (address) => {
    try {
      const provider = new ethers.JsonRpcProvider(RPC_URL);
      const contract = new ethers.Contract(
        QXC_CONTRACT,
        ['function balanceOf(address) view returns (uint256)'],
        provider
      );
      const balance = await contract.balanceOf(address);
      setBalance(ethers.formatEther(balance));
    } catch (error) {
      console.error('Error loading balance:', error);
    }
  };

  const sendQXC = async () => {
    if (!wallet || !recipient || !amount) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }

    try {
      const provider = new ethers.JsonRpcProvider(RPC_URL);
      const signer = wallet.connect(provider);
      const contract = new ethers.Contract(
        QXC_CONTRACT,
        ['function transfer(address to, uint256 amount) returns (bool)'],
        signer
      );
      
      const tx = await contract.transfer(recipient, ethers.parseEther(amount));
      Alert.alert('Transaction Sent', `Hash: ${tx.hash}`);
      await tx.wait();
      Alert.alert('Success', 'Transaction confirmed!');
      await loadBalance(wallet.address);
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    if (wallet) {
      await loadBalance(wallet.address);
    }
    setRefreshing(false);
  };

  if (!wallet) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.welcomeContainer}>
          <Text style={styles.logo}>QXC</Text>
          <Text style={styles.title}>QENEX Wallet</Text>
          <TouchableOpacity style={styles.button} onPress={createWallet}>
            <Text style={styles.buttonText}>Create New Wallet</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.buttonOutline} onPress={() => {}}>
            <Text style={styles.buttonOutlineText}>Import Wallet</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>QXC Wallet</Text>
        <Text style={styles.address}>
          {wallet.address.substring(0, 6)}...{wallet.address.substring(38)}
        </Text>
      </View>

      <View style={styles.balanceCard}>
        <Text style={styles.balanceLabel}>Total Balance</Text>
        <Text style={styles.balanceAmount}>{balance} QXC</Text>
        <Text style={styles.balanceUSD}>≈ ${(parseFloat(balance) * 0.5).toFixed(2)} USD</Text>
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'wallet' && styles.activeTab]}
          onPress={() => setActiveTab('wallet')}
        >
          <Text style={styles.tabText}>Wallet</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'mining' && styles.activeTab]}
          onPress={() => setActiveTab('mining')}
        >
          <Text style={styles.tabText}>Mining</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'staking' && styles.activeTab]}
          onPress={() => setActiveTab('staking')}
        >
          <Text style={styles.tabText}>Staking</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {activeTab === 'wallet' && (
          <View style={styles.sendContainer}>
            <Text style={styles.sectionTitle}>Send QXC</Text>
            <TextInput
              style={styles.input}
              placeholder="Recipient Address"
              value={recipient}
              onChangeText={setRecipient}
              placeholderTextColor="#666"
            />
            <TextInput
              style={styles.input}
              placeholder="Amount"
              value={amount}
              onChangeText={setAmount}
              keyboardType="numeric"
              placeholderTextColor="#666"
            />
            <TouchableOpacity style={styles.sendButton} onPress={sendQXC}>
              <Text style={styles.buttonText}>Send</Text>
            </TouchableOpacity>
          </View>
        )}

        {activeTab === 'mining' && (
          <View style={styles.miningContainer}>
            <Text style={styles.sectionTitle}>AI Mining Rewards</Text>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Today's Rewards</Text>
              <Text style={styles.statValue}>0.42 QXC</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Total Mined</Text>
              <Text style={styles.statValue}>{miningRewards} QXC</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Mining Rate</Text>
              <Text style={styles.statValue}>0.018 QXC/hour</Text>
            </View>
          </View>
        )}

        {activeTab === 'staking' && (
          <View style={styles.stakingContainer}>
            <Text style={styles.sectionTitle}>Staking</Text>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Staked Amount</Text>
              <Text style={styles.statValue}>500 QXC</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>APY</Text>
              <Text style={styles.statValue}>15%</Text>
            </View>
            <TouchableOpacity style={styles.stakeButton}>
              <Text style={styles.buttonText}>Stake More</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  welcomeContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  logo: {
    fontSize: 72,
    fontWeight: 'bold',
    color: '#00ff88',
    marginBottom: 10,
  },
  title: {
    fontSize: 24,
    color: '#fff',
    marginBottom: 40,
  },
  header: {
    padding: 20,
    backgroundColor: '#111',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  address: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  balanceCard: {
    backgroundColor: '#1a1a1a',
    margin: 20,
    padding: 20,
    borderRadius: 15,
    alignItems: 'center',
  },
  balanceLabel: {
    fontSize: 14,
    color: '#666',
  },
  balanceAmount: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#00ff88',
    marginVertical: 10,
  },
  balanceUSD: {
    fontSize: 16,
    color: '#888',
  },
  tabs: {
    flexDirection: 'row',
    paddingHorizontal: 20,
  },
  tab: {
    flex: 1,
    padding: 15,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#00ff88',
  },
  tabText: {
    color: '#fff',
    fontSize: 16,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  sendContainer: {
    backgroundColor: '#1a1a1a',
    padding: 20,
    borderRadius: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#222',
    padding: 15,
    borderRadius: 10,
    color: '#fff',
    marginBottom: 15,
  },
  button: {
    backgroundColor: '#00ff88',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    width: '100%',
    marginBottom: 10,
  },
  buttonOutline: {
    borderWidth: 1,
    borderColor: '#00ff88',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    width: '100%',
  },
  buttonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  buttonOutlineText: {
    color: '#00ff88',
    fontSize: 16,
    fontWeight: 'bold',
  },
  sendButton: {
    backgroundColor: '#00ff88',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  miningContainer: {
    backgroundColor: '#1a1a1a',
    padding: 20,
    borderRadius: 15,
  },
  stakingContainer: {
    backgroundColor: '#1a1a1a',
    padding: 20,
    borderRadius: 15,
  },
  statCard: {
    backgroundColor: '#222',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  statLabel: {
    fontSize: 14,
    color: '#666',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 5,
  },
  stakeButton: {
    backgroundColor: '#00ff88',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 10,
  },
});

export default App;