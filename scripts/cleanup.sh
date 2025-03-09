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
echo "- Container images in Artifact Registry/GCR"
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
# First, list all firewall rules that might be related to our project
echo "Looking for firewall rules with 'isoner' or 'allow' in the name..."
FIREWALL_RULES=$(gcloud compute firewall-rules list --filter="name~'isoner' OR name~'allow'" --format="value(name)" --project=$PROJECT_ID)

if [ -n "$FIREWALL_RULES" ]; then
    echo "Found the following firewall rules to delete:"
    echo "$FIREWALL_RULES"
    for RULE in $FIREWALL_RULES; do
        echo "Deleting firewall rule: $RULE"
        gcloud compute firewall-rules delete $RULE --project=$PROJECT_ID --quiet || echo "Firewall rule $RULE not found or already deleted"
    done
else
    echo "No matching firewall rules found."
fi

# Delete Pub/Sub subscriptions and topics
echo "Deleting all Pub/Sub subscriptions..."
# List all subscriptions in the project
SUBSCRIPTIONS=$(gcloud pubsub subscriptions list --project=$PROJECT_ID --format="value(name)")
if [ -n "$SUBSCRIPTIONS" ]; then
    for SUB in $SUBSCRIPTIONS; do
        # Extract just the subscription name from the full path
        SUB_NAME=$(echo $SUB | sed 's|.*/||')
        echo "Deleting subscription: $SUB_NAME"
        gcloud pubsub subscriptions delete $SUB_NAME --project=$PROJECT_ID --quiet || echo "Subscription $SUB_NAME not found or already deleted"
    done
else
    echo "No Pub/Sub subscriptions found."
fi

echo "Deleting all Pub/Sub topics..."
# List all topics in the project
TOPICS=$(gcloud pubsub topics list --project=$PROJECT_ID --format="value(name)")
if [ -n "$TOPICS" ]; then
    for TOPIC in $TOPICS; do
        # Extract just the topic name from the full path
        TOPIC_NAME=$(echo $TOPIC | sed 's|.*/||')
        echo "Deleting topic: $TOPIC_NAME"
        gcloud pubsub topics delete $TOPIC_NAME --project=$PROJECT_ID --quiet || echo "Topic $TOPIC_NAME not found or already deleted"
    done
else
    echo "No Pub/Sub topics found."
fi

# Delete container images - more comprehensive approach
echo "Deleting all container images in gcr.io/$PROJECT_ID..."

# List all repositories in the project
REPOS=$(gcloud container images list --repository=gcr.io/$PROJECT_ID --format="value(name)" 2>/dev/null || echo "")
if [ -n "$REPOS" ]; then
    for REPO in $REPOS; do
        echo "Processing repository: $REPO"
        
        # List all image digests in the repository
        DIGESTS=$(gcloud container images list-tags $REPO --format="value(digest)" --limit=999999)
        if [ -n "$DIGESTS" ]; then
            for DIGEST in $DIGESTS; do
                echo "Deleting image: $REPO@$DIGEST"
                gcloud container images delete "$REPO@$DIGEST" --force-delete-tags --quiet || echo "Failed to delete $REPO@$DIGEST"
            done
        else
            echo "No images found in $REPO"
            
            # Try to delete the repository itself
            gcloud container images delete $REPO --force-delete-tags --quiet || echo "Failed to delete repository $REPO"
        fi
    done
else
    echo "No container repositories found in gcr.io/$PROJECT_ID"
fi

# Verify cleanup
echo "Verifying cleanup..."

# Check Cloud Run services
REMAINING_SERVICES=$(gcloud run services list --platform managed --region=$REGION --project=$PROJECT_ID --format="value(name)" 2>/dev/null || echo "")
if [ -n "$REMAINING_SERVICES" ]; then
    echo "⚠️ Warning: Some Cloud Run services still exist:"
    echo "$REMAINING_SERVICES"
    echo "You may need to delete these manually."
else
    echo "✅ All Cloud Run services have been deleted."
fi

# Check VM instance
REMAINING_VM=$(gcloud compute instances list --filter="name=$INSTANCE_NAME" --project=$PROJECT_ID --format="value(name)" 2>/dev/null || echo "")
if [ -n "$REMAINING_VM" ]; then
    echo "⚠️ Warning: VM instance $INSTANCE_NAME still exists."
    echo "You may need to delete it manually."
else
    echo "✅ VM instance has been deleted."
fi

# Check Pub/Sub topics
REMAINING_TOPICS=$(gcloud pubsub topics list --project=$PROJECT_ID --format="value(name)" 2>/dev/null || echo "")
if [ -n "$REMAINING_TOPICS" ]; then
    echo "⚠️ Warning: Some Pub/Sub topics still exist:"
    echo "$REMAINING_TOPICS"
    echo "You may need to delete these manually."
else
    echo "✅ All Pub/Sub topics have been deleted."
fi

# Check container images
REMAINING_REPOS=$(gcloud container images list --repository=gcr.io/$PROJECT_ID --format="value(name)" 2>/dev/null || echo "")
if [ -n "$REMAINING_REPOS" ]; then
    echo "⚠️ Warning: Some container repositories still exist:"
    echo "$REMAINING_REPOS"
    echo "You may need to delete these manually using:"
    echo "gcloud container images delete [IMAGE] --force-delete-tags --quiet"
else
    echo "✅ All container images have been deleted."
fi

echo "✅ Cleanup completed! All Modern ISONER resources have been removed from project $PROJECT_ID."
echo "You can now start a fresh deployment." 