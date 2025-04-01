# Function to update the latest GitHub release
function Update-LatestRelease {
    # Check if GITHUB_TOKEN is set
    if (-not $env:GITHUB_TOKEN) {
        Write-Host "Error: GITHUB_TOKEN environment variable not set"
        Write-Host "Please set it with: $env:GITHUB_TOKEN = 'your_github_token'"
        exit 1
    }

    # API Headers
    $headers = @{
        "Authorization" = "token $env:GITHUB_TOKEN"
        "Accept" = "application/vnd.github.v3+json"
    }

    try {
        # Get the latest release
        Write-Host "Fetching latest release information..."
        $releaseUrl = "https://api.github.com/repos/CWade3051/AIPrompt/releases/latest"
        $releaseInfo = Invoke-RestMethod -Uri $releaseUrl -Headers $headers -Method Get
        
        if (-not $releaseInfo.id) {
            Write-Host "Error: Could not find latest release ID"
            exit 1
        }
        
        Write-Host "Found release: $($releaseInfo.name) (ID: $($releaseInfo.id))"

        # Delete existing Windows asset if it exists
        foreach ($asset in $releaseInfo.assets) {
            if ($asset.name -eq "AIPrompt-win.exe") {
                Write-Host "Found existing Windows asset (ID: $($asset.id)). Deleting..."
                try {
                    $deleteUrl = "https://api.github.com/repos/CWade3051/AIPrompt/releases/assets/$($asset.id)"
                    Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers
                    Write-Host "Successfully deleted existing asset"
                } catch {
                    Write-Host "Warning: Failed to delete existing asset: $($_.Exception.Message)"
                }
                break
            }
        }

        # Upload new build
        $filePath = ".\release\AIPrompt-win.exe"
        if (-not (Test-Path $filePath)) {
            Write-Host "Error: Build file not found at $filePath"
            exit 1
        }

        Write-Host "Uploading new build to release..."
        
        # Construct upload URL
        $uploadUrl = "https://uploads.github.com/repos/CWade3051/AIPrompt/releases/$($releaseInfo.id)/assets?name=AIPrompt-win.exe"
        
        # Upload the file
        $uploadHeaders = $headers.Clone()
        $uploadHeaders["Content-Type"] = "application/octet-stream"
        
        try {
            $response = Invoke-RestMethod -Uri $uploadUrl -Method Post -Headers $uploadHeaders -InFile $filePath
            Write-Host "Successfully uploaded new Windows build!"
            Write-Host "Download URL: $($response.browser_download_url)"
        } catch {
            Write-Host "Error uploading asset:"
            Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
            Write-Host "Status Description: $($_.Exception.Response.StatusDescription)"
            
            # Try to get response body for more details
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $reader.BaseStream.Position = 0
                $reader.DiscardBufferedData()
                $responseBody = $reader.ReadToEnd()
                Write-Host "Response Body: $responseBody"
            } catch {
                Write-Host "Could not read response body: $($_.Exception.Message)"
            }
            exit 1
        }

    } catch {
        Write-Host "Error updating release: $($_.Exception.Message)"
        Write-Host "Full Error: $_"
        exit 1
    }
}

# Kill any running instances of AIPrompt
$processes = Get-Process "AIPrompt" -ErrorAction SilentlyContinue
if ($processes) {
    Write-Host "Stopping running AIPrompt instances..."
    $processes | Stop-Process -Force
    Start-Sleep -Seconds 1  # Give it a moment to fully close
}

# Clean and rebuild
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\release\AIPrompt-win.exe" -ErrorAction SilentlyContinue
pyinstaller AIPrompt.spec
New-Item -ItemType Directory -Force -Path ".\release"
Copy-Item ".\dist\AIPrompt.exe" ".\release\AIPrompt-win.exe" -Force

# Check if this script was called by version.py
if (-not $env:VERSION_SCRIPT_RUNNING) {
    Write-Host "Not called by version.py, updating latest GitHub release..."
    Update-LatestRelease
} else {
    Write-Host "Called by version.py, skipping GitHub release update"
}

#Compress-Archive -Path ".\dist\AIPrompt\AIPrompt.exe" -DestinationPath ".\release\AIPrompt-win.zip" -Force
