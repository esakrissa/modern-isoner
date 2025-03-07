#!/bin/bash

# Setup script for ISONER Modern Chatbot

echo "Setting up ISONER Modern Chatbot development environment..."

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please update the .env file with your actual credentials."
fi

# Create necessary directories if they don't exist
mkdir -p logs

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and Docker Compose."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "Building Docker images..."
docker-compose build

echo "Setup complete! You can now run the project with:"
echo "docker-compose up" 