rm -rf build dist                          
pyinstaller AIPrompt.spec
zip -r AIPrompt-mac.zip ./dist/AIPrompt.app