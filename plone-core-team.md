# Plone Core Team Contribution Analysis (2017-2025)

## Executive Summary

This document analyzes contribution patterns across the entire Plone ecosystem (300+ repositories) for the period 2017-2025. Unlike the Volto-specific analysis, this covers all Plone repositories including core, add-ons, documentation, infrastructure, and frontend projects.

## Key Differences: Plone Ecosystem vs. Volto

| Metric | Plone Ecosystem | Volto Only | Factor |
|--------|-----------------|------------|--------|
| **Repositories** | 300+ | 1 | 300x |
| **Median PRs/year** | 2 | 11 | 0.18x |
| **Mean PRs/year** | 12.6 | 29.7 | 0.43x |
| **Active contributor-years (2020-2025)** | 984 | 127 | 7.7x |

**Key Insight:** The Plone ecosystem has significantly lower median PR counts because contributions are spread across hundreds of repositories, making individual repository activity appear lower than focused projects like Volto.

## Overall Statistics (2020-2025)

- **Total active contributor-years:** 984
- **Mean PRs/year:** 12.6
- **Median PRs/year:** 2
- **Mean Commits/year:** 43.8
- **Median Commits/year:** 2
- **Mean Repositories/year:** 4.4
- **Median Repositories/year:** 1

## Top 15 All-Time Contributors (2017-2025)

| Rank | Username | Total PRs | Total Commits | Years Active | Avg PRs/Year | Avg Commits/Year |
|------|----------|-----------|---------------|--------------|--------------|------------------|
| 1 | sneridagh | 1,878 | 4,380 | 9 | 208.7 | 486.7 |
| 2 | mauritsvanrees | 1,393 | 11,518 | 9 | 154.8 | 1,279.8 |
| 3 | stevepiercy | 900 | 3,375 | 9 | 100.0 | 375.0 |
| 4 | gforcada | 764 | 4,236 | 9 | 84.9 | 470.7 |
| 5 | petschki | 749 | 3,072 | 9 | 83.2 | 341.3 |
| 6 | jensens | 639 | 3,890 | 9 | 71.0 | 432.2 |
| 7 | thet | 580 | 1,975 | 9 | 64.4 | 219.4 |
| 8 | vangheem | 550 | 2,690 | 6 | 91.7 | 448.3 |
| 9 | pbauer | 526 | 2,482 | 9 | 58.4 | 275.8 |
| 10 | tisto | 454 | 3,204 | 9 | 50.4 | 356.0 |
| 11 | davisagli | 447 | 1,815 | 6 | 74.5 | 302.5 |
| 12 | erral | 409 | 710 | 9 | 45.4 | 78.9 |
| 13 | ale-rt | 351 | 798 | 9 | 39.0 | 88.7 |
| 14 | mpellerin42 | 348 | 236 | 8 | 43.5 | 29.5 |
| 15 | ksuess | 319 | 1,246 | 9 | 35.4 | 138.4 |

### Notable Observations

**Top Tier (150+ PRs/year):**
- **sneridagh:** Lead across both Volto and broader Plone ecosystem (208.7 PRs/yr)
- **mauritsvanrees:** Plone Release Manager, exceptional commit count (1,279.8 commits/yr)

**Core Maintainers (70-100 PRs/year):**
- **stevepiercy:** Documentation specialist (100.0 PRs/yr)
- **vangheem:** High-impact contributor despite only 6 years (91.7 PRs/yr)
- **gforcada:** Consistent infrastructure and core work (84.9 PRs/yr)
- **petschki:** Broad ecosystem contributor (83.2 PRs/yr)

## Contributor Distribution (2020-2025)

### PR Percentile Distribution

| Percentile | PRs/Year |
|------------|----------|
| 10th | 1 |
| 25th | 1 |
| 50th (Median) | 2 |
| 75th | 8 |
| 90th | 27 |
| 95th | 61 |
| 99th | 185 |

### Contributor Categories

