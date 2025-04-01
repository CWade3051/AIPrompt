#!/bin/bash

# Function to check if AIPrompt is running
check_running() {
    pgrep -f "AIPrompt.app/Contents/MacOS/AIPrompt" > /dev/null
    return $?
}

# Function to kill AIPrompt if it's running
kill_running() {
    if check_running; then
        echo "AIPrompt is running. Attempting to close it..."
        pkill -f "AIPrompt.app/Contents/MacOS/AIPrompt"
        sleep 2
        if check_running; then
            echo "Failed to close AIPrompt gracefully. Force killing..."
            pkill -9 -f "AIPrompt.app/Contents/MacOS/AIPrompt"
        fi
        echo "AIPrompt has been closed."
    fi
}

# Kill any running instances before building
kill_running

# Clean up previous build
echo "Cleaning up previous build..."
rm -rf build dist

# Build the application
echo "Building AIPrompt..."
pyinstaller AIPrompt.spec

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build successful. Creating zip archive..."
    # Create zip archive
    zip -r ./release/AIPrompt-mac.zip ./dist/AIPrompt.app
    echo "Build and packaging complete!"
else
    echo "Build failed!"
    exit 1
fi