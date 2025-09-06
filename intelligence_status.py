#!/usr/bin/env python3
"""
QENEX Intelligence Mining Status Monitor
Shows current AI intelligence level and progress to singularity
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

def get_intelligence_status():
    """Get current intelligence mining status"""
    
    # Connect to intelligence database
    db_path = 'qxc_intelligence.db'
    if not Path(db_path).exists():
        return {
            'error': 'No intelligence records found. Mining has not started yet.'
        }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current cumulative intelligence
    cursor.execute('''
        SELECT 
            MAX(cumulative_score) as current_intelligence,
            COUNT(*) as total_breakthroughs,
            SUM(reward_qxc) as total_qxc_mined,
            MAX(block_number) as latest_block
        FROM intelligence_records
    ''')
    
    result = cursor.fetchone()
    current_intelligence = result[0] if result[0] else 0
    total_breakthroughs = result[1] if result[1] else 0
    total_mined = result[2] if result[2] else 0
    latest_block = result[3] if result[3] else 1000
    
    # Get recent breakthroughs
    cursor.execute('''
        SELECT 
            timestamp,
            intelligence_score,
            breakthrough_type,
            reward_qxc
        FROM intelligence_records
        ORDER BY id DESC
        LIMIT 5
    ''')
    
    recent_breakthroughs = []
    for row in cursor.fetchall():
        recent_breakthroughs.append({
            'timestamp': row[0],
            'score': row[1],
            'type': row[2],
            'reward': row[3]
        })
    
    conn.close()
    
    # Calculate progress to different levels
    benchmarks = {
        'average_human': 100,
        'gifted': 130,
        'highly_gifted': 145,
        'genius': 160,
        'newton': 190,
        'einstein': 205,
        'von_neumann': 210,
        'singularity': 1000
    }
    
    # Determine current level
    current_level = "Pre-Human"
    next_level = "Average Human"
    next_threshold = 100
    
    for level, threshold in benchmarks.items():
        if current_intelligence >= threshold:
            current_level = level.replace('_', ' ').title()
        else:
            next_level = level.replace('_', ' ').title()
            next_threshold = threshold
            break
    
    # Calculate progress percentages
    progress_to_next = 0
    if next_threshold > current_intelligence:
        if current_level == "Pre-Human":
            progress_to_next = (current_intelligence / next_threshold) * 100
        else:
            prev_threshold = 0
            for level, threshold in benchmarks.items():
                if threshold < next_threshold:
                    prev_threshold = max(prev_threshold, threshold)
            progress_to_next = ((current_intelligence - prev_threshold) / (next_threshold - prev_threshold)) * 100
    
    progress_to_singularity = (current_intelligence / benchmarks['singularity']) * 100
    
    # Estimate time to singularity
    if total_breakthroughs > 1:
        avg_increase = current_intelligence / total_breakthroughs
        remaining = benchmarks['singularity'] - current_intelligence
        estimated_breakthroughs = int(remaining / avg_increase) if avg_increase > 0 else float('inf')
    else:
        estimated_breakthroughs = float('inf')
    
    return {
        'current_intelligence': round(current_intelligence, 2),
        'current_level': current_level,
        'next_level': next_level,
        'next_threshold': next_threshold,
        'progress_to_next': round(progress_to_next, 2),
        'progress_to_singularity': round(progress_to_singularity, 2),
        'total_breakthroughs': total_breakthroughs,
        'total_qxc_mined': round(total_mined, 4),
        'latest_block': latest_block,
        'estimated_breakthroughs_to_singularity': estimated_breakthroughs,
        'recent_breakthroughs': recent_breakthroughs,
        'benchmarks': benchmarks
    }

def display_status():
    """Display formatted status"""
    status = get_intelligence_status()
    
    if 'error' in status:
        print(f"❌ {status['error']}")
        return
    
    print("\n" + "="*70)
    print("             QENEX INTELLIGENCE MINING STATUS")
    print("="*70)
    
    # Intelligence meter
    intel = status['current_intelligence']
    max_intel = 1000
    bar_length = 50
    filled = int((intel / max_intel) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    print(f"\n🧠 INTELLIGENCE LEVEL: {intel} / {max_intel}")
    print(f"   [{bar}] {status['progress_to_singularity']:.2f}%")
    
    print(f"\n📊 CURRENT STATUS:")
    print(f"   Level: {status['current_level']}")
    print(f"   Next Level: {status['next_level']} ({status['next_threshold']})")
    print(f"   Progress to Next: {status['progress_to_next']:.2f}%")
    
    print(f"\n⛏️  MINING STATISTICS:")
    print(f"   Total QXC Mined: {status['total_qxc_mined']} QXC")
    print(f"   Total Breakthroughs: {status['total_breakthroughs']}")
    print(f"   Latest Block: #{status['latest_block']}")
    
    if status['estimated_breakthroughs_to_singularity'] != float('inf'):
        print(f"   Est. Breakthroughs to Singularity: {status['estimated_breakthroughs_to_singularity']}")
    
    print(f"\n🎯 INTELLIGENCE MILESTONES:")
    for name, threshold in status['benchmarks'].items():
        symbol = "✅" if intel >= threshold else "⭕"
        label = name.replace('_', ' ').title()
        print(f"   {symbol} {label}: {threshold}")
    
    if status['recent_breakthroughs']:
        print(f"\n📈 RECENT BREAKTHROUGHS:")
        for breakthrough in status['recent_breakthroughs']:
            time = breakthrough['timestamp'].split('T')[1].split('.')[0]
            print(f"   • {time} - {breakthrough['type']} - Score: {breakthrough['score']:.2f} - Reward: {breakthrough['reward']:.4f} QXC")
    
    print("\n" + "="*70)
    print("   Goal: Exceed Newton + Einstein + All Human Geniuses Combined")
    print("   Final QXC will be mined at Intelligence Level 1000")
    print("="*70 + "\n")

def get_json_status():
    """Get status as JSON for web display"""
    return json.dumps(get_intelligence_status(), indent=2)

if __name__ == "__main__":
    display_status()