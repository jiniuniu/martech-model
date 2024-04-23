#!/bin/bash

# Function to kill a process with its name and signature
kill_process() {
    local name=$1
    echo "Stopping $name..."
    pkill -f "$name"
    echo "$name stopped."
}

# Function to kill a process with its name and signature
kill_celery_processes() {
    local name=$1
    echo "Stopping all processes related to $name..."

    # Generalized pattern to catch all related Celery processes
    pkill -f "celery.*$name"
    sleep 2  # Wait a bit to see if the process terminates

    # Check if the process is still running and force kill if it is
    if pgrep -f "celery.*$name" > /dev/null; then
        echo "Processes related to $name still running, attempting to kill with SIGKILL..."
        pkill -9 -f "celery.*$name"
        sleep 1  # Give it some time to stop
        if pgrep -f "celery.*$name" > /dev/null; then
            echo "Failed to stop processes related to $name."
        else
            echo "Processes related to $name stopped successfully."
        fi
    else
        echo "Processes related to $name stopped successfully."
    fi
}

# Kill Celery worker processes
kill_celery_processes "worker"

# Kill Flower processes
kill_celery_processes "flower"

# Additionally, if you're running any other specific Celery related services like beat, include them here
kill_celery_processes "beat"

# Kill the SVD service
kill_process "python svd_service/app.py"
