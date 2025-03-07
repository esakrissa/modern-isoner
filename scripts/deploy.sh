#!/bin/bash

# Check if project ID is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <project-id> <region>"
  exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1}

# Set project
gcloud config set project $PROJECT_ID

# Build and push Docker images
echo "Building and pushing Docker images..."

# API Gateway
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/api-gateway:latest ./api_gateway

# Auth Service
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/auth-service:latest ./auth_service

# Message Service
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/message-service:latest ./message_service

# NLP Service
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/nlp-service:latest ./nlp_service

# External Data Service
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/external-data-service:latest ./external_data_service

# Response Service
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/isoner-chatbot/response-service:latest ./response_service

echo "Docker images built and pushed successfully!"

# Apply Terraform configuration
echo "Applying Terraform configuration..."
cd terraform
terraform init
terraform apply -auto-approve -var="project_id=${PROJECT_ID}" -var="region=${REGION}"

echo "Deployment complete!"