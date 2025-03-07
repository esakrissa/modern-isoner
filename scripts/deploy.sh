#!/bin/bash

# Script to deploy ISONER Modern Chatbot to GCP Cloud Run

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <gcp-project-id> <region>"
    echo "Example: $0 my-project-id us-central1"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
echo "Deploying ISONER Modern Chatbot to project: $PROJECT_ID in region: $REGION"

# Build and push Docker images
echo "Building and pushing Docker images..."

# API Gateway
gcloud builds submit --tag gcr.io/$PROJECT_ID/api-gateway api_gateway/
gcloud run deploy api-gateway \
    --image gcr.io/$PROJECT_ID/api-gateway \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --project $PROJECT_ID

# Auth Service
gcloud builds submit --tag gcr.io/$PROJECT_ID/auth-service auth_service/
gcloud run deploy auth-service \
    --image gcr.io/$PROJECT_ID/auth-service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID

# Message Service
gcloud builds submit --tag gcr.io/$PROJECT_ID/message-service message_service/
gcloud run deploy message-service \
    --image gcr.io/$PROJECT_ID/message-service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID

# NLP Service
gcloud builds submit --tag gcr.io/$PROJECT_ID/nlp-service nlp_service/
gcloud run deploy nlp-service \
    --image gcr.io/$PROJECT_ID/nlp-service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID

# External Data Service
gcloud builds submit --tag gcr.io/$PROJECT_ID/external-data-service external_data_service/
gcloud run deploy external-data-service \
    --image gcr.io/$PROJECT_ID/external-data-service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID

# Response Service
gcloud builds submit --tag gcr.io/$PROJECT_ID/response-service response_service/
gcloud run deploy response-service \
    --image gcr.io/$PROJECT_ID/response-service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID

echo "Deployment complete!"