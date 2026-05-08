import os
from typing import Optional
import openai

class AzureOpenAIClientSingleton:
    _instance: Optional['AzureOpenAIClientSingleton'] = None
    _client: Optional[openai.AzureOpenAI] = None
    _deployment_name: Optional[str] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AzureOpenAIClientSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._init_client()
            self._initialized = True

    def _init_client(self):
        try:
            api_key = os.getenv("API_KEY")
            api_version = os.getenv("API_VERSION")
            azure_endpoint = os.getenv("AZURE_ENDPOINT")
            deployment_name = os.getenv("DEPLOYMENT_NAME")
            
            if not all([api_key, api_version, azure_endpoint, deployment_name]):
                raise ValueError("Missing Azure OpenAI environment variables")
            
            self._client = openai.AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                timeout=30.0,  # Add explicit timeout
                max_retries=2   # Limit retries
            )
            
            # Store deployment name
            self._deployment_name = deployment_name
            
            print("Azure OpenAI client initialized with timeouts")
            
        except Exception as e:
            print(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

    @property
    def client(self) -> openai.AzureOpenAI:
        if self._client is None:
            raise RuntimeError("Azure OpenAI client not initialized")
        return self._client

    def get_client(self) -> openai.AzureOpenAI:
        """Get the Azure OpenAI client instance."""
        if self._client is None:
            raise RuntimeError("Azure OpenAI client not initialized")
        return self._client

    def get_deployment_name(self) -> str:
        """Get the deployment name."""
        if self._deployment_name is None:
            raise RuntimeError("Deployment name not initialized")
        return self._deployment_name

    @classmethod
    def get_instance(cls) -> 'AzureOpenAIClientSingleton':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
