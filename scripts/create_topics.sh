#!/bin/bash

# Check if project ID is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <project-id>"
  exit 1
fi

PROJECT_ID=$1

# Create Pub/Sub topics
echo "Creating Pub/Sub topics..."
gcloud pubsub topics create incoming-messages --project=$PROJECT_ID
gcloud pubsub topics create processed-messages --project=$PROJECT_ID
gcloud pubsub topics create external-data-requests --project=$PROJECT_ID
gcloud pubsub topics create external-data-responses --project=$PROJECT_ID
gcloud pubsub topics create outgoing-messages --project=$PROJECT_ID

# Create Pub/Sub subscriptions
echo "Creating Pub/Sub subscriptions..."
gcloud pubsub subscriptions create incoming-messages-nlp-sub \
  --topic=incoming-messages \
  --ack-deadline=20 \
  --project=$PROJECT_ID

gcloud pubsub subscriptions create processed-messages-response-sub \
  --topic=processed-messages \
  --ack-deadline=20 \
  --project=$PROJECT_ID

gcloud pubsub subscriptions create external-data-requests-sub \
  --topic=external-data-requests \
  --ack-deadline=20 \
  --project=$PROJECT_ID

gcloud pubsub subscriptions create outgoing-messages-sub \
  --topic=outgoing-messages \
  --ack-deadline=20 \
  --project=$PROJECT_ID

echo "Pub/Sub setup complete!"