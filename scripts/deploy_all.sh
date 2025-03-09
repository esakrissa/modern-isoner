#!/bin/bash

# Main deployment script for Modern ISONER Chatbot
# Optimized for free tier deployment with VM instance and Cloud Run

# Check for required parameters
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <gcp-project-id> <region>"
    echo "Example: $0 my-project-id us-central1"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting deployment of Modern ISONER Chatbot to project: $PROJECT_ID in region: $REGION"
echo "This script will:"
echo "1. Setup Pub/Sub topics and subscriptions"
echo "2. Deploy Redis, API Gateway, and Auth Service to a VM instance (Ubuntu 24.04 LTS)"
echo "3. Deploy remaining services to Cloud Run"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Create Pub/Sub topics
echo "Step 1: Creating Pub/Sub topics and subscriptions..."
bash "$SCRIPT_DIR/create_topics.sh" $PROJECT_ID
if [ $? -ne 0 ]; then
    echo "Failed to create Pub/Sub topics. Please check the error and try again."
    exit 1
fi

# Step 2: Set up VM instance
echo "Step 2: Setting up VM instance with Ubuntu 24.04 LTS, Redis, API Gateway, and Auth Service..."
bash "$SCRIPT_DIR/setup_vm.sh" $PROJECT_ID
if [ $? -ne 0 ]; then
    echo "Failed to set up VM instance. Please check the error and try again."
    exit 1
fi

# Get the VM instance IP
INSTANCE_NAME="modern-isoner-services"
ZONE="us-central1-a"
INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

if [ -z "$INSTANCE_IP" ]; then
    echo "Failed to get VM instance IP. Please check if the instance was created correctly."
    exit 1
fi

echo "VM instance is running at IP: $INSTANCE_IP"

# Step 3: Deploy services to Cloud Run
echo "Step 3: Deploying remaining services to Cloud Run..."
bash "$SCRIPT_DIR/deploy_cloud_run.sh" $PROJECT_ID $REGION $INSTANCE_IP
if [ $? -ne 0 ]; then
    echo "Failed to deploy to Cloud Run. Please check the error and try again."
    exit 1
fi

# Step 4: Verify deployment
echo "Step 4: Verifying deployment..."

# Check if services are running in Cloud Run
echo "Checking Cloud Run services..."
SERVICES=("message-service" "nlp-service" "external-data-service" "response-service" "telegram-bot")
for SERVICE in "${SERVICES[@]}"; do
    SERVICE_URL=$(gcloud run services describe $SERVICE --platform managed --region $REGION --project $PROJECT_ID --format="value(status.url)" 2>/dev/null)
    if [ -z "$SERVICE_URL" ]; then
        echo "⚠️  Warning: $SERVICE is not running in Cloud Run."
    else
        echo "✅ $SERVICE is running at: $SERVICE_URL"
    fi
done

# Check if VM services are running
echo "Checking VM services..."
VM_SERVICES=("redis" "api-gateway" "auth-service")
for SERVICE in "${VM_SERVICES[@]}"; do
    # Try to check the service status remotely
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command "docker ps | grep $SERVICE" &>/dev/null
    if [ $? -ne 0 ]; then
        echo "⚠️  Warning: $SERVICE might not be running on the VM instance."
    else
        echo "✅ $SERVICE is running on the VM instance."
    fi
done

echo ""
echo "======================================================"
echo "Modern ISONER Chatbot Deployment Complete!"
echo "======================================================"
echo ""
echo "Services deployed:"
echo "- VM instance (Ubuntu 24.04 LTS) running Redis, API Gateway, Auth Service: http://$INSTANCE_IP:8000"
echo "- Cloud Run services:"
for SERVICE in "${SERVICES[@]}"; do
    SERVICE_URL=$(gcloud run services describe $SERVICE --platform managed --region $REGION --project $PROJECT_ID --format="value(status.url)" 2>/dev/null)
    if [ ! -z "$SERVICE_URL" ]; then
        echo "  - $SERVICE: $SERVICE_URL"
    fi
done
echo ""
echo "Important Notes:"
echo "1. The setup is optimized for free tier usage."
echo "2. You can monitor usage in the GCP Console to ensure you stay within free tier limits."
echo "3. For troubleshooting, check the Cloud Run logs and SSH into the VM instance."
echo ""
echo "To SSH into the VM instance, run:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID" 