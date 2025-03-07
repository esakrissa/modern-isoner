variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "supabase_url" {
  description = "The Supabase URL"
  type        = string
}

variable "supabase_key" {
  description = "The Supabase API key"
  type        = string
  sensitive   = true
}

variable "redis_host" {
  description = "The Redis host"
  type        = string
}

variable "redis_port" {
  description = "The Redis port"
  type        = string
  default     = "6379"
}

variable "redis_password" {
  description = "The Redis password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "The OpenAI API key"
  type        = string
  sensitive   = true
}

variable "rapidapi_key" {
  description = "The RapidAPI key"
  type        = string
  sensitive   = true
}