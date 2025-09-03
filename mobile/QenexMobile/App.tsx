/**
 * QENEX OS Mobile Management App
 */
import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

// API Configuration
const API_BASE = 'https://qenex.ai/api/v1';

// Dashboard Screen
const DashboardScreen = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_BASE}/metrics`);
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#667eea" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={fetchMetrics} />
      }>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>System Metrics</Text>
        <View style={styles.metric}>
          <Text style={styles.metricLabel}>CPU Usage</Text>
          <Text style={styles.metricValue}>{metrics?.cpu || 0}%</Text>
        </View>
        <View style={styles.metric}>
          <Text style={styles.metricLabel}>Memory Usage</Text>
          <Text style={styles.metricValue}>{metrics?.memory || 0}%</Text>
        </View>
        <View style={styles.metric}>
          <Text style={styles.metricLabel}>Disk Usage</Text>
          <Text style={styles.metricValue}>{metrics?.disk || 0}%</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quick Actions</Text>
        <TouchableOpacity style={styles.button}>
          <Icon name="refresh" size={20} color="white" />
          <Text style={styles.buttonText}>Restart System</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button}>
          <Icon name="backup" size={20} color="white" />
          <Text style={styles.buttonText}>Create Backup</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button}>
          <Icon name="healing" size={20} color="white" />
          <Text style={styles.buttonText}>Run Health Check</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

// Agents Screen
const AgentsScreen = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_BASE}/agents`);
      const data = await response.json();
      setAgents(data);
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch agents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const deployAgent = () => {
    Alert.alert(
      'Deploy Agent',
      'Select agent type to deploy',
      [
        { text: 'Monitor', onPress: () => console.log('Deploy Monitor') },
        { text: 'Optimizer', onPress: () => console.log('Deploy Optimizer') },
        { text: 'Cancel', style: 'cancel' }
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <TouchableOpacity style={styles.addButton} onPress={deployAgent}>
        <Icon name="add" size={24} color="white" />
        <Text style={styles.buttonText}>Deploy New Agent</Text>
      </TouchableOpacity>

      {agents.map((agent: any) => (
        <View key={agent.id} style={styles.card}>
          <Text style={styles.agentName}>{agent.type.toUpperCase()}</Text>
          <Text style={styles.agentStatus}>Status: {agent.status}</Text>
          <Text style={styles.agentId}>ID: {agent.id}</Text>
          <View style={styles.agentActions}>
            <TouchableOpacity style={styles.smallButton}>
              <Text style={styles.smallButtonText}>Restart</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.smallButton, styles.dangerButton]}>
              <Text style={styles.smallButtonText}>Remove</Text>
            </TouchableOpacity>
          </View>
        </View>
      ))}
    </ScrollView>
  );
};

// Logs Screen
const LogsScreen = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/logs?limit=50`);
      const data = await response.json();
      setLogs(data.logs);
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <ScrollView style={styles.container}>
      <View style={styles.logsContainer}>
        {logs.map((log, index) => (
          <Text key={index} style={styles.logEntry}>
            {log}
          </Text>
        ))}
      </View>
    </ScrollView>
  );
};

// Settings Screen
const SettingsScreen = () => {
  return (
    <ScrollView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connection</Text>
        <TouchableOpacity style={styles.settingRow}>
          <Text>API Endpoint</Text>
          <Text style={styles.settingValue}>{API_BASE}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.settingRow}>
          <Text>Authentication</Text>
          <Text style={styles.settingValue}>Connected</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Notifications</Text>
        <TouchableOpacity style={styles.settingRow}>
          <Text>System Alerts</Text>
          <Text style={styles.settingValue}>Enabled</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.settingRow}>
          <Text>Health Checks</Text>
          <Text style={styles.settingValue}>Every 5 min</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>About</Text>
        <View style={styles.settingRow}>
          <Text>Version</Text>
          <Text style={styles.settingValue}>5.0.0</Text>
        </View>
        <View style={styles.settingRow}>
          <Text>Server Version</Text>
          <Text style={styles.settingValue}>5.0.0</Text>
        </View>
      </View>
    </ScrollView>
  );
};

const Tab = createBottomTabNavigator();

const App = () => {
  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#667eea" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarIcon: ({ focused, color, size }) => {
            let iconName;
            if (route.name === 'Dashboard') {
              iconName = 'dashboard';
            } else if (route.name === 'Agents') {
              iconName = 'memory';
            } else if (route.name === 'Logs') {
              iconName = 'description';
            } else if (route.name === 'Settings') {
              iconName = 'settings';
            }
            return <Icon name={iconName!} size={size} color={color} />;
          },
          tabBarActiveTintColor: '#667eea',
          tabBarInactiveTintColor: 'gray',
        })}>
        <Tab.Screen name="Dashboard" component={DashboardScreen} />
        <Tab.Screen name="Agents" component={AgentsScreen} />
        <Tab.Screen name="Logs" component={LogsScreen} />
        <Tab.Screen name="Settings" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: 'white',
    margin: 10,
    padding: 15,
    borderRadius: 8,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#333',
  },
  metric: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  metricLabel: {
    fontSize: 14,
    color: '#666',
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#667eea',
  },
  button: {
    backgroundColor: '#667eea',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 6,
    marginVertical: 5,
  },
  buttonText: {
    color: 'white',
    marginLeft: 8,
    fontSize: 16,
    fontWeight: '600',
  },
  addButton: {
    backgroundColor: '#667eea',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    margin: 10,
    borderRadius: 6,
  },
  agentName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  agentStatus: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  agentId: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  agentActions: {
    flexDirection: 'row',
    marginTop: 10,
  },
  smallButton: {
    backgroundColor: '#667eea',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    marginRight: 8,
  },
  dangerButton: {
    backgroundColor: '#f56565',
  },
  smallButtonText: {
    color: 'white',
    fontSize: 12,
  },
  logsContainer: {
    backgroundColor: '#1a1a1a',
    margin: 10,
    padding: 10,
    borderRadius: 6,
  },
  logEntry: {
    color: '#0f0',
    fontFamily: 'monospace',
    fontSize: 12,
    marginVertical: 2,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  settingValue: {
    color: '#667eea',
    fontWeight: '600',
  },
});

export default App;