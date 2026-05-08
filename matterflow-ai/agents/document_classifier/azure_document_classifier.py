import os
import asyncio
import time
import concurrent.futures
from typing import List, Dict
from utils.azure_openai_client import AzureOpenAIClientSingleton
from utils.prompt_manager import prompt_manager

class AzureOpenAIDocumentClassifier:
    def __init__(self, templates: List[str]):
        self.templates = templates
        self.azure_client_singleton = AzureOpenAIClientSingleton()
        self.deployment_name = os.getenv("DEPLOYMENT_NAME")
        
        if not self.deployment_name:
            raise ValueError("DEPLOYMENT_NAME environment variable is required")
        

    async def classify(self, text: str) -> Dict:
        start_time = time.time()
        
        try:
            # Validate input
            if not text or len(text.strip()) < 10:
                return {
                    'classification': 'ERROR',
                    'confidence': 0.0,
                    'error': 'Text too short for classification',
                    'status': 'failed'
                }
            
            prompt = prompt_manager.get_classification_prompt(self.templates, text)
            print(f"Created prompt for {prompt} character text")
            
            try:
                print("Making Azure OpenAI request...")
                response = await self._make_safe_openai_request(prompt)
                print("Azure OpenAI request completed")
                
            except asyncio.TimeoutError:
                print("Azure OpenAI request timed out")
                return {
                    'classification': 'ERROR',
                    'confidence': 0.0,
                    'error': 'Azure OpenAI request timed out after 120 seconds',
                    'processing_time_ms': round((time.time() - start_time) * 1000),
                    'status': 'failed'
                }

            selected_template = response.choices[0].message.content.strip()
            print(f"Azure OpenAI returned: '{selected_template}'")
            
            if selected_template not in self.templates:
                closest_template = self._find_closest_template(selected_template)
                confidence = 0.7
                classification = closest_template
                reasoning = f"Adjusted from '{selected_template}' to closest valid template"
                print(f"Adjusted to closest template: {closest_template}")
            else:
                confidence = 0.95
                classification = selected_template
                reasoning = "Exact template match found"
            
            processing_time = round((time.time() - start_time) * 1000)
            
            return {
                'classification': classification,
                'confidence': confidence,
                'reasoning': reasoning,
                'processing_time_ms': processing_time,
                'method': 'azure_openai',
                'model': self.deployment_name,
                'status': 'success'
            }
            
        except Exception as e:
            print(f"Azure OpenAI classification error: {str(e)}")
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': f"Azure OpenAI classification failed: {str(e)}",
                'processing_time_ms': round((time.time() - start_time) * 1000),
                'status': 'failed'
            }

    async def _make_safe_openai_request(self, prompt: str):
        
        def _sync_openai_call():
            try:
                client = self.azure_client_singleton.get_client()
                return client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=50,
                    timeout=20.0
                )
            except Exception as e:
                print(f"Sync OpenAI call failed: {str(e)}")
                raise
        
        # Run in thread pool with asyncio timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(_sync_openai_call)
                response = await asyncio.wait_for(
                    asyncio.wrap_future(future),
                    timeout=25.0
                )
                return response
                
            except concurrent.futures.TimeoutError:
                print("Thread pool execution timed out")
                raise asyncio.TimeoutError("OpenAI request timed out in thread pool")
            except Exception as e:
                print(f"Thread pool execution failed: {str(e)}")
                raise

    def _find_closest_template(self, classification: str) -> str:
        """Find closest matching template"""
        classification_lower = classification.lower().strip()
        
        # Direct substring match
        for template in self.templates:
            if classification_lower in template.lower() or template.lower() in classification_lower:
                return template
        
        # Keyword matching
        classification_words = set(classification_lower.split())
        best_match = self.templates[0]
        max_score = 0
        
        for template in self.templates:
            template_words = set(template.lower().split())
            common_words = classification_words.intersection(template_words)
            score = len(common_words)
            
            if score > max_score:
                max_score = score
                best_match = template
        
        return best_match

    def classify_sync(self, text: str) -> Dict:
        """Synchronous wrapper that handles event loop issues"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_in_new_loop, text)
                    return future.result(timeout=60)
            else:
                return asyncio.run(self.classify(text))
                
        except Exception as e:
            print(f"Sync classification failed: {str(e)}")
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': f"Sync classification failed: {str(e)}",
                'status': 'failed'
            }

    def _run_in_new_loop(self, text: str) -> Dict:
        """Run classification in a new event loop"""
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(self.classify(text))
            finally:
                new_loop.close()
        except Exception as e:
            return {
                'classification': 'ERROR',
                'confidence': 0.0,
                'error': f"New loop execution failed: {str(e)}",
                'status': 'failed'
            }
