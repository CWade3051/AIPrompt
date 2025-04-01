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

# Function to update the latest GitHub release
update_latest_release() {
    # Check if GITHUB_TOKEN is set
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "Error: GITHUB_TOKEN environment variable not set"
        echo "Please set it with: export GITHUB_TOKEN=your_github_token"
        exit 1
    fi

    # Get the latest release ID
    echo "Fetching latest release information..."
    RELEASE_INFO=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
        "https://api.github.com/repos/CWade3051/AIPrompt/releases/latest")
    
    RELEASE_ID=$(echo "$RELEASE_INFO" | grep -o '"id": [0-9]*' | head -1 | awk '{print $2}')
    if [ -z "$RELEASE_ID" ]; then
        echo "Error: Could not find latest release ID"
        exit 1
    fi

    # Get the upload URL
    UPLOAD_URL=$(echo "$RELEASE_INFO" | grep -o '"upload_url": "[^"]*' | cut -d'"' -f4 | sed 's/{?name,label}//')
    if [ -z "$UPLOAD_URL" ]; then
        echo "Error: Could not find upload URL"
        exit 1
    fi

    # Delete existing macOS asset if it exists
    ASSETS=$(echo "$RELEASE_INFO" | grep -o '"id": [0-9]*' | awk '{print $2}')
    for ASSET_ID in $ASSETS; do
        ASSET_NAME=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
            "https://api.github.com/repos/CWade3051/AIPrompt/releases/assets/$ASSET_ID" | \
            grep -o '"name": "AIPrompt-mac.zip"' | cut -d'"' -f4)
        if [ "$ASSET_NAME" = "AIPrompt-mac.zip" ]; then
            echo "Deleting existing macOS asset..."
            curl -X DELETE -H "Authorization: Bearer $GITHUB_TOKEN" \
                "https://api.github.com/repos/CWade3051/AIPrompt/releases/assets/$ASSET_ID"
        fi
    done

    # Upload new build
    echo "Uploading new build to release..."
    curl -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Content-Type: application/zip" \
        --data-binary @./release/AIPrompt-mac.zip \
        "$UPLOAD_URL?name=AIPrompt-mac.zip"

    echo "Successfully updated latest release with new macOS build!"
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

    # Check if this script was called by version.py
    if [ -z "$VERSION_SCRIPT_RUNNING" ]; then
        echo "Not called by version.py, updating latest GitHub release..."
        update_latest_release
    else
        echo "Called by version.py, skipping GitHub release update"
    fi
else
    echo "Build failed!"
    exit 1
fi