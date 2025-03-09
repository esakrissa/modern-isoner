#!/bin/bash

# Script to create Pub/Sub topics and subscriptions for Modern ISONER Chatbot
# Optimized for free tier usage

if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id>"
    exit 1
fi

PROJECT_ID=$1
echo "Creating Pub/Sub topics and subscriptions for Modern ISONER project: $PROJECT_ID"

# Function to check if a topic exists
topic_exists() {
    local topic_name=$1
    if gcloud pubsub topics describe $topic_name --project=$PROJECT_ID &>/dev/null; then
        return 0  # Topic exists
    else
        return 1  # Topic doesn't exist
    fi
}

# Function to check if a subscription exists
subscription_exists() {
    local sub_name=$1
    if gcloud pubsub subscriptions describe $sub_name --project=$PROJECT_ID &>/dev/null; then
        return 0  # Subscription exists
    else
        return 1  # Subscription doesn't exist
    fi
}

# Create topics with message retention settings
echo "Creating topics with optimized retention settings..."

# Incoming messages topic - short retention as they are processed quickly
if topic_exists "incoming-messages"; then
    echo "✅ Topic 'incoming-messages' already exists."
else
    echo "Creating topic 'incoming-messages'..."
    gcloud pubsub topics create incoming-messages \
        --message-retention-duration=10m \
        --project=$PROJECT_ID
fi

# Processed messages topic - moderate retention
if topic_exists "processed-messages"; then
    echo "✅ Topic 'processed-messages' already exists."
else
    echo "Creating topic 'processed-messages'..."
    gcloud pubsub topics create processed-messages \
        --message-retention-duration=30m \
        --project=$PROJECT_ID
fi

# External data requests topic - short retention
if topic_exists "external-data-requests"; then
    echo "✅ Topic 'external-data-requests' already exists."
else
    echo "Creating topic 'external-data-requests'..."
    gcloud pubsub topics create external-data-requests \
        --message-retention-duration=10m \
        --project=$PROJECT_ID
fi

# External data responses topic - short retention
if topic_exists "external-data-responses"; then
    echo "✅ Topic 'external-data-responses' already exists."
else
    echo "Creating topic 'external-data-responses'..."
    gcloud pubsub topics create external-data-responses \
        --message-retention-duration=10m \
        --project=$PROJECT_ID
fi

# Outgoing messages topic - moderate retention for reliability
if topic_exists "outgoing-messages"; then
    echo "✅ Topic 'outgoing-messages' already exists."
else
    echo "Creating topic 'outgoing-messages'..."
    gcloud pubsub topics create outgoing-messages \
        --message-retention-duration=30m \
        --project=$PROJECT_ID
fi

# Create subscriptions with optimized ack deadlines and expiration policy
echo "Creating subscriptions with optimized settings..."

# NLP Service subscription - longer ack deadline due to AI processing
if subscription_exists "incoming-messages-nlp-sub"; then
    echo "✅ Subscription 'incoming-messages-nlp-sub' already exists."
else
    echo "Creating subscription 'incoming-messages-nlp-sub'..."
    gcloud pubsub subscriptions create incoming-messages-nlp-sub \
        --topic=incoming-messages \
        --ack-deadline=60 \
        --message-retention-duration=10m \
        --expiration-period=2d \
        --project=$PROJECT_ID
fi

# Response service subscription
if subscription_exists "processed-messages-response-sub"; then
    echo "✅ Subscription 'processed-messages-response-sub' already exists."
else
    echo "Creating subscription 'processed-messages-response-sub'..."
    gcloud pubsub subscriptions create processed-messages-response-sub \
        --topic=processed-messages \
        --ack-deadline=30 \
        --message-retention-duration=30m \
        --expiration-period=2d \
        --project=$PROJECT_ID
fi

# External data service subscription
if subscription_exists "external-data-requests-sub"; then
    echo "✅ Subscription 'external-data-requests-sub' already exists."
else
    echo "Creating subscription 'external-data-requests-sub'..."
    gcloud pubsub subscriptions create external-data-requests-sub \
        --topic=external-data-requests \
        --ack-deadline=30 \
        --message-retention-duration=10m \
        --expiration-period=2d \
        --project=$PROJECT_ID
fi

# Response to external data subscription
if subscription_exists "external-data-responses-sub"; then
    echo "✅ Subscription 'external-data-responses-sub' already exists."
else
    echo "Creating subscription 'external-data-responses-sub'..."
    gcloud pubsub subscriptions create external-data-responses-sub \
        --topic=external-data-responses \
        --ack-deadline=30 \
        --message-retention-duration=10m \
        --expiration-period=2d \
        --project=$PROJECT_ID
fi

# Telegram bot subscription
if subscription_exists "outgoing-messages-telegram-sub"; then
    echo "✅ Subscription 'outgoing-messages-telegram-sub' already exists."
else
    echo "Creating subscription 'outgoing-messages-telegram-sub'..."
    gcloud pubsub subscriptions create outgoing-messages-telegram-sub \
        --topic=outgoing-messages \
        --ack-deadline=30 \
        --message-retention-duration=30m \
        --expiration-period=2d \
        --project=$PROJECT_ID
fi

echo "Pub/Sub setup complete with optimized settings for Modern ISONER free tier usage!"