Based on PR contributions across the ecosystem:

| Category | Range | Contributor-Years | Percentage |
|----------|-------|-------------------|------------|
| Minimal | 1-5 PRs | 689 | 70.0% |
| Occasional | 6-15 PRs | 149 | 15.1% |
| Regular | 16-30 PRs | 52 | 5.3% |
| Active | 31-75 PRs | 60 | 6.1% |
| Core | 76-150 PRs | 17 | 1.7% |
| Lead | 150+ PRs | 17 | 1.7% |

## Long-Term Contributors (5+ Years Active)

**Total:** 89 contributors with 5+ years of sustained activity

### Top 20 Sustained Contributors

| Username | Years | Total PRs | Total Commits | Avg PRs/Year |
|----------|-------|-----------|---------------|--------------|
| sneridagh | 9 | 1,878 | 4,380 | 208.7 |
| mauritsvanrees | 9 | 1,393 | 11,518 | 154.8 |
| stevepiercy | 9 | 900 | 3,375 | 100.0 |
| gforcada | 9 | 764 | 4,236 | 84.9 |
| petschki | 9 | 749 | 3,072 | 83.2 |
| jensens | 9 | 639 | 3,890 | 71.0 |
| thet | 9 | 580 | 1,975 | 64.4 |
| vangheem | 6 | 550 | 2,690 | 91.7 |
| pbauer | 9 | 526 | 2,482 | 58.4 |
| tisto | 9 | 454 | 3,204 | 50.4 |
| davisagli | 6 | 447 | 1,815 | 74.5 |
| erral | 9 | 409 | 710 | 45.4 |
| ale-rt | 9 | 351 | 798 | 39.0 |
| mpellerin42 | 8 | 348 | 236 | 43.5 |
| ksuess | 9 | 319 | 1,246 | 35.4 |
| tiberiuichim | 8 | 292 | 494 | 36.5 |
| ericof | 8 | 286 | 1,663 | 35.8 |
| MrTango | 9 | 218 | 1,994 | 24.2 |
| agitator | 7 | 213 | 914 | 30.4 |
| wesleybl | 6 | 193 | 194 | 32.2 |

## Recommended Contribution Levels

### Understanding the Context

**Critical Difference from Volto:**
- Plone has 300+ repositories vs. Volto's single repository
- Contributors often specialize in specific areas (core, add-ons, docs, infrastructure)
- A "low" PR count may represent deep work in a few critical repositories
- Commits matter more than PRs in some repositories (especially core)

### Contribution Tiers

#### 1. Community Member
**Recommended: 5-15 PRs/year**

- **Rationale:** Places contributor above 70th percentile (8 PRs/year)
- Meaningful participation across the ecosystem
- Approximately 1 PR every 1-2 months
- May focus on 1-3 specific repositories
- Can be domain specialist (docs, specific add-on, core feature)

**Examples:**
- Contributing to documentation
- Maintaining 1-2 add-on packages
- Regular bug fixes in core
- Infrastructure improvements

#### 2. Active Contributor
**Recommended: 15-40 PRs/year**

- **Rationale:** Solidly in 90th percentile range (27 PRs/year at 90th)
- Shows broad or deep engagement
- Approximately 1-3 PRs per month
- Working across multiple repositories or deeply in core
- Regular participant in development discussions

**Examples:**
- Maintaining multiple packages
- Active in core development
- Cross-cutting features (API, testing, CI/CD)
- Regular reviewer and mentor

#### 3. Core Team Member
**Recommended: 40-100 PRs/year**

- **Rationale:** Top 5% of contributors (61+ PRs at 95th percentile)
- Significant impact on ecosystem
- Approximately 3-8 PRs per month
- Likely working across many repositories
- Architectural and strategic contributions

**Examples:**
- Release team member
- Framework team participation
- Multiple package maintainer
- Infrastructure and DevOps

#### 4. Lead/Maintainer
**Recommended: 100+ PRs/year**

