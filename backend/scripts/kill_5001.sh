#!/bin/bash
# Kill processes on port 5001 cross-platform

echo "Cleaning up port 5001..."

# macOS/Linux
if command -v lsof >/dev/null 2>&1; then
    echo "Using lsof to find processes on port 5001..."
    PIDS=$(lsof -ti:5001 2>/dev/null || echo "")
    if [ -n "$PIDS" ]; then
        echo "Found processes: $PIDS"
        echo "$PIDS" | xargs kill -9
        echo "Killed processes on port 5001"
    else
        echo "No processes found on port 5001"
    fi
# Windows (if running in Git Bash or similar)
elif command -v netstat >/dev/null 2>&1; then
    echo "Using netstat to find processes on port 5001..."
    PIDS=$(netstat -ano | grep :5001 | awk '{print $5}' | sort -u)
    if [ -n "$PIDS" ]; then
        echo "Found processes: $PIDS"
        echo "$PIDS" | xargs taskkill /F /PID
        echo "Killed processes on port 5001"
    else
        echo "No processes found on port 5001"
    fi
else
    echo "Warning: Could not find lsof or netstat. Port 5001 may still be in use."
    echo "Please manually kill processes using port 5001."
fi

echo "Port cleanup complete."
