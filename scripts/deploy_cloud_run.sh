#!/bin/bash

# Script to deploy Modern ISONER Chatbot services to GCP Cloud Run

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: $0 <gcp-project-id> <region> <vm-instance-ip>"
    echo "Example: $0 my-project-id us-central1 34.123.45.67"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
VM_IP=$3
echo "Deploying Modern ISONER Chatbot services to Cloud Run in project: $PROJECT_ID in region: $REGION"
echo "Using VM instance at IP: $VM_IP for Redis, API Gateway, and Auth Service"

# Build and push Docker images for Cloud Run services
echo "Building and pushing Docker images..."

# Message Service
echo "Deploying Message Service..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/message-service message_service/
gcloud run deploy message-service \
    --image gcr.io/$PROJECT_ID/message-service \
    --platform managed \
    --region $REGION \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "REDIS_HOST=$VM_IP,REDIS_PORT=6379,API_GATEWAY_URL=http://$VM_IP:8000,GCP_PROJECT_ID=$PROJECT_ID" \
    --project $PROJECT_ID

# NLP Service (higher memory allocation for AI processing)
echo "Deploying NLP Service..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/nlp-service nlp_service/
gcloud run deploy nlp-service \
    --image gcr.io/$PROJECT_ID/nlp-service \
    --platform managed \
    --region $REGION \
    --min-instances 0 \
    --max-instances 2 \
    --memory 1024Mi \
    --cpu 1 \
    --set-env-vars "REDIS_HOST=$VM_IP,REDIS_PORT=6379,GCP_PROJECT_ID=$PROJECT_ID" \
    --project $PROJECT_ID

# External Data Service
echo "Deploying External Data Service..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/external-data-service external_data_service/
gcloud run deploy external-data-service \
    --image gcr.io/$PROJECT_ID/external-data-service \
    --platform managed \
    --region $REGION \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "REDIS_HOST=$VM_IP,REDIS_PORT=6379" \
    --project $PROJECT_ID

# Response Service
echo "Deploying Response Service..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/response-service response_service/
gcloud run deploy response-service \
    --image gcr.io/$PROJECT_ID/response-service \
    --platform managed \
    --region $REGION \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "REDIS_HOST=$VM_IP,REDIS_PORT=6379,GCP_PROJECT_ID=$PROJECT_ID" \
    --project $PROJECT_ID

# Telegram Bot (using webhook mode for better resource usage)
echo "Deploying Telegram Bot..."
# Get the URL of the API Gateway service
API_GATEWAY_URL="http://$VM_IP:8000"

gcloud builds submit --tag gcr.io/$PROJECT_ID/telegram-bot telegram_bot/
gcloud run deploy telegram-bot \
    --image gcr.io/$PROJECT_ID/telegram-bot \
    --platform managed \
    --region $REGION \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "API_GATEWAY_URL=$API_GATEWAY_URL,GCP_PROJECT_ID=$PROJECT_ID,TELEGRAM_WEBHOOK_MODE=true,PORT=8080" \
    --project $PROJECT_ID

# Get service URLs to update API Gateway configuration
MESSAGE_SERVICE_URL=$(gcloud run services describe message-service --platform managed --region $REGION --project $PROJECT_ID --format="value(status.url)")
EXTERNAL_DATA_SERVICE_URL=$(gcloud run services describe external-data-service --platform managed --region $REGION --project $PROJECT_ID --format="value(status.url)")

echo "Updating API Gateway configuration with Cloud Run service URLs..."
gcloud compute ssh isoner-services --zone=us-central1-a --project $PROJECT_ID --command "
    # Update environment variables in docker-compose.yml
    sed -i 's|MESSAGE_SERVICE_URL=.*|MESSAGE_SERVICE_URL=$MESSAGE_SERVICE_URL|g' .env
    sed -i 's|EXTERNAL_DATA_SERVICE_URL=.*|EXTERNAL_DATA_SERVICE_URL=$EXTERNAL_DATA_SERVICE_URL|g' .env
    
    # Restart API Gateway to apply changes
    docker-compose restart api-gateway
"

# Setup Telegram webhook
TELEGRAM_BOT_URL=$(gcloud run services describe telegram-bot --platform managed --region $REGION --project $PROJECT_ID --format="value(status.url)")
TELEGRAM_BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f2)

if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Setting up Telegram webhook..."
    curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$TELEGRAM_BOT_URL/webhook\"}"
else
    echo "TELEGRAM_BOT_TOKEN not found in .env, skipping webhook setup."
    echo "Please manually set up the webhook using: curl -X POST https://api.telegram.org/bot<your-token>/setWebhook -d url=<telegram-bot-service-url>/webhook"
fi

echo "Deployment to Cloud Run complete!"
echo "Services are now running:"
echo "- Redis, API Gateway, Auth Service: http://$VM_IP:8000"
echo "- Message Service: $MESSAGE_SERVICE_URL"
echo "- External Data Service: $EXTERNAL_DATA_SERVICE_URL"
echo "- Telegram Bot (webhook URL): $TELEGRAM_BOT_URL/webhook" 