- **Rationale:** Top 1-2% of contributors
- Full-time or near full-time dedication
- Approximately 8+ PRs per month
- Cross-ecosystem responsibility
- Leadership and mentorship role

**Examples:**
- Release Manager (mauritsvanrees)
- Team Lead (sneridagh for Volto)
- Documentation Lead (stevepiercy)
- Framework Team Lead

## Commits vs. Pull Requests

### Important Distinction

Unlike single-repository projects, Plone's ecosystem requires looking at both metrics:

**High Commit/Low PR Scenarios:**
- Working directly in core repositories
- Batch changes across multiple packages
- Infrastructure and tooling work
- Release management activities

**Examples:**
- **mauritsvanrees:** 154.8 PRs/yr but 1,279.8 commits/yr (8.3 commits per PR)
- **jensens:** 71.0 PRs/yr but 432.2 commits/yr (6.1 commits per PR)
- **tisto:** 50.4 PRs/yr but 356.0 commits/yr (7.1 commits per PR)

**High PR/Lower Commit Scenarios:**
- Documentation contributions
- Add-on development with focused changes
- Review-heavy participation
- Cross-package coordination

**Examples:**
- **stevepiercy:** 100.0 PRs/yr, 375.0 commits/yr (3.8 commits per PR)
- **mpellerin42:** 43.5 PRs/yr, 29.5 commits/yr (0.7 commits per PR - likely review focus)

### Recommendation: Consider Both Metrics

For Plone core team membership, evaluate:
- **PRs:** Breadth of participation
- **Commits:** Depth of work
- **Repositories:** Scope of expertise
- **Consistency:** Years of sustained contribution

## Repository Diversity

**Mean repositories per year:** 4.4
**Median repositories per year:** 1

### Specialist vs. Generalist Patterns

**Specialists (1-2 repos/year):**
- Deep expertise in specific areas
- Critical for complex packages
- Often core infrastructure work

**Generalists (5+ repos/year):**
- Cross-cutting concerns
- Framework-level work
- Integration specialists
- Release coordination

**Both are valuable** - recognize different contribution styles.

## Comparison: Volto Team vs. Plone Core

| Metric | Volto Team | Plone Core | Notes |
|--------|------------|------------|-------|
| **Minimal baseline** | 6-10 PRs/year | 5-15 PRs/year | Plone: spread across repos |
| **Active member** | 15-25 PRs/year | 15-40 PRs/year | Plone: higher ceiling due to scope |
| **Core member** | 50-100 PRs/year | 40-100 PRs/year | Similar ranges |
| **Lead** | 100+ PRs/year | 100+ PRs/year | Similar expectations |
| **Key difference** | Single repo focus | Multi-repo scope | Context matters |

## Recommendations by Role

### 1. Add-on Maintainer
**Minimum: 5-10 PRs/year**
- Focus on 1-3 specific packages
- Responsive to issues and PRs
- Regular maintenance releases
- Above 70th percentile in ecosystem

### 2. Core Developer
**Minimum: 20-40 PRs/year**
- Active in Products.CMFPlone and related packages
- Participates in architectural decisions
- Reviews others' contributions
- Top 10% of contributors

### 3. Framework Team Member
**Minimum: 30-60 PRs/year**
- Works across multiple core repositories
- Addresses cross-cutting concerns
- Mentors other contributors
- Top 5-10% range

### 4. Release Team Member
**Minimum: 40+ PRs/year + significant commit count**
- Release management requires deep work
- Many commits per PR typical
- Cross-repository coordination
- Consider commit count heavily

### 5. Documentation Team Member
**Minimum: 15-30 PRs/year**
- May have lower commit-per-PR ratio
- High value despite lower commit counts
- Consistency more important than volume
- Specialist contribution pattern

### 6. Infrastructure/DevOps
**Minimum: 10-30 PRs/year**
- May work in background repositories
- Impact not always visible in PR counts
- CI/CD, Jenkins, Docker, etc.
- Consider breadth of repositories

