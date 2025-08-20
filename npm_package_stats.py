#!/usr/bin/env python3
"""
NPM Package Statistics for Plone Organizations

Queries NPM registry for packages published by Plone organizations
to analyze their contribution to the npm ecosystem.
"""

import requests
import json
import time
from datetime import datetime
import pandas as pd
from pathlib import Path
import re
from collections import defaultdict


class NPMPackageAnalyzer:
    """Analyzer for NPM packages published by organizations."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'plone-github-stats/1.0.0 (Package Analysis Tool)'
        })
        self.rate_limit_delay = 0.1  # 100ms between requests
        
    def search_packages_by_author(self, author):
        """Search for packages by author/organization."""
        packages = []
        
        try:
            # NPM search API
            search_url = f"https://registry.npmjs.org/-/v1/search"
            params = {
                'text': f'author:{author}',
                'size': 250,  # Maximum allowed
                'from': 0
            }
            
            print(f"  🔍 Searching NPM for packages by '{author}'...")
            
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for package in data.get('objects', []):
                pkg_info = package.get('package', {})
                packages.append({
                    'name': pkg_info.get('name'),
                    'version': pkg_info.get('version'),
                    'description': pkg_info.get('description', ''),
                    'author': pkg_info.get('author', {}),
                    'maintainers': pkg_info.get('maintainers', []),
                    'keywords': pkg_info.get('keywords', []),
                    'date': pkg_info.get('date'),
                    'npm_url': f"https://www.npmjs.com/package/{pkg_info.get('name')}"
                })
            
            time.sleep(self.rate_limit_delay)
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Error searching for {author}: {e}")
        
        return packages
    
    def get_package_details(self, package_name):
        """Get detailed information about a specific package."""
        try:
            detail_url = f"https://registry.npmjs.org/{package_name}"
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Get latest version info
            latest_version = data.get('dist-tags', {}).get('latest', '')
            versions = data.get('versions', {})
            
            # Calculate download stats (we'll use a proxy endpoint)
            downloads = self.get_download_stats(package_name)
            
            # Repository info
            repository = data.get('repository', {})
            if isinstance(repository, dict):
                repo_url = repository.get('url', '')
            else:
                repo_url = str(repository) if repository else ''
            
            # Clean up repository URL
            if repo_url.startswith('git+'):
                repo_url = repo_url[4:]
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            package_info = {
                'name': package_name,
                'latest_version': latest_version,
                'description': data.get('description', ''),
                'homepage': data.get('homepage', ''),
                'repository_url': repo_url,
                'license': data.get('license', ''),
                'keywords': data.get('keywords', []),
                'author': data.get('author', {}),
                'maintainers': data.get('maintainers', []),
                'created': data.get('time', {}).get('created', ''),
                'modified': data.get('time', {}).get('modified', ''),
                'version_count': len(versions),
                'weekly_downloads': downloads.get('weekly', 0),
                'monthly_downloads': downloads.get('monthly', 0),
                'npm_url': f"https://www.npmjs.com/package/{package_name}"
            }
            
            time.sleep(self.rate_limit_delay)
            return package_info
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Error getting details for {package_name}: {e}")
            return None
    
    def get_download_stats(self, package_name):
        """Get download statistics for a package."""
        downloads = {'weekly': 0, 'monthly': 0}
        
        try:
            # NPM download stats API
            stats_url = f"https://api.npmjs.org/downloads/point/last-week/{package_name}"
            response = self.session.get(stats_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                downloads['weekly'] = data.get('downloads', 0)
            
            # Monthly stats
            stats_url = f"https://api.npmjs.org/downloads/point/last-month/{package_name}"
            response = self.session.get(stats_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                downloads['monthly'] = data.get('downloads', 0)
            
            time.sleep(self.rate_limit_delay)
            
        except requests.exceptions.RequestException:
            # Download stats are optional, don't fail on this
            pass
        
        return downloads
    
    def analyze_organization_packages(self, org_name, search_terms=None):
        """Analyze all packages for an organization."""
        print(f"\n📦 Analyzing NPM packages for: {org_name}")
        print("=" * 50)
        
        packages = []
        
        # Search terms to try
        if search_terms is None:
            search_terms = [org_name, f"@{org_name}"]
        
        # Try different search approaches
        for term in search_terms:
            found_packages = self.search_packages_by_author(term)
            packages.extend(found_packages)
        
        # Also search for scoped packages
        try:
            scoped_url = f"https://registry.npmjs.org/-/org/{org_name}/package"
            response = self.session.get(scoped_url, timeout=30)
            if response.status_code == 200:
                scoped_packages = response.json()
                for pkg_name in scoped_packages:
                    packages.append({'name': pkg_name})
        except:
            pass
        
        # Remove duplicates and get detailed info
        unique_packages = {}
        for pkg in packages:
            name = pkg.get('name')
            if name and name not in unique_packages:
                unique_packages[name] = pkg
        
        detailed_packages = []
        
        print(f"  📊 Found {len(unique_packages)} unique packages")
        
        for i, (pkg_name, pkg_basic) in enumerate(unique_packages.items(), 1):
            print(f"  📋 Getting details for package {i}/{len(unique_packages)}: {pkg_name}")
            
            detailed_info = self.get_package_details(pkg_name)
            if detailed_info:
                detailed_packages.append(detailed_info)
        
        return detailed_packages
    
    def generate_organization_report(self, org_name, packages):
        """Generate a report for an organization's packages."""
        if not packages:
            return f"# {org_name} NPM Packages\n\nNo packages found.\n"
        
        report = []
        report.append(f"# {org_name} NPM Packages")
        report.append("")
        report.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total packages found: {len(packages)}")
        report.append("")
        
        # Summary statistics
        total_downloads_weekly = sum(pkg.get('weekly_downloads', 0) for pkg in packages)
        total_downloads_monthly = sum(pkg.get('monthly_downloads', 0) for pkg in packages)
        total_versions = sum(pkg.get('version_count', 0) for pkg in packages)
        
        report.append("## Summary Statistics")
        report.append("")
        report.append(f"- **Total packages**: {len(packages)}")
        report.append(f"- **Total weekly downloads**: {total_downloads_weekly:,}")
        report.append(f"- **Total monthly downloads**: {total_downloads_monthly:,}")
        report.append(f"- **Total versions published**: {total_versions}")
        report.append("")
        
        # Top packages by downloads
        sorted_packages = sorted(packages, key=lambda x: x.get('weekly_downloads', 0), reverse=True)
        
        report.append("## Top Packages by Weekly Downloads")
        report.append("")
        report.append("| Package | Weekly Downloads | Monthly Downloads | Latest Version |")
        report.append("|---------|------------------|-------------------|----------------|")
        
        for pkg in sorted_packages[:10]:  # Top 10
            name = pkg.get('name', '')
            weekly = pkg.get('weekly_downloads', 0)
            monthly = pkg.get('monthly_downloads', 0)
            version = pkg.get('latest_version', '')
            
            report.append(f"| [{name}]({pkg.get('npm_url', '')}) | {weekly:,} | {monthly:,} | {version} |")
        
        report.append("")
        
        # All packages
        report.append("## All Packages")
        report.append("")
        
        for pkg in sorted_packages:
            name = pkg.get('name', '')
            description = pkg.get('description', 'No description')
            version = pkg.get('latest_version', '')
            weekly = pkg.get('weekly_downloads', 0)
            repo_url = pkg.get('repository_url', '')
            
            report.append(f"### {name}")
            report.append("")
            report.append(f"- **Description**: {description}")
            report.append(f"- **Latest Version**: {version}")
            report.append(f"- **Weekly Downloads**: {weekly:,}")
            if repo_url:
                report.append(f"- **Repository**: {repo_url}")
            report.append(f"- **NPM**: {pkg.get('npm_url', '')}")
            report.append("")
        
            return "\n".join(report)


