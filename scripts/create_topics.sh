#!/bin/bash

# Script to create Pub/Sub topics and subscriptions for ISONER Modern Chatbot

if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id>"
    exit 1
fi

PROJECT_ID=$1
echo "Creating Pub/Sub topics and subscriptions for project: $PROJECT_ID"

# Create topics
echo "Creating topics..."
gcloud pubsub topics create incoming-messages --project=$PROJECT_ID
gcloud pubsub topics create processed-messages --project=$PROJECT_ID
gcloud pubsub topics create external-data-requests --project=$PROJECT_ID
gcloud pubsub topics create external-data-responses --project=$PROJECT_ID
gcloud pubsub topics create outgoing-messages --project=$PROJECT_ID

# Create subscriptions
echo "Creating subscriptions..."
gcloud pubsub subscriptions create incoming-messages-nlp-sub \
    --topic=incoming-messages \
    --ack-deadline=30 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create processed-messages-response-sub \
    --topic=processed-messages \
    --ack-deadline=30 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create external-data-requests-sub \
    --topic=external-data-requests \
    --ack-deadline=30 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create external-data-responses-sub \
    --topic=external-data-responses \
    --ack-deadline=30 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create outgoing-messages-telegram-sub \
    --topic=outgoing-messages \
    --ack-deadline=30 \
    --project=$PROJECT_ID

echo "Pub/Sub setup complete!"