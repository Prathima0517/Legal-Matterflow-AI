import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# Azure OpenAI settings
API_KEY = os.getenv("API_KEY")
API_VERSION = os.getenv("API_VERSION")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

if not all([API_KEY, API_VERSION, AZURE_ENDPOINT, DEPLOYMENT_NAME]):
    raise RuntimeError("Missing one or more Azure OpenAI environment variables")

# AWS settings
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

if not S3_BUCKET_NAME:
    raise RuntimeError("S3_BUCKET_NAME environment variable not set")

if not AWS_REGION:
    raise RuntimeError("AWS_REGION environment variable not set")