## Special Considerations

### 1. Multi-Repository Work

Contributors working across many repositories may have:
- Lower PRs per repository
- Higher total ecosystem impact
- Cross-cutting expertise value
- Coordination overhead

**Don't penalize** breadth for depth or vice versa.

### 2. Seasonal Patterns

- Sprint-driven contributions
- Conference/event-related work
- Release cycle patterns
- Holiday and vacation impacts

**Evaluate annually**, not quarterly.

### 3. Quality Over Quantity

Some contributions that deserve recognition despite lower numbers:
- Major architectural refactorings
- Security fixes
- Performance improvements
- Breaking API migrations
- Complete documentation overhauls

### 4. Sponsored vs. Volunteer

Consider contributor context:
- Full-time sponsored developers: higher expectations
- Volunteer contributors: celebrate consistency
- Company-backed: may focus on specific areas
- Independent: may have broader but lighter touch

## Sustained Contribution Value

### The 89 Long-Term Contributors

Having 89 contributors with 5+ years of activity is exceptional:
- **Institutional knowledge**
- **Mentorship capacity**
- **Stability and reliability**
- **Community leadership**

**Value consistency:** Someone contributing 10-20 PRs/year for 9 years (90-180 total) has massive impact versus sporadic high-volume contributors.

## Final Recommendations

### Plone Core Team Membership

**Minimum Baseline: 10-20 PRs/year**
- Consistently above ecosystem median (2 PRs/year)
- Meaningful participation
- Approximately 1-2 PRs per month
- Shows commitment to Plone

**Ideal Active Member: 20-50 PRs/year**
- Top 10-15% of contributors
- Significant ecosystem impact
- Regular participation in team activities
- Strong community presence

**Core Maintainer: 50+ PRs/year**
- Top 5% of contributors
- Leadership role in specific areas
- Likely full-time or heavily sponsored
- Mentorship and architectural input

### Context Always Matters

Look beyond the numbers:
1. **Repository diversity:** How many repos touched?
2. **Commit depth:** Commits per PR ratio
3. **Review activity:** Comments, reviews, mentorship
4. **Sustainability:** Years of consistent contribution
5. **Impact quality:** What changes, not just how many
6. **Team participation:** Sprints, meetings, discussions

### Recommended Evaluation Framework

For Plone core team membership decisions:

**Must Have (All Required):**
- 10+ PRs/year OR 50+ commits/year
- Active in 2+ repositories
- 1+ years of consistent contribution

**Highly Valued (At Least 2):**
- 20+ PRs/year
- 5+ repositories touched
- Code review participation
- Sprint/conference attendance
- Mentorship of new contributors

**Exceptional (Bonus Points):**
- 3+ years sustained contribution
- 50+ PRs/year
- Release team participation
- Framework/architectural work
- Cross-project coordination

## Conclusion

The Plone ecosystem has different contribution patterns than single-repository projects like Volto:

**Key Insights:**
1. **Lower PR counts are normal** due to 300+ repository spread
2. **Median is 2 PRs/year** but context matters enormously
3. **10-20 PRs/year** represents strong ecosystem contribution
4. **Commits matter as much as PRs** for core development
5. **89 long-term contributors** show healthy ecosystem
6. **Specialization is valuable** - not everyone works everywhere

**Recommended Baseline for Core Team: 10-20 PRs/year across the ecosystem**

This represents:
- Top 30% of all contributors
- Meaningful, sustained participation
- Achievable for part-time/volunteer contributors
- Above minimal threshold while remaining inclusive
- Recognizes both specialists and generalists

**Ultimate Guideline:** Sustained, consistent contribution over multiple years is more valuable than short bursts of high activity. Quality of engagement, mentorship, and community participation matter as much as raw PR counts.

---

*Analysis based on Plone contributor data from 2017-2025, covering 300+ repositories and 984 active contributor-years (2020-2025).*
