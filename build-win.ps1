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

#Compress-Archive -Path ".\dist\AIPrompt\AIPrompt.exe" -DestinationPath ".\release\AIPrompt-win.zip" -Force
