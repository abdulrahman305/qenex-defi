#!/usr/bin/env python3
"""
QENEX AI Model Marketplace
Buy, sell, and trade AI models for QXC
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AIMarketplace')

class ModelCategory(Enum):
    NLP = "Natural Language Processing"
    COMPUTER_VISION = "Computer Vision"
    REINFORCEMENT_LEARNING = "Reinforcement Learning"
    GENERATIVE = "Generative AI"
    CLASSIFICATION = "Classification"
    REGRESSION = "Regression"
    TIME_SERIES = "Time Series"
    AUDIO = "Audio Processing"

@dataclass
class AIModel:
    """AI Model listing"""
    id: str
    name: str
    description: str
    category: ModelCategory
    creator: str
    price_qxc: float
    performance_score: float
    downloads: int
    rating: float
    size_mb: float
    created_at: float
    updated_at: float
    royalty_percentage: float
    hash: str
    
class AIModelMarketplace:
    """Marketplace for AI models"""
    
    def __init__(self):
        self.marketplace_dir = Path('/opt/qenex-os/marketplace')
        self.marketplace_dir.mkdir(exist_ok=True)
        self.models_db = self.marketplace_dir / 'models.json'
        self.transactions_db = self.marketplace_dir / 'transactions.json'
        self.models = self._load_models()
        self.transactions = self._load_transactions()
        
    def _load_models(self) -> Dict[str, AIModel]:
        """Load models from database"""
        if self.models_db.exists():
            with open(self.models_db, 'r') as f:
                data = json.load(f)
                return {k: AIModel(**v) for k, v in data.items()}
        return {}
        
    def _load_transactions(self) -> List[Dict]:
        """Load transaction history"""
        if self.transactions_db.exists():
            with open(self.transactions_db, 'r') as f:
                return json.load(f)
        return []
        
    def _save_models(self):
        """Save models to database"""
        data = {k: v.__dict__ for k, v in self.models.items()}
        with open(self.models_db, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def _save_transactions(self):
        """Save transactions"""
        with open(self.transactions_db, 'w') as f:
            json.dump(self.transactions, f, indent=2)
            
    def list_model(self, model_data: Dict) -> AIModel:
        """List a new AI model for sale"""
        
        model_id = hashlib.sha256(
            f"{model_data['name']}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        model = AIModel(
            id=model_id,
            name=model_data['name'],
            description=model_data['description'],
            category=ModelCategory[model_data['category']],
            creator=model_data['creator'],
            price_qxc=model_data['price'],
            performance_score=model_data.get('performance_score', 0.0),
            downloads=0,
            rating=0.0,
            size_mb=model_data.get('size_mb', 0.0),
            created_at=time.time(),
            updated_at=time.time(),
            royalty_percentage=model_data.get('royalty', 10.0),
            hash=hashlib.sha256(str(model_data).encode()).hexdigest()
        )
        
        self.models[model_id] = model
        self._save_models()
        
        logger.info(f"Listed model: {model.name} for {model.price_qxc} QXC")
        return model
        
    def purchase_model(self, model_id: str, buyer: str) -> Dict[str, Any]:
        """Purchase an AI model"""
        
        if model_id not in self.models:
            return {'error': 'Model not found'}
            
        model = self.models[model_id]
        
        # Create transaction
        transaction = {
            'id': hashlib.sha256(f"{model_id}_{buyer}_{time.time()}".encode()).hexdigest()[:16],
            'model_id': model_id,
            'model_name': model.name,
            'buyer': buyer,
            'seller': model.creator,
            'price': model.price_qxc,
            'royalty': model.price_qxc * (model.royalty_percentage / 100),
            'timestamp': time.time(),
            'type': 'purchase'
        }
        
        # Update model stats
        model.downloads += 1
        self.models[model_id] = model
        
        # Save transaction
        self.transactions.append(transaction)
        self._save_transactions()
        self._save_models()
        
        return {
            'success': True,
            'transaction': transaction,
            'download_url': f"/marketplace/download/{model_id}",
            'model': model.__dict__
        }
        
    def rate_model(self, model_id: str, rating: float) -> bool:
        """Rate a model"""
        if model_id not in self.models:
            return False
            
        model = self.models[model_id]
        # Simple rating average (in production, track individual ratings)
        if model.rating == 0:
            model.rating = rating
        else:
            model.rating = (model.rating + rating) / 2
            
        self.models[model_id] = model
        self._save_models()
        return True
        
    def get_trending_models(self, limit: int = 10) -> List[AIModel]:
        """Get trending models"""
        sorted_models = sorted(
            self.models.values(),
            key=lambda x: (x.downloads * 0.5 + x.rating * 0.3 + x.performance_score * 0.2),
            reverse=True
        )
        return sorted_models[:limit]
        
    def search_models(self, query: str = None, category: ModelCategory = None,
                     max_price: float = None) -> List[AIModel]:
        """Search for models"""
        results = list(self.models.values())
        
        if query:
            query_lower = query.lower()
            results = [m for m in results 
                      if query_lower in m.name.lower() or query_lower in m.description.lower()]
                      
        if category:
            results = [m for m in results if m.category == category]
            
        if max_price:
            results = [m for m in results if m.price_qxc <= max_price]
            
        return results
        
    def calculate_earnings(self, creator: str) -> Dict[str, float]:
        """Calculate earnings for a creator"""
        earnings = {
            'sales': 0,
            'royalties': 0,
            'total': 0
        }
        
        for tx in self.transactions:
            if tx['seller'] == creator:
                earnings['sales'] += tx['price']
            # Royalties from resales would go here
            
        earnings['total'] = earnings['sales'] + earnings['royalties']
        return earnings

class ModelIntegration:
    """Integration with popular ML frameworks"""
    
    @staticmethod
    def export_to_huggingface(model: AIModel) -> Dict[str, str]:
        """Export model to Hugging Face format"""
        return {
            'model_card': f"""
