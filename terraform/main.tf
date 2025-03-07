provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "pubsub" {
  service = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Create Pub/Sub topics
resource "google_pubsub_topic" "incoming_messages" {
  name = "incoming-messages"
  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_topic" "processed_messages" {
  name = "processed-messages"
  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_topic" "external_data_requests" {
  name = "external-data-requests"
  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_topic" "external_data_responses" {
  name = "external-data-responses"
  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_topic" "outgoing_messages" {
  name = "outgoing-messages"
  depends_on = [google_project_service.pubsub]
}

# Create Pub/Sub subscriptions
resource "google_pubsub_subscription" "incoming_messages_nlp_sub" {
  name  = "incoming-messages-nlp-sub"
  topic = google_pubsub_topic.incoming_messages.name

  ack_deadline_seconds = 20
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_pubsub_topic.incoming_messages]
}

resource "google_pubsub_subscription" "processed_messages_response_sub" {
  name  = "processed-messages-response-sub"
  topic = google_pubsub_topic.processed_messages.name

  ack_deadline_seconds = 20
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_pubsub_topic.processed_messages]
}

resource "google_pubsub_subscription" "external_data_requests_sub" {
  name  = "external-data-requests-sub"
  topic = google_pubsub_topic.external_data_requests.name

  ack_deadline_seconds = 20
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_pubsub_topic.external_data_requests]
}

resource "google_pubsub_subscription" "outgoing_messages_sub" {
  name  = "outgoing-messages-sub"
  topic = google_pubsub_topic.outgoing_messages.name

  ack_deadline_seconds = 20
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_pubsub_topic.outgoing_messages]
}

# Create Artifact Registry repository
resource "google_artifact_registry_repository" "isoner_chatbot" {
  location      = var.region
  repository_id = "isoner-chatbot"
  description   = "Docker repository for ISONER Chatbot"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry]
}

# Create Cloud Run services
resource "google_cloud_run_service" "api_gateway" {
  name     = "api-gateway"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/api-gateway:latest"
        
        env {
          name  = "AUTH_SERVICE_URL"
          value = "https://${google_cloud_run_service.auth_service.status[0].url}"
        }
        
        env {
          name  = "MESSAGE_SERVICE_URL"
          value = "https://${google_cloud_run_service.message_service.status[0].url}"
        }
        
        env {
          name  = "EXTERNAL_DATA_SERVICE_URL"
          value = "https://${google_cloud_run_service.external_data_service.status[0].url}"
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot
  ]
}

resource "google_cloud_run_service" "auth_service" {
  name     = "auth-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/auth-service:latest"
        
        env {
          name  = "SUPABASE_URL"
          value = var.supabase_url
        }
        
        env {
          name  = "SUPABASE_KEY"
          value = var.supabase_key
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot
  ]
}

resource "google_cloud_run_service" "message_service" {
  name     = "message-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/message-service:latest"
        
        env {
          name  = "SUPABASE_URL"
          value = var.supabase_url
        }
        
        env {
          name  = "SUPABASE_KEY"
          value = var.supabase_key
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_INCOMING_MESSAGES_TOPIC"
          value = google_pubsub_topic.incoming_messages.name
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot,
    google_pubsub_topic.incoming_messages
  ]
}

resource "google_cloud_run_service" "nlp_service" {
  name     = "nlp-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/nlp-service:latest"
        
        env {
          name  = "REDIS_HOST"
          value = var.redis_host
        }
        
        env {
          name  = "REDIS_PORT"
          value = var.redis_port
        }
        
        env {
          name  = "REDIS_PASSWORD"
          value = var.redis_password
        }
        
        env {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_INCOMING_MESSAGES_TOPIC"
          value = google_pubsub_topic.incoming_messages.name
        }
        
        env {
          name  = "PUBSUB_INCOMING_MESSAGES_SUBSCRIPTION"
          value = google_pubsub_subscription.incoming_messages_nlp_sub.name
        }
        
        env {
          name  = "PUBSUB_PROCESSED_MESSAGES_TOPIC"
          value = google_pubsub_topic.processed_messages.name
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot,
    google_pubsub_topic.incoming_messages,
    google_pubsub_topic.processed_messages,
    google_pubsub_subscription.incoming_messages_nlp_sub
  ]
}

resource "google_cloud_run_service" "external_data_service" {
  name     = "external-data-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/external-data-service:latest"
        
        env {
          name  = "REDIS_HOST"
          value = var.redis_host
        }
        
        env {
          name  = "REDIS_PORT"
          value = var.redis_port
        }
        
        env {
          name  = "REDIS_PASSWORD"
          value = var.redis_password
        }
        
        env {
          name  = "RAPIDAPI_KEY"
          value = var.rapidapi_key
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot
  ]
}

resource "google_cloud_run_service" "response_service" {
  name     = "response-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.isoner_chatbot.repository_id}/response-service:latest"
        
        env {
          name  = "SUPABASE_URL"
          value = var.supabase_url
        }
        
        env {
          name  = "SUPABASE_KEY"
          value = var.supabase_key
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_PROCESSED_MESSAGES_TOPIC"
          value = google_pubsub_topic.processed_messages.name
        }
        
        env {
          name  = "PUBSUB_PROCESSED_MESSAGES_SUBSCRIPTION"
          value = google_pubsub_subscription.processed_messages_response_sub.name
        }
        
        env {
          name  = "PUBSUB_OUTGOING_MESSAGES_TOPIC"
          value = google_pubsub_topic.outgoing_messages.name
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.isoner_chatbot,
    google_pubsub_topic.processed_messages,
    google_pubsub_topic.outgoing_messages,
    google_pubsub_subscription.processed_messages_response_sub
  ]
}

# IAM policy for public access to API Gateway
resource "google_cloud_run_service_iam_member" "api_gateway_public" {
  service  = google_cloud_run_service.api_gateway.name
  location = google_cloud_run_service.api_gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}