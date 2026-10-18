# Plone Core vs. Volto: Contributor Metrics Comparison

## Executive Summary

This document provides a detailed comparison between contribution patterns in the Plone ecosystem (300+ repositories) and the Volto project (single repository). **Bottom line: The metrics are NOT directly comparable** due to fundamental structural differences, but both provide valuable insights when understood in context.

## Key Structural Differences

| Aspect | Plone Core Ecosystem | Volto Project | Impact on Metrics |
|--------|---------------------|---------------|-------------------|
| **Repositories** | 300+ repos | 1 repo | PRs spread vs. concentrated |
| **Scope** | Full CMS ecosystem | Frontend framework | Breadth vs. depth |
| **Age** | 23+ years (2001-2025) | 8 years (2017-2025) | Mature vs. growing |
| **Contributor base** | ~1,000+ historical | 24 team members | Open vs. focused team |
| **Contribution style** | Specialized packages | Unified codebase | Fragmented vs. cohesive |

## Statistical Comparison (2020-2025)

### Raw Numbers

| Metric | Plone Ecosystem | Volto Project | Ratio (Plone/Volto) |
|--------|-----------------|---------------|---------------------|
| **Median PRs/year** | 2 | 11 | 0.18x (5.5x lower) |
| **Mean PRs/year** | 12.6 | 29.7 | 0.42x (2.4x lower) |
| **25th Percentile** | 1 PR | 3 PRs | 0.33x |
| **75th Percentile** | 8 PRs | 30 PRs | 0.27x |
| **90th Percentile** | 27 PRs | 67 PRs | 0.40x |
| **95th Percentile** | 61 PRs | 144 PRs | 0.42x |

### What This Means

**Plone's lower numbers reflect:**
1. **Repository fragmentation** - PRs distributed across 300+ repos
2. **Specialized contributions** - Contributors focus on specific packages
3. **Higher barrier to entry** - More repos to understand
4. **Deeper commits per PR** - More substantial changes per PR

**Volto's higher numbers reflect:**
1. **Concentrated activity** - All PRs in one repository
2. **Unified codebase** - Easier to contribute across features
3. **Active development phase** - Rapid iteration and evolution
4. **Smaller, focused team** - 24 defined members vs. open ecosystem

## Percentile-by-Percentile Analysis

### Bottom 25% (Minimal Contributors)

| Percentile | Plone | Volto | Interpretation |
|------------|-------|-------|----------------|
| 10th | 1 PR | 2 PRs | Both include very light contributors |
| 25th | 1 PR | 3 PRs | Volto has slightly more "minimum viable" activity |

**Conclusion:** Both projects have occasional/minimal contributors. The difference (1-2 PRs) is within noise range.

**Comparable?** ✅ **Yes** - Both accept light contributions

### Middle 50% (Regular Contributors)

| Percentile | Plone | Volto | Plone Adjusted* | Comparable? |
|------------|-------|-------|-----------------|-------------|
| 50th (Median) | 2 PRs | 11 PRs | 6-10 PRs | ❌ Not directly |
| 75th | 8 PRs | 30 PRs | 20-40 PRs | ✅ Similar range |

*Adjusted = Plone × 3-5 to account for repository spread

**Explanation:**
- **Median difference (2 vs 11):** Plone's median is dragged down by many single-repo contributors
- **75th percentile (8 vs 30):** When adjusted for multi-repo, these align (8×3 = 24, close to 30)

**Comparable?** ⚠️ **Partially** - Need to adjust for repository count

### Top 25% (Active to Core Contributors)

| Percentile | Plone | Volto | Observation |
|------------|-------|-------|-------------|
| 90th | 27 PRs | 67 PRs | Plone top 10% ≈ Volto top 25% |
| 95th | 61 PRs | 144 PRs | Similar 2-2.5x multiplier |

**Comparable?** ✅ **Yes with adjustment** - Apply 2-3x multiplier for Plone

### Top 5% (Lead Contributors)

