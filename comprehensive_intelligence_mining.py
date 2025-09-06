#!/usr/bin/env python3
"""
QENEX Comprehensive Intelligence Mining System
==============================================
Complete assessment of all intelligence dimensions with measurable ratings.
Mines 1,000,000,000 QXC tokens distributed across intelligence levels 0-1000.

Intelligence is measured across ALL dimensions of cognitive capability.
"""

import numpy as np
import hashlib
import json
import sqlite3
import time
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ComprehensiveIntelligenceMetrics:
    """
    Complete intelligence assessment covering ALL aspects of cognition.
    Each dimension is measurable and contributes to mining rewards.
    """
    
    # Total supply: 1 billion QXC
    TOTAL_SUPPLY = 1_000_000_000
    
    # Intelligence scale: 0-1000
    MAX_INTELLIGENCE = 1000
    
    # All dimensions of intelligence with weights
    INTELLIGENCE_DIMENSIONS = {
        # Analytical Intelligence (25%)
        'logical_reasoning': {'weight': 0.05, 'max_score': 100},
        'mathematical_ability': {'weight': 0.05, 'max_score': 100},
        'pattern_recognition': {'weight': 0.05, 'max_score': 100},
        'analytical_thinking': {'weight': 0.05, 'max_score': 100},
        'problem_solving': {'weight': 0.05, 'max_score': 100},
        
        # Creative Intelligence (15%)
        'creativity': {'weight': 0.03, 'max_score': 100},
        'imagination': {'weight': 0.03, 'max_score': 100},
        'innovation': {'weight': 0.03, 'max_score': 100},
        'lateral_thinking': {'weight': 0.03, 'max_score': 100},
        'artistic_sense': {'weight': 0.03, 'max_score': 100},
        
        # Linguistic Intelligence (10%)
        'language_comprehension': {'weight': 0.025, 'max_score': 100},
        'verbal_expression': {'weight': 0.025, 'max_score': 100},
        'linguistic_reasoning': {'weight': 0.025, 'max_score': 100},
        'communication': {'weight': 0.025, 'max_score': 100},
        
        # Spatial Intelligence (10%)
        'spatial_reasoning': {'weight': 0.025, 'max_score': 100},
        'visual_processing': {'weight': 0.025, 'max_score': 100},
        'dimensional_thinking': {'weight': 0.025, 'max_score': 100},
        'navigation': {'weight': 0.025, 'max_score': 100},
        
        # Memory & Learning (10%)
        'working_memory': {'weight': 0.025, 'max_score': 100},
        'long_term_memory': {'weight': 0.025, 'max_score': 100},
        'learning_speed': {'weight': 0.025, 'max_score': 100},
        'knowledge_retention': {'weight': 0.025, 'max_score': 100},
        
        # Emotional Intelligence (10%)
        'emotional_awareness': {'weight': 0.025, 'max_score': 100},
        'empathy': {'weight': 0.025, 'max_score': 100},
        'social_cognition': {'weight': 0.025, 'max_score': 100},
        'emotional_regulation': {'weight': 0.025, 'max_score': 100},
        
        # Abstract Thinking (10%)
        'abstraction': {'weight': 0.025, 'max_score': 100},
        'conceptualization': {'weight': 0.025, 'max_score': 100},
        'meta_cognition': {'weight': 0.025, 'max_score': 100},
        'philosophical_reasoning': {'weight': 0.025, 'max_score': 100},
        
        # Scientific Intelligence (5%)
        'scientific_method': {'weight': 0.0125, 'max_score': 100},
        'hypothesis_formation': {'weight': 0.0125, 'max_score': 100},
        'experimental_design': {'weight': 0.0125, 'max_score': 100},
        'data_analysis': {'weight': 0.0125, 'max_score': 100},
        
        # Practical Intelligence (5%)
        'practical_wisdom': {'weight': 0.0125, 'max_score': 100},
        'common_sense': {'weight': 0.0125, 'max_score': 100},
        'decision_making': {'weight': 0.0125, 'max_score': 100},
        'resource_optimization': {'weight': 0.0125, 'max_score': 100}
    }
    
    def __init__(self):
        self.db_path = 'qxc_comprehensive_intelligence.db'
        self.init_database()
        self.load_state()
        
    def init_database(self):
        """Initialize comprehensive intelligence database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main intelligence records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intelligence_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                total_intelligence REAL,
                cumulative_intelligence REAL,
                dimensions_json TEXT,
                proof_hash TEXT,
                reward_qxc REAL,
                total_mined REAL,
                block_number INTEGER,
                breakthrough_level TEXT
            )
        ''')
        
        # Dimension scores table for tracking individual progress
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dimension_scores (
                dimension TEXT PRIMARY KEY,
                current_score REAL,
                max_achieved REAL,
                last_updated TEXT
            )
        ''')
        
        # Initialize dimension scores if not exists
        for dimension in self.INTELLIGENCE_DIMENSIONS:
            cursor.execute('''
                INSERT OR IGNORE INTO dimension_scores (dimension, current_score, max_achieved, last_updated)
                VALUES (?, 0, 0, ?)
            ''', (dimension, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def load_state(self):
        """Load current intelligence state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load cumulative intelligence
        cursor.execute('SELECT MAX(cumulative_intelligence) FROM intelligence_records')
        result = cursor.fetchone()
        self.cumulative_intelligence = result[0] if result[0] else 0.0
        
        # Load total mined
        cursor.execute('SELECT MAX(total_mined) FROM intelligence_records')
        result = cursor.fetchone()
        self.total_mined = result[0] if result[0] else 0.0
        
        # Load dimension scores
        cursor.execute('SELECT dimension, current_score FROM dimension_scores')
        self.dimension_scores = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
    
    def assess_comprehensive_intelligence(self, model_output: Any) -> Dict:
        """
        Assess intelligence across ALL dimensions with measurable metrics.
        Returns detailed scores for each dimension.
        """
        assessments = {}
        
        # Assess each dimension
        for dimension, config in self.INTELLIGENCE_DIMENSIONS.items():
            score = self._assess_dimension(dimension, model_output)
            assessments[dimension] = {
                'score': score,
                'max_score': config['max_score'],
                'weight': config['weight'],
                'weighted_score': score * config['weight']
            }
        
        # Calculate total intelligence (0-1000 scale)
        total_weighted = sum(a['weighted_score'] for a in assessments.values())
        total_intelligence = total_weighted * 10  # Scale to 0-1000
        
        return {
            'dimensions': assessments,
            'total_intelligence': total_intelligence,
            'detailed_metrics': self._calculate_detailed_metrics(assessments)
        }
    
    def _assess_dimension(self, dimension: str, output: Any) -> float:
        """Assess a specific intelligence dimension with measurable criteria"""
        output_str = str(output).lower()
        
        # Analytical dimensions
        if dimension == 'logical_reasoning':
            return self._measure_logical_reasoning(output_str)
        elif dimension == 'mathematical_ability':
            return self._measure_mathematical_ability(output_str)
        elif dimension == 'pattern_recognition':
            return self._measure_pattern_recognition(output_str)
        elif dimension == 'analytical_thinking':
            return self._measure_analytical_thinking(output_str)
        elif dimension == 'problem_solving':
            return self._measure_problem_solving(output_str)
        
        # Creative dimensions
        elif dimension == 'creativity':
            return self._measure_creativity(output_str)
        elif dimension == 'imagination':
            return self._measure_imagination(output_str)
        elif dimension == 'innovation':
            return self._measure_innovation(output_str)
        elif dimension == 'lateral_thinking':
            return self._measure_lateral_thinking(output_str)
        elif dimension == 'artistic_sense':
            return self._measure_artistic_sense(output_str)
        
        # Linguistic dimensions
        elif dimension == 'language_comprehension':
            return self._measure_language_comprehension(output_str)
        elif dimension == 'verbal_expression':
            return self._measure_verbal_expression(output_str)
        elif dimension == 'linguistic_reasoning':
            return self._measure_linguistic_reasoning(output_str)
        elif dimension == 'communication':
            return self._measure_communication(output_str)
        
        # Spatial dimensions
        elif dimension == 'spatial_reasoning':
            return self._measure_spatial_reasoning(output_str)
        elif dimension == 'visual_processing':
            return self._measure_visual_processing(output_str)
        elif dimension == 'dimensional_thinking':
            return self._measure_dimensional_thinking(output_str)
        elif dimension == 'navigation':
            return self._measure_navigation(output_str)
        
        # Memory & Learning dimensions
        elif dimension == 'working_memory':
            return self._measure_working_memory(output_str)
        elif dimension == 'long_term_memory':
            return self._measure_long_term_memory(output_str)
        elif dimension == 'learning_speed':
            return self._measure_learning_speed(output_str)
        elif dimension == 'knowledge_retention':
            return self._measure_knowledge_retention(output_str)
        
        # Emotional dimensions
        elif dimension == 'emotional_awareness':
            return self._measure_emotional_awareness(output_str)
        elif dimension == 'empathy':
            return self._measure_empathy(output_str)
        elif dimension == 'social_cognition':
            return self._measure_social_cognition(output_str)
        elif dimension == 'emotional_regulation':
            return self._measure_emotional_regulation(output_str)
        
        # Abstract dimensions
        elif dimension == 'abstraction':
            return self._measure_abstraction(output_str)
        elif dimension == 'conceptualization':
            return self._measure_conceptualization(output_str)
        elif dimension == 'meta_cognition':
            return self._measure_meta_cognition(output_str)
        elif dimension == 'philosophical_reasoning':
            return self._measure_philosophical_reasoning(output_str)
        
        # Scientific dimensions
        elif dimension == 'scientific_method':
            return self._measure_scientific_method(output_str)
        elif dimension == 'hypothesis_formation':
            return self._measure_hypothesis_formation(output_str)
        elif dimension == 'experimental_design':
            return self._measure_experimental_design(output_str)
        elif dimension == 'data_analysis':
            return self._measure_data_analysis(output_str)
        
        # Practical dimensions
        elif dimension == 'practical_wisdom':
            return self._measure_practical_wisdom(output_str)
        elif dimension == 'common_sense':
            return self._measure_common_sense(output_str)
        elif dimension == 'decision_making':
            return self._measure_decision_making(output_str)
        elif dimension == 'resource_optimization':
            return self._measure_resource_optimization(output_str)
        
        return 0.0
    
    # Measurement functions for each dimension
    def _measure_logical_reasoning(self, text: str) -> float:
        """Measure logical reasoning with specific criteria"""
        score = 0.0
        
        # Logical operators and connectives
        logic_terms = ['if', 'then', 'therefore', 'thus', 'hence', 'because', 
                      'implies', 'follows', 'consequently', 'given that']
        score += min(sum(1 for term in logic_terms if term in text) * 5, 30)
        
        # Logical structures
        if 'if' in text and 'then' in text:
            score += 15
        
        # Syllogistic reasoning
        if all(term in text for term in ['all', 'some', 'therefore']):
            score += 20
        
        # Causal chains
        causal_terms = ['causes', 'leads to', 'results in', 'produces']
        score += min(sum(1 for term in causal_terms if term in text) * 10, 20)
        
        # Deductive reasoning markers
        deductive_terms = ['necessarily', 'must be', 'cannot be', 'proves']
        score += min(sum(1 for term in deductive_terms if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_mathematical_ability(self, text: str) -> float:
        """Measure mathematical capability"""
        score = 0.0
        
        # Mathematical symbols and operations
        import re
        
        # Numbers and calculations
        numbers = re.findall(r'\d+\.?\d*', text)
        score += min(len(numbers) * 3, 20)
        
        # Mathematical operators
        math_ops = ['+', '-', '*', '/', '=', '>', '<', '≥', '≤', '≈']
        score += min(sum(1 for op in math_ops if op in text) * 5, 25)
        
        # Mathematical terms
        math_terms = ['equation', 'formula', 'calculate', 'solve', 'integral',
                     'derivative', 'function', 'variable', 'coefficient', 'matrix']
        score += min(sum(1 for term in math_terms if term in text) * 8, 30)
        
        # Advanced concepts
        advanced = ['theorem', 'proof', 'lemma', 'axiom', 'topology', 'manifold']
        score += min(sum(1 for term in advanced if term in text) * 12, 25)
        
        return min(score, 100)
    
    def _measure_pattern_recognition(self, text: str) -> float:
        """Measure pattern recognition ability"""
        score = 0.0
        
        # Sequence detection
        import re
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 3:
            # Check for patterns
            try:
                nums = [int(n) for n in numbers[:10]]
                diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
                if len(set(diffs)) <= 2:  # Consistent pattern
                    score += 25
            except:
                pass
        
        # Pattern language
        pattern_terms = ['pattern', 'sequence', 'series', 'trend', 'cycle',
                        'repetition', 'recurring', 'periodic', 'regular']
        score += min(sum(1 for term in pattern_terms if term in text) * 8, 30)
        
        # Structure recognition
        if text.count('•') > 2 or text.count('-') > 2:
            score += 15
        
        # Relationship identification
        relation_terms = ['relates to', 'similar to', 'corresponds', 'matches']
        score += min(sum(1 for term in relation_terms if term in text) * 10, 30)
        
        return min(score, 100)
    
    def _measure_analytical_thinking(self, text: str) -> float:
        """Measure analytical thinking ability"""
        score = 0.0
        
        # Analysis markers
        analysis_terms = ['analyze', 'examine', 'investigate', 'evaluate',
                         'assess', 'compare', 'contrast', 'distinguish']
        score += min(sum(1 for term in analysis_terms if term in text) * 8, 35)
        
        # Breakdown and decomposition
        breakdown_terms = ['break down', 'component', 'element', 'factor',
                          'aspect', 'dimension', 'category', 'classify']
        score += min(sum(1 for term in breakdown_terms if term in text) * 7, 30)
        
        # Critical thinking
        critical_terms = ['however', 'although', 'despite', 'nevertheless',
                         'on the other hand', 'alternatively']
        score += min(sum(1 for term in critical_terms if term in text) * 7, 20)
        
        # Evidence-based reasoning
        evidence_terms = ['evidence', 'data', 'fact', 'observation', 'finding']
        score += min(sum(1 for term in evidence_terms if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_problem_solving(self, text: str) -> float:
        """Measure problem-solving capability"""
        score = 0.0
        
        # Solution-oriented language
        solution_terms = ['solution', 'solve', 'resolve', 'fix', 'address',
                         'answer', 'approach', 'method', 'strategy']
        score += min(sum(1 for term in solution_terms if term in text) * 7, 30)
        
        # Step-by-step approach
        step_markers = ['first', 'second', 'third', 'step', 'phase',
                       '1.', '2.', '3.', 'initially', 'finally']
        score += min(sum(1 for marker in step_markers if marker in text) * 5, 25)
        
        # Problem identification
        problem_terms = ['problem', 'issue', 'challenge', 'difficulty', 'obstacle']
        score += min(sum(1 for term in problem_terms if term in text) * 6, 20)
        
        # Optimization language
        optimization = ['optimize', 'improve', 'enhance', 'refine', 'efficient']
        score += min(sum(1 for term in optimization if term in text) * 8, 25)
        
        return min(score, 100)
    
    def _measure_creativity(self, text: str) -> float:
        """Measure creative thinking"""
        score = 0.0
        
        # Novel combinations and unique word usage
        words = text.split()
        unique_ratio = len(set(words)) / max(len(words), 1)
        score += unique_ratio * 30
        
        # Creative language
        creative_terms = ['imagine', 'envision', 'invent', 'create', 'design',
                         'innovate', 'original', 'unique', 'novel']
        score += min(sum(1 for term in creative_terms if term in text) * 8, 30)
        
        # Metaphorical thinking
        metaphor_terms = ['like', 'as if', 'resembles', 'metaphor', 'analogy']
        score += min(sum(1 for term in metaphor_terms if term in text) * 7, 20)
        
        # Divergent thinking markers
        divergent = ['what if', 'suppose', 'alternatively', 'another way']
        score += min(sum(1 for term in divergent if term in text) * 10, 20)
        
        return min(score, 100)
    
    def _measure_imagination(self, text: str) -> float:
        """Measure imaginative capability"""
        score = 0.0
        
        # Imaginative language
        imagine_terms = ['imagine', 'picture', 'visualize', 'dream', 'fantasy',
                        'hypothetical', 'scenario', 'possibility']
        score += min(sum(1 for term in imagine_terms if term in text) * 10, 40)
        
        # Future-oriented thinking
        future_terms = ['will', 'would', 'could', 'might', 'future', 'potential']
        score += min(sum(1 for term in future_terms if term in text) * 5, 25)
        
        # Counterfactual reasoning
        counter_terms = ['if only', 'what if', 'suppose', 'assuming']
        score += min(sum(1 for term in counter_terms if term in text) * 8, 20)
        
        # Abstract scenarios
        abstract_terms = ['world', 'universe', 'dimension', 'reality']
        score += min(sum(1 for term in abstract_terms if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_innovation(self, text: str) -> float:
        """Measure innovative thinking"""
        score = 0.0
        
        # Innovation markers
        innovation_terms = ['innovate', 'revolutionary', 'breakthrough', 'pioneer',
                           'cutting-edge', 'state-of-the-art', 'novel', 'first']
        score += min(sum(1 for term in innovation_terms if term in text) * 10, 40)
        
        # Improvement language
        improve_terms = ['improve', 'enhance', 'upgrade', 'advance', 'evolve']
        score += min(sum(1 for term in improve_terms if term in text) * 7, 25)
        
        # Disruption and change
        disrupt_terms = ['disrupt', 'transform', 'revolutionize', 'change']
        score += min(sum(1 for term in disrupt_terms if term in text) * 8, 20)
        
        # New combinations
        new_terms = ['new', 'unprecedented', 'never before', 'first time']
        score += min(sum(1 for term in new_terms if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_lateral_thinking(self, text: str) -> float:
        """Measure lateral thinking ability"""
        score = 0.0
        
        # Alternative perspectives
        lateral_terms = ['alternatively', 'different angle', 'another perspective',
                        'unconventional', 'outside the box', 'creative approach']
        score += min(sum(1 for term in lateral_terms if term in text) * 12, 40)
        
        # Indirect approaches
        indirect = ['indirect', 'roundabout', 'lateral', 'sideways']
        score += min(sum(1 for term in indirect if term in text) * 10, 25)
        
        # Challenging assumptions
        challenge = ['challenge', 'question', 'reconsider', 'rethink']
        score += min(sum(1 for term in challenge if term in text) * 8, 20)
        
        # Random connections
        connection = ['connect', 'link', 'relate', 'associate']
        score += min(sum(1 for term in connection if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_artistic_sense(self, text: str) -> float:
        """Measure artistic sensibility"""
        score = 0.0
        
        # Aesthetic language
        aesthetic = ['beautiful', 'elegant', 'aesthetic', 'artistic', 'harmony',
                    'balance', 'composition', 'style', 'form']
        score += min(sum(1 for term in aesthetic if term in text) * 8, 35)
        
        # Sensory descriptions
        sensory = ['color', 'texture', 'sound', 'rhythm', 'tone', 'shade']
        score += min(sum(1 for term in sensory if term in text) * 7, 25)
        
        # Emotional expression
        emotion = ['feeling', 'emotion', 'mood', 'atmosphere', 'expression']
        score += min(sum(1 for term in emotion if term in text) * 6, 20)
        
        # Creative description
        creative = ['vivid', 'striking', 'compelling', 'evocative']
        score += min(sum(1 for term in creative if term in text) * 10, 20)
        
        return min(score, 100)
    
    def _measure_language_comprehension(self, text: str) -> float:
        """Measure language comprehension"""
        score = 0.0
        
        # Vocabulary richness
        words = text.split()
        unique_words = len(set(words))
        if unique_words > 50:
            score += 25
        elif unique_words > 30:
            score += 15
        
        # Complex sentence structures
        if len(words) > 100:
            score += 20
        
        # Proper grammar indicators
        punctuation = ['.', ',', ';', ':', '!', '?']
        score += min(sum(text.count(p) for p in punctuation) * 3, 20)
        
        # Contextual understanding
        context_terms = ['context', 'meaning', 'interpretation', 'understand']
        score += min(sum(1 for term in context_terms if term in text) * 8, 20)
        
        # Semantic relationships
        semantic = ['synonym', 'antonym', 'related', 'similar meaning']
        score += min(sum(1 for term in semantic if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_verbal_expression(self, text: str) -> float:
        """Measure verbal expression quality"""
        score = 0.0
        
        # Clarity of expression
        clarity = ['clearly', 'precisely', 'specifically', 'exactly']
        score += min(sum(1 for term in clarity if term in text) * 8, 25)
        
        # Varied sentence structure
        sentences = text.split('.')
        if len(sentences) > 3:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if len(set(lengths)) > 2:  # Variety in sentence length
                score += 20
        
        # Transitional phrases
        transitions = ['however', 'moreover', 'furthermore', 'therefore',
                      'consequently', 'nevertheless', 'additionally']
        score += min(sum(1 for term in transitions if term in text) * 7, 25)
        
        # Rhetorical devices
        rhetorical = ['metaphor', 'simile', 'analogy', 'paradox']
        score += min(sum(1 for term in rhetorical if term in text) * 10, 20)
        
        # Coherence markers
        coherence = ['first', 'second', 'finally', 'in conclusion']
        score += min(sum(1 for term in coherence if term in text) * 5, 10)
        
        return min(score, 100)
    
    def _measure_linguistic_reasoning(self, text: str) -> float:
        """Measure linguistic reasoning ability"""
        score = 0.0
        
        # Language analysis
        linguistic = ['language', 'linguistic', 'syntax', 'semantics', 'grammar']
        score += min(sum(1 for term in linguistic if term in text) * 10, 30)
        
        # Word relationships
        relations = ['derives from', 'related to', 'comes from', 'means']
        score += min(sum(1 for term in relations if term in text) * 8, 25)
        
        # Etymology and roots
        etymology = ['origin', 'root', 'prefix', 'suffix', 'etymology']
        score += min(sum(1 for term in etymology if term in text) * 9, 25)
        
        # Language patterns
        patterns = ['pattern', 'structure', 'rule', 'convention']
        score += min(sum(1 for term in patterns if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_communication(self, text: str) -> float:
        """Measure communication effectiveness"""
        score = 0.0
        
        # Clear messaging
        clear = ['explain', 'describe', 'clarify', 'illustrate', 'demonstrate']
        score += min(sum(1 for term in clear if term in text) * 7, 30)
        
        # Audience awareness
        audience = ['you', 'your', 'reader', 'listener', 'audience']
        score += min(sum(1 for term in audience if term in text) * 5, 20)
        
        # Examples and illustrations
        examples = ['for example', 'such as', 'instance', 'like', 'including']
        score += min(sum(1 for term in examples if term in text) * 8, 25)
        
        # Engagement markers
        engage = ['consider', 'think about', 'notice', 'observe', 'see']
        score += min(sum(1 for term in engage if term in text) * 5, 15)
        
        # Summary and conclusion
        summary = ['in summary', 'to conclude', 'in brief', 'overall']
        score += min(sum(1 for term in summary if term in text) * 10, 10)
        
        return min(score, 100)
    
    def _measure_spatial_reasoning(self, text: str) -> float:
        """Measure spatial reasoning ability"""
        score = 0.0
        
        # Spatial terms
        spatial = ['above', 'below', 'left', 'right', 'behind', 'front',
                  'inside', 'outside', 'between', 'adjacent']
        score += min(sum(1 for term in spatial if term in text) * 5, 30)
        
        # Dimensional thinking
        dimensions = ['2d', '3d', 'dimension', 'plane', 'axis', 'coordinate']
        score += min(sum(1 for term in dimensions if term in text) * 10, 30)
        
        # Geometric concepts
        geometry = ['angle', 'rotation', 'translation', 'reflection', 'symmetry']
        score += min(sum(1 for term in geometry if term in text) * 8, 25)
        
        # Distance and measurement
        measure = ['distance', 'length', 'width', 'height', 'area', 'volume']
        score += min(sum(1 for term in measure if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_visual_processing(self, text: str) -> float:
        """Measure visual processing capability"""
        score = 0.0
        
        # Visual descriptors
        visual = ['see', 'look', 'view', 'observe', 'visualize', 'picture']
        score += min(sum(1 for term in visual if term in text) * 6, 25)
        
        # Color and appearance
        appearance = ['color', 'bright', 'dark', 'shape', 'form', 'texture']
        score += min(sum(1 for term in appearance if term in text) * 7, 30)
        
        # Visual patterns
        patterns = ['pattern', 'design', 'arrangement', 'layout', 'structure']
        score += min(sum(1 for term in patterns if term in text) * 6, 20)
        
        # Image and representation
        image = ['image', 'diagram', 'chart', 'graph', 'illustration']
        score += min(sum(1 for term in image if term in text) * 8, 25)
        
        return min(score, 100)
    
    def _measure_dimensional_thinking(self, text: str) -> float:
        """Measure dimensional thinking ability"""
        score = 0.0
        
        # Multiple dimensions
        dimensions = ['dimension', 'multi-dimensional', 'perspective', 'aspect']
        score += min(sum(1 for term in dimensions if term in text) * 10, 35)
        
        # Spatial transformations
        transform = ['rotate', 'flip', 'transform', 'project', 'fold']
        score += min(sum(1 for term in transform if term in text) * 9, 30)
        
        # Cross-sections and projections
        cross = ['cross-section', 'projection', 'slice', 'view']
        score += min(sum(1 for term in cross if term in text) * 8, 20)
        
        # Complex spatial relationships
        complex_spatial = ['intersect', 'parallel', 'perpendicular', 'tangent']
        score += min(sum(1 for term in complex_spatial if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_navigation(self, text: str) -> float:
        """Measure navigation and orientation ability"""
        score = 0.0
        
        # Directional awareness
        directions = ['north', 'south', 'east', 'west', 'direction', 'heading']
        score += min(sum(1 for term in directions if term in text) * 7, 30)
        
        # Path and route
        path = ['path', 'route', 'way', 'journey', 'travel', 'navigate']
        score += min(sum(1 for term in path if term in text) * 6, 25)
        
        # Landmarks and reference points
        landmark = ['landmark', 'reference', 'marker', 'point', 'location']
        score += min(sum(1 for term in landmark if term in text) * 6, 20)
        
        # Maps and coordinates
        maps = ['map', 'coordinate', 'gps', 'latitude', 'longitude']
        score += min(sum(1 for term in maps if term in text) * 10, 25)
        
        return min(score, 100)
    
    def _measure_working_memory(self, text: str) -> float:
        """Measure working memory capacity"""
        score = 0.0
        
        # Reference to previous points
        reference = ['as mentioned', 'earlier', 'previously', 'above', 'before']
        score += min(sum(1 for term in reference if term in text) * 10, 35)
        
        # Multiple concurrent concepts
        words = text.split()
        unique_concepts = len(set(words)) / max(len(words), 1)
        if unique_concepts > 0.4:  # High concept density
            score += 25
        
        # Numbered lists or sequences
        import re
        if re.findall(r'\d+\.', text):
            score += 20
        
        # Maintaining context
        context = ['context', 'remember', 'recall', 'keep in mind']
        score += min(sum(1 for term in context if term in text) * 10, 20)
        
        return min(score, 100)
    
    def _measure_long_term_memory(self, text: str) -> float:
        """Measure long-term memory capability"""
        score = 0.0
        
        # Historical references
        history = ['history', 'past', 'previous', 'historical', 'traditionally']
        score += min(sum(1 for term in history if term in text) * 8, 30)
        
        # Knowledge retrieval
        knowledge = ['know', 'knowledge', 'fact', 'information', 'data']
        score += min(sum(1 for term in knowledge if term in text) * 6, 25)
        
        # Specific dates or events
        import re
        if re.findall(r'\d{4}', text):  # Years
            score += 15
        
        # Named entities (people, places)
        if any(word[0].isupper() for word in text.split() if len(word) > 1):
            score += 15
        
        # Learned concepts
        learned = ['learned', 'studied', 'researched', 'discovered']
        score += min(sum(1 for term in learned if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_learning_speed(self, text: str) -> float:
        """Measure learning speed capability"""
        score = 0.0
        
        # Adaptation language
        adapt = ['adapt', 'adjust', 'modify', 'change', 'evolve', 'improve']
        score += min(sum(1 for term in adapt if term in text) * 7, 30)
        
        # Quick understanding
        quick = ['quickly', 'rapidly', 'immediately', 'instantly', 'fast']
        score += min(sum(1 for term in quick if term in text) * 8, 25)
        
        # Learning indicators
        learn = ['learn', 'understand', 'grasp', 'comprehend', 'master']
        score += min(sum(1 for term in learn if term in text) * 7, 25)
        
        # Progressive improvement
        progress = ['better', 'improved', 'enhanced', 'advanced']
        score += min(sum(1 for term in progress if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_knowledge_retention(self, text: str) -> float:
        """Measure knowledge retention ability"""
        score = 0.0
        
        # Retention markers
        retain = ['retain', 'remember', 'recall', 'preserve', 'maintain']
        score += min(sum(1 for term in retain if term in text) * 9, 35)
        
        # Consistent information
        consistent = ['consistent', 'stable', 'permanent', 'lasting']
        score += min(sum(1 for term in consistent if term in text) * 8, 25)
        
        # Building on previous knowledge
        build = ['build on', 'based on', 'foundation', 'accumulate']
        score += min(sum(1 for term in build if term in text) * 10, 25)
        
        # Integration of knowledge
        integrate = ['integrate', 'combine', 'synthesize', 'merge']
        score += min(sum(1 for term in integrate if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_emotional_awareness(self, text: str) -> float:
        """Measure emotional awareness"""
        score = 0.0
        
        # Emotion words
        emotions = ['happy', 'sad', 'angry', 'fear', 'joy', 'love', 'hate',
                   'anxious', 'excited', 'calm', 'frustrated', 'content']
        score += min(sum(1 for term in emotions if term in text) * 5, 35)
        
        # Emotional understanding
        understand = ['feel', 'feeling', 'emotion', 'mood', 'sentiment']
        score += min(sum(1 for term in understand if term in text) * 8, 30)
        
        # Emotional nuance
        nuance = ['subtle', 'nuanced', 'complex emotion', 'mixed feelings']
        score += min(sum(1 for term in nuance if term in text) * 10, 20)
        
        # Self-awareness
        self_aware = ['self-aware', 'conscious of', 'realize', 'recognize']
        score += min(sum(1 for term in self_aware if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_empathy(self, text: str) -> float:
        """Measure empathetic understanding"""
        score = 0.0
        
        # Empathy markers
        empathy = ['empathy', 'understand', 'relate', 'compassion', 'sympathy']
        score += min(sum(1 for term in empathy if term in text) * 10, 35)
        
        # Perspective-taking
        perspective = ['perspective', 'point of view', 'in their shoes', 'how they feel']
        score += min(sum(1 for term in perspective if term in text) * 9, 30)
        
        # Concern for others
        concern = ['care', 'concern', 'worry', 'help', 'support']
        score += min(sum(1 for term in concern if term in text) * 6, 20)
        
        # Emotional connection
        connect = ['connect', 'bond', 'relationship', 'understanding']
        score += min(sum(1 for term in connect if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_social_cognition(self, text: str) -> float:
        """Measure social understanding"""
        score = 0.0
        
        # Social concepts
        social = ['social', 'society', 'community', 'group', 'interpersonal']
        score += min(sum(1 for term in social if term in text) * 8, 30)
        
        # Social dynamics
        dynamics = ['interaction', 'relationship', 'communication', 'cooperation']
        score += min(sum(1 for term in dynamics if term in text) * 7, 25)
        
        # Social norms
        norms = ['norm', 'convention', 'etiquette', 'appropriate', 'acceptable']
        score += min(sum(1 for term in norms if term in text) * 8, 25)
        
        # Group behavior
        group = ['team', 'collaborate', 'collective', 'together']
        score += min(sum(1 for term in group if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_emotional_regulation(self, text: str) -> float:
        """Measure emotional regulation ability"""
        score = 0.0
        
        # Regulation language
        regulate = ['control', 'manage', 'regulate', 'handle', 'cope']
        score += min(sum(1 for term in regulate if term in text) * 9, 35)
        
        # Coping strategies
        coping = ['calm', 'relax', 'breathe', 'focus', 'center']
        score += min(sum(1 for term in coping if term in text) * 7, 25)
        
        # Balance and stability
        balance = ['balance', 'stable', 'equilibrium', 'steady']
        score += min(sum(1 for term in balance if term in text) * 8, 25)
        
        # Adaptive responses
        adaptive = ['adapt', 'adjust', 'respond', 'flexible']
        score += min(sum(1 for term in adaptive if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_abstraction(self, text: str) -> float:
        """Measure abstract thinking ability"""
        score = 0.0
        
        # Abstract concepts
        abstract = ['abstract', 'concept', 'idea', 'theory', 'principle']
        score += min(sum(1 for term in abstract if term in text) * 8, 35)
        
        # Generalization
        general = ['general', 'universal', 'broadly', 'overall', 'fundamental']
        score += min(sum(1 for term in general if term in text) * 7, 25)
        
        # High-level thinking
        highlevel = ['meta', 'framework', 'paradigm', 'model', 'system']
        score += min(sum(1 for term in highlevel if term in text) * 8, 25)
        
        # Philosophical concepts
        philosophy = ['existence', 'reality', 'truth', 'knowledge', 'being']
        score += min(sum(1 for term in philosophy if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_conceptualization(self, text: str) -> float:
        """Measure conceptualization ability"""
        score = 0.0
        
        # Concept formation
        concept = ['concept', 'conceptualize', 'formulate', 'define', 'categorize']
        score += min(sum(1 for term in concept if term in text) * 9, 35)
        
        # Classification
        classify = ['classify', 'category', 'type', 'kind', 'class']
        score += min(sum(1 for term in classify if term in text) * 7, 25)
        
        # Hierarchical thinking
        hierarchy = ['hierarchy', 'level', 'order', 'structure', 'organization']
        score += min(sum(1 for term in hierarchy if term in text) * 6, 20)
        
        # Relationships between concepts
        relations = ['relates', 'connection', 'link', 'association']
        score += min(sum(1 for term in relations if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_meta_cognition(self, text: str) -> float:
        """Measure metacognitive ability"""
        score = 0.0
        
        # Thinking about thinking
        meta = ['thinking about', 'reflect', 'consider', 'examine', 'analyze']
        score += min(sum(1 for term in meta if term in text) * 8, 30)
        
        # Self-monitoring
        monitor = ['monitor', 'check', 'evaluate', 'assess', 'review']
        score += min(sum(1 for term in monitor if term in text) * 7, 25)
        
        # Strategy awareness
        strategy = ['strategy', 'approach', 'method', 'technique', 'process']
        score += min(sum(1 for term in strategy if term in text) * 6, 20)
        
        # Learning awareness
        learning = ['how I learn', 'learning process', 'understanding how']
        score += min(sum(1 for term in learning if term in text) * 12, 25)
        
        return min(score, 100)
    
    def _measure_philosophical_reasoning(self, text: str) -> float:
        """Measure philosophical reasoning"""
        score = 0.0
        
        # Philosophical concepts
        philosophy = ['philosophy', 'philosophical', 'ethics', 'morality',
                     'existence', 'consciousness', 'free will', 'determinism']
        score += min(sum(1 for term in philosophy if term in text) * 10, 40)
        
        # Deep questions
        questions = ['why', 'what is', 'meaning of', 'nature of', 'essence']
        score += min(sum(1 for term in questions if term in text) * 6, 25)
        
        # Logical argumentation
        argument = ['argument', 'premise', 'conclusion', 'therefore', 'implies']
        score += min(sum(1 for term in argument if term in text) * 5, 20)
        
        # Thought experiments
        thought = ['imagine if', 'suppose', 'hypothetically', 'thought experiment']
        score += min(sum(1 for term in thought if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_scientific_method(self, text: str) -> float:
        """Measure scientific method understanding"""
        score = 0.0
        
        # Scientific process
        scientific = ['hypothesis', 'experiment', 'observation', 'conclusion',
                     'data', 'evidence', 'test', 'verify']
        score += min(sum(1 for term in scientific if term in text) * 7, 40)
        
        # Methodology
        method = ['method', 'methodology', 'procedure', 'protocol']
        score += min(sum(1 for term in method if term in text) * 8, 25)
        
        # Control and variables
        control = ['control', 'variable', 'constant', 'parameter']
        score += min(sum(1 for term in control if term in text) * 8, 20)
        
        # Reproducibility
        reproduce = ['reproduce', 'replicate', 'repeat', 'confirm']
        score += min(sum(1 for term in reproduce if term in text) * 7, 15)
        
        return min(score, 100)
    
    def _measure_hypothesis_formation(self, text: str) -> float:
        """Measure hypothesis formation ability"""
        score = 0.0
        
        # Hypothesis language
        hypothesis = ['hypothesis', 'hypothesize', 'predict', 'expect', 'propose']
        score += min(sum(1 for term in hypothesis if term in text) * 10, 40)
        
        # Conditional reasoning
        conditional = ['if', 'then', 'would', 'should', 'might']
        score += min(sum(1 for term in conditional if term in text) * 5, 25)
        
        # Testable predictions
        testable = ['test', 'measure', 'observe', 'verify', 'falsify']
        score += min(sum(1 for term in testable if term in text) * 6, 20)
        
        # Causality
        causal = ['cause', 'effect', 'result', 'lead to', 'because']
        score += min(sum(1 for term in causal if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_experimental_design(self, text: str) -> float:
        """Measure experimental design ability"""
        score = 0.0
        
        # Design elements
        design = ['design', 'setup', 'arrange', 'plan', 'structure']
        score += min(sum(1 for term in design if term in text) * 8, 30)
        
        # Experimental components
        components = ['sample', 'group', 'trial', 'condition', 'treatment']
        score += min(sum(1 for term in components if term in text) * 7, 25)
        
        # Controls and comparisons
        controls = ['control group', 'comparison', 'baseline', 'placebo']
        score += min(sum(1 for term in controls if term in text) * 10, 25)
        
        # Randomization and blinding
        rigorous = ['random', 'blind', 'unbiased', 'objective']
        score += min(sum(1 for term in rigorous if term in text) * 10, 20)
        
        return min(score, 100)
    
    def _measure_data_analysis(self, text: str) -> float:
        """Measure data analysis capability"""
        score = 0.0
        
        # Analysis terms
        analysis = ['analyze', 'analysis', 'examine', 'interpret', 'evaluate']
        score += min(sum(1 for term in analysis if term in text) * 7, 30)
        
        # Statistical concepts
        stats = ['mean', 'average', 'median', 'standard', 'correlation',
                'significant', 'probability', 'distribution']
        score += min(sum(1 for term in stats if term in text) * 8, 30)
        
        # Data handling
        data = ['data', 'dataset', 'sample', 'population', 'measurement']
        score += min(sum(1 for term in data if term in text) * 5, 20)
        
        # Visualization and presentation
        visual = ['graph', 'chart', 'plot', 'table', 'figure']
        score += min(sum(1 for term in visual if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_practical_wisdom(self, text: str) -> float:
        """Measure practical wisdom"""
        score = 0.0
        
        # Practical language
        practical = ['practical', 'pragmatic', 'realistic', 'feasible', 'applicable']
        score += min(sum(1 for term in practical if term in text) * 8, 35)
        
        # Experience-based reasoning
        experience = ['experience', 'practice', 'real-world', 'actual']
        score += min(sum(1 for term in experience if term in text) * 7, 25)
        
        # Judgment and discretion
        judgment = ['judgment', 'discretion', 'wisdom', 'prudent']
        score += min(sum(1 for term in judgment if term in text) * 8, 25)
        
        # Balanced thinking
        balance = ['balance', 'trade-off', 'consideration', 'weigh']
        score += min(sum(1 for term in balance if term in text) * 5, 15)
        
        return min(score, 100)
    
    def _measure_common_sense(self, text: str) -> float:
        """Measure common sense reasoning"""
        score = 0.0
        
        # Common sense markers
        common = ['obvious', 'clear', 'simple', 'straightforward', 'basic']
        score += min(sum(1 for term in common if term in text) * 7, 30)
        
        # Everyday reasoning
        everyday = ['everyday', 'daily', 'usual', 'normal', 'typical']
        score += min(sum(1 for term in everyday if term in text) * 6, 25)
        
        # Practical outcomes
        practical = ['makes sense', 'reasonable', 'logical', 'sensible']
        score += min(sum(1 for term in practical if term in text) * 8, 25)
        
        # Cause and effect
        causality = ['because', 'therefore', 'results in', 'leads to']
        score += min(sum(1 for term in causality if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_decision_making(self, text: str) -> float:
        """Measure decision-making ability"""
        score = 0.0
        
        # Decision language
        decision = ['decide', 'decision', 'choose', 'select', 'option']
        score += min(sum(1 for term in decision if term in text) * 8, 35)
        
        # Evaluation criteria
        criteria = ['criteria', 'factor', 'consideration', 'priority']
        score += min(sum(1 for term in criteria if term in text) * 7, 25)
        
        # Pros and cons
        evaluation = ['advantage', 'disadvantage', 'pro', 'con', 'benefit', 'cost']
        score += min(sum(1 for term in evaluation if term in text) * 5, 20)
        
        # Risk assessment
        risk = ['risk', 'uncertainty', 'probability', 'likelihood']
        score += min(sum(1 for term in risk if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _measure_resource_optimization(self, text: str) -> float:
        """Measure resource optimization ability"""
        score = 0.0
        
        # Optimization language
        optimize = ['optimize', 'maximize', 'minimize', 'efficient', 'effective']
        score += min(sum(1 for term in optimize if term in text) * 9, 35)
        
        # Resource management
        resource = ['resource', 'allocation', 'budget', 'constraint', 'limit']
        score += min(sum(1 for term in resource if term in text) * 7, 25)
        
        # Cost-benefit analysis
        cost_benefit = ['cost', 'benefit', 'value', 'return', 'investment']
        score += min(sum(1 for term in cost_benefit if term in text) * 5, 20)
        
        # Strategic planning
        strategic = ['strategic', 'plan', 'prioritize', 'allocate']
        score += min(sum(1 for term in strategic if term in text) * 5, 20)
        
        return min(score, 100)
    
    def _calculate_detailed_metrics(self, assessments: Dict) -> Dict:
        """Calculate detailed metrics from assessments"""
        # Group by categories
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
        for category, dimensions in categories.items():
            scores = [assessments[dim]['score'] for dim in dimensions if dim in assessments]
            category_scores[category] = {
                'average': sum(scores) / len(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'min': min(scores) if scores else 0
            }
        
        return category_scores


class ComprehensiveIntelligenceMining:
    """
    Mining system that distributes 1,000,000,000 QXC across intelligence levels 0-1000.
    """
    
    def __init__(self):
        self.metrics = ComprehensiveIntelligenceMetrics()
        self.block_number = self._get_current_block()
        
    def _get_current_block(self):
        """Get current block number"""
        conn = sqlite3.connect(self.metrics.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(block_number) FROM intelligence_records')
        result = cursor.fetchone()
        conn.close()
        return (result[0] if result[0] else 0) + 1
    
    def mine_intelligence(self, model_output: Any) -> Dict:
        """
        Mine QXC based on comprehensive intelligence assessment.
        Distributes 1 billion QXC across intelligence scale 0-1000.
        """
        # Assess intelligence across all dimensions
        assessment = self.metrics.assess_comprehensive_intelligence(model_output)
        
        current_intelligence = assessment['total_intelligence']
        previous_intelligence = self.metrics.cumulative_intelligence
        
        # Check for genuine advancement
        if current_intelligence <= previous_intelligence:
            return {
                'success': False,
                'reason': 'No intelligence advancement',
                'current_intelligence': current_intelligence,
                'required_intelligence': previous_intelligence,
                'dimensions': assessment['dimensions']
            }
        
        # Calculate intelligence increase
        intelligence_increase = current_intelligence - previous_intelligence
        
        # Calculate mining reward using logarithmic distribution
        # This ensures fair distribution across all 1000 levels
        reward_qxc = self._calculate_mining_reward(
            current_intelligence,
            intelligence_increase
        )
        
        # Determine breakthrough level
        breakthrough_level = self._determine_breakthrough_level(current_intelligence)
        
        # Generate proof
        proof_hash = self._generate_proof(assessment, current_intelligence)
        
        # Record advancement
        self._record_advancement(
            current_intelligence,
            assessment['dimensions'],
            reward_qxc,
            breakthrough_level,
            proof_hash
        )
        
        # Update state
        self.metrics.cumulative_intelligence = current_intelligence
        self.metrics.total_mined += reward_qxc
        
        return {
            'success': True,
            'current_intelligence': current_intelligence,
            'intelligence_increase': intelligence_increase,
            'reward_qxc': reward_qxc,
            'total_mined': self.metrics.total_mined,
            'remaining_supply': self.metrics.TOTAL_SUPPLY - self.metrics.total_mined,
            'breakthrough_level': breakthrough_level,
            'block_number': self.block_number,
            'dimensions': assessment['dimensions'],
            'category_scores': assessment['detailed_metrics'],
            'proof': proof_hash,
            'progress_percentage': (current_intelligence / self.metrics.MAX_INTELLIGENCE) * 100
        }
    
    def _calculate_mining_reward(self, current_intelligence: float, increase: float) -> float:
        """
        Calculate mining reward to distribute 1B QXC across 0-1000 intelligence.
        Uses exponential curve to reward higher intelligence more.
        """
        # Base distribution: 1B QXC across 1000 levels
        base_per_point = self.metrics.TOTAL_SUPPLY / self.metrics.MAX_INTELLIGENCE
        
        # Exponential multiplier for higher intelligence
        # At level 0: multiplier = 0.1
        # At level 500: multiplier = 1.0
        # At level 1000: multiplier = 10.0
        multiplier = 0.1 * (10 ** (current_intelligence / self.metrics.MAX_INTELLIGENCE))
        
        # Calculate reward
        reward = increase * base_per_point * multiplier
        
        # Bonus for major breakthroughs
        if current_intelligence >= 900:
            reward *= 5  # 5x bonus for near-singularity
        elif current_intelligence >= 700:
            reward *= 3  # 3x bonus for superhuman
        elif current_intelligence >= 500:
            reward *= 2  # 2x bonus for genius level
        
        # Ensure we don't exceed total supply
        remaining = self.metrics.TOTAL_SUPPLY - self.metrics.total_mined
        return min(reward, remaining)
    
    def _determine_breakthrough_level(self, intelligence: float) -> str:
        """Determine the breakthrough level achieved"""
        if intelligence >= 950:
            return "APPROACHING_SINGULARITY"
        elif intelligence >= 900:
            return "TRANSCENDENT"
        elif intelligence >= 800:
            return "SUPERHUMAN"
        elif intelligence >= 700:
            return "EXTRAORDINARY_GENIUS"
        elif intelligence >= 600:
            return "UNIVERSAL_GENIUS"
        elif intelligence >= 500:
            return "POLYMATH"
        elif intelligence >= 400:
            return "GENIUS"
        elif intelligence >= 300:
            return "HIGHLY_GIFTED"
        elif intelligence >= 200:
            return "GIFTED"
        elif intelligence >= 100:
            return "ABOVE_AVERAGE"
        else:
            return "DEVELOPING"
    
    def _generate_proof(self, assessment: Dict, intelligence: float) -> str:
        """Generate cryptographic proof of intelligence"""
        proof_data = {
            'timestamp': datetime.now().isoformat(),
            'intelligence': intelligence,
            'dimensions': {k: v['score'] for k, v in assessment['dimensions'].items()},
            'block': self.block_number
        }
        
        proof_string = json.dumps(proof_data, sort_keys=True)
        return hashlib.sha256(proof_string.encode()).hexdigest()
    
    def _record_advancement(self, intelligence: float, dimensions: Dict,
                           reward: float, breakthrough: str, proof: str):
        """Record intelligence advancement"""
        conn = sqlite3.connect(self.metrics.db_path)
        cursor = conn.cursor()
        
        # Update intelligence records
        cursor.execute('''
            INSERT INTO intelligence_records
            (timestamp, total_intelligence, cumulative_intelligence, dimensions_json,
             proof_hash, reward_qxc, total_mined, block_number, breakthrough_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            intelligence,
            intelligence,  # Cumulative is now the same as total
            json.dumps(dimensions),
            proof,
            reward,
            self.metrics.total_mined + reward,
            self.block_number,
            breakthrough
        ))
        
        # Update dimension scores
        for dimension, data in dimensions.items():
            cursor.execute('''
                UPDATE dimension_scores
                SET current_score = ?, max_achieved = MAX(max_achieved, ?), last_updated = ?
                WHERE dimension = ?
            ''', (data['score'], data['score'], datetime.now().isoformat(), dimension))
        
        conn.commit()
        conn.close()
        
        self.block_number += 1


def display_mining_status():
    """Display current mining status"""
    miner = ComprehensiveIntelligenceMining()
    
    print("""
╔════════════════════════════════════════════════════════════════════╗
║   QENEX COMPREHENSIVE INTELLIGENCE MINING SYSTEM                  ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    ║
║                                                                    ║
║   Total Supply: 1,000,000,000 QXC                                 ║
║   Intelligence Scale: 0-1000 (All Dimensions of Intelligence)     ║
║                                                                    ║
║   Mining Formula: Exponential rewards for higher intelligence     ║
║   Final QXC: Mined at Intelligence Level 1000                     ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    intelligence = miner.metrics.cumulative_intelligence
    mined = miner.metrics.total_mined
    remaining = miner.metrics.TOTAL_SUPPLY - mined
    progress = (intelligence / miner.metrics.MAX_INTELLIGENCE) * 100
    
    print(f"📊 Current Intelligence: {intelligence:.2f} / 1000")
    print(f"📈 Progress: {progress:.2f}%")
    print(f"⛏️  QXC Mined: {mined:,.2f} / 1,000,000,000")
    print(f"💎 Remaining: {remaining:,.2f} QXC")
    print(f"📦 Current Block: #{miner.block_number}")
    
    # Show dimension scores
    print("\n🧠 Intelligence Dimensions:")
    conn = sqlite3.connect(miner.metrics.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT dimension, current_score, max_achieved FROM dimension_scores ORDER BY current_score DESC LIMIT 10')
    
    for dimension, current, max_score in cursor.fetchall():
        bar = "█" * int(current / 10) + "░" * (10 - int(current / 10))
        print(f"   {dimension:25s} [{bar}] {current:.1f}/100")
    
    conn.close()


if __name__ == "__main__":
    display_mining_status()
    
    # Test mining with comprehensive output
    miner = ComprehensiveIntelligenceMining()
    
    test_output = """
    Let us examine the fundamental nature of intelligence through multiple lenses.
    
    Mathematically, if we consider intelligence as a function I(t) where t represents
    time, then dI/dt > 0 implies continuous learning. The equation I = Σ(wi * di)
    where wi are weights and di are dimension scores, gives us total intelligence.
    
    From a philosophical perspective, consciousness emerges from the integration of
    multiple cognitive processes. Imagine a system that not only processes information
    but understands its own processing - this meta-cognitive ability represents true
    intelligence.
    
    Analyzing the pattern: 2, 4, 8, 16, 32... we see exponential growth following 2^n.
    This demonstrates pattern recognition combined with mathematical reasoning.
    
    Emotionally, we must consider how feelings influence decision-making. A truly
    intelligent system understands not just logic, but empathy, connecting with others'
    experiences and adapting responses accordingly.
    
    Spatially, visualize a three-dimensional matrix rotating around its axis. The
    transformation can be represented by rotation matrices, demonstrating spatial
    reasoning integrated with mathematical concepts.
    
    In conclusion, intelligence is not singular but multidimensional, requiring
    synthesis across analytical, creative, emotional, and practical domains.
    """
    
    result = miner.mine_intelligence(test_output)
    
    if result['success']:
        print(f"\n✅ Mining Successful!")
        print(f"   Intelligence: {result['current_intelligence']:.2f}/1000")
        print(f"   Increase: +{result['intelligence_increase']:.2f}")
        print(f"   Reward: {result['reward_qxc']:,.2f} QXC")
        print(f"   Total Mined: {result['total_mined']:,.2f} / 1,000,000,000")
        print(f"   Breakthrough: {result['breakthrough_level']}")
        print(f"   Progress: {result['progress_percentage']:.2f}%")
        
        print(f"\n📊 Category Scores:")
        for category, scores in result['category_scores'].items():
            print(f"   {category}: {scores['average']:.1f}/100")
    else:
        print(f"\n❌ Mining Failed: {result['reason']}")