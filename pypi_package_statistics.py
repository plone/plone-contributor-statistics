#!/usr/bin/env python3
"""
Refactored PyPI Package Statistics for Plone Organizations

This version first downloads metadata for all plone.* and collective.* packages,
then processes the data to categorize by organization.
"""

import requests
import json
import time
from datetime import datetime
import pandas as pd
from pathlib import Path
import re
from collections import defaultdict
from urllib.parse import urlparse
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os


class PyPIPackageDownloader:
    """Downloads and caches package metadata from PyPI."""
    
    def __init__(self, cache_dir="pypi_cache"):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'plone-github-stats/2.0.0 (Refactored PyPI Package Analysis Tool)'
        })
        self.rate_limit_delay = 0.05  # 50ms between requests
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_all_package_names(self, prefixes):
        """Get all package names from PyPI simple index that match given prefixes."""
        packages = set()
        
        try:
            print("📥 Fetching PyPI simple index...")
            response = self.session.get("https://pypi.org/simple/", timeout=60)
            response.raise_for_status()
            
            content = response.text
            
            # Extract all package names that match our prefixes
            for prefix in prefixes:
                # Convert prefix to URL format (dots become hyphens)
                url_prefix = prefix.replace('.', '-')
                
                # Use regex to find package links starting with the prefix
                pattern = rf'<a href="/simple/({re.escape(url_prefix)}[^/"]*)/[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                for url_name, display_name in matches:
                    # Convert URL name back to package name (hyphens become dots where appropriate)
                    if url_prefix == 'plone-':
                        package_name = url_name.replace('-', '.', 1)  # Only first hyphen becomes dot
                    else:  # collective-
                        package_name = url_name.replace('-', '.', 1)  # Only first hyphen becomes dot
                    
                    packages.add(package_name)
                    
            print(f"📋 Found {len(packages)} packages matching prefixes: {prefixes}")
            time.sleep(self.rate_limit_delay)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching simple index: {e}")
        
        return sorted(list(packages))
    
    def download_package_metadata(self, package_name):
        """Download metadata for a single package."""
        cache_file = self.cache_dir / f"{package_name.replace('/', '_')}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # Cache file is corrupted, will re-download
                pass
        
        try:
            detail_url = f"https://pypi.org/pypi/{package_name}/json"
            response = self.session.get(detail_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache the result
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                time.sleep(self.rate_limit_delay)
                return data
            else:
                print(f"⚠️  HTTP {response.status_code} for {package_name}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {package_name}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error processing {package_name}: {e}")
            return None
    
    def download_all_metadata(self, package_names, max_workers=10):
        """Download metadata for all packages using parallel processing."""
        print(f"\n📥 Downloading metadata for {len(package_names)} packages...")
        
        metadata = {}
        total = len(package_names)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_package = {
                executor.submit(self.download_package_metadata, pkg): pkg 
                for pkg in package_names
            }
            
            # Process completed downloads
            for future in as_completed(future_to_package):
                package_name = future_to_package[future]
                completed += 1
                
                if completed % 50 == 0 or completed == total:
                    print(f"  📊 Progress: {completed}/{total} ({completed/total*100:.1f}%)")
                
                try:
                    result = future.result()
                    if result:
                        metadata[package_name] = result
                except Exception as e:
                    print(f"❌ Failed to process {package_name}: {e}")
        
        print(f"✅ Successfully downloaded metadata for {len(metadata)} packages")
        return metadata


class PyPIPackageAnalyzer:
    """Analyzes downloaded package metadata."""
    
    def __init__(self, organization_mapping_file="organisation_mapping.txt"):
        self.organization_mapping = self.load_organization_mapping(organization_mapping_file)
    
    def load_organization_mapping(self, mapping_file):
        """Load organization mapping from file."""
        org_mapping = {}
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        org_name, contributors = line.split(':', 1)
                        # Create mapping of contributor names to organization
                        contributor_list = [name.strip().lower() for name in contributors.split(',')]
                        org_mapping[org_name.strip().lower()] = contributor_list
                        
                        # Also create reverse mapping (contributor -> org)
                        for contributor in contributor_list:
                            org_mapping[contributor] = org_name.strip().lower()
            
            print(f"📋 Loaded organization mapping for {len([k for k in org_mapping.keys() if ':' not in str(k)])} contributors")
            
        except FileNotFoundError:
            print(f"⚠️  Organization mapping file not found: {mapping_file}")
        
        return org_mapping
    
    def truncate_description(self, description, max_length=500):
        """Truncate description for readability."""
        if not description:
            return ''
        
        # Remove HTML tags and excessive whitespace
        clean_desc = re.sub(r'<[^>]+>', '', str(description))
        clean_desc = ' '.join(clean_desc.split())
        
        if len(clean_desc) > max_length:
            return clean_desc[:max_length] + '...'
        return clean_desc
    
    def extract_github_url(self, info):
        """Extract GitHub URL from package info."""
        # Check various fields for GitHub URLs
        fields_to_check = [
            info.get('home_page', ''),
            str(info.get('project_urls', {}))
        ]
        
        for field in fields_to_check:
            if 'github.com' in field.lower():
                # Extract GitHub URL
                github_match = re.search(r'https://github\.com/[^\s/"]+/[^\s/"]+', field)
                if github_match:
                    return github_match.group(0)
        
        return ''
    
    def is_plone_related(self, info):
        """Determine if a package is Plone-related."""
        plone_indicators = [
            'plone', 'zope', 'cmf', 'collective', 'dexterity', 
            'archetypes', 'buildout', 'z3c', 'plonetheme'
        ]
        
        text_to_check = ' '.join([
            info.get('summary', '').lower(),
            info.get('description', '').lower()[:500],  # First 500 chars
            ' '.join(info.get('keywords', '').split()).lower(),
            ' '.join(info.get('classifiers', [])).lower()
        ])
        
        return any(indicator in text_to_check for indicator in plone_indicators)
    
    def determine_organization_from_package_info(self, info):
        """Determine organization from package info using organization mapping and enhanced patterns."""
        name = info.get('name', '').lower()
        author = (info.get('author') or '').lower()
        maintainer = (info.get('maintainer') or '').lower()
        home_page = (info.get('home_page') or '').lower()
        
        # Target organizations (focus on these four as requested)
        target_orgs = ['kitconcept', 'redturtle', 'codesyntax', 'starzel']
        
        # First, check organization mapping for individual contributors
        # Extract potential contributor names from author/maintainer fields
        potential_contributors = []
        
        # Split and clean author/maintainer names
        for field in [author, maintainer]:
            if field:
                # Handle various formats: "Name (Company)", "Name <email>", "Name, Name2"
                # Remove company info in parentheses and email addresses
                cleaned = re.sub(r'\([^)]*\)', '', field)  # Remove (Company)
                cleaned = re.sub(r'<[^>]*>', '', cleaned)  # Remove <email>
                cleaned = re.sub(r'gmbh|ltd|inc|corp|company', '', cleaned, flags=re.IGNORECASE)  # Remove company suffixes
                
                # Split by common separators and extract names
                names = re.split(r'[,;&\n]', cleaned)
                for n in names:
                    n = n.strip()
                    if n and len(n) > 2:  # Avoid single letters or very short strings
                        potential_contributors.append(n.lower())
        
        # Check if any contributor matches organization mapping
        for contrib in potential_contributors:
            if contrib in self.organization_mapping:
                mapped_org = self.organization_mapping[contrib]
                if mapped_org in target_orgs:
                    print(f"  🎯 Found contributor '{contrib}' -> {mapped_org} for package {name}")
                    return mapped_org
        
        # Enhanced organization mapping with author and company patterns
        # Priority: author patterns first, then name patterns
        org_indicators = [
            ('kitconcept', ['kitconcept'], ['kitconcept gmbh', 'kitconcept']),
            ('redturtle', ['redturtle'], ['redturtle technology', 'redturtle', 'redturtletechnology']),
            ('codesyntax', ['codesyntax'], ['codesyntax', 'mikel larreategi']),
            ('starzel', ['starzel'], ['starzel']),
            ('eeacms', ['eea.'], ['european environment', 'eea']),
            ('rohberg', ['rohberg'], ['rohberg', 'katja süss']),
            ('plone-foundation', ['plone.', 'products.cmf', 'products.plone'], ['plone foundation']),
            ('plone-collective', ['collective.'], ['plone collective', 'collective'])
        ]
        
        # Check author/maintainer/homepage fields for organization patterns
        for org, name_patterns, author_patterns in org_indicators:
            for pattern in author_patterns:
                if (pattern in author or 
                    pattern in maintainer or 
                    pattern in home_page):
                    return org
        
        # Then check package name patterns
        for org, name_patterns, author_patterns in org_indicators:
            for pattern in name_patterns:
                if name.startswith(pattern) or pattern in name:
                    return org
        
        return 'other'
    
    def process_package_metadata(self, package_name, metadata):
        """Process a single package's metadata into structured format."""
        try:
            info = metadata.get('info', {})
            
            # Get release information
            releases = metadata.get('releases', {})
            latest_version = info.get('version', '')
            
            # Calculate creation date from first release
            creation_date = ''
            if releases:
                # Get the oldest release date
                all_dates = []
                for version, release_info in releases.items():
                    if release_info:  # Some versions might be empty
                        for release in release_info:
                            upload_time = release.get('upload_time', '')
                            if upload_time:
                                all_dates.append(upload_time)
                
                if all_dates:
                    creation_date = min(all_dates)
            
            # Extract organization
            organization = self.determine_organization_from_package_info(info)
            
            package_info = {
                'name': package_name,
                'version': latest_version,
                'summary': info.get('summary', ''),
                'description': self.truncate_description(info.get('description', '')),
                'author': (info.get('author') or ''),
                'author_email': (info.get('author_email') or ''),
                'maintainer': (info.get('maintainer') or ''),
                'maintainer_email': (info.get('maintainer_email') or ''),
                'organization': organization,
                'home_page': (info.get('home_page') or ''),
                'project_urls': info.get('project_urls', {}),
                'license': (info.get('license') or ''),
                'keywords': (info.get('keywords') or ''),
                'classifiers': info.get('classifiers', []),
                'requires_python': (info.get('requires_python') or ''),
                'created': creation_date,
                'pypi_url': f"https://pypi.org/project/{package_name}/",
                'github_url': self.extract_github_url(info),
                'is_plone_related': self.is_plone_related(info)
            }
            
            return package_info
            
        except Exception as e:
            print(f"❌ Error processing metadata for {package_name}: {e}")
            return None
    
    def analyze_all_packages(self, all_metadata):
        """Analyze all downloaded package metadata."""
        print(f"\n🔍 Analyzing {len(all_metadata)} packages...")
        
        processed_packages = []
        failed = 0
        
        for package_name, metadata in all_metadata.items():
            result = self.process_package_metadata(package_name, metadata)
            if result:
                processed_packages.append(result)
            else:
                failed += 1
        
        print(f"✅ Successfully processed {len(processed_packages)} packages")
        if failed > 0:
            print(f"⚠️  Failed to process {failed} packages")
        
        return processed_packages
    
    def categorize_packages_by_organization(self, packages):
        """Categorize packages by organization."""
        organizations = defaultdict(list)
        
        for package in packages:
            if package:  # Skip None results
                org = package.get('organization', 'other')
                organizations[org].append(package)
        
        return organizations
    
    def generate_organization_report(self, org_name, packages):
        """Generate a report for an organization's packages."""
        if not packages:
            return f"# {org_name} PyPI Packages (Refactored)\n\nNo packages found.\n"
        
        report = []
        report.append(f"# {org_name} PyPI Packages (Refactored)")
        report.append("")
        report.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total packages found: {len(packages)}")
        report.append("")
        
        # Sort packages by name
        sorted_packages = sorted(packages, key=lambda x: x['name'])
        
        # Summary statistics
        plone_related = sum(1 for p in packages if p.get('is_plone_related', False))
        has_github = sum(1 for p in packages if p.get('github_url', ''))
        
        report.append("## Summary")
        report.append("")
        report.append(f"- **Total packages**: {len(packages)}")
        report.append(f"- **Plone-related packages**: {plone_related}")
        report.append(f"- **Packages with GitHub links**: {has_github}")
        report.append("")
        
        report.append("## Package List")
        report.append("")
        report.append("| Package | Version | Summary |")
        report.append("|---------|---------|---------|")
        
        for pkg in sorted_packages:
            name = pkg['name']
            version = pkg['version']
            summary = pkg['summary'][:80] + "..." if len(pkg['summary']) > 80 else pkg['summary']
            summary = summary.replace('|', '\\|').replace('\n', ' ')  # Escape for markdown
            
            report.append(f"| [{name}]({pkg['pypi_url']}) | {version} | {summary} |")
        
        report.append("")
        
        # Detailed package information
        report.append("## Package Details")
        report.append("")
        
        for pkg in sorted_packages:
            report.append(f"### {pkg['name']}")
            report.append("")
            report.append(f"- **Version**: {pkg['version']}")
            report.append(f"- **Summary**: {pkg['summary']}")
            if pkg['author']:
                report.append(f"- **Author**: {pkg['author']}")
            if pkg['maintainer']:
                report.append(f"- **Maintainer**: {pkg['maintainer']}")
            if pkg['license']:
                report.append(f"- **License**: {pkg['license']}")
            if pkg['home_page']:
                report.append(f"- **Homepage**: {pkg['home_page']}")
            if pkg['github_url']:
                report.append(f"- **GitHub**: {pkg['github_url']}")
            if pkg['created']:
                report.append(f"- **Created**: {pkg['created'][:10]}")  # Just the date part
            report.append(f"- **PyPI**: {pkg['pypi_url']}")
            if pkg['is_plone_related']:
                report.append("- **Plone-related**: Yes")
            report.append("")
        
        return "\n".join(report)
    
    def generate_summary_report(self, all_organizations):
        """Generate a summary report of all organizations."""
        report = []
        report.append("# PyPI Packages - Plone Organizations (Refactored)")
        report.append("")
        report.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Calculate totals
        total_packages = sum(len(packages) for packages in all_organizations.values())
        total_plone_related = sum(
            sum(1 for p in packages if p.get('is_plone_related', False)) 
            for packages in all_organizations.values()
        )
        
        report.append(f"**Total packages analyzed**: {total_packages}")
        report.append(f"**Plone-related packages**: {total_plone_related}")
        report.append("")
        
        # Sort organizations by package count
        sorted_orgs = sorted(all_organizations.items(), key=lambda x: len(x[1]), reverse=True)
        
        report.append("## Summary by Organization")
        report.append("")
        
        for org_name, packages in sorted_orgs:
            plone_count = sum(1 for p in packages if p.get('is_plone_related', False))
            report.append(f"- **{org_name}**: {len(packages)} packages ({plone_count} Plone-related)")
        
        report.append("")
        report.append("## Details")
        report.append("")
        report.append("See individual organization reports:")
        report.append("")
        
        for org_name, _ in sorted_orgs:
            report.append(f"- [{org_name}](pypi-packages-refactored-{org_name}.md)")
        
        return "\n".join(report)


def main():
    """Main execution function."""
    print("Refactored PyPI Package Statistics for Plone Organizations")
    print("=" * 70)
    
    # Step 1: Download all package metadata
    downloader = PyPIPackageDownloader()
    
    # Get all package names for plone.* and collective.*
    prefixes = ['plone.', 'collective.']
    package_names = downloader.get_all_package_names(prefixes)
    
    # Download metadata for all packages
    all_metadata = downloader.download_all_metadata(package_names, max_workers=10)
    
    # Step 2: Process the downloaded data
    analyzer = PyPIPackageAnalyzer()
    processed_packages = analyzer.analyze_all_packages(all_metadata)
    
    # Categorize by organization
    print("\n🏢 Categorizing packages by organization...")
    organizations = analyzer.categorize_packages_by_organization(processed_packages)
    
    # Generate reports
    for org_name, org_packages in organizations.items():
        if len(org_packages) > 0:  # Only generate reports for orgs with packages
            print(f"\n📝 Generating report for {org_name} ({len(org_packages)} packages)")
            
            report = analyzer.generate_organization_report(org_name, org_packages)
            
            # Save report
            report_filename = f"pypi-packages-refactored-{org_name}.md"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"  ✅ Saved report: {report_filename}")
            
            # Save CSV data
            if org_packages:
                df = pd.DataFrame(org_packages)
                csv_filename = f"pypi-packages-refactored-{org_name}.csv"
                df.to_csv(csv_filename, index=False)
                print(f"  ✅ Saved CSV: {csv_filename}")
    
    # Generate summary report
    summary_report = analyzer.generate_summary_report(organizations)
    summary_filename = "pypi-packages-refactored-summary.md"
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    print(f"\n✅ Refactored analysis complete!")
    print(f"   Generated summary: {summary_filename}")
    
    for org_name, packages in organizations.items():
        if len(packages) > 0:
            print(f"   - pypi-packages-refactored-{org_name}.md")
            print(f"   - pypi-packages-refactored-{org_name}.csv")
    
    # Print organization summary
    print(f"\n📊 Organization Summary:")
    sorted_orgs = sorted(organizations.items(), key=lambda x: len(x[1]), reverse=True)
    for org_name, packages in sorted_orgs:
        if len(packages) > 0:
            print(f"   - {org_name}: {len(packages)} packages")
    
    return 0


if __name__ == "__main__":
    exit(main())