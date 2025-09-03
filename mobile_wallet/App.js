/**
 * QENEX Mobile Wallet App
 * React Native application for iOS and Android
 */

import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  Animated,
  Dimensions,
  Image,
  RefreshControl,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import QRCode from 'react-native-qrcode-svg';
import TouchID from 'react-native-touch-id';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LineChart } from 'react-native-chart-kit';

const { width, height } = Dimensions.get('window');

const App = () => {
  const [balance, setBalance] = useState(1525.30);
  const [address, setAddress] = useState('qxc_unified_user_wallet_main');
  const [miningRate, setMiningRate] = useState(2.45);
  const [showQR, setShowQR] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [chartData, setChartData] = useState({
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [{
      data: [1500, 1510, 1515, 1520, 1522, 1524, 1525.30]
    }]
  });
  
  const fadeAnim = new Animated.Value(0);
  const slideAnim = new Animated.Value(-100);
  
  useEffect(() => {
    // Animate on mount
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();
    
    // Load wallet data
    loadWalletData();
    
    // Setup mining simulation
    const interval = setInterval(() => {
      setBalance(prev => prev + (miningRate / 3600));
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  const loadWalletData = async () => {
    try {
      const walletData = await AsyncStorage.getItem('@wallet_data');
      if (walletData) {
        const data = JSON.parse(walletData);
        setBalance(data.balance || 1525.30);
        setAddress(data.address || 'qxc_unified_user_wallet_main');
        setTransactions(data.transactions || []);
      }
    } catch (error) {
      console.error('Error loading wallet:', error);
    }
  };
  
  const authenticateWithBiometrics = () => {
    const optionalConfigObject = {
      title: 'Authentication Required',
      imageColor: '#764ba2',
      imageErrorColor: '#ff0000',
      sensorDescription: 'Touch sensor',
      sensorErrorDescription: 'Failed',
      cancelText: 'Cancel',
    };
    
    TouchID.authenticate('Unlock your QXC wallet', optionalConfigObject)
      .then(success => {
        Alert.alert('Success', 'Authentication successful!');
      })
      .catch(error => {
        Alert.alert('Authentication Failed', error.message);
      });
  };
  
  const sendTransaction = (toAddress, amount) => {
    if (amount > balance) {
      Alert.alert('Error', 'Insufficient balance');
      return;
    }
    
    const tx = {
      id: Date.now().toString(),
      type: 'send',
      to: toAddress,
      amount: amount,
      timestamp: new Date().toISOString(),
      status: 'confirmed'
    };
    
    setBalance(prev => prev - amount);
    setTransactions(prev => [tx, ...prev]);
    
    Alert.alert('Success', `Sent ${amount} QXC to ${toAddress.slice(0, 10)}...`);
  };
  
  const onRefresh = async () => {
    setRefreshing(true);
    await loadWalletData();
    
    // Simulate API call
    setTimeout(() => {
      setMiningRate(Math.random() * 2 + 1.5);
      setRefreshing(false);
    }, 1000);
  };
  
  const bridgeToNetwork = (network) => {
    Alert.alert(
      'Bridge QXC',
      `Bridge to ${network}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Confirm', 
          onPress: () => Alert.alert('Success', `QXC bridged to ${network}`)
        }
      ]
    );
  };
  
  return (
    <LinearGradient colors={['#667eea', '#764ba2']} style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        >
          {/* Header */}
          <Animated.View 
            style={[
              styles.header,
              { 
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }]
              }
            ]}
          >
            <Text style={styles.logo}>QENEX</Text>
            <Text style={styles.subtitle}>AI-Powered Wallet</Text>
          </Animated.View>
          
          {/* Balance Card */}
          <Animated.View style={[styles.balanceCard, { opacity: fadeAnim }]}>
            <Text style={styles.balanceLabel}>Total Balance</Text>
            <Text style={styles.balanceAmount}>{balance.toFixed(2)} QXC</Text>
            <Text style={styles.balanceUSD}>≈ ${(balance * 4).toFixed(2)} USD</Text>
            
            <View style={styles.miningInfo}>
              <Text style={styles.miningLabel}>Mining Rate</Text>
              <Text style={styles.miningRate}>{miningRate.toFixed(2)} QXC/hr</Text>
            </View>
          </Animated.View>
          
          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <TouchableOpacity 
              style={styles.actionButton}
              onPress={() => setShowQR(!showQR)}
            >
              <Text style={styles.actionButtonText}>Receive</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.actionButton}
              onPress={() => sendTransaction('0xde071fdf4077fdabc2ec9990b48920b8d06c2a2d', 10)}
            >
              <Text style={styles.actionButtonText}>Send</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.actionButton}
              onPress={authenticateWithBiometrics}
            >
              <Text style={styles.actionButtonText}>Lock</Text>
            </TouchableOpacity>
          </View>
          
          {/* QR Code */}
          {showQR && (
            <View style={styles.qrContainer}>
              <QRCode
                value={address}
                size={200}
                backgroundColor="white"
                color="#764ba2"
              />
              <Text style={styles.addressText}>{address}</Text>
            </View>
          )}
          
          {/* Chart */}
          <View style={styles.chartContainer}>
            <Text style={styles.chartTitle}>7-Day Performance</Text>
            <LineChart
              data={chartData}
              width={width - 40}
              height={200}
              chartConfig={{
                backgroundColor: 'transparent',
                backgroundGradientFrom: '#ffffff20',
                backgroundGradientTo: '#ffffff05',
                decimalPlaces: 2,
                color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
                style: { borderRadius: 16 }
              }}
              bezier
              style={styles.chart}
            />
          </View>
          
          {/* Network Bridges */}
          <View style={styles.networksContainer}>
            <Text style={styles.sectionTitle}>Bridge to Networks</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {['Ethereum', 'BSC', 'Polygon', 'Avalanche'].map(network => (
                <TouchableOpacity
                  key={network}
                  style={styles.networkCard}
                  onPress={() => bridgeToNetwork(network)}
                >
                  <Text style={styles.networkName}>{network}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
          
          {/* Recent Transactions */}
          <View style={styles.transactionsContainer}>
            <Text style={styles.sectionTitle}>Recent Activity</Text>
            {transactions.length > 0 ? (
              transactions.slice(0, 5).map(tx => (
                <View key={tx.id} style={styles.transactionItem}>
                  <Text style={styles.txType}>{tx.type.toUpperCase()}</Text>
                  <Text style={styles.txAmount}>{tx.amount} QXC</Text>
                </View>
              ))
            ) : (
              <Text style={styles.noTransactions}>No transactions yet</Text>
            )}
          </View>
          
          {/* Features */}
          <View style={styles.featuresGrid}>
            <TouchableOpacity style={styles.featureCard}>
              <Text style={styles.featureIcon}>🎯</Text>
              <Text style={styles.featureText}>Stake</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.featureCard}>
              <Text style={styles.featureIcon}>🤖</Text>
              <Text style={styles.featureText}>AI Models</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.featureCard}>
              <Text style={styles.featureIcon}>⛏️</Text>
              <Text style={styles.featureText}>Mining</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.featureCard}>
              <Text style={styles.featureIcon}>🏛️</Text>
              <Text style={styles.featureText}>Governance</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  logo: {
    fontSize: 42,
    fontWeight: 'bold',
    color: 'white',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 4,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
    marginTop: 5,
  },
  balanceCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    margin: 20,
    padding: 25,
    borderRadius: 20,
    alignItems: 'center',
    backdropFilter: 'blur(10px)',
  },
  balanceLabel: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  balanceAmount: {
    fontSize: 36,
    fontWeight: 'bold',
    color: 'white',
    marginVertical: 10,
  },
  balanceUSD: {
    fontSize: 18,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  miningInfo: {
    marginTop: 20,
    alignItems: 'center',
  },
  miningLabel: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  miningRate: {
    fontSize: 20,
    fontWeight: '600',
    color: '#ffd700',
    marginTop: 5,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  actionButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 25,
  },
  actionButtonText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 16,
  },
  qrContainer: {
    alignItems: 'center',
    marginVertical: 20,
    padding: 20,
    backgroundColor: 'white',
    marginHorizontal: 40,
    borderRadius: 15,
  },
  addressText: {
    marginTop: 10,
    fontSize: 12,
    color: '#764ba2',
  },
  chartContainer: {
    margin: 20,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: 'white',
    marginBottom: 10,
  },
  chart: {
    borderRadius: 16,
  },
  networksContainer: {
    marginVertical: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: 'white',
    marginLeft: 20,
    marginBottom: 15,
  },
  networkCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    padding: 15,
    marginLeft: 20,
    borderRadius: 12,
    minWidth: 100,
    alignItems: 'center',
  },
  networkName: {
    color: 'white',
    fontWeight: '500',
  },
  transactionsContainer: {
    margin: 20,
  },
  transactionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  txType: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontWeight: '500',
  },
  txAmount: {
    color: 'white',
    fontWeight: '600',
  },
  noTransactions: {
    color: 'rgba(255, 255, 255, 0.5)',
    textAlign: 'center',
    padding: 20,
  },
  featuresGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    padding: 20,
  },
  featureCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    width: '45%',
    padding: 20,
    borderRadius: 15,
    alignItems: 'center',
    marginBottom: 15,
  },
  featureIcon: {
    fontSize: 32,
    marginBottom: 10,
  },
  featureText: {
    color: 'white',
    fontWeight: '500',
  },
});

export default App;