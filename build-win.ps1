# Function to update the latest GitHub release
function Update-LatestRelease {
    # Check if GITHUB_TOKEN is set
    if (-not $env:GITHUB_TOKEN) {
        Write-Host "Error: GITHUB_TOKEN environment variable not set"
        Write-Host "Please set it with: $env:GITHUB_TOKEN = 'your_github_token'"
        exit 1
    }

    # Get the latest release information
    Write-Host "Fetching latest release information..."
    $headers = @{
        "Authorization" = "Bearer $env:GITHUB_TOKEN"
        "Accept" = "application/vnd.github.v3+json"
    }

    $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/CWade3051/AIPrompt/releases/latest" -Headers $headers
    $releaseId = $releaseInfo.id
    $uploadUrl = $releaseInfo.upload_url -replace '{?name,label}', ''

    if (-not $releaseId) {
        Write-Host "Error: Could not find latest release ID"
        exit 1
    }

    # Delete existing Windows asset if it exists
    foreach ($asset in $releaseInfo.assets) {
        if ($asset.name -eq "AIPrompt-win.exe") {
            Write-Host "Deleting existing Windows asset..."
            Invoke-RestMethod -Uri "https://api.github.com/repos/CWade3051/AIPrompt/releases/assets/$($asset.id)" -Method Delete -Headers $headers
        }
    }

    # Upload new build
    Write-Host "Uploading new build to release..."
    $filePath = ".\release\AIPrompt-win.exe"
    $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
    
    $headers["Content-Type"] = "application/octet-stream"
    Invoke-RestMethod -Uri "$uploadUrl?name=AIPrompt-win.exe" -Method Post -Headers $headers -Body $fileBytes

    Write-Host "Successfully updated latest release with new Windows build!"
}

# Kill any running instances of AIPrompt
$processes = Get-Process "AIPrompt" -ErrorAction SilentlyContinue
if ($processes) {
    Write-Host "Stopping running AIPrompt instances..."
    $processes | Stop-Process -Force
    Start-Sleep -Seconds 1  # Give it a moment to fully close
}

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
