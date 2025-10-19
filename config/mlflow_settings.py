import mlflow
from config.settings import settings
from config import get_logger
logger = get_logger()
    
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

if settings.mlflow_location == 'LOCAL':
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment("content")
    mlflow.openai.autolog()
    logger.info(f"Logging on mlflow server on {mlflow.get_tracking_uri()}")
elif settings.mlflow_location == 'AZURE':
    ml_client = MLClient(
        DefaultAzureCredential(), settings.azure_subscription_id, settings.azure_resource_group, settings.azure_workspace_name
    )
    mlflow_tracking_uri = ml_client.workspaces.get(settings.azure_workspace_name).mlflow_tracking_uri
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("content")
    mlflow.openai.autolog()
    logger.info(f"Logging on mlflow server on {mlflow.get_tracking_uri()}")
    
