# Modern ISONER

Modern implementation of ISONER (Information System on Internet Messenger) framework using microservices architecture. This project modernizes the original ISONER concept with Python, FastAPI, Supabase, Redis, and GCP Pub/Sub, providing a scalable and efficient chatbot system accessible through Telegram.

## 🔑 Key features:
- Microservices architecture with Python and FastAPI
- Supabase (PostgreSQL) for database
- GCP Pub/Sub for message broker
- Redis for caching
- OpenAI integration for advanced NLP
- Telegram Bot interface
- Role-Based Access Control (RBAC)
- Containerized with Docker and orchestrated with Kubernetes
- Infrastructure as Code with Terraform

## ⚡ Architecture

This project implements a microservices architecture for a chatbot system with the following components:

- **API Gateway**: Routes requests to appropriate services
- **Auth Service**: Handles user authentication and authorization
- **Message Service**: Manages user messages and conversations
- **NLP Service**: Processes messages using OpenAI API
- **External Data Service**: Fetches data from external APIs (e.g., hotel information)
- **Response Service**: Generates and formats responses to users

### System Flow Diagram

<details>
<summary>Click to view the architecture diagram</summary>

<div align="center">
  <img src="./docs/assets/system-flow-diagram.svg" alt="Modern ISONER Architecture" width="100%">
</div>

</details>

<details>
<summary>Click to view the architecture diagram alternate version</summary>

<div align="center">
  <img src="./docs/assets/system-flow-diagram-alt.svg" alt="Modern ISONER Architecture" width="100%">
</div>

</details>

## 💻 Technologies

- **Backend**: Python 3.11+ with FastAPI
- **Database**: Supabase (PostgreSQL)
- **Message Broker**: Google Cloud Pub/Sub
- **Caching**: Redis
- **NLP**: OpenAI GPT API
- **External Data**: RapidAPI (Hotels API from Booking.com)
- **Deployment**: Google Cloud Run
- **Infrastructure as Code**: Terraform
- **CI/CD**: GitHub Actions

## 🔐 Security & Access Control

This project implements Role-Based Access Control (RBAC) for secure access management:

- **Authentication**: JWT-based authentication via Supabase Auth
- **Authorization**: Custom middleware for permission and role checks
- **Roles**: Pre-defined roles (admin, manager, user) with different access levels
- **Permissions**: Granular permissions for specific actions
- **Row Level Security**: Database-level security policies in Supabase

## 🚀 Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Google Cloud SDK
- Supabase account
- Redis instance (local or cloud)
- OpenAI API key
- RapidAPI key
- Telegram Bot token

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# GCP
GCP_PROJECT_ID=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# Redis
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# API Keys
OPENAI_API_KEY=your_openai_api_key
RAPIDAPI_KEY=your_rapidapi_key

# JWT
JWT_SECRET=your_jwt_secret_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### Database Setup

1. Run the combined SQL setup script to create all necessary tables and functions:

```bash
psql -U your_username -d your_database -f sql/combined_setup.sql
```

### Running Locally

1. Start the services using Docker Compose:

```bash
docker-compose up
```

2. Access the API Gateway at http://localhost:8000

## 📋 Deployment Guide

### Deployment Architecture

The deployment is optimized to stay within GCP's free tier limits:

1. **VM Instance** hosts:
   - Ubuntu 24.04 LTS (Noble) operating system
   - Redis Cache (256MB memory limit)
   - API Gateway Service
   - Auth Service

2. **Cloud Run** hosts:
   - Message Service
   - NLP Service (with 2GB memory for AI processing)
   - External Data Service
   - Response Service
   - Telegram Bot (in webhook mode)

3. **GCP Pub/Sub** for message brokering with optimized settings:
   - Short message retention periods
   - Proper subscription configurations
   - Optimized for free tier limits

### Prerequisites

Before deploying, make sure you have:

1. A Google Cloud Platform account
2. GCP project with billing enabled
3. gcloud CLI installed and configured
4. Docker installed (for local testing)
5. The following APIs enabled in your GCP project:
   ```bash
   gcloud services enable pubsub.googleapis.com run.googleapis.com artifactregistry.googleapis.com compute.googleapis.com
   ```
6. A Supabase account and project
7. Environment variables set up in `.env` file (as shown in the Development Setup section)

### Deployment Methods

#### All-in-One Deployment

To deploy the entire system in one go:

```bash
./scripts/deploy_all.sh your-gcp-project-id us-central1
```

This script will:
- Create Pub/Sub topics and subscriptions
- Set up the VM instance with Ubuntu 24.04 LTS, Redis, API Gateway, and Auth Service
- Deploy remaining services to Cloud Run
- Configure services to communicate with each other
- Set up Telegram webhook

#### Step-by-Step Deployment

If you prefer to deploy step by step:

##### 1. Create Pub/Sub Topics and Subscriptions

```bash
./scripts/create_topics.sh your-gcp-project-id
```

##### 2. Set Up VM Instance

```bash
./scripts/setup_vm.sh your-gcp-project-id
```

Note: This will create a VM instance using Ubuntu 24.04 LTS (Noble) on an e2-micro machine type for free tier, and deploy Redis, API Gateway, and Auth Service.

##### 3. Deploy Services to Cloud Run

First, get the IP address of your VM instance:

