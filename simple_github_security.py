#!/usr/bin/env python3
"""
Simple GitHub Security Issues Loader

A simplified version that fetches security information using GitHub's REST API
through PyGithub with correct method calls.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from github import Github, GithubException


class SimpleGitHubSecurityLoader:
    """Load security issues from GitHub repositories using REST API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize with GitHub token."""
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable.")

        try:
            # Use modern auth method
            try:
                from github import Auth

                auth = Auth.Token(self.token)
                self.github = Github(auth=auth)
            except ImportError:
                # Fallback for older versions
                self.github = Github(self.token)

            # Test authentication
            self.user = self.github.get_user()
            print(f"✅ Authenticated as: {self.user.login}")

            # Setup for direct API calls
            self.headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }

        except GithubException as e:
            raise ValueError(f"Failed to authenticate with GitHub: {e}")

    def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """Get basic repository information."""
        try:
            repo = self.github.get_repo(repo_name)
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "size": repo.size,
                "stargazers_count": repo.stargazers_count,
                "language": repo.language,
                "has_issues": repo.has_issues,
                "security_and_analysis": self._get_security_features(repo_name),
            }
        except GithubException as e:
            print(f"❌ Error fetching repository info: {e}")
            return {}

    def _get_security_features(self, repo_name: str) -> Dict[str, Any]:
        """Get security features status using direct API call."""
        try:
            url = f"https://api.github.com/repos/{repo_name}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                security_analysis = data.get("security_and_analysis", {})
                return {
                    "advanced_security": security_analysis.get("advanced_security", {}).get(
                        "status", "unknown"
                    ),
                    "secret_scanning": security_analysis.get("secret_scanning", {}).get(
                        "status", "unknown"
                    ),
                    "secret_scanning_push_protection": security_analysis.get(
                        "secret_scanning_push_protection", {}
                    ).get("status", "unknown"),
                    "dependabot_security_updates": security_analysis.get(
                        "dependabot_security_updates", {}
                    ).get("status", "unknown"),
                }
        except Exception as e:
            print(f"⚠️  Could not fetch security features: {e}")
        return {}

    def get_code_scanning_alerts(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get code scanning alerts using direct API call."""
        try:
            url = f"https://api.github.com/repos/{repo_name}/code-scanning/alerts"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                alerts = response.json()
                print(f"✅ Found {len(alerts)} code scanning alerts")
                return alerts
            elif response.status_code == 404:
                print("ℹ️  Code scanning not enabled or no alerts found")
                return []
            else:
                print(f"⚠️  Code scanning alerts: HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error fetching code scanning alerts: {e}")
            return []

    def get_secret_scanning_alerts(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get secret scanning alerts using direct API call."""
        try:
            url = f"https://api.github.com/repos/{repo_name}/secret-scanning/alerts"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                alerts = response.json()
                print(f"✅ Found {len(alerts)} secret scanning alerts")
                return alerts
            elif response.status_code == 404:
                print("ℹ️  Secret scanning not enabled or no alerts found")
                return []
            else:
                print(f"⚠️  Secret scanning alerts: HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error fetching secret scanning alerts: {e}")
            return []

    def get_dependabot_alerts(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get Dependabot alerts using direct API call."""
        try:
            url = f"https://api.github.com/repos/{repo_name}/dependabot/alerts"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                alerts = response.json()
                print(f"✅ Found {len(alerts)} Dependabot alerts")
                return alerts
            elif response.status_code == 404:
                print("ℹ️  Dependabot not enabled or no alerts found")
                return []
            else:
                print(f"⚠️  Dependabot alerts: HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error fetching Dependabot alerts: {e}")
            return []

    def get_vulnerability_alerts(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get vulnerability alerts using PyGithub."""
        try:
            repo = self.github.get_repo(repo_name)
            alerts = []

            # Get vulnerability alerts if available
            try:
                vuln_alerts = repo.get_vulnerability_alert()
                if vuln_alerts:
                    alerts.append(
                        {
                            "type": "vulnerability_alert",
                            "enabled": True,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            except:
                pass  # Vulnerability alerts not available or not enabled

            return alerts

        except GithubException as e:
            print(f"❌ Error fetching vulnerability alerts: {e}")
            return []

    def get_all_security_data(self, repo_name: str) -> Dict[str, Any]:
        """Get comprehensive security data for a repository."""
        print(f"🔍 Fetching security data for {repo_name}...")

        # Get repository information
        repo_info = self.get_repository_info(repo_name)

        # Get security alerts
        code_scanning = self.get_code_scanning_alerts(repo_name)
        secret_scanning = self.get_secret_scanning_alerts(repo_name)
        dependabot = self.get_dependabot_alerts(repo_name)
        vulnerability = self.get_vulnerability_alerts(repo_name)

        security_data = {
            "repository": repo_name,
            "timestamp": datetime.now().isoformat(),
            "repository_info": repo_info,
            "security_alerts": {
                "code_scanning": code_scanning,
                "secret_scanning": secret_scanning,
                "dependabot": dependabot,
                "vulnerability_alerts": vulnerability,
            },
            "summary": {
                "total_code_scanning_alerts": len(code_scanning),
                "total_secret_scanning_alerts": len(secret_scanning),
                "total_dependabot_alerts": len(dependabot),
                "total_vulnerability_alerts": len(vulnerability),
                "security_features": repo_info.get("security_and_analysis", {}),
            },
        }

        # Print summary
        print(f"\n📊 Security Summary for {repo_name}:")
        print(
            f"   - Code Scanning Alerts: {security_data['summary']['total_code_scanning_alerts']}"
        )
        print(
            f"   - Secret Scanning Alerts: {security_data['summary']['total_secret_scanning_alerts']}"
        )
        print(f"   - Dependabot Alerts: {security_data['summary']['total_dependabot_alerts']}")
        print(
            f"   - Vulnerability Alerts: {security_data['summary']['total_vulnerability_alerts']}"
        )

        return security_data

    def save_to_file(self, data: Dict[str, Any], filename: str = "security_data.json"):
        """Save security data to a JSON file."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Security data saved to {filename}")


def main():
    """Main function."""
    try:
        # Initialize loader
        loader = SimpleGitHubSecurityLoader()

        # Get security data for DinoAir repository
        repo_name = "dinoopitstudios/DinoAir"
        security_data = loader.get_all_security_data(repo_name)

        # Save to file
        loader.save_to_file(security_data, "dinoair_security_data.json")

        return security_data

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