def load_npm_mapping(mapping_file="npm_mapping.txt"):
    """Load NPM organization mapping from file."""
    organizations = {}
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    org_name, search_terms = line.split(':', 1)
                    organizations[org_name.strip()] = [term.strip() for term in search_terms.split(',')]
        
        print(f"  📋 Loaded {len(organizations)} organizations from {mapping_file}")
        
    except FileNotFoundError:
        print(f"  ❌ Warning: {mapping_file} not found, using default mapping")
        # Fallback to hardcoded mapping
        organizations = {
            'kitconcept': ['kitconcept', '@kitconcept'],
            'redturtle': ['redturtle', '@redturtle', 'redturtle-it'],
            'codesyntax': ['codesyntax', '@codesyntax']
        }
    
    return organizations


def main():
    """Main execution function."""
    print("NPM Package Statistics for Plone Organizations")
    print("=" * 60)
    
    analyzer = NPMPackageAnalyzer()
    
    # Load organizations from mapping file
    organizations = load_npm_mapping()
    
    all_results = {}
    
    for org_name, search_terms in organizations.items():
        packages = analyzer.analyze_organization_packages(org_name, search_terms)
        all_results[org_name] = packages
        
        # Generate individual report
        report = analyzer.generate_organization_report(org_name, packages)
        
        # Save report
        report_filename = f"npm-packages-{org_name}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"  ✅ Saved report: {report_filename}")
        
        # Save CSV data
        if packages:
            df = pd.DataFrame(packages)
            csv_filename = f"npm-packages-{org_name}.csv"
            df.to_csv(csv_filename, index=False)
            print(f"  ✅ Saved CSV: {csv_filename}")
    
    # Generate combined report
    combined_report = []
    combined_report.append("# NPM Packages - Plone Organizations")
    combined_report.append("")
    combined_report.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    combined_report.append("")
    
    for org_name, packages in all_results.items():
        total_weekly = sum(pkg.get('weekly_downloads', 0) for pkg in packages)
        combined_report.append(f"- **{org_name}**: {len(packages)} packages, {total_weekly:,} weekly downloads")
    
    combined_report.append("")
    combined_report.append("## Details")
    combined_report.append("")
    combined_report.append("See individual organization reports:")
    combined_report.append("")
    
    for org_name in all_results.keys():
        combined_report.append(f"- [{org_name}](npm-packages-{org_name}.md)")
    
    # Save combined report
    combined_filename = "npm-packages-summary.md"
    with open(combined_filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(combined_report))
    
    print(f"\n✅ Analysis complete!")
    print(f"   Generated reports: {combined_filename}")
    for org_name in all_results.keys():
        print(f"   - npm-packages-{org_name}.md")
        print(f"   - npm-packages-{org_name}.csv")
    
    return 0


if __name__ == "__main__":
    exit(main())