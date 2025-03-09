#!/bin/bash

# Script to set up VM instance with Redis, API Gateway, and Auth Service for Modern ISONER

# Check if we have the necessary parameters
if [ -z "$1" ]; then
    echo "Usage: $0 <gcp-project-id>"
    echo "Example: $0 my-project-id"
    exit 1
fi

PROJECT_ID=$1
INSTANCE_NAME="modern-isoner-services"
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
        --tags=http-server,https-server
    
    # Add firewall rules to allow HTTP/HTTPS traffic
    gcloud compute firewall-rules create modern-isoner-allow-http \
        --project=$PROJECT_ID \
        --allow=tcp:80,tcp:8000 \
        --target-tags=http-server \
        --description="Allow HTTP traffic" || true  # Continue if rule exists
    
    gcloud compute firewall-rules create modern-isoner-allow-https \
        --project=$PROJECT_ID \
        --allow=tcp:443 \
        --target-tags=https-server \
        --description="Allow HTTPS traffic" || true  # Continue if rule exists
    
    # Allow Redis port for internal access
    gcloud compute firewall-rules create modern-isoner-allow-redis \
        --project=$PROJECT_ID \
        --allow=tcp:6379 \
        --target-tags=http-server \
        --description="Allow Redis traffic" \
        --source-ranges="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" || true  # Continue if rule exists
    
    # Ensure SSH access is allowed (essential)
    gcloud compute firewall-rules create modern-isoner-allow-ssh \
        --project=$PROJECT_ID \
        --allow=tcp:22 \
        --target-tags=http-server,https-server \
        --description="Allow SSH access to VM instance" || true  # Continue if rule exists
    
    # Allow internal communication between services
    gcloud compute firewall-rules create modern-isoner-allow-internal \
        --project=$PROJECT_ID \
        --allow=tcp:1-65535,udp:1-65535,icmp \
        --target-tags=http-server,https-server \
        --source-ranges="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" \
        --description="Allow internal communication between services" || true  # Continue if rule exists
else
    echo "Instance $INSTANCE_NAME already exists, skipping creation."
fi

# Wait for instance to be ready (important for newly created instances)
echo "Waiting for instance to be ready..."
sleep 30  # Wait for instance to initialize

# Get the instance external IP
INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "Instance IP: $INSTANCE_IP"

# Copy necessary files to the instance
echo "Copying necessary files to the instance..."
gcloud compute scp --recurse api_gateway auth_service docker-compose.yml .env \
    $INSTANCE_NAME:~/ --zone=$ZONE --project=$PROJECT_ID

# Create a setup script to run on the VM
cat > setup_docker.sh << EOF
#!/bin/bash
set -e

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install prerequisites
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the Docker repository
echo "deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update apt package index again
sudo apt-get update

# Install Docker Engine
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add current user to docker group
sudo usermod -aG docker \$USER
sudo systemctl enable docker
sudo systemctl start docker

# Install Docker Compose
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
sudo ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Setup Redis with optimal configuration for VM instance
mkdir -p ~/redis/data

# Create a Redis configuration file with optimal settings for VM instance
cat > ~/redis/redis.conf << EOL
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
notify-keyspace-events ""

# Reduce memory usage by using smaller data structures when possible
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
EOL

# Fix paths in docker-compose.yml
sed -i "s|./redis/data:/data|\$HOME/redis/data:/data|g" docker-compose.yml
sed -i "s|./redis/redis.conf:/usr/local/etc/redis/redis.conf|\$HOME/redis/redis.conf:/usr/local/etc/redis/redis.conf|g" docker-compose.yml

# Set up swap file (important for low memory instances)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Optimize the system for e2-micro
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'net.core.somaxconn=1024' | sudo tee -a /etc/sysctl.conf
echo 'vm.overcommit_memory=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Build and start the containers
sudo docker-compose up -d

echo 'Setup complete!'
EOF

# Copy the setup script to the VM
gcloud compute scp setup_docker.sh $INSTANCE_NAME:~/ --zone=$ZONE --project=$PROJECT_ID

# Make the script executable and run it
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command "
    chmod +x ~/setup_docker.sh
    ~/setup_docker.sh
"

echo "VM instance setup complete! Redis, API Gateway, and Auth Service are now running."
echo "Instance IP: $INSTANCE_IP"
echo "Use this IP in your Cloud Run services configuration to connect to Redis and the API Gateway." 