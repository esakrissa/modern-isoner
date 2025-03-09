#!/bin/bash

# Script to create Pub/Sub topics and subscriptions for Modern ISONER Chatbot
# Optimized for free tier usage

if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id>"
    exit 1
fi

PROJECT_ID=$1
echo "Creating Pub/Sub topics and subscriptions for Modern ISONER project: $PROJECT_ID"

# Create topics with message retention settings
echo "Creating topics with optimized retention settings..."

# Incoming messages topic - short retention as they are processed quickly
gcloud pubsub topics create incoming-messages \
    --message-retention-duration=10m \
    --project=$PROJECT_ID

# Processed messages topic - moderate retention
gcloud pubsub topics create processed-messages \
    --message-retention-duration=30m \
    --project=$PROJECT_ID

# External data requests topic - short retention
gcloud pubsub topics create external-data-requests \
    --message-retention-duration=10m \
    --project=$PROJECT_ID

# External data responses topic - short retention
gcloud pubsub topics create external-data-responses \
    --message-retention-duration=10m \
    --project=$PROJECT_ID

# Outgoing messages topic - moderate retention for reliability
gcloud pubsub topics create outgoing-messages \
    --message-retention-duration=30m \
    --project=$PROJECT_ID

# Create subscriptions with optimized ack deadlines and expiration policy
echo "Creating subscriptions with optimized settings..."

# NLP Service subscription - longer ack deadline due to AI processing
gcloud pubsub subscriptions create incoming-messages-nlp-sub \
    --topic=incoming-messages \
    --ack-deadline=60 \
    --message-retention-duration=10m \
    --expiration-period=2d \
    --project=$PROJECT_ID

# Response service subscription
gcloud pubsub subscriptions create processed-messages-response-sub \
    --topic=processed-messages \
    --ack-deadline=30 \
    --message-retention-duration=30m \
    --expiration-period=2d \
    --project=$PROJECT_ID

# External data service subscription
gcloud pubsub subscriptions create external-data-requests-sub \
    --topic=external-data-requests \
    --ack-deadline=30 \
    --message-retention-duration=10m \
    --expiration-period=2d \
    --project=$PROJECT_ID

# Response to external data subscription
gcloud pubsub subscriptions create external-data-responses-sub \
    --topic=external-data-responses \
    --ack-deadline=30 \
    --message-retention-duration=10m \
    --expiration-period=2d \
    --project=$PROJECT_ID

# Telegram bot subscription
gcloud pubsub subscriptions create outgoing-messages-telegram-sub \
    --topic=outgoing-messages \
    --ack-deadline=30 \
    --message-retention-duration=30m \
    --expiration-period=2d \
    --project=$PROJECT_ID

echo "Pub/Sub setup complete with optimized settings for Modern ISONER free tier usage!"