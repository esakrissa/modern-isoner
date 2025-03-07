output "api_gateway_url" {
  description = "The URL of the API Gateway"
  value       = google_cloud_run_service.api_gateway.status[0].url
}

output "auth_service_url" {
  description = "The URL of the Auth Service"
  value       = google_cloud_run_service.auth_service.status[0].url
}

output "message_service_url" {
  description = "The URL of the Message Service"
  value       = google_cloud_run_service.message_service.status[0].url
}

output "nlp_service_url" {
  description = "The URL of the NLP Service"
  value       = google_cloud_run_service.nlp_service.status[0].url
}

output "external_data_service_url" {
  description = "The URL of the External Data Service"
  value       = google_cloud_run_service.external_data_service.status[0].url
}

output "response_service_url" {
  description = "The URL of the Response Service"
  value       = google_cloud_run_service.response_service.status[0].url
}

output "pubsub_topics" {
  description = "The Pub/Sub topics created"
  value = {
    incoming_messages      = google_pubsub_topic.incoming_messages.name
    processed_messages     = google_pubsub_topic.processed_messages.name
    external_data_requests = google_pubsub_topic.external_data_requests.name
    external_data_responses = google_pubsub_topic.external_data_responses.name
    outgoing_messages      = google_pubsub_topic.outgoing_messages.name
  }
} 