| Level | Plone | Volto | Notes |
|-------|-------|-------|-------|
| Top 5% threshold | ~61 PRs | ~144 PRs | Volto requires 2.4x more |
| Top 1% | ~185 PRs | ~225 PRs | Convergence at highest levels |

**Comparable?** ✅ **Yes** - Lead contributors work at similar intensity in both

## Contributor Category Comparison

### Plone Ecosystem Categories (2020-2025)

| Category | Range | Percentage |
|----------|-------|------------|
| Minimal | 1-5 PRs/yr | 70.0% |
| Occasional | 6-15 PRs/yr | 15.1% |
| Regular | 16-30 PRs/yr | 5.3% |
| Active | 31-75 PRs/yr | 6.1% |
| Core | 76-150 PRs/yr | 1.7% |
| Lead | 150+ PRs/yr | 1.7% |

### Volto Project Categories (2017-2025)

| Category | Range | Percentage |
|----------|-------|------------|
| Occasional | 1-5 PRs/yr | 35.4% |
| Regular | 6-20 PRs/yr | 27.6% |
| Active | 21-50 PRs/yr | 22.0% |
| Core | 51-100 PRs/yr | 9.4% |
| Lead | 100+ PRs/yr | 5.5% |

### Side-by-Side with Adjustment

Applying a 3x adjustment factor to Plone to account for repository spread:

| Category | Plone (Raw) | Plone (×3 Adjusted) | Volto | Match Quality |
|----------|-------------|---------------------|-------|---------------|
| Minimal/Occasional | 1-5 PRs | 3-15 PRs | 1-5 PRs | ⚠️ Plone needs higher floor |
| Occasional/Regular | 6-15 PRs | 18-45 PRs | 6-20 PRs | ✅ Good alignment |
| Regular/Active | 16-30 PRs | 48-90 PRs | 21-50 PRs | ⚠️ Plone overestimates |
| Active/Core | 31-75 PRs | 93-225 PRs | 51-100 PRs | ❌ Poor alignment |
| Core/Lead | 76+ PRs | 228+ PRs | 100+ PRs | ✅ Convergence at top |

**Conclusion:** Simple multiplier doesn't work across all levels. Need nuanced adjustment.

## Better Comparison: Normalized Metrics

### Proposed Normalization Approach

Instead of raw PR counts, compare **percentile positions**:

| Contributor Level | Plone Percentile | Volto Percentile | Equivalent Meaning |
|-------------------|------------------|------------------|-------------------|
| **Minimal** | 0-50th | 0-25th | Light participation |
| **Occasional** | 50-75th | 25-50th | Regular but limited |
| **Regular** | 75-90th | 50-75th | Consistent contributor |
| **Active** | 90-95th | 75-90th | Strong contributor |
| **Core** | 95-99th | 90-95th | Top tier contributor |
| **Lead** | 99th+ | 95th+ | Exceptional contributor |

### Using This Framework

**Example 1: "Regular Contributor"**
- **Plone:** 8 PRs/year (75th percentile)
- **Volto:** 30 PRs/year (75th percentile)
- **Both represent:** Same relative contribution level
- **Comparable?** ✅ **Yes** - Same percentile position

**Example 2: "Core Contributor"**
- **Plone:** 61 PRs/year (95th percentile)
- **Volto:** 144 PRs/year (95th percentile)
- **Both represent:** Top 5% of contributors
- **Comparable?** ✅ **Yes** - Same elite status

## Commits vs. Pull Requests

### Plone Ecosystem

- **Mean commits/PR:** ~3.5
- **High commit contributors:** mauritsvanrees (8.3), jensens (6.1), tisto (7.1)
- **Pattern:** Core work tends to have more commits per PR
- **Reason:** Batch changes across packages, release work

### Volto Project

- **Mean commits/PR:** ~2.2
- **Pattern:** More granular PRs
- **Reason:** Single repo encourages smaller, focused changes

**Comparable?** ❌ **No** - Different PR granularity

**Implication:** Can't compare commit counts directly. Plone PRs are "heavier."

