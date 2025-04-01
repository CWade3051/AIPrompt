Remove-Item -Recurse -Force build, dist
pyinstaller AIPrompt.spec
New-Item -ItemType Directory -Force -Path ".\release"
Copy-Item ".\dist\AIPrompt.exe" ".\release\AIPrompt-win.exe" -Force

#Compress-Archive -Path ".\dist\AIPrompt\AIPrompt.exe" -DestinationPath ".\release\AIPrompt-win.zip" -Force
