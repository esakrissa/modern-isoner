#!/bin/bash

# Cleanup script for Modern ISONER deployment
# This script removes all GCP resources created during deployment

if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id> [region]"
    echo "Example: $0 my-project-id us-central1"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-"us-central1"}
ZONE="${REGION}-a"
INSTANCE_NAME="isoner-services"

echo "🧹 Cleaning up Modern ISONER resources in project: $PROJECT_ID"
echo "This will remove ALL resources created during deployment!"
echo "Region: $REGION, Zone: $ZONE"
echo ""
echo "Resources that will be deleted:"
echo "- VM instance: $INSTANCE_NAME"
echo "- Cloud Run services: message-service, nlp-service, external-data-service, response-service, telegram-bot"
echo "- Pub/Sub topics and subscriptions"
echo ""
read -p "Are you sure you want to proceed? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo "Starting cleanup process..."

# Delete Cloud Run services
echo "Deleting Cloud Run services..."
SERVICES=("message-service" "nlp-service" "external-data-service" "response-service" "telegram-bot")
for SERVICE in "${SERVICES[@]}"; do
    echo "Deleting $SERVICE..."
    gcloud run services delete $SERVICE --region=$REGION --project=$PROJECT_ID --quiet || echo "Service $SERVICE not found or already deleted"
done

# Delete VM instance
echo "Deleting VM instance: $INSTANCE_NAME..."
gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --quiet || echo "VM instance not found or already deleted"

# Delete firewall rules
echo "Deleting firewall rules..."
gcloud compute firewall-rules delete isoner-allow-http --project=$PROJECT_ID --quiet || echo "Firewall rule not found or already deleted"
gcloud compute firewall-rules delete isoner-allow-https --project=$PROJECT_ID --quiet || echo "Firewall rule not found or already deleted"
gcloud compute firewall-rules delete isoner-allow-redis --project=$PROJECT_ID --quiet || echo "Firewall rule not found or already deleted"

# Delete Pub/Sub topics and subscriptions
echo "Deleting Pub/Sub subscriptions..."
SUBSCRIPTIONS=("incoming-messages-nlp-sub" "processed-messages-response-sub" "external-data-request-sub" "external-data-response-sub")
for SUB in "${SUBSCRIPTIONS[@]}"; do
    gcloud pubsub subscriptions delete $SUB --project=$PROJECT_ID --quiet || echo "Subscription $SUB not found or already deleted"
done

echo "Deleting Pub/Sub topics..."
TOPICS=("incoming-messages" "processed-messages" "external-data-request" "external-data-response")
for TOPIC in "${TOPICS[@]}"; do
    gcloud pubsub topics delete $TOPIC --project=$PROJECT_ID --quiet || echo "Topic $TOPIC not found or already deleted"
done

# Delete container images
echo "Deleting container images..."
IMAGES=("message-service" "nlp-service" "external-data-service" "response-service" "telegram-bot")
for IMAGE in "${IMAGES[@]}"; do
    gcloud container images delete gcr.io/$PROJECT_ID/$IMAGE --force-delete-tags --quiet || echo "Image $IMAGE not found or already deleted"
done

echo "✅ Cleanup completed! All Modern ISONER resources have been removed from project $PROJECT_ID."
echo "You can now start a fresh deployment." 