## Repository Diversity Factor

### Plone Contributors

- **Mean repos/year:** 4.4
- **Median repos/year:** 1
- **Pattern:** Most contribute to 1 repo, generalists touch 5-10+

### Volto Contributors

- **Repos/year:** Always 1 (by definition)
- **Pattern:** N/A - single repository

**Comparable?** ❌ **No** - Fundamentally different

**Implication:** Plone "generalists" (10+ repos) are like Volto contributors who also contribute to plone.restapi, plone.api, etc.

## Apples-to-Apples Comparison: Cross-Project Contributors

Let's look at contributors active in BOTH ecosystems:

### Contributors in Both Plone Ecosystem AND Volto

| Username | Plone PRs/yr | Volto PRs/yr | Ratio (Plone/Volto) |
|----------|--------------|--------------|---------------------|
| sneridagh | 208.7 | 203.4 | 1.03x (essentially same) |
| stevepiercy | 100.0 | 53.0 | 1.89x (more in Plone) |
| tisto | 50.4 | 19.4 | 2.60x (more in Plone) |
| davisagli | 74.5 | 24.2 | 3.08x (more in Plone) |
| ksuess | 35.4 | 18.2 | 1.95x (more in Plone) |
| erral | 45.4 | 13.0 | 3.49x (more in Plone) |

**Average Plone/Volto ratio for cross-contributors: ~2.3x**

### What This Tells Us

**The same people contribute ~2-3x more PRs across Plone ecosystem than to Volto alone.**

This suggests:
- **Rough equivalence:** 10 Plone PRs ≈ 3-5 Volto PRs
- **Or inversely:** 10 Volto PRs ≈ 20-30 Plone PRs
- **Adjustment factor: 2-3x** for ecosystem vs. single repo

**Comparable?** ✅ **Yes with 2-3x adjustment**

## Recommended Equivalent Contribution Levels

Based on the analysis, here are equivalent contribution levels:

### Minimal Viable Contributor

| Level | Plone Ecosystem | Volto Project | Percentile |
|-------|-----------------|---------------|------------|
| Minimal | 5-10 PRs/year | 6-10 PRs/year | ~70th |
| Reasoning | Above median (2), shows commitment | Above median (11), minimal viability | Both above median |

**Comparable?** ✅ **Yes** - Both represent "showing up regularly"

### Regular Active Contributor

| Level | Plone Ecosystem | Volto Project | Percentile |
|-------|-----------------|---------------|------------|
| Regular | 10-20 PRs/year | 15-25 PRs/year | ~75-85th |
| Reasoning | Top 30%, meaningful impact | Above median, regular participation | Similar relative position |

**Comparable?** ✅ **Yes** - Both show consistent engagement

### Active Team Member

| Level | Plone Ecosystem | Volto Project | Percentile |
|-------|-----------------|---------------|------------|
| Active | 20-40 PRs/year | 20-50 PRs/year | ~90th |
| Reasoning | Top 10%, strong contribution | Top 25%, active member | Similar commitment |

**Comparable?** ✅ **Yes** - Both represent significant time investment

### Core Contributor

| Level | Plone Ecosystem | Volto Project | Percentile |
|-------|-----------------|---------------|------------|
| Core | 40-80 PRs/year | 50-100 PRs/year | ~95th |
| Reasoning | Top 5%, architectural work | Top 10%, core team member | High-impact contributors |

**Comparable?** ⚠️ **Partially** - Plone may include more cross-repo coordination

### Lead/Maintainer

| Level | Plone Ecosystem | Volto Project | Percentile |
|-------|-----------------|---------------|------------|
| Lead | 100+ PRs/year | 100+ PRs/year | ~99th |
| Reasoning | Top 1%, leadership role | Top 5%, team lead | Full-time dedication |

**Comparable?** ✅ **Yes** - Lead-level contributions converge

## Summary Table: Equivalent Contribution Levels

