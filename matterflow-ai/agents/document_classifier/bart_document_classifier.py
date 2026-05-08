import asyncio
import time
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from utils.model_manager import model_manager

class BartDocumentClassifier:
    def __init__(self):
        print("Initializing Bart DocumentClassifier...")
        self.bart_classifier = model_manager.get_distilbart_classifier()
        self.templates = model_manager.get_templates()
        self.high_confidence_threshold = 0.9
        self.executor = None
        self._shutdown = False
        self._init_executor()
        print(f"SimpleDocumentClassifier initialized with {len(self.templates)} templates")

    def _init_executor(self):
        """Initialize executor safely"""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bart_")

    async def classify(self, text: str) -> Dict:
        if self._shutdown:
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': 'Classifier shutting down',
                'status': 'failed'
            }
            
        try:
            print(f"Starting classification for text of length: {len(text)}")
            start_time = time.time()
            clean_text = re.sub(r'\s+', ' ', text.strip())
            
            if len(clean_text) <= 1500:
                print("Using direct classification for short text")
                result = await self._classify_single_text(clean_text)
                
                if result is None or result.get('classification') == 'ERROR':
                    return {
                        'classification': 'ERROR',
                        'confidence': 0.0,
                        'error': 'Direct classification failed',
                        'status': 'failed'
                    }
                    
                processing_time = round((time.time() - start_time) * 1000)
                print(f"Direct classification completed in {processing_time}ms: {result['classification']} ({result['confidence']:.3f})")
                
                return {
                    'classification': result['classification'],
                    'confidence': result['confidence'],
                    'method': 'direct',
                    'processing_time_ms': processing_time,
                    'status': 'success'
                }
            else:
                print(f"Using chunked classification for long text ({len(clean_text)} chars)")
                result = await self._classify_with_chunks(clean_text, start_time)
                return result
                
        except Exception as e:
            print(f"Classification error: {str(e)}")
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': str(e),
                'status': 'failed'
            }

    async def _classify_single_text(self, text: str) -> Optional[Dict]:
        """Classify single text with longer timeout for CPU"""
        if self._shutdown or not self.executor:
            print("Classifier not available")
            return None
            
        try:
            print("Starting BART classification...")
            classification_start = time.time()
            
            loop = asyncio.get_running_loop()
            
            # Increased timeout for CPU processing
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    lambda: self._run_bart_classification(text)
                ),
                timeout=60.0  # 60 seconds timeout for CPU
            )
            
            classification_time = round((time.time() - classification_start) * 1000)
            print(f"BART classification took {classification_time}ms")
            
            if result is None:
                return None
                
            return {
                'classification': result['labels'][0],
                'confidence': result['scores'][0]
            }
            
        except asyncio.TimeoutError:
            print("BART classification timed out after 60 seconds")
            return None
        except Exception as e:
            print(f"BART classification error: {str(e)}")
            return None

    def _run_bart_classification(self, text: str):
        """Run BART classification with error handling"""
        try:
            print(f"Running BART on text of length {len(text)}")
            result = self.bart_classifier(text, candidate_labels=self.templates)
            print(f"BART returned {len(result['labels'])} predictions")
            return result
        except Exception as e:
            print(f"BART model error: {str(e)}")
            return None

    async def _classify_with_chunks(self, text: str, start_time: float) -> Dict:
        try:
            chunks = self._create_chunks(text, chunk_size=800, overlap=150) 
            print(f"Created {len(chunks)} chunks")
            
            all_results = []
            
            for i, chunk in enumerate(chunks):
                if self._shutdown:
                    break
                    
                print(f"Processing chunk {i+1}/{len(chunks)}")
                
                try:
                    result = await asyncio.wait_for(
                        self._classify_single_text(chunk['text']), 
                        timeout=60.0  # 60 seconds per chunk
                    )
                    
                    if result and result.get('classification') != 'ERROR':
                        result['chunk_id'] = i
                        all_results.append(result)
                        
                        # Early stopping on high confidence
                        if result.get('confidence', 0) >= self.high_confidence_threshold:
                            print(f"Early stop with high confidence: {result['classification']} ({result['confidence']:.3f})")
                            return {
                                'classification': result['classification'],
                                'confidence': result['confidence'],
                                'method': 'chunks_early_stop',
                                'chunks_processed': i + 1,
                                'total_chunks': len(chunks),
                                'early_stop': True,
                                'processing_time_ms': round((time.time() - start_time) * 1000),
                                'status': 'success'
                            }
                    else:
                        print(f"Chunk {i+1} failed or timed out")
                        
                except asyncio.TimeoutError:
                    print(f"Chunk {i+1} timed out")
                    continue
            
            if not all_results:
                return {
                    'classification': 'ERROR',
                    'confidence': 0.0,
                    'error': 'All chunks failed to process',
                    'status': 'failed'
                }
            
            final_result = self._aggregate_results(all_results)
            print(f"Final result from {len(all_results)} chunks: {final_result['classification']} ({final_result['confidence']:.3f})")
            
            return {
                'classification': final_result['classification'],
                'confidence': final_result['confidence'],
                'method': 'chunks_aggregated',
                'chunks_processed': len(all_results),
                'total_chunks': len(chunks),
                'early_stop': False,
                'processing_time_ms': round((time.time() - start_time) * 1000),
                'status': 'success'
            }
            
        except Exception as e:
            print(f"Chunk processing error: {str(e)}")
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': str(e),
                'status': 'failed'
            }

    def _create_chunks(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[Dict]:
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + chunk_size
            if end > len(text):
                end = len(text)
            
            # Try to break at sentence boundary
            if end < len(text):
                sentence_break = text.rfind('.', end - 50, end)
                if sentence_break != -1:
                    end = sentence_break + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text and len(chunk_text) > 20:  # Only add meaningful chunks
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text
                })
                chunk_id += 1

            start = end - overlap
            if start >= len(text):
                break
        
        return chunks

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        if not results:
            return {'classification': 'UNKNOWN', 'confidence': 0.0}

        label_votes = {}
        total_confidence = 0
        
        for result in results:
            label = result['classification']
            confidence = result['confidence']
            
            if label not in label_votes:
                label_votes[label] = {'total_confidence': 0, 'count': 0}
            
            label_votes[label]['total_confidence'] += confidence
            label_votes[label]['count'] += 1
            total_confidence += confidence
        
        best_label = None
        best_score = 0
        
        for label, data in label_votes.items():
            avg_confidence = data['total_confidence'] / data['count']
            weighted_score = avg_confidence * (data['count'] / len(results))
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_label = label
        
        return {
            'classification': best_label or 'UNKNOWN',
            'confidence': round(best_score, 3)
        }

    def cleanup(self):
        print("Cleaning up classifier...")
        self._shutdown = True
        if self.executor:
            try:
                self.executor.shutdown(wait=False)
                self.executor = None
                print("Executor shutdown completed")
            except Exception as e:
                print(f"Cleanup error: {str(e)}")

    def __del__(self):
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False)
