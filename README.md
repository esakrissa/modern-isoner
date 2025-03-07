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
        User --> TBH
        Admin --> ADM
        
        TBH --> RO
        ADM --> RO
        
        RO --> JWT
        RO --> MP
        
        JWT --> AUTH
        RBAC --> PERM
        MP --> CONV
        MP --> PUB
        
        SUB --> IR
        IR --> GPT
        IR --> SESS
        IR --> RAC
        RAC --> HOT
        
        IR --> RT
        RT --> PUB
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