#!/bin/bash
set -e
RESOURCE_GROUP="rg-banking-agent"
LOCATION="uksouth"
APP_NAME="banking-support-agent"
echo "Deploying Banking Support Agent..."
az group create --name $RESOURCE_GROUP --location $LOCATION
az acr create --resource-group $RESOURCE_GROUP --name "${APP_NAME}acr" --sku Basic
az acr build --registry "${APP_NAME}acr" --image banking-agent:latest .
az containerapp env create --name "${APP_NAME}-env" --resource-group $RESOURCE_GROUP --location $LOCATION
az containerapp create --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --environment "${APP_NAME}-env" \
  --image "${APP_NAME}acr.azurecr.io/banking-agent:latest" \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 10
echo "Done!"
