#!/usr/bin/env python3
"""
QENEX Intelligence Mining API Server
Serves real-time data from the comprehensive intelligence mining system
"""

import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pathlib import Path

class IntelligenceAPIHandler(BaseHTTPRequestHandler):
    """API handler for intelligence mining data"""
    
    def do_GET(self):
        """Handle GET requests for live data"""
        if self.path == '/api/intelligence-status':
            self.send_intelligence_status()
        elif self.path == '/api/mining-stats':
            self.send_mining_stats()
        elif self.path == '/api/dimensions':
            self.send_dimensions_data()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_intelligence_status(self):
        """Send current intelligence status"""
        try:
            # Connect to database
            db_path = '/opt/qenex-os/qxc_comprehensive_intelligence.db'
            
            if not Path(db_path).exists():
                # No database yet, send initial state
                data = {
                    'current_intelligence': 0.0,
                    'total_mined': 0.0,
                    'remaining_supply': 1000000000.0,
                    'block_number': 0,
                    'breakthrough_level': 'INITIALIZING',
                    'progress_percentage': 0.0,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get latest record
                cursor.execute('''
                    SELECT total_intelligence, total_mined, block_number, 
                           breakthrough_level, timestamp
                    FROM intelligence_records 
                    ORDER BY id DESC LIMIT 1
                ''')
                
                result = cursor.fetchone()
                
                if result:
                    intelligence, mined, block, breakthrough, timestamp = result
                    data = {
                        'current_intelligence': intelligence,
                        'total_mined': mined,
                        'remaining_supply': 1000000000 - mined,
                        'block_number': block,
                        'breakthrough_level': breakthrough,
                        'progress_percentage': (intelligence / 1000) * 100,
                        'timestamp': timestamp,
                        'supply_percentage': (mined / 1000000000) * 100
                    }
                else:
                    data = {
                        'current_intelligence': 0.0,
                        'total_mined': 0.0,
                        'remaining_supply': 1000000000.0,
                        'block_number': 0,
                        'breakthrough_level': 'INITIALIZING',
                        'progress_percentage': 0.0,
                        'timestamp': datetime.now().isoformat()
                    }
                
                conn.close()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def send_mining_stats(self):
        """Send detailed mining statistics"""
        try:
            db_path = '/opt/qenex-os/qxc_comprehensive_intelligence.db'
            
            if not Path(db_path).exists():
                data = {
                    'total_breakthroughs': 0,
                    'average_reward': 0,
                    'largest_reward': 0,
                    'recent_mining': []
                }
            else:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get statistics
                cursor.execute('''
                    SELECT COUNT(*), AVG(reward_qxc), MAX(reward_qxc)
                    FROM intelligence_records
                ''')
                count, avg_reward, max_reward = cursor.fetchone()
                
                # Get recent mining
                cursor.execute('''
                    SELECT timestamp, total_intelligence, reward_qxc, breakthrough_level
                    FROM intelligence_records
                    ORDER BY id DESC LIMIT 10
                ''')
                
                recent = []
                for row in cursor.fetchall():
                    recent.append({
                        'timestamp': row[0],
                        'intelligence': row[1],
                        'reward': row[2],
                        'breakthrough': row[3]
                    })
                
                data = {
                    'total_breakthroughs': count or 0,
                    'average_reward': avg_reward or 0,
                    'largest_reward': max_reward or 0,
                    'recent_mining': recent
                }
                
                conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def send_dimensions_data(self):
        """Send all 40 dimension scores"""
        try:
            db_path = '/opt/qenex-os/qxc_comprehensive_intelligence.db'
            
            if not Path(db_path).exists():
                # Return zeros for all dimensions
                dimensions = {}
                dimension_names = [
                    'logical_reasoning', 'mathematical_ability', 'pattern_recognition',
                    'analytical_thinking', 'problem_solving', 'creativity', 'imagination',
                    'innovation', 'lateral_thinking', 'artistic_sense', 'language_comprehension',
                    'verbal_expression', 'linguistic_reasoning', 'communication',
                    'spatial_reasoning', 'visual_processing', 'dimensional_thinking',
                    'navigation', 'working_memory', 'long_term_memory', 'learning_speed',
                    'knowledge_retention', 'emotional_awareness', 'empathy', 'social_cognition',
                    'emotional_regulation', 'abstraction', 'conceptualization', 'meta_cognition',
                    'philosophical_reasoning', 'scientific_method', 'hypothesis_formation',
                    'experimental_design', 'data_analysis', 'practical_wisdom', 'common_sense',
                    'decision_making', 'resource_optimization'
                ]
                
                for dim in dimension_names:
                    dimensions[dim] = {
                        'current_score': 0.0,
                        'max_achieved': 0.0
                    }
            else:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get dimension scores
                cursor.execute('SELECT dimension, current_score, max_achieved FROM dimension_scores')
                
                dimensions = {}
                for dimension, current, max_score in cursor.fetchall():
                    dimensions[dimension] = {
                        'current_score': current,
                        'max_achieved': max_score
                    }
                
                # Get latest dimension details from last record
                cursor.execute('''
                    SELECT dimensions_json FROM intelligence_records 
                    ORDER BY id DESC LIMIT 1
                ''')
                
                result = cursor.fetchone()
                if result and result[0]:
                    try:
                        latest_dimensions = json.loads(result[0])
                        # Update with latest scores
                        for dim, data in latest_dimensions.items():
                            if dim in dimensions:
                                dimensions[dim]['latest_score'] = data.get('score', 0)
                                dimensions[dim]['weight'] = data.get('weight', 0)
                    except:
                        pass
                
                conn.close()
            
            # Calculate category averages
            categories = {
                'Analytical': ['logical_reasoning', 'mathematical_ability', 'pattern_recognition',
                              'analytical_thinking', 'problem_solving'],
                'Creative': ['creativity', 'imagination', 'innovation', 'lateral_thinking', 'artistic_sense'],
                'Linguistic': ['language_comprehension', 'verbal_expression', 'linguistic_reasoning', 'communication'],
                'Spatial': ['spatial_reasoning', 'visual_processing', 'dimensional_thinking', 'navigation'],
                'Memory': ['working_memory', 'long_term_memory', 'learning_speed', 'knowledge_retention'],
                'Emotional': ['emotional_awareness', 'empathy', 'social_cognition', 'emotional_regulation'],
                'Abstract': ['abstraction', 'conceptualization', 'meta_cognition', 'philosophical_reasoning'],
                'Scientific': ['scientific_method', 'hypothesis_formation', 'experimental_design', 'data_analysis'],
                'Practical': ['practical_wisdom', 'common_sense', 'decision_making', 'resource_optimization']
            }
            
            category_scores = {}
            for category, dims in categories.items():
                scores = [dimensions.get(d, {}).get('current_score', 0) for d in dims]
                category_scores[category] = sum(scores) / len(scores) if scores else 0
            
            data = {
                'dimensions': dimensions,
                'categories': category_scores,
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))


def run_api_server(port=8547):
    """Run the API server"""
    server = HTTPServer(('localhost', port), IntelligenceAPIHandler)
    print(f"Intelligence Mining API Server running on port {port}")
    print(f"Endpoints:")
    print(f"  http://localhost:{port}/api/intelligence-status")
    print(f"  http://localhost:{port}/api/mining-stats")
    print(f"  http://localhost:{port}/api/dimensions")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API server...")
        server.shutdown()


if __name__ == "__main__":
    run_api_server()