# {model.name}

## Model Description
{model.description}

## Performance
- Score: {model.performance_score}
- Downloads: {model.downloads}
- Rating: {model.rating}/5

## Usage
```python
from transformers import AutoModel
model = AutoModel.from_pretrained("qenex/{model.id}")
```

## Price
{model.price_qxc} QXC

## Creator
{model.creator}
            """,
            'config': {
                'model_type': model.category.value,
                'qenex_id': model.id,
                'price_qxc': model.price_qxc
            }
        }
        
    @staticmethod
    def import_from_pytorch(model_path: str, metadata: Dict) -> Dict:
        """Import PyTorch model"""
        model_hash = hashlib.sha256(model_path.encode()).hexdigest()
        
        return {
            'name': metadata.get('name', 'PyTorch Model'),
            'description': metadata.get('description', ''),
            'category': 'CLASSIFICATION',
            'performance_score': metadata.get('accuracy', 0.0),
            'size_mb': metadata.get('size_mb', 0.0),
            'hash': model_hash,
            'framework': 'pytorch'
        }
        
    @staticmethod
    def import_from_tensorflow(model_path: str, metadata: Dict) -> Dict:
        """Import TensorFlow model"""
        model_hash = hashlib.sha256(model_path.encode()).hexdigest()
        
        return {
            'name': metadata.get('name', 'TensorFlow Model'),
            'description': metadata.get('description', ''),
            'category': 'CLASSIFICATION',
            'performance_score': metadata.get('accuracy', 0.0),
            'size_mb': metadata.get('size_mb', 0.0),
            'hash': model_hash,
            'framework': 'tensorflow'
        }

def create_sample_models():
    """Create sample models for the marketplace"""
    marketplace = AIModelMarketplace()
    
    sample_models = [
        {
            'name': 'QXC-GPT-Mini',
            'description': 'Lightweight language model optimized for edge devices',
            'category': 'NLP',
            'creator': 'qxc_unified_user_wallet_main',
            'price': 50.0,
            'performance_score': 92.5,
            'size_mb': 125.0,
            'royalty': 15.0
        },
        {
            'name': 'VisionQXC-2024',
            'description': 'State-of-the-art image classification model',
            'category': 'COMPUTER_VISION',
            'creator': 'qxc_ai_researcher_001',
            'price': 100.0,
            'performance_score': 95.8,
            'size_mb': 450.0,
            'royalty': 20.0
        },
        {
            'name': 'CryptoPredictor-XL',
            'description': 'Advanced cryptocurrency price prediction model',
            'category': 'TIME_SERIES',
            'creator': 'qxc_quant_trader',
            'price': 250.0,
            'performance_score': 88.3,
            'size_mb': 200.0,
            'royalty': 25.0
        },
        {
            'name': 'QXC-StableDiffusion',
            'description': 'Text-to-image generation model trained on QXC data',
            'category': 'GENERATIVE',
            'creator': 'qxc_artist_collective',
            'price': 150.0,
            'performance_score': 94.2,
            'size_mb': 2000.0,
            'royalty': 10.0
        }
    ]
    
    for model_data in sample_models:
        marketplace.list_model(model_data)
        
    return marketplace

def main():
    """CLI interface for marketplace"""
    import sys
    
    marketplace = AIModelMarketplace()
    
    if len(sys.argv) < 2:
        print("\nQENEX AI Model Marketplace")
        print("="*40)
        print("\nCommands:")
        print("  list <name> <price> <category>  - List a model")
        print("  buy <model_id>                  - Purchase a model")
        print("  search [query]                  - Search models")
        print("  trending                        - Show trending models")
        print("  earnings <creator>              - Check earnings")
        print("  sample                          - Create sample models")
        return
        
    command = sys.argv[1].lower()
    
    if command == 'sample':
        marketplace = create_sample_models()
        print("✓ Sample models created")
        
    elif command == 'trending':
        models = marketplace.get_trending_models()
        print("\n🔥 Trending Models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model.name} - {model.price_qxc} QXC - ⭐{model.rating:.1f}")
            
    elif command == 'search' and len(sys.argv) > 2:
        query = sys.argv[2]
        results = marketplace.search_models(query=query)
        print(f"\n🔍 Search results for '{query}':")
        for model in results:
            print(f"- {model.name} ({model.category.value}) - {model.price_qxc} QXC")
            
    elif command == 'earnings' and len(sys.argv) > 2:
        creator = sys.argv[2]
        earnings = marketplace.calculate_earnings(creator)
        print(f"\n💰 Earnings for {creator}:")
        print(f"Sales: {earnings['sales']:.2f} QXC")
        print(f"Royalties: {earnings['royalties']:.2f} QXC")
        print(f"Total: {earnings['total']:.2f} QXC")

if __name__ == '__main__':
    main()