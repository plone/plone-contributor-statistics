#!/usr/bin/env python3
"""
Volto Add-on Discovery Script

Searches NPM for Volto add-ons to identify organizations and individuals
that might be missing from our npm_mapping.txt file.
"""

import requests
import json
import time
from datetime import datetime
import re
from collections import defaultdict


class VoltoAddonDiscovery:
    """Discovers Volto add-ons on NPM to find potential missing organizations."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'plone-github-stats/1.0.0 (Volto Add-on Discovery)'
        })
        self.rate_limit_delay = 0.2  # 200ms between requests to be safe
        
    def search_volto_addons(self):
        """Search for Volto add-ons using various search terms."""
        packages = []
        
        # Different search terms to find Volto add-ons
        search_terms = [
            'volto',
            'volto-addon',
            'volto-block',
            'volto add-on',
            'plone volto',
            '@plone/volto'
        ]
        
        for term in search_terms:
            print(f"🔍 Searching for: '{term}'")
            
            try:
                search_url = "https://registry.npmjs.org/-/v1/search"
                params = {
                    'text': term,
                    'size': 250,  # Maximum allowed
                    'from': 0
                }
                
                response = self.session.get(search_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                for package in data.get('objects', []):
                    pkg_info = package.get('package', {})
                    name = pkg_info.get('name', '')
                    
                    # Filter for likely Volto add-ons
                    if self.is_likely_volto_addon(pkg_info):
                        packages.append({
                            'name': name,
                            'description': pkg_info.get('description', ''),
                            'keywords': pkg_info.get('keywords', []),
                            'author': pkg_info.get('author', {}),
                            'maintainers': pkg_info.get('maintainers', []),
                            'npm_url': f"https://www.npmjs.com/package/{name}"
                        })
                
                time.sleep(self.rate_limit_delay)
                
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Error searching for '{term}': {e}")
        
        # Remove duplicates
        unique_packages = {}
        for pkg in packages:
            name = pkg['name']
            if name not in unique_packages:
                unique_packages[name] = pkg
        
        return list(unique_packages.values())
    
    def is_likely_volto_addon(self, pkg_info):
        """Determine if a package is likely a Volto add-on."""
        name = pkg_info.get('name', '').lower()
        description = pkg_info.get('description', '').lower()
        keywords = [k.lower() for k in pkg_info.get('keywords', [])]
        
        # Strong indicators
        strong_indicators = [
            'volto' in name,
            'volto' in description,
            'volto' in keywords,
            'plone' in keywords,
            any('volto' in k for k in keywords),
            'volto add-on' in description,
            'volto addon' in description,
            name.startswith('@') and 'volto' in name
        ]
        
        # Weak indicators (need multiple)
        weak_indicators = [
            'plone' in description,
            'block' in name and ('plone' in description or 'volto' in description),
            'react' in keywords and 'plone' in description
        ]
        
        return any(strong_indicators) or sum(weak_indicators) >= 2
    
    def extract_organizations(self, packages):
        """Extract potential organizations from package names and authors."""
        organizations = defaultdict(list)
        
        for pkg in packages:
            name = pkg['name']
            
            # Extract from scoped package names (@organization/package)
            if name.startswith('@'):
                org = name.split('/')[0][1:]  # Remove @ and get org name
                organizations[org].append(name)
            
            # Extract from author information
            author = pkg.get('author', {})
            if isinstance(author, dict):
                author_name = author.get('name', '')
            elif isinstance(author, str):
                author_name = author
            else:
                author_name = ''
            
            if author_name:
                # Clean up author name (remove email, etc.)
                clean_author = re.sub(r'\s*<[^>]+>', '', author_name).strip()
                if clean_author and not clean_author.lower() in ['unknown', 'anonymous']:
                    organizations[f"author:{clean_author}"].append(name)
            
            # Extract from maintainers
            for maintainer in pkg.get('maintainers', []):
                if isinstance(maintainer, dict):
                    maint_name = maintainer.get('name', '')
                    if maint_name and not maint_name.lower() in ['unknown', 'anonymous']:
                        organizations[f"maintainer:{maint_name}"].append(name)
        
        return organizations
    
    def load_existing_mapping(self, mapping_file="npm_mapping.txt"):
        """Load existing npm mapping to see what we already have."""
        existing_orgs = set()
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        org_name = line.split(':', 1)[0].strip()
                        existing_orgs.add(org_name.lower())
        except FileNotFoundError:
            print(f"  ⚠️  Warning: {mapping_file} not found")
        
        return existing_orgs
    
    def analyze_missing_organizations(self, organizations, existing_orgs):
        """Analyze which organizations might be missing from our mapping."""
        missing_candidates = {}
        
        for org_key, packages in organizations.items():
            # Skip if we have very few packages (likely individual contributors)
            if len(packages) < 2:
                continue
                
            # Extract clean org name
            if org_key.startswith('author:') or org_key.startswith('maintainer:'):
                org_name = org_key.split(':', 1)[1].lower()
            else:
                org_name = org_key.lower()
            
            # Skip if we already have this organization
            if org_name in existing_orgs:
                continue
            
            # Skip obviously individual names (contains spaces, common first names)
            individual_indicators = [
                ' ' in org_name,
                org_name in ['john', 'jane', 'admin', 'user', 'test', 'demo'],
                len(org_name) < 3
            ]
            
            if any(individual_indicators):
                continue
            
            missing_candidates[org_name] = {
                'packages': packages,
                'count': len(packages),
                'original_key': org_key
            }
        
        return missing_candidates
    
    def generate_report(self, packages, organizations, missing_candidates):
        """Generate a comprehensive report."""
        report = []
        report.append("# Volto Add-on Discovery Report")
        report.append("")
        report.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Volto add-ons found: {len(packages)}")
        report.append("")
        
        # Summary of organizations found
        report.append("## Organizations Found")
        report.append("")
        for org, info in sorted(organizations.items(), key=lambda x: len(x[1]), reverse=True):
            if len(info) >= 2:  # Only show orgs with multiple packages
                report.append(f"- **{org}**: {len(info)} packages")
        
        report.append("")
        
        # Missing candidates
        if missing_candidates:
            report.append("## Potential Missing Organizations")
            report.append("")
            report.append("Organizations that might be missing from npm_mapping.txt:")
            report.append("")
            
            for org, info in sorted(missing_candidates.items(), key=lambda x: x[1]['count'], reverse=True):
                report.append(f"### {org}")
                report.append(f"- **Package count**: {info['count']}")
                report.append(f"- **Packages**: {', '.join(info['packages'][:5])}")
                if len(info['packages']) > 5:
                    report.append(f"  - ... and {len(info['packages']) - 5} more")
                report.append("")
        else:
            report.append("## No Missing Organizations Found")
            report.append("")
            report.append("All organizations with multiple Volto packages appear to be in npm_mapping.txt already.")
            report.append("")
        
        # All packages found
        report.append("## All Volto Add-ons Found")
        report.append("")
        report.append("| Package | Description |")
        report.append("|---------|-------------|")
        
        for pkg in sorted(packages, key=lambda x: x['name']):
            name = pkg['name']
            desc = pkg['description'][:100] + "..." if len(pkg['description']) > 100 else pkg['description']
            desc = desc.replace('|', '\\|')  # Escape pipes for markdown
            report.append(f"| [{name}]({pkg['npm_url']}) | {desc} |")
        
        return "\\n".join(report)


def main():
    """Main execution function."""
    print("Volto Add-on Discovery")
    print("=" * 40)
    
    discovery = VoltoAddonDiscovery()
    
    # Search for Volto add-ons
    print("\\n🔍 Searching for Volto add-ons...")
    packages = discovery.search_volto_addons()
    print(f"  ✅ Found {len(packages)} unique Volto add-ons")
    
    # Extract organizations
    print("\\n📊 Analyzing organizations...")
    organizations = discovery.extract_organizations(packages)
    print(f"  ✅ Found {len(organizations)} potential organizations")
    
    # Load existing mapping
    existing_orgs = discovery.load_existing_mapping()
    print(f"  📋 Loaded {len(existing_orgs)} existing organizations from mapping")
    
    # Find missing candidates
    missing_candidates = discovery.analyze_missing_organizations(organizations, existing_orgs)
    print(f"  🎯 Found {len(missing_candidates)} potential missing organizations")
    
    # Generate report
    report = discovery.generate_report(packages, organizations, missing_candidates)
    
    # Save report
    report_filename = "volto-addon-discovery.md"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\\n✅ Analysis complete! Report saved to: {report_filename}")
    
    # Print summary of missing candidates
    if missing_candidates:
        print("\\n🎯 Potential missing organizations:")
        for org, info in sorted(missing_candidates.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"  - {org}: {info['count']} packages")
    else:
        print("\\n✅ No obvious missing organizations found")
    
    return 0


if __name__ == "__main__":
    exit(main())