```bash
INSTANCE_IP=$(gcloud compute instances describe isoner-services --zone=us-central1-a --project=your-gcp-project-id --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
```

Then deploy the Cloud Run services:

```bash
./scripts/deploy_cloud_run.sh your-gcp-project-id us-central1 $INSTANCE_IP
```

### VM Instance Optimizations

The VM instance is optimized for e2-micro's limited resources:

1. **Swap File**: A 2GB swap file is added to prevent out-of-memory issues
2. **System Tuning**: Kernel parameters are tuned for Redis and performance
3. **Redis Optimizations**: Redis is configured with memory limits and optimized data structures
4. **Memory Management**: Swappiness is reduced for better performance
5. **Service Resilience**: Services are configured to restart automatically

### Monitoring and Maintenance

#### Checking Service Status

To check if all services are running properly:

```bash
# Check VM services
gcloud compute ssh isoner-services --zone=us-central1-a --project=your-gcp-project-id --command "docker ps"

# Check Cloud Run services
gcloud run services list --platform managed --region=us-central1 --project=your-gcp-project-id
```

#### Logs

To view logs:

```bash
# VM logs
gcloud compute ssh isoner-services --zone=us-central1-a --project=your-gcp-project-id --command "docker logs api-gateway"
gcloud compute ssh isoner-services --zone=us-central1-a --project=your-gcp-project-id --command "docker logs auth-service"
gcloud compute ssh isoner-services --zone=us-central1-a --project=your-gcp-project-id --command "docker logs redis"

# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=message-service" --project=your-gcp-project-id --limit=10
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=nlp-service" --project=your-gcp-project-id --limit=10
```

#### Monitoring Free Tier Usage

To stay within free tier limits, regularly monitor your usage in the GCP Console:

1. Go to Billing > Reports
2. Filter by service (Compute Engine, Cloud Run, Pub/Sub)
3. Check usage against free tier limits

### Troubleshooting

#### Common Issues

1. **Services Not Communicating**: Check firewall rules and ensure services have proper environment variables set.

2. **Redis Connection Issues**: Verify the Redis port (6379) is allowed in the firewall rules.

3. **Cloud Run Cold Start**: Initial requests may be slow due to cold starts. This is normal behavior.

4. **Pub/Sub Message Processing Issues**: Check subscription ack deadlines and retry policies.

5. **Telegram Webhook Not Working**: Verify the webhook URL is correctly set and the Telegram Bot service is running.

#### Restarting Services

To restart services:

```bash
# Restart VM services
gcloud compute ssh isoner-services --zone=us-central1-a --project=your-gcp-project-id --command "docker-compose restart"

# Restart Cloud Run services (requires redeployment)
gcloud run deploy message-service --image gcr.io/your-gcp-project-id/message-service --platform managed --region us-central1
```

### Security Considerations

1. **Firewall Rules**: Only necessary ports are exposed.
2. **Service Authentication**: Cloud Run services use internal authentication.
3. **Redis Access**: Redis is only accessible from within the GCP network.
4. **Supabase Security**: Follows Supabase best practices for authentication and authorization.

## 📁 Project Structure

```
modern-isoner/
├── api_gateway/         # API Gateway service (deployed on VM)
├── auth_service/        # Authentication service (deployed on VM) 
├── message_service/     # Message handling service (deployed on Cloud Run)
├── nlp_service/         # Natural Language Processing service (deployed on Cloud Run)
├── external_data_service/ # External data fetching service (deployed on Cloud Run)
├── response_service/    # Response generation service (deployed on Cloud Run)
├── telegram_bot/        # Telegram Bot interface (deployed on Cloud Run)
├── middleware/          # Shared middleware components
├── routes/              # API route definitions
├── docs/                # Documentation files and assets
├── sql/                 # Database setup and migration scripts
├── scripts/             # Deployment and utility scripts
├── docker-compose.yml   # Local development container orchestration
├── .github/workflows/   # CI/CD pipelines
└── .env.example         # Example environment variables template
```

## 🗺️ Deployment Map

The Modern ISONER architecture is distributed across different resources to optimize for cost and performance:

### VM Instance Components (e2-micro with Ubuntu 24.04 LTS)
- **Redis Cache**: In-memory data store with 256MB memory limit, optimized for e2-micro
- **API Gateway**: Central entry point that routes requests to appropriate services
- **Auth Service**: Handles user authentication and authorization

### Cloud Run Components
- **Message Service**: Processes and routes user messages through the system
- **NLP Service**: Analyzes text using OpenAI, allocated with 1GB memory and optimized Redis caching
- **External Data Service**: Fetches information from external APIs (weather, hotels, etc.)
- **Response Service**: Formats and finalizes responses to be sent to users
- **Telegram Bot**: Provides the interface for users to interact with the system

### Communication Flow
1. User messages are received by the Telegram Bot
2. Messages are published to Pub/Sub topics
3. Appropriate services process the messages
4. Responses flow back through the API Gateway
5. Final responses are delivered to users via the Telegram Bot

This architecture balances performance needs with cost optimization by:
- Placing stateful and always-on services on the VM instance
- Running stateless, scalable services on Cloud Run
- Using Pub/Sub for reliable message passing between components

## 🔄 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0. - visit: https://www.apache.org/licenses/LICENSE-2.0 for details.
