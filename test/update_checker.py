#!/usr/bin/env python3

import subprocess
import sys
import os
from typing import List, Dict, Tuple
import json
from datetime import datetime

class UpdateChecker:
    def __init__(self):
        self.updates_available: Dict[str, List[str]] = {}
        self.commands = {
            'brew': '/opt/homebrew/bin/brew',
            'pip3': 'pip3',
            'npm': 'npm',
            'gem': 'gem',
            'mas': 'mas',
            'softwareupdate': '/usr/sbin/softwareupdate'
        }

    def _run_command(self, command: List[str], use_sudo: bool = False) -> Tuple[str, str, int]:
        try:
            if use_sudo:
                command = ['sudo'] + command
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            return stdout, stderr, process.returncode
        except Exception as e:
            return "", str(e), 1

    def _check_command_exists(self, command: str) -> bool:
        if os.path.isfile(command):
            return True
        try:
            subprocess.run(['which', command], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
            return True
        except:
            return False

    def check_brew_updates(self):
        if not self._check_command_exists(self.commands['brew']):
            print("Homebrew not installed, skipping brew updates check...")
            return

        print("Checking Homebrew updates...")
        self.updates_available['brew'] = []
        
        # Update Homebrew itself
        stdout, _, _ = self._run_command([self.commands['brew'], 'update'])
        
        # Check outdated packages
        stdout, _, _ = self._run_command([self.commands['brew'], 'outdated'])
        if stdout.strip():
            self.updates_available['brew'].extend(stdout.strip().split('\n'))

    def check_pip_updates(self):
        if not self._check_command_exists(self.commands['pip3']):
            print("pip3 not installed, skipping Python package updates check...")
            return

        print("Checking Python package updates...")
        self.updates_available['pip'] = []
        
        stdout, _, _ = self._run_command([
            self.commands['pip3'], 'list', '--outdated', '--format=json'
        ])
        
        try:
            outdated = json.loads(stdout)
            for package in outdated:
                self.updates_available['pip'].append(
                    f"{package['name']} ({package['version']} → {package['latest_version']})"
                )
        except:
            pass

    def check_npm_updates(self):
        if not self._check_command_exists(self.commands['npm']):
            print("npm not installed, skipping Node.js package updates check...")
            return

        print("Checking npm global package updates...")
        self.updates_available['npm'] = []
        
        stdout, _, _ = self._run_command([self.commands['npm'], 'outdated', '-g'])
        if stdout.strip():
            for line in stdout.strip().split('\n')[1:]:  # Skip header line
                self.updates_available['npm'].append(line.strip())

    def check_gem_updates(self):
        if not self._check_command_exists(self.commands['gem']):
            print("gem not installed, skipping Ruby gems updates check...")
            return

        print("Checking Ruby gems updates...")
        self.updates_available['gem'] = []
        
        stdout, _, _ = self._run_command([self.commands['gem'], 'outdated'])
        if stdout.strip():
            self.updates_available['gem'].extend(stdout.strip().split('\n'))

    def check_mas_updates(self):
        if not self._check_command_exists(self.commands['mas']):
            print("mas not installed, skipping Mac App Store updates check...")
            return

        print("Checking Mac App Store updates...")
        self.updates_available['mas'] = []
        
        stdout, _, _ = self._run_command([self.commands['mas'], 'outdated'])
        if stdout.strip():
            self.updates_available['mas'].extend(stdout.strip().split('\n'))

    def check_system_updates(self):
        print("Checking macOS system updates...")
        self.updates_available['system'] = []
        
        stdout, _, _ = self._run_command([
            self.commands['softwareupdate'], '--list'
        ])
        
        if 'No new software available.' not in stdout:
            for line in stdout.split('\n'):
                if line.strip().startswith('*'):
                    self.updates_available['system'].append(line.strip())

    def perform_all_checks(self):
        self.check_brew_updates()
        self.check_pip_updates()
        self.check_npm_updates()
        self.check_gem_updates()
        self.check_mas_updates()
        self.check_system_updates()

    def display_updates(self):
        print("\nUpdate Summary:")
        print("=" * 50)
        
        total_updates = 0
        for manager, updates in self.updates_available.items():
            if updates:
                print(f"\n{manager.upper()} Updates Available:")
                for update in updates:
                    print(f"  • {update}")
                total_updates += len(updates)
        
        if total_updates == 0:
            print("\nAll software is up to date! 🎉")
            return False
        
        print(f"\nTotal updates available: {total_updates}")
        return True

    def perform_updates(self):
        print("\nPerforming updates...")
        print("=" * 50)

        if 'brew' in self.updates_available and self.updates_available['brew']:
            print("\nUpdating Homebrew packages...")
            self._run_command([self.commands['brew'], 'upgrade'])

        if 'pip' in self.updates_available and self.updates_available['pip']:
            print("\nUpdating Python packages...")
            for package in self.updates_available['pip']:
                package_name = package.split()[0]
                self._run_command([
                    self.commands['pip3'], 'install', '--upgrade', package_name
                ])

        if 'npm' in self.updates_available and self.updates_available['npm']:
            print("\nUpdating npm global packages...")
            self._run_command([self.commands['npm'], 'update', '-g'])

        if 'gem' in self.updates_available and self.updates_available['gem']:
            print("\nUpdating Ruby gems...")
            # First try without sudo
            stdout, stderr, returncode = self._run_command([self.commands['gem'], 'update'])
            
            # Check for permission error
            if returncode != 0 and "permissions" in stderr.lower():
                print("Permission error detected, retrying with sudo...")
                self._run_command([self.commands['gem'], 'update'], use_sudo=True)
            elif returncode != 0:
                print(f"Error updating gems: {stderr}")

        if 'mas' in self.updates_available and self.updates_available['mas']:
            print("\nUpdating Mac App Store apps...")
            self._run_command([self.commands['mas'], 'upgrade'])

        if 'system' in self.updates_available and self.updates_available['system']:
            print("\nInstalling system updates...")
            self._run_command([
                self.commands['softwareupdate'], '--install', '--all'
            ], use_sudo=True)  # Always use sudo for system updates

def main():
    print(f"Starting software update check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    checker = UpdateChecker()
    checker.perform_all_checks()
    
    if checker.display_updates():
        response = input("\nWould you like to install all available updates? (y/N): ")
        if response.lower() == 'y':
            checker.perform_updates()
            print("\nAll updates have been completed! 🎉")
        else:
            print("\nUpdate installation cancelled.")
    
    print("\nScript completed!")

if __name__ == "__main__":
    main() 