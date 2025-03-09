#!/bin/bash

# Script to set up VM instance with Redis, API Gateway, and Auth Service for Modern ISONER

# Check if we have the necessary parameters
if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id>"
    echo "Example: $0 my-project-id"
    exit 1
fi

PROJECT_ID=$1
INSTANCE_NAME="isoner-services"
ZONE="us-central1-a"  # Choose a zone that offers e2-micro in always free tier
INSTANCE_TYPE="e2-micro"  # Using e2-micro type for free tier, but naming as VM instance

echo "Setting up VM instance for Modern ISONER services in project: $PROJECT_ID"

# Create the VM instance if it doesn't exist
if ! gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "Creating VM instance: $INSTANCE_NAME with Ubuntu 24.04 LTS (Noble)"
    gcloud compute instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=$INSTANCE_TYPE \
        --boot-disk-size=30GB \
        --boot-disk-type=pd-standard \
        --image-family=ubuntu-2404-lts-amd64 \
        --image-project=ubuntu-os-cloud \
        --tags=http-server,https-server \
        --metadata=startup-script="#! /bin/bash
        # Update system and install dependencies
        apt-get update
        apt-get upgrade -y
        apt-get install -y git docker.io apt-transport-https ca-certificates curl software-properties-common gnupg
        
        # Set up Docker properly
        systemctl start docker
        systemctl enable docker
        usermod -aG docker \$USER
        
        # Install Docker Compose
        curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        # Optimize the system for e2-micro
        # Reduce swappiness to improve performance
        echo 'vm.swappiness=10' >> /etc/sysctl.conf
        
        # Set up swap file (important for low memory instances)
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        
        # Set Redis to start on boot
        echo 'net.core.somaxconn=1024' >> /etc/sysctl.conf
        echo 'vm.overcommit_memory=1' >> /etc/sysctl.conf
        sysctl -p
        "
    
    # Add firewall rules to allow HTTP/HTTPS traffic
    gcloud compute firewall-rules create allow-http \
        --project=$PROJECT_ID \
        --allow=tcp:80 \
        --target-tags=http-server \
        --description="Allow HTTP traffic" || true  # Continue if rule exists
    
    gcloud compute firewall-rules create allow-https \
        --project=$PROJECT_ID \
        --allow=tcp:443 \
        --target-tags=https-server \
        --description="Allow HTTPS traffic" || true  # Continue if rule exists
    
    # Allow Redis port for internal access
    gcloud compute firewall-rules create allow-redis \
        --project=$PROJECT_ID \
        --allow=tcp:6379 \
        --target-tags=http-server \
        --description="Allow Redis traffic" \
        --source-ranges="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" || true  # Continue if rule exists
else
    echo "Instance $INSTANCE_NAME already exists, skipping creation."
fi

# Wait for instance to be ready (important for newly created instances)
echo "Waiting for instance to be ready..."
sleep 30

# Get the instance external IP
INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "Instance IP: $INSTANCE_IP"

# Copy necessary files to the instance
echo "Copying necessary files to the instance..."
gcloud compute scp --recurse api_gateway auth_service docker-compose.yml .env \
    $INSTANCE_NAME:~/ --zone=$ZONE --project=$PROJECT_ID

# Connect to the instance and set up Redis, API Gateway, and Auth Service
echo "Setting up Redis, API Gateway, and Auth Service on the instance..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command "
    # Setup Redis with optimal configuration for VM instance
    echo 'Setting up Redis...'
    mkdir -p ~/redis/data
    
    # Create a Redis configuration file with optimal settings for VM instance
    cat > ~/redis/redis.conf << EOF
    # Redis configuration optimized for VM instance (e2-micro)
    bind 0.0.0.0
    protected-mode yes
    port 6379
    
    # Memory management optimized for e2-micro
    maxmemory 256mb
    maxmemory-policy allkeys-lru
    
    # Reduce memory usage
    activedefrag yes
    active-defrag-ignore-bytes 100mb
    active-defrag-threshold-lower 10
    active-defrag-threshold-upper 30
    
    # Persistence settings
    dir /data
    appendonly no
    save 900 1
    save 300 10
    save 60 10000
    
    # Performance optimizations
    tcp-keepalive 300
    timeout 0
    databases 2
    
    # Disable expensive operations
    notify-keyspace-events \"\"
    
    # Reduce memory usage by using smaller data structures when possible
    set-max-intset-entries 512
    zset-max-ziplist-entries 128
    zset-max-ziplist-value 64
    hash-max-ziplist-entries 512
    hash-max-ziplist-value 64
    list-max-ziplist-size -2
    list-compress-depth 0
EOF
    
    # Make sure redis directory is in the docker-compose.yml
    sed -i 's|./redis/data:/data|~/redis/data:/data|g' docker-compose.yml
    sed -i 's|./redis/redis.conf:/usr/local/etc/redis/redis.conf|~/redis/redis.conf:/usr/local/etc/redis/redis.conf|g' docker-compose.yml
    
    # Build and start the containers
    echo 'Building and starting containers...'
    docker-compose up -d
    
    # Enable automatic container restart on boot
    sudo systemctl enable docker
    
    echo 'Setup complete!'
"

echo "VM instance setup complete! Redis, API Gateway, and Auth Service are now running."
echo "Instance IP: $INSTANCE_IP"
echo "Use this IP in your Cloud Run services configuration to connect to Redis and the API Gateway." 