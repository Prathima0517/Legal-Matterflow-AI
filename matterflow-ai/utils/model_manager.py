from transformers import pipeline
from utils.json_loader import load_legal_templates
import time
import threading


class ModelManager:
    _instance = None
    _initialized = False
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # Initialize all model containers
                    self.distilbart_classifier = None
                    self.legal_bert_ner = None
                    self.templates = None
                    
                    # Load all models
                    self._load_models()
                    ModelManager._initialized = True
    
    def _load_models(self):
        start_time = time.time()
        
        # 1. Load DistilBART for zero-shot classification
        if self.distilbart_classifier is None:
            try:
                self.distilbart_classifier = pipeline(
                    "zero-shot-classification",
                    model="valhalla/distilbart-mnli-12-6"
                )
            except Exception as e:
                raise e
        
        # 2. Load Legal BERT for Named Entity Recognition
        if self.legal_bert_ner is None:
            try:
                self.legal_bert_ner = pipeline(
                    "ner",
                    model="nlpaueb/legal-bert-base-uncased",
                    aggregation_strategy="simple"
                )
            except Exception as e:
                raise
        
        # 3. Load legal templates
        if self.templates is None:
            try:
                self.templates = load_legal_templates()
            except Exception as e:
                raise e

        loading_time = time.time() - start_time
        print(f"Models loaded in {loading_time:.2f} seconds")
    
    # Public getter methods
    def get_distilbart_classifier(self):
        if self.distilbart_classifier is None:
            raise RuntimeError("DistilBART classifier not loaded")
        return self.distilbart_classifier
    
    def get_legal_bert_ner(self):
        if self.legal_bert_ner is None:
            raise RuntimeError("Legal BERT NER not loaded")
        return self.legal_bert_ner
    
    def get_templates(self):
        if self.templates is None:
            raise RuntimeError("Legal templates not loaded")
        return self.templates
    
    # Backward compatibility
    def get_model(self):
        return self.get_distilbart_classifier()
    
    # Utility methods
    def is_ready(self) -> bool:
        return (self.distilbart_classifier is not None and
                self.legal_bert_ner is not None and
                self.templates is not None)
    
    def get_model_info(self) -> dict:
        return {
            'initialized': ModelManager._initialized,
            'models_loaded': {
                'distilbart_classifier': self.distilbart_classifier is not None,
                'legal_bert_ner': self.legal_bert_ner is not None,
                'templates': self.templates is not None
            },
            'template_count': len(self.templates) if self.templates else 0,
            'ready': self.is_ready(),
            'instance_id': id(self)
        }
    
    def warm_up(self) -> dict:
        if not self.is_ready():
            raise RuntimeError("Models not ready for warm-up")
        
        try:
            start_time = time.time()
            
            test_text = "This is a test legal document for model warm-up."
            
            # Warm up DistilBART
            bart_result = self.distilbart_classifier(
                test_text, 
                candidate_labels=self.templates[:3]
            )
            
            # Warm up Legal BERT NER
            ner_result = self.legal_bert_ner(test_text)
            
            warm_up_time = time.time() - start_time
            
            result = {
                'status': 'success',
                'warm_up_time': f"{warm_up_time:.2f}s",
                'test_results': {
                    'bart_classification': bart_result['labels'][0],
                    'bart_confidence': round(bart_result['scores'][0], 3),
                    'entities_found': len(ner_result)
                },
                'message': 'All models warmed up successfully'
            }
            
            return result
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}


# Create global singleton instance
model_manager = ModelManager()
