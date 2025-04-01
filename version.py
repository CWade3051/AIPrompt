import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

VERSION_FILE = "version.json"
CHANGELOG_FILE = "CHANGELOG.md"
ARCHIVE_DIR = "archive"
RELEASE_DIR = "release"

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
    """Archive current version of code"""
    version_info = load_version()
    current_version = version_info['version']
    
    # Create archive directory if it doesn't exist
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Archive source files
    archive_dir = os.path.join(ARCHIVE_DIR, f"v{current_version}")
    os.makedirs(archive_dir, exist_ok=True)
    
    # Copy relevant files
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
    
    # Build new version
    build_new_version()
    
    print(f"\nVersion {new_version} update complete!")
    print("\nNext steps:")
    print("1. Review the changes in CHANGELOG.md")
    print("2. Build for the other platform if needed (run build script directly)")
    print("3. Commit and push all changes to the repository")
    print("4. Create a new release on GitHub with the built executables")

if __name__ == "__main__":
    main() 