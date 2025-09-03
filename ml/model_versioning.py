"""Machine Learning Model Versioning for QENEX OS"""
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
import mlflow.pytorch
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
import joblib
import numpy as np

class QenexMLVersioning:
    """ML Model versioning and management system"""
    
    def __init__(self, tracking_uri: str = "sqlite:///mlruns.db"):
        """Initialize ML versioning system"""
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        self.experiment_name = "qenex-os-models"
        mlflow.set_experiment(self.experiment_name)
    
    def register_model(self,
                      model: Any,
                      model_name: str,
                      framework: str = "sklearn",
                      metrics: Dict[str, float] = None,
                      params: Dict[str, Any] = None,
                      tags: Dict[str, str] = None) -> str:
        """
        Register a new model version
        
        Args:
            model: The model object to register
            model_name: Name of the model
            framework: ML framework (sklearn, tensorflow, pytorch)
            metrics: Model metrics to log
            params: Model parameters to log
            tags: Additional tags for the model
        
        Returns:
            Model version ID
        """
        with mlflow.start_run() as run:
            # Log parameters
            if params:
                for key, value in params.items():
                    mlflow.log_param(key, value)
            
            # Log metrics
            if metrics:
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
            
            # Log tags
            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)
            
            # Add QENEX-specific tags
            mlflow.set_tag("qenex.version", "5.0.0")
            mlflow.set_tag("qenex.component", "ai-model")
            mlflow.set_tag("qenex.timestamp", datetime.now().isoformat())
            
            # Log model based on framework
            if framework == "sklearn":
                mlflow.sklearn.log_model(model, model_name)
            elif framework == "tensorflow":
                mlflow.tensorflow.log_model(model, model_name)
            elif framework == "pytorch":
                mlflow.pytorch.log_model(model, model_name)
            else:
                # Generic model logging
                mlflow.pyfunc.log_model(
                    artifact_path=model_name,
                    python_model=model
                )
            
            # Register model
            model_uri = f"runs:/{run.info.run_id}/{model_name}"
            mv = mlflow.register_model(model_uri, model_name)
            
            return mv.version
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> Any:
        """
        Load a specific model version
        
        Args:
            model_name: Name of the model
            version: Version to load (latest if None)
        
        Returns:
            Loaded model object
        """
        if version:
            model_uri = f"models:/{model_name}/{version}"
        else:
            model_uri = f"models:/{model_name}/latest"
        
        return mlflow.pyfunc.load_model(model_uri)
    
    def compare_models(self, model_name: str, version1: str, version2: str) -> Dict:
        """
        Compare two model versions
        
        Args:
            model_name: Name of the model
            version1: First version to compare
            version2: Second version to compare
        
        Returns:
            Comparison results
        """
        client = mlflow.tracking.MlflowClient()
        
        # Get model versions
        mv1 = client.get_model_version(model_name, version1)
        mv2 = client.get_model_version(model_name, version2)
        
        # Get run data
        run1 = client.get_run(mv1.run_id)
        run2 = client.get_run(mv2.run_id)
        
        comparison = {
            "model_name": model_name,
            "versions": {
                "v1": version1,
                "v2": version2
            },
            "metrics_comparison": {},
            "params_comparison": {},
            "timestamps": {
                "v1": mv1.creation_timestamp,
                "v2": mv2.creation_timestamp
            }
        }
        
        # Compare metrics
        for metric_key in run1.data.metrics:
            if metric_key in run2.data.metrics:
                comparison["metrics_comparison"][metric_key] = {
                    "v1": run1.data.metrics[metric_key],
                    "v2": run2.data.metrics[metric_key],
                    "improvement": run2.data.metrics[metric_key] - run1.data.metrics[metric_key]
                }
        
        # Compare parameters
        for param_key in run1.data.params:
            if param_key in run2.data.params:
                comparison["params_comparison"][param_key] = {
                    "v1": run1.data.params[param_key],
                    "v2": run2.data.params[param_key],
                    "changed": run1.data.params[param_key] != run2.data.params[param_key]
                }
        
        return comparison
    
    def promote_model(self, model_name: str, version: str, stage: str = "Production"):
        """
        Promote a model version to a specific stage
        
        Args:
            model_name: Name of the model
            version: Version to promote
            stage: Target stage (Staging, Production, Archived)
        """
        client = mlflow.tracking.MlflowClient()
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage
        )
        
        # Log promotion event
        mlflow.set_tag(f"qenex.promoted_to_{stage.lower()}", datetime.now().isoformat())
    
    def rollback_model(self, model_name: str, target_version: str):
        """
        Rollback to a previous model version
        
        Args:
            model_name: Name of the model
            target_version: Version to rollback to
        """
        client = mlflow.tracking.MlflowClient()
        
        # Archive current production version
        current_prod = client.get_latest_versions(model_name, stages=["Production"])
        if current_prod:
            client.transition_model_version_stage(
                name=model_name,
                version=current_prod[0].version,
                stage="Archived"
            )
        
        # Promote target version to production
        client.transition_model_version_stage(
            name=model_name,
            version=target_version,
            stage="Production"
        )
        
        # Log rollback event
        mlflow.set_tag("qenex.rollback", f"Rolled back to v{target_version}")
    
    def get_model_lineage(self, model_name: str) -> list:
        """
        Get complete lineage of a model
        
        Args:
            model_name: Name of the model
        
        Returns:
            List of all model versions with metadata
        """
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        
        lineage = []
        for version in versions:
            run = client.get_run(version.run_id)
            lineage.append({
                "version": version.version,
                "stage": version.current_stage,
                "created": version.creation_timestamp,
                "metrics": run.data.metrics,
                "params": run.data.params,
                "tags": run.data.tags
            })
        
        return sorted(lineage, key=lambda x: x["version"])
    
    def auto_version(self, model: Any, model_name: str, test_data: np.ndarray) -> str:
        """
        Automatically version and evaluate model
        
        Args:
            model: Model to version
            model_name: Name of the model
            test_data: Test data for evaluation
        
        Returns:
            Model version ID
        """
        # Calculate model hash
        model_bytes = joblib.dumps(model)
        model_hash = hashlib.sha256(model_bytes).hexdigest()[:8]
        
        # Evaluate model
        predictions = model.predict(test_data)
        
        # Calculate metrics
        metrics = {
            "predictions_mean": float(np.mean(predictions)),
            "predictions_std": float(np.std(predictions)),
            "model_size_bytes": len(model_bytes)
        }
        
        # Register model with auto-generated tags
        tags = {
            "auto_versioned": "true",
            "model_hash": model_hash,
            "framework": type(model).__module__.split('.')[0]
        }
        
        return self.register_model(
            model=model,
            model_name=model_name,
            metrics=metrics,
            tags=tags
        )

# Example usage
if __name__ == "__main__":
    versioning = QenexMLVersioning()
    
    # Example: Register a sklearn model
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import make_classification
    
    X, y = make_classification(n_samples=100, n_features=20)
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X, y)
    
    version_id = versioning.register_model(
        model=model,
        model_name="qenex-classifier",
        framework="sklearn",
        metrics={"accuracy": 0.95, "f1_score": 0.93},
        params={"n_estimators": 10, "max_depth": 5},
        tags={"purpose": "demo", "environment": "development"}
    )
    
    print(f"Model registered with version: {version_id}")