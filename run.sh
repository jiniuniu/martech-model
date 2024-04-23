#!/bin/bash

# Load environment variables
source .env

# Set PYTHONPATH
export PYTHONPATH="$(pwd)"

# Function to start a service with nohup and redirect output to a log file
start_service() {
    local service_name="$1"
    local command="$2"
    local log_file="$3"

    echo "Starting $service_name..."
    nohup $command > "$log_file" 2>&1 &
    local pid=$!

    # Wait for a few seconds to ensure the process starts
    sleep 3

    # Check if the process is still running
    if ps -p $pid > /dev/null; then
        echo "$service_name started successfully with PID $pid."
    else
        echo "Failed to start $service_name. See $log_file for details."
        exit 1  # Exit the script with an error if the service fails to start
    fi
}

# Start Celery worker
start_service "Celery Worker" "celery -A worker.app worker --loglevel=info --concurrency=1" "/tmp/celery_log.txt"

# Start SVD Service
start_service "SVD Service" "python svd_service/app.py" "/tmp/svd_service_log.txt"

# Start Flower for Celery monitoring
start_service "Flower" "celery -A worker.app flower --basic_auth=$FLOWER_USER:$FLOWER_PWD" "/tmp/flower_log.txt"

# Print running processes
echo "All services started. Processes running:"
ps aux | grep -E 'celery|svd_service|flower' | grep -v grep
