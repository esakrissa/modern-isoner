# Modern ISONER

Modern implementation of ISONER (Information System on Internet Messenger) framework using microservices architecture. This project modernizes the original ISONER concept with Python, FastAPI, Supabase, Redis, and GCP Pub/Sub, providing a scalable and efficient chatbot system accessible through Telegram.

Key features:
- Microservices architecture with Python and FastAPI
- Supabase (PostgreSQL) for database
- GCP Pub/Sub for message broker
- Redis for caching
- OpenAI integration for advanced NLP
- Telegram Bot interface
- Role-Based Access Control (RBAC)
- Containerized with Docker and orchestrated with Kubernetes
- Infrastructure as Code with Terraform

## Architecture

This project implements a microservices architecture for a chatbot system with the following components:

- **API Gateway**: Routes requests to appropriate services
- **Auth Service**: Handles user authentication and authorization
- **Message Service**: Manages user messages and conversations
- **NLP Service**: Processes messages using OpenAI API
- **External Data Service**: Fetches data from external APIs (e.g., hotel information)
- **Response Service**: Generates and formats responses to users

### System Flow Diagram

```mermaid
%%{init: {
  'theme': 'base', 
  'themeVariables': { 
    'primaryColor': '#ffffff', 
    'primaryTextColor': '#000000', 
    'primaryBorderColor': '#000000', 
    'lineColor': '#000000', 
    'secondaryColor': '#ffffff', 
    'tertiaryColor': '#ffffff',
    'background': '#ffffff'
  },
  'flowchart': {
    'htmlLabels': true,
    'curve': 'basis',
    'diagramPadding': 40,
    'useMaxWidth': false
  }
}}%%
flowchart TB
    %% Create a background container for the entire diagram
    subgraph BG [" "]
        %% Define nodes with proper spacing
        subgraph UI["User Interfaces"]
            TB["Telegram Bot"]
            AD["Admin Dashboard<br/>(Optional)"]
        end
        
        subgraph API["API Layer"]
            AG["API Gateway"]
        end
        
        subgraph CS["Core Services"]
            AS["Auth<br/>Service"]
            MS["Message<br/>Service"]
            NLP["NLP<br/>Service"]
            EDS["External Data<br/>Service"]
            RS["Response<br/>Service"]
        end
        
        subgraph DS["Data Storage & Messaging"]
            SB[(Supabase DB)]
            PS["GCP Pub/Sub"]
            RC[(Redis Cache)]
        end
        
        subgraph ES["External Services"]
            OAI["OpenAI API"]
            RAPI["RapidAPI<br/>(Booking.com)"]
        end
        
        %% Define connections with proper spacing
        TB -->|"Request"| AG
        AD -->|"Admin<br/>Request"| AG
        
        AG -->|"Auth<br/>Request"| AS
        AG -->|"Message<br/>Request"| MS
        
        AS -->|"Store/Query"| SB
        MS -->|"Store/Query"| SB
        MS -->|"Publish"| PS
        
        PS -->|"Subscribe"| NLP
        NLP -->|"Process"| OAI
        NLP -->|"Cache"| RC
        
        NLP -->|"Request<br/>Data"| EDS
        NLP -->|"Generate<br/>Response"| RS
        
        EDS -->|"Fetch"| RAPI
        EDS -->|"Cache"| RC
        
        RS -->|"Publish"| PS
        PS -->|"Subscribe"| TB
    end
    
    %% Style all links and nodes
    linkStyle default stroke:#000000,stroke-width:1.5px;
    
    style BG fill:#ffffff,stroke:#ffffff,stroke-width:0px;
    style UI fill:#ffffff,stroke:#000000,stroke-width:1px;
    style API fill:#ffffff,stroke:#000000,stroke-width:1px;
    style CS fill:#ffffff,stroke:#000000,stroke-width:1px;
    style DS fill:#ffffff,stroke:#000000,stroke-width:1px;
    style ES fill:#ffffff,stroke:#000000,stroke-width:1px;
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant TB as Telegram Bot
    participant AG as API Gateway
    participant AS as Auth Service
    participant MS as Message Service
    participant NLP as NLP Service
    participant EDS as External Data Service
    participant RS as Response Service
    participant SB as Supabase
    participant PS as Pub/Sub
    participant RC as Redis Cache
    participant OAI as OpenAI API
    participant RAPI as RapidAPI

    User->>TB: Send message
    TB->>AG: Forward request
    AG->>AS: Authenticate user
    AS->>SB: Verify credentials
    SB-->>AS: User verified
    AS-->>AG: Auth success

    AG->>MS: Process message
    MS->>SB: Store message
    MS->>PS: Publish message
    PS-->>NLP: Subscribe & process

    par NLP Processing
        NLP->>OAI: Process text
        OAI-->>NLP: Intent & entities
        NLP->>RC: Cache results
    and External Data
        NLP->>EDS: Request data
        EDS->>RAPI: Fetch hotel info
        EDS->>RC: Cache response
        RAPI-->>EDS: Hotel data
        EDS-->>NLP: Processed data
    end

    NLP->>RS: Generate response
    RS->>PS: Publish response
    PS-->>TB: Subscribe & receive
    TB->>User: Send response

    loop Cache Management
        RC->>RC: Expire old data
    end

    Note over NLP,RS: All services use Redis<br/>for caching responses
    Note over MS,PS: Pub/Sub ensures<br/>asynchronous communication
```

## Technologies

- **Backend**: Python 3.11+ with FastAPI
- **Database**: Supabase (PostgreSQL)
- **Message Broker**: Google Cloud Pub/Sub
- **Caching**: Redis
- **NLP**: OpenAI GPT API
- **External Data**: RapidAPI (Hotels API from Booking.com)
- **Deployment**: Google Cloud Run
- **Infrastructure as Code**: Terraform
- **CI/CD**: GitHub Actions

## Security & Access Control

This project implements Role-Based Access Control (RBAC) for secure access management:

- **Authentication**: JWT-based authentication via Supabase Auth
- **Authorization**: Custom middleware for permission and role checks
- **Roles**: Pre-defined roles (admin, manager, user) with different access levels
- **Permissions**: Granular permissions for specific actions
- **Row Level Security**: Database-level security policies in Supabase

## Development Setup

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

### Deployment

1. Set up GCP project and enable required APIs:

```bash
gcloud services enable pubsub.googleapis.com run.googleapis.com artifactregistry.googleapis.com
```

2. Create Pub/Sub topics and subscriptions:

```bash
./scripts/create_topics.sh your-gcp-project-id
```

3. Deploy to GCP:

```bash
./scripts/deploy.sh your-gcp-project-id us-central1
```

## Project Structure

```
modern-isoner/
├── api_gateway/         # API Gateway service
├── auth_service/        # Authentication service
├── message_service/     # Message handling service
├── nlp_service/         # Natural Language Processing service
├── external_data_service/ # External data fetching service
├── response_service/    # Response generation service
├── telegram_bot/        # Telegram Bot interface
├── middleware/          # Shared middleware components
├── routes/             # API route definitions
├── terraform/          # Infrastructure as code
├── scripts/            # Utility scripts
├── sql/               # SQL scripts
└── .github/workflows/  # CI/CD pipelines
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.