| Role | Plone Ecosystem | Volto Project | Adjustment Factor |
|------|-----------------|---------------|-------------------|
| **Community Member** | 5-15 PRs/yr | 6-10 PRs/yr | ~1x (similar) |
| **Active Contributor** | 15-40 PRs/yr | 15-25 PRs/yr | ~1.5x |
| **Core Team Member** | 40-100 PRs/yr | 50-100 PRs/yr | ~1x at high end |
| **Lead/Maintainer** | 100+ PRs/yr | 100+ PRs/yr | 1x (converges) |

## Are They Comparable? Final Answer

### ❌ **NOT Directly Comparable** If You:
1. Compare raw PR counts without adjustment
2. Ignore repository count differences
3. Don't account for contribution style (specialist vs. generalist)
4. Only look at PRs without considering commits
5. Compare percentiles literally across distributions

### ✅ **YES, Comparable** If You:
1. **Use percentile-based comparisons** (75th percentile vs. 75th percentile)
2. **Apply 2-3x adjustment** for Plone ecosystem breadth
3. **Consider cross-project contributors** as calibration points
4. **Focus on relative position** within each community
5. **Account for commits per PR** differences
6. **Recognize different contribution patterns** (deep vs. broad)

## Practical Recommendations

### For Setting Expectations

**DON'T SAY:**
- "You need 20 PRs/year in Plone just like Volto"
- "Volto contributors are more active because higher PR counts"
- "10 PRs/year is the same standard everywhere"

**DO SAY:**
- "You need to be in the top 30% of contributors" (10-20 PRs for Plone, 15-25 for Volto)
- "Consistent contribution above the median for 2+ years"
- "Focus on percentile position, not raw numbers"

### For Evaluating Contributors

**Framework:**
1. **Determine their percentile** in their primary contribution area
2. **Consider repository diversity** (1 repo vs. 5+ repos)
3. **Look at sustained contribution** (consistency over years)
4. **Evaluate impact quality** (architectural vs. bug fixes)
5. **Account for role** (maintainer vs. specialist vs. generalist)

### For Cross-Project Contributors

If someone contributes to both Plone and Volto:
- **Add their percentiles**, don't add raw PR counts
- Example: 75th percentile in Plone + 50th in Volto = strong cross-project contributor
- **Recognize breadth** as a separate value dimension

## Conclusion

### The Bottom Line

**Plone and Volto contribution metrics are fundamentally different but conceptually comparable when properly contextualized.**

### Key Insights

1. **Raw numbers mislead** - 2 Plone PRs ≠ 11 Volto PRs in meaning
2. **Percentiles work** - 75th percentile represents same relative contribution
3. **Adjustment factor: ~2-3x** - Multiply Plone PRs by 2-3 to compare to Volto
4. **Lead level converges** - Top contributors work similarly hard in both
5. **Context is everything** - Consider repos, commits, years, and impact

### Recommended Approach

**Use this equivalency table for practical decisions:**

| Category | Plone Minimum | Volto Minimum | Meaning |
|----------|---------------|---------------|---------|
| Team Member | 10 PRs/yr | 10 PRs/yr | Regular participation |
| Active Member | 20 PRs/yr | 20 PRs/yr | Strong engagement |
| Core Member | 50 PRs/yr | 50 PRs/yr | Significant commitment |
| Lead | 100 PRs/yr | 100 PRs/yr | Full-time level |

**Why this works:**
- Plone's lower numbers offset by multi-repo work
- Volto's higher numbers reflect focused single-repo work
- At each level, represents similar time/effort investment
- Easy to remember and communicate

### Final Recommendation

**For team membership decisions, use percentile-based thresholds:**

- **Minimum:** Top 30% in their primary contribution area
- **Active:** Top 15% in their primary area
- **Core:** Top 5% in their primary area
- **Lead:** Top 1% in their primary area

This works regardless of whether it's Plone, Volto, or any other project in the ecosystem.

---

*Analysis based on 2017-2025 data: Plone ecosystem (300+ repos, 984 active contributor-years) vs. Volto project (1 repo, 127 active contributor-years).*
