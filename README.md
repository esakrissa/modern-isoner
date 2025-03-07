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
  }
}}%%
flowchart TB
    subgraph MainContainer[" "]
        %% User Interface Layer
        subgraph UI[User Interface Layer]
            subgraph TB[Telegram Bot]
                TBH[Message Handler]
                TBM[Media Processor]
            end
            subgraph AD[Admin Dashboard]
                ADM[Monitoring]
                ADS[Statistics]
            end
        end
        
        %% Gateway Layer
        subgraph GW[API Gateway Layer]
            subgraph AG[API Gateway]
                RL[Rate Limiter]
                RO[Router]
                LG[Logger]
                MO[Monitoring]
            end
        end
        
        %% Service Layer
        subgraph SVC[Service Layer]
            subgraph AS[Auth Service]
                JWT[JWT Authentication]
                RBAC[Role-Based Access]
                PM[Permission Manager]
            end
            
            subgraph MS[Message Service]
                MP[Message Processor]
                CM[Conversation Manager]
                MQ[Message Queue]
            end
            
            subgraph NLP[NLP Service]
                IR[Intent Recognition]
                EE[Entity Extraction]
                CA[Context Analyzer]
            end
            
            subgraph EDS[External Data Service]
                RAC[RapidAPI Client]
                DF[Data Formatter]
                CH[Cache Handler]
            end
            
            subgraph RS[Response Service]
                RT[Response Templates]
                FC[Format Converter]
                RG[Response Generator]
            end
        end
        
        %% Storage Layer
        subgraph ST[Storage Layer]
            subgraph SB[Supabase DB]
                AUTH[Auth Data]
                CONV[Conversations]
                PERM[Permissions]
            end
            subgraph PS[GCP Pub/Sub]
                PUB[Publisher]
                SUB[Subscriber]
            end
            subgraph RC[Redis Cache]
                SESS[Session Data]
                RESP[Response Cache]
            end
        end
        
        %% External Layer
        subgraph EXT[External Layer]
            subgraph OAI[OpenAI API]
                GPT[GPT Model]
                EMB[Embeddings]
            end
            subgraph RAPI[RapidAPI]
                HOT[Hotels API]
                BOOK[Booking.com API]
            end
        end
        
        %% Connections
        %% User Interface to Gateway
        User --> TBH
        TBM --> TBH
        Admin --> ADM
        TBH --> RL
        RL --> RO
        ADM --> RO
        
        %% Gateway to Services
        RO --> JWT
        RO --> MP
        LG --> MO
        
        %% Auth Service Connections
        JWT --> RBAC
        RBAC --> PM
        JWT --> AUTH
        RBAC --> PERM
        PM --> PERM
        
        %% Message Service Connections
        MP --> CM
        CM --> CONV
        MP --> MQ
        MQ --> PUB
        
        %% Message Flow to NLP
        PUB --> SUB
        SUB --> IR
        
        %% NLP Service Connections
        IR --> EE
        EE --> CA
        IR --> GPT
        IR --> EMB
        CA --> SESS
        
        %% External Data Service Connections
        IR --> RAC
        RAC --> HOT
        RAC --> BOOK
        HOT --> DF
        BOOK --> DF
        DF --> CH
        CH --> RESP
        
        %% Response Service Connections
        CA --> RT
        RT --> FC
        FC --> RG
        RG --> PUB
        
        %% Completing the Loop
        SUB --> TBH
        TBH --> User
    end

    %% Styling
    style MainContainer fill:#ffffff,stroke:#ffffff,stroke-width:4px
    style UI fill:#ffffff,stroke:#000000,stroke-width:2px
    style GW fill:#ffffff,stroke:#000000,stroke-width:2px
    style SVC fill:#ffffff,stroke:#000000,stroke-width:2px
    style ST fill:#ffffff,stroke:#000000,stroke-width:2px
    style EXT fill:#ffffff,stroke:#000000,stroke-width:2px
    
    %% Node Styling - Main Components
    style TB fill:#ffffff,stroke:#000000,stroke-width:2px
    style AD fill:#ffffff,stroke:#000000,stroke-width:2px
    style AG fill:#ffffff,stroke:#000000,stroke-width:2px
    style AS fill:#ffffff,stroke:#000000,stroke-width:2px
    style MS fill:#ffffff,stroke:#000000,stroke-width:2px
    style NLP fill:#ffffff,stroke:#000000,stroke-width:2px
    style EDS fill:#ffffff,stroke:#000000,stroke-width:2px
    style RS fill:#ffffff,stroke:#000000,stroke-width:2px
    style SB fill:#ffffff,stroke:#000000,stroke-width:2px
    style PS fill:#ffffff,stroke:#000000,stroke-width:2px
    style RC fill:#ffffff,stroke:#000000,stroke-width:2px
    style OAI fill:#ffffff,stroke:#000000,stroke-width:2px
    style RAPI fill:#ffffff,stroke:#000000,stroke-width:2px

    %% Node Styling - Internal Components
    style TBH fill:#ffffff,stroke:#000000,stroke-width:2px
    style TBM fill:#ffffff,stroke:#000000,stroke-width:2px
    style ADM fill:#ffffff,stroke:#000000,stroke-width:2px
    style ADS fill:#ffffff,stroke:#000000,stroke-width:2px
    style RL fill:#ffffff,stroke:#000000,stroke-width:2px
    style RO fill:#ffffff,stroke:#000000,stroke-width:2px
    style LG fill:#ffffff,stroke:#000000,stroke-width:2px
    style MO fill:#ffffff,stroke:#000000,stroke-width:2px
    style JWT fill:#ffffff,stroke:#000000,stroke-width:2px
    style RBAC fill:#ffffff,stroke:#000000,stroke-width:2px
    style PM fill:#ffffff,stroke:#000000,stroke-width:2px
    style MP fill:#ffffff,stroke:#000000,stroke-width:2px
    style CM fill:#ffffff,stroke:#000000,stroke-width:2px
    style MQ fill:#ffffff,stroke:#000000,stroke-width:2px
    style IR fill:#ffffff,stroke:#000000,stroke-width:2px
    style EE fill:#ffffff,stroke:#000000,stroke-width:2px
    style CA fill:#ffffff,stroke:#000000,stroke-width:2px
    style RAC fill:#ffffff,stroke:#000000,stroke-width:2px
    style DF fill:#ffffff,stroke:#000000,stroke-width:2px
    style CH fill:#ffffff,stroke:#000000,stroke-width:2px
    style RT fill:#ffffff,stroke:#000000,stroke-width:2px
    style FC fill:#ffffff,stroke:#000000,stroke-width:2px
    style RG fill:#ffffff,stroke:#000000,stroke-width:2px
    style AUTH fill:#ffffff,stroke:#000000,stroke-width:2px
    style CONV fill:#ffffff,stroke:#000000,stroke-width:2px
    style PERM fill:#ffffff,stroke:#000000,stroke-width:2px
    style PUB fill:#ffffff,stroke:#000000,stroke-width:2px
    style SUB fill:#ffffff,stroke:#000000,stroke-width:2px
    style SESS fill:#ffffff,stroke:#000000,stroke-width:2px
    style RESP fill:#ffffff,stroke:#000000,stroke-width:2px
    style GPT fill:#ffffff,stroke:#000000,stroke-width:2px
    style EMB fill:#ffffff,stroke:#000000,stroke-width:2px
    style HOT fill:#ffffff,stroke:#000000,stroke-width:2px
    style BOOK fill:#ffffff,stroke:#000000,stroke-width:2px

    %% Link Styling
    linkStyle default stroke:#000000,stroke-width:2px
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

