import os
import sys
import json
import shutil
import subprocess
import requests
from datetime import datetime
from urllib.parse import urljoin

VERSION_FILE = "version.json"
CHANGELOG_FILE = "CHANGELOG.md"
ARCHIVE_DIR = "archive"
RELEASE_DIR = "release"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_USERNAME = "CWade3051"
GITHUB_REPO = "AIPrompt"

def load_version():
    """Load current version info"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return json.load(f)
    return {"version": "1.0.0", "last_updated": None}

def save_version(version_info):
    """Save version info"""
    with open(VERSION_FILE, 'w') as f:
        json.dump(version_info, f, indent=2)

def increment_version(version_str, increment_type='patch'):
    """Increment version number"""
    major, minor, patch = map(int, version_str.split('.'))
    if increment_type == 'major':
        return f"{major + 1}.0.0"
    elif increment_type == 'minor':
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def update_changelog(version, changes):
    """Update changelog with new version info"""
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"\n## [{version}] - {today}\n\n"
    
    if isinstance(changes, str):
        new_entry += f"- {changes}\n"
    elif isinstance(changes, list):
        for change in changes:
            new_entry += f"- {change}\n"
    
    if os.path.exists(CHANGELOG_FILE):
        with open(CHANGELOG_FILE, 'r') as f:
            content = f.read()
    else:
        content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n"
    
    # Insert new entry after header
    header_end = content.find('\n\n')
    if header_end == -1:
        header_end = len(content)
    content = content[:header_end + 2] + new_entry + content[header_end + 2:]
    
    with open(CHANGELOG_FILE, 'w') as f:
        f.write(content)

def archive_current_version():
    """Archive current version of code and release files"""
    version_info = load_version()
    current_version = version_info['version']
    
    # Create archive directory if it doesn't exist
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Archive source files
    archive_dir = os.path.join(ARCHIVE_DIR, f"v{current_version}")
    os.makedirs(archive_dir, exist_ok=True)
    
    # Copy source files
    files_to_archive = [
        'AIPrompt.py',
        'AIPrompt.spec',
        'build-mac.sh',
        'build-win.ps1',
        'requirements.txt',
        'README.md',
        'CHANGELOG.md',
        'version.json'
    ]
    
    for file in files_to_archive:
        if os.path.exists(file):
            shutil.copy2(file, archive_dir)
    
    # Archive release files if they exist
    release_files = {
        'win': 'AIPrompt-win.exe',
        'mac': 'AIPrompt-mac.zip'
    }
    
    for platform, file in release_files.items():
        src = os.path.join(RELEASE_DIR, file)
        if os.path.exists(src):
            shutil.copy2(src, archive_dir)
            print(f"Archived {file}")

def build_new_version():
    """Build new version for the current platform"""
    # Create release directory
    os.makedirs(RELEASE_DIR, exist_ok=True)
    
    # Build for current platform only
    if sys.platform.startswith('win'):
        print("\nBuilding Windows version...")
        subprocess.run(['powershell', '-File', 'build-win.ps1'], check=True)
        print("\nWindows build complete! The executable can be found in the release directory.")
        print("NOTE: To build for macOS, run the build-mac.sh script on a Mac system.")
    else:
        print("\nBuilding macOS version...")
        subprocess.run(['./build-mac.sh'], check=True)
        print("\nmacOS build complete! The zipped app can be found in the release directory.")
        print("NOTE: To build for Windows, run the build-win.ps1 script on a Windows system.")

def update_readme(version):
    """Update README.md with release information"""
    if not os.path.exists('README.md'):
        return
    
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Check if release section exists
    release_section = "\n## Releases\n\n"
    if release_section not in content:
        content += release_section
    
    # Update release information
    release_info = f"""Latest release: v{version}

### Download Latest Release
- [Windows (AIPrompt-win.exe)](https://github.com/CWade3051/AIPrompt/releases/latest/download/AIPrompt-win.exe)
- [macOS (AIPrompt-mac.zip)](https://github.com/CWade3051/AIPrompt/releases/latest/download/AIPrompt-mac.zip)

For older releases, visit the [GitHub releases page](https://github.com/CWade3051/AIPrompt/releases).
"""
    
    # Replace or add release information
    if "Latest release:" in content:
        # Replace existing release info
        start = content.find("Latest release:")
        end = content.find("\n\n", start)
        if end == -1:
            end = len(content)
        content = content[:start] + release_info + content[end:]
    else:
        # Add release info after the release section
        content = content.replace(release_section, release_section + release_info)
    
    with open('README.md', 'w') as f:
        f.write(content)

def get_github_token():
    """Get GitHub token from environment variable"""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set it with: export GITHUB_TOKEN=your_github_token")
        sys.exit(1)
    return token

def create_github_release(version, changes, token):
    """Create a new GitHub release"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get the latest changes from changelog
    with open(CHANGELOG_FILE, 'r') as f:
        content = f.read()
        # Find the section for this version
        version_section = f"## [{version}]"
        start = content.find(version_section)
        if start != -1:
            end = content.find("##", start + len(version_section))
            if end == -1:
                end = len(content)
            release_notes = content[start:end].strip()
        else:
            release_notes = f"Release v{version}\n\n{changes}"
    
    # Create release
    release_data = {
        "tag_name": f"v{version}",
        "name": f"Release v{version}",
        "body": release_notes,
        "draft": False,
        "prerelease": False
    }
    
    url = urljoin(GITHUB_API_BASE, f"/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/releases")
    print(f"\nCreating release at: {url}")
    print(f"Release data: {json.dumps(release_data, indent=2)}")
    
    response = requests.post(url, headers=headers, json=release_data)
    print(f"Release creation response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    if response.status_code != 201:
        print(f"Error creating GitHub release: {response.text}")
        return None
    
    release_info = response.json()
    return release_info

def upload_release_assets(release_info, token):
    """Upload release assets to GitHub"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/octet-stream"
    }
    
    upload_url = release_info['upload_url'].replace("{?name,label}", "")
    print(f"\nUpload URL: {upload_url}")
    
    # Upload Windows executable
    win_exe = os.path.join(RELEASE_DIR, "AIPrompt-win.exe")
    if os.path.exists(win_exe):
        print(f"\nUploading Windows executable: {win_exe}")
        with open(win_exe, 'rb') as f:
            response = requests.post(
                f"{upload_url}?name=AIPrompt-win.exe",
                headers=headers,
                data=f
            )
            print(f"Windows upload status: {response.status_code}")
            print(f"Response: {response.text}")
            if response.status_code != 201:
                print(f"Error uploading Windows executable: {response.text}")
    else:
        print(f"Windows executable not found at: {win_exe}")
    
    # Upload macOS zip
    mac_zip = os.path.join(RELEASE_DIR, "AIPrompt-mac.zip")
    if os.path.exists(mac_zip):
        print(f"\nUploading macOS zip: {mac_zip}")
        with open(mac_zip, 'rb') as f:
            response = requests.post(
                f"{upload_url}?name=AIPrompt-mac.zip",
                headers=headers,
                data=f
            )
            print(f"macOS upload status: {response.status_code}")
            print(f"Response: {response.text}")
            if response.status_code != 201:
                print(f"Error uploading macOS zip: {response.text}")
    else:
        print(f"macOS zip not found at: {mac_zip}")

def push_to_github():
    """Push changes to GitHub"""
    try:
        # Add all changes
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Commit changes
        version_info = load_version()
        commit_message = f"Release v{version_info['version']}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        # Push to GitHub
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("Successfully pushed changes to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to GitHub: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python version.py [major|minor|patch] 'change description' or ['change1', 'change2', ...]")
        sys.exit(1)
    
    increment_type = sys.argv[1].lower()
    if increment_type not in ['major', 'minor', 'patch']:
        print("Version increment must be 'major', 'minor', or 'patch'")
        sys.exit(1)
    
    # Parse changes
    try:
        changes = json.loads(sys.argv[2])
    except json.JSONDecodeError:
        changes = sys.argv[2]
    
    print(f"\nUpdating version information...")
    
    # Load and update version
    version_info = load_version()
    new_version = increment_version(version_info['version'], increment_type)
    
    print(f"Creating archive of current version {version_info['version']}...")
    # Archive current version
    archive_current_version()
    
    # Update version info
    version_info['version'] = new_version
    version_info['last_updated'] = datetime.now().isoformat()
    save_version(version_info)
    print(f"Version updated to {new_version}")
    
    print("\nUpdating changelog...")
    # Update changelog
    update_changelog(new_version, changes)
    
    # Update README with release information
    print("\nUpdating README with release information...")
    update_readme(new_version)
    
    # Build new version
    build_new_version()
    
    print(f"\nVersion {new_version} update complete!")
    
    # Get GitHub token
    token = get_github_token()
    
    # Create GitHub release
    print("\nCreating GitHub release...")
    release_info = create_github_release(new_version, changes, token)
    if release_info:
        print("Successfully created GitHub release")
        
        # Upload release assets
        print("\nUploading release assets...")
        upload_release_assets(release_info, token)
        print("Successfully uploaded release assets")
        
        # Push changes to GitHub
        print("\nPushing changes to GitHub...")
        push_to_github()
        
        print(f"\nRelease v{new_version} is now complete!")
        print("\nNext steps:")
        print("1. Build for the other platform if needed (run build script directly)")
        print("2. The release will be automatically updated with the new build")
    else:
        print("\nFailed to create GitHub release. Please create it manually:")
        print("1. Go to https://github.com/CWade3051/AIPrompt/releases/new")
        print("2. Tag version: v" + new_version)
        print("3. Title: Release v" + new_version)
        print("4. Description: Copy the latest changes from CHANGELOG.md")
        print("5. Upload the following files from the release directory:")
        print("   - AIPrompt-win.exe (Windows)")
        print("   - AIPrompt-mac.zip (macOS)")
        print("6. Publish the release")

if __name__ == "__main__":
    main() 