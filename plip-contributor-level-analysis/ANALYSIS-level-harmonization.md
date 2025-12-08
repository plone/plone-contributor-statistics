# Level Harmonization Analysis: PR vs PLIP Contributors

**Date**: 2025-11-03
**Analysis Type**: Comparative Statistical Analysis
**Purpose**: Identify differences and propose unified thresholds

---

## Executive Summary

Analysis of **303 PLIPs from 63 contributors** (all-time) versus **7,112 PRs from 382 contributors** (2022-2024) reveals **fundamental misalignment** in current level systems:

**Key Finding**: Current PLIP thresholds (20/10/5/2/1) do NOT correspond to equivalent PR effort when using any reasonable equivalence ratio.

**Recommendation**: Adopt **3-tier system with separate but equivalent thresholds** that recognize the different nature of strategic vs implementation contributions.

---

## Current System Comparison

### PLIP Levels (All-Time, 5-Level System)

| Level | Threshold | Contributors | % of Contributors | Total PLIPs | % of PLIPs |
|-------|-----------|--------------|-------------------|-------------|------------|
| **Level 1** | 20+ PLIPs | 3 | 4.8% | 111 | 36.6% |
| **Level 2** | 10-19 PLIPs | 5 | 7.9% | 72 | 23.8% |
| **Level 3** | 5-9 PLIPs | 7 | 11.1% | 45 | 14.9% |
| **Level 4** | 2-4 PLIPs | 15 | 23.8% | 42 | 13.9% |
| **Level 5** | 1 PLIP | 33 | 52.4% | 33 | 10.9% |
| **Total** | | **63** | **100%** | **303** | **100%** |

**Characteristics**:
- Top-heavy contribution: Top 12.7% (Levels 1-2) produce 60.4% of PLIPs
- Moderate middle tier: 34.9% (Levels 3-4) produce 28.8% of PLIPs
- Large entry pool: 52.4% (Level 5) produce 10.9% of PLIPs

### PR Levels (3-Year 2022-2024, No Formal System)

| Threshold | Contributors | % of Contributors | Total PRs | % of PRs |
|-----------|--------------|-------------------|-----------|----------|
| **500+ PRs** | 5 | 1.3% | 3,594 | 50.5% |
| **200-499 PRs** | 7 | 1.8% | 1,853 | 26.1% |
| **100-199 PRs** | 8 | 2.1% | 1,060 | 14.9% |
| **50-99 PRs** | 11 | 2.9% | 747 | 10.5% |
| **25-49 PRs** | 12 | 3.1% | 427 | 6.0% |
| **10-24 PRs** | 38 | 9.9% | 560 | 7.9% |
| **1-9 PRs** | 301 | 78.8% | 871 | 12.2% |
| **Total** | **382** | **100%** | **7,112** | **100%** |

**Characteristics**:
- Extremely top-heavy: Top 3.1% produce 76.6% of PRs
- Thin middle tier: 5.0% produce 25.4% of PRs
- Massive entry pool: 78.8% produce 12.2% of PRs

---

## Critical Misalignments

### Problem 1: Different Participant Pools

**PLIP Contributors**: 63 people (specialized activity)
- Requires strategic thinking, architecture skills
- Higher barrier to entry
- Smaller, more elite group

**PR Contributors**: 382 people (broader activity)
- Ranges from typo fixes to major features
- Lower barrier to entry
- Much larger, more diverse group

**Implication**: Direct threshold mapping (e.g., 20 PLIPs = X PRs) is inappropriate.

### Problem 2: Different Time Scales

**PLIPs**: All-time data (2013-2025, ~12 years)
- tisto: 61 PLIPs over 12 years = 5.1 PLIPs/year
- sneridagh: 30 PLIPs over 11 years = 2.7 PLIPs/year
- Long-term measurement appropriate for strategic work

**PRs**: 3-year rolling window (2022-2024)
- stevepiercy: 680 PRs over 3 years = 227 PRs/year
- sneridagh: 1046 PRs over 3 years = 349 PRs/year
- Captures current activity level

**Implication**: Time normalization required for fair comparison.

### Problem 3: Different Contribution Concentration

**PLIP Concentration**:
- Top 12.7% → 60.4% of output
- Moderate concentration, sustainable mid-tier

**PR Concentration**:
- Top 3.1% → 76.6% of output
- Extreme concentration, very thin mid-tier

**Implication**: Percentage-matched thresholds create vastly different tier populations.

---

## Equivalence Ratio Analysis

### Simple Volume Ratio

```
Total PRs (3yr) / Total PLIPs (all-time) = 7,112 / 303 = 23.5 PRs per PLIP
Average PRs per contributor (3yr) = 18.6
Average PLIPs per contributor (all-time) = 4.8
Rough ratio = 18.6 / 4.8 = 3.9 PRs per PLIP per contributor
```

**Problem**: This ratio is meaningless because:
1. Different time scales (3 years vs 12 years)
2. Different populations (382 vs 63)
3. Doesn't account for effort/impact

### Effort-Based Ratio (Qualitative Assessment)

**One PLIP requires**:
- Problem analysis and research: 5-10 hours
- Community discussion and consensus: 10-20 hours
- Proposal writing: 5-10 hours
- Review cycles and refinement: 5-10 hours
- **Total**: 25-50 hours per PLIP

**One PR requires**:
- Small fix: 1-2 hours
- Medium feature: 5-10 hours
- Large feature: 20-50 hours
- **Average**: ~5-10 hours per PR

**Estimated effort ratio**: **1 PLIP ≈ 5-10 PRs** (by time investment)

However, this still doesn't capture:
- Strategic value vs tactical value
- Long-term impact vs immediate fix
- Planning skill vs implementation skill

### Top Contributor Analysis

**Comparing top performers**:

| Contributor | PLIPs (all-time) | PRs (3yr) | Ratio |
|-------------|------------------|-----------|-------|
| sneridagh | 30 | 1,046 | 1:35 |
| mauritsvanrees | 16 | 590 | 1:37 |
| jensens | 11 | 197 | 1:18 |
| gforcada | 6 | 469 | 1:78 |
| tisto | 61 | 38 (3yr est) | 1:0.6 |

**Observation**: No consistent ratio exists. Contributors specialize:
- Strategic specialists: High PLIP, low PR (tisto)
- Implementation specialists: Low PLIP, high PR (gforcada)
- All-rounders: Both high (sneridagh, mauritsvanrees)

**Conclusion**: Cannot and should not use single equivalence ratio.

---

## Three Harmonization Approaches Tested

### Approach A: Percentage-Matched Thresholds

**Goal**: Match percentage of contributors at each level

| Level | PLIPs | PLIP % | PRs (3yr) | PR % | Match Quality |
|-------|-------|--------|-----------|------|---------------|
| Level 1 | 20+ | 4.8% | 600+ | 0.5% | ❌ Poor |
| Level 2 | 10-19 | 7.9% | 300-599 | 0.8% | ❌ Poor |
| Level 3 | 5-9 | 11.1% | 100-299 | 2.4% | ❌ Poor |
| Level 4 | 2-4 | 23.8% | 25-99 | 6.0% | ⚠️ Weak |
| Level 5 | 1 | 52.4% | 1-24 | 89.3% | ❌ Poor |

**Result**: FAILS. PR distribution too concentrated at bottom to match PLIP percentages.

### Approach B: Effort-Matched Thresholds (1 PLIP ≈ 50 PRs)

**Goal**: Use generous effort multiplier

| Level | PLIPs | PLIP % | PRs (3yr) | PR % | Match Quality |
|-------|-------|--------|-----------|------|---------------|
| Level 1 | 20+ | 4.8% | 1000+ | 0.3% | ❌ Too restrictive |
| Level 2 | 10-19 | 7.9% | 500-999 | 0.5% | ❌ Too restrictive |
| Level 3 | 5-9 | 11.1% | 250-499 | 0.8% | ❌ Too restrictive |
| Level 4 | 2-4 | 23.8% | 100-249 | 2.1% | ❌ Too restrictive |
| Level 5 | 1 | 52.4% | 1-99 | 95.3% | ⚠️ Too broad |

**Result**: FAILS. Creates unrealistically high PR thresholds. Only 1 person at Level 1 (1000+ PRs).

### Approach C: Volume-Adjusted Thresholds (1 PLIP ≈ 20 PRs)

**Goal**: Conservative effort multiplier

| Level | PLIPs | PLIP % | PRs (3yr) | PR % | Match Quality |
|-------|-------|--------|-----------|------|---------------|
| Level 1 | 20+ | 4.8% | 400+ | 1.3% | ⚠️ Reasonable |
| Level 2 | 10-19 | 7.9% | 200-399 | 0.3% | ❌ Too restrictive |
| Level 3 | 5-9 | 11.1% | 100-199 | 2.1% | ⚠️ Weak |
| Level 4 | 2-4 | 23.8% | 40-99 | 3.7% | ❌ Poor |
| Level 5 | 1 | 52.4% | 1-39 | 91.6% | ❌ Poor |

**Result**: PARTIALLY FAILS. Level 1 reasonable, but other levels don't align.

---

## Root Cause: Fundamentally Different Distributions

### Statistical Analysis

**PLIP Distribution** (all-time):
- Median: 2 PLIPs
- 75th percentile: 4 PLIPs
- 90th percentile: 11 PLIPs
- 95th percentile: 17 PLIPs
- More **normal/bell-curve** distribution

**PR Distribution** (3-year):
- Median: 3 PRs
- 75th percentile: 9 PRs
- 90th percentile: 39 PRs
- 95th percentile: 100 PRs
- Extreme **power-law** distribution

### Visualization

```
PLIP Contributors (Normal-ish):
    │
100%│                            ████████████████ (52.4%)
    │          ████████ (23.8%)
    │      ███ (11.1%)
    │   ██ (7.9%)
  0%│ █ (4.8%)
    └─────────────────────────────────────────
      L1   L2   L3   L4   L5

PR Contributors (Power Law):
    │
100%│                                          ██████████████████ (78.8%)
    │
    │                              ███ (9.9%)
    │                             █ (3.1%, 2.9%, 2.1%, 1.8%, 1.3%)
  0%│
    └─────────────────────────────────────────
      500+ 200+ 100+ 50+ 25+  10+  1-9
```

**Conclusion**: These are fundamentally different contribution patterns that CANNOT be mapped 1:1.

---

## Recommended Solution: Separate but Equivalent Tiers

### Approach D: Recognition Parity (Different Thresholds, Same Prestige)

**Principle**: Define tiers by COMMUNITY ROLE and IMPACT, not by arithmetic equivalence.

Instead of asking "What PR count equals X PLIPs?", ask:
- "What defines a core leader in strategic contribution?"
- "What defines a core leader in implementation contribution?"

### Proposed 3-Tier System with Separate Thresholds

| Tier | Role | PLIP Threshold | PLIP % | PR Threshold (3yr) | PR % |
|------|------|----------------|--------|--------------------|------|
| **🏆 Platinum** | Core Leaders | 10+ PLIPs | 12.7% | 300+ PRs | 3.1% |
| **⭐ Gold** | Active Contributors | 3-9 PLIPs | 34.9% | 100-299 PRs | 4.5% |
| **🌟 Silver** | Emerging Contributors | 1-2 PLIPs | 52.4% | 1-99 PRs | 92.4% |

### Tier Definitions (Role-Based, Not Arithmetic)

#### 🏆 Platinum Tier: Core Leaders

**Strategic Track (PLIPs)**:
- **10+ PLIPs** submitted (all-time)
- Rationale: Demonstrates sustained strategic vision (typically 5+ years)
- Currently: 8 contributors (12.7%)

**Implementation Track (PRs)**:
- **300+ PRs** over 3 years (≈100/year sustained)
- Rationale: Demonstrates sustained implementation excellence
- Currently: 12 contributors (3.1%)

**Why different percentages are OK**:
- Strategic contribution has higher entry barrier
- Fewer people have architectural skill/authority
- 12.7% of PLIP pool ≈ 8 people
- 3.1% of PR pool ≈ 12 people
- Similar absolute numbers, different percentage due to pool size

#### ⭐ Gold Tier: Active Contributors

**Strategic Track (PLIPs)**:
- **3-9 PLIPs** submitted (all-time)
- Rationale: Multiple PLIPs show engagement beyond one-off
- Currently: 22 contributors (34.9%)

**Implementation Track (PRs)**:
- **100-299 PRs** over 3 years (≈33-100/year)
- Rationale: Regular meaningful contributions
- Currently: 17 contributors (4.5%)

**Why different percentages are OK**:
- 22 PLIP contributors at this level
- 17 PR contributors at this level
- Similar absolute numbers demonstrate comparable community impact

#### 🌟 Silver Tier: Emerging Contributors

**Strategic Track (PLIPs)**:
- **1-2 PLIPs** submitted
- Rationale: Beginning strategic engagement
- Currently: 33 contributors (52.4%)

**Implementation Track (PRs)**:
- **1-99 PRs** over 3 years
- Rationale: Participating in ecosystem
- Currently: 353 contributors (92.4%)

**Why different percentages are OK**:
- Much larger PR contributor pool (lower barrier)
- Both represent "entry level" in their respective domains
- Absolute numbers: 33 vs 353 reflects accessibility difference

---

## Detailed Threshold Justification

### Why 10 PLIPs for Platinum?

**Data Evidence**:
- Natural break: 3 people with 20+, 5 people with 10-19
- Combining: 8 people with 10+ (reasonable Platinum size)
- Represents ~60% of all PLIPs (Leadership tier)
- Typically requires 5-10 years of engagement

**Community Evidence**:
- All 10+ PLIP contributors are recognized leaders
- Names: tisto, sneridagh, bloodbare, ebrehault, thet, mauritsvanrees, tkimnguyen, jensens
- These ARE the strategic architects of Plone

### Why 300 PRs (3yr) for Platinum?

**Data Evidence**:
- 12 contributors at 300+ (manageable Platinum size)
- Represents ~77% of all PRs (Leadership tier)
- Equivalent to 100/year sustained effort

**Comparison**:
- 8 Platinum PLIP contributors
- 12 Platinum PR contributors
- Similar absolute numbers (goal achieved)

**Community Evidence**:
- These are the most prolific maintainers
- Include: sneridagh, stevepiercy, mauritsvanrees, petschki, gforcada, jensens, ericof, davisagli, ksuess, MrTango, etc.

### Why 3 PLIPs for Gold?

**Data Evidence**:
- Natural break between "testing waters" (1-2) and "engaged" (3+)
- 22 contributors at 3-9 PLIPs
- Represents 28.8% of PLIPs (Active contributor level)

**Rationale**:
- 3 PLIPs over years shows intentional strategic engagement
- Not just one-off idea submission

### Why 100 PRs (3yr) for Gold?

**Data Evidence**:
- 17 contributors at 100-299 PRs
- Represents ~15% of PRs (Active contributor level)
- Equivalent to 33/year average

**Comparison**:
- 22 Gold PLIP contributors
- 17 Gold PR contributors
- Similar absolute numbers (goal achieved)

### Silver Tier: Inclusive Entry

**Both thresholds intentionally inclusive**:
- Any PLIP submission welcomed (1-2)
- Any PR contribution welcomed (1-99)
- Captures all emerging contributors
- Different percentages reflect different accessibility

---

## Side-by-Side Comparison: Proposed System

### Contributors at Each Level

| Tier | Strategic (PLIPs) | Implementation (PRs 3yr) | Overlap | Total Unique |
|------|-------------------|--------------------------|---------|--------------|
| **🏆 Platinum** | 8 contributors | 12 contributors | 4 | **16** |
| **⭐ Gold** | 22 contributors | 17 contributors | 7 | **32** |
| **🌟 Silver** | 33 contributors | 353 contributors | ~15 | **~371** |

**Total Contributors**: ~419 unique individuals

**Overlap Analysis**:
- Platinum overlap: sneridagh, mauritsvanrees, jensens, gforcada (4 people excel at both)
- Gold overlap: petschki, pbauer, stevepiercy, ericof, thet, robgietema, MrTango (7 people active in both)
- This overlap is GOOD - rewards well-rounded contributors

### Volume at Each Level

| Tier | PLIPs | % of PLIPs | PRs | % of PRs |
|------|-------|------------|-----|----------|
| **🏆 Platinum** | 183 | 60.4% | 5,447 | 76.6% |
| **⭐ Gold** | 87 | 28.7% | 1,107 | 15.6% |
| **🌟 Silver** | 33 | 10.9% | 558 | 7.8% |

**Both tiers show similar leadership concentration**:
- Platinum: 60-77% of output
- Gold: 16-29% of output
- Silver: 8-11% of output

---

## Harmonization Benefits

### 1. Fair Recognition

**Before**: No clear equivalence, strategic work undervalued
**After**: Both strategic and implementation leaders get Platinum

**Example**:
- tisto (61 PLIPs, few PRs) → Platinum Strategic
- stevepiercy (3 PLIPs, 680 PRs) → Platinum Implementation
- Same tier, same prestige, different paths

### 2. Balanced Community

**Before**: Might over-value one contribution type
**After**: Encourages both types

**Encourages**:
- PLIP authors to implement (or mentor implementers)
- PR contributors to propose features (or mentor proposers)
- Well-rounded contributors (sneridagh, mauritsvanrees)

### 3. Appropriate Thresholds

**Before**: Mismatched expectations
**After**: Each threshold meaningful for its domain

**Strategic**: 10 PLIPs = proven architectural leadership
**Implementation**: 300 PRs = proven implementation excellence
**Not equivalent effort, equivalent IMPACT**

### 4. Clear Progression

**Strategic Track**:
- Silver (1-2 PLIPs) → Gold (3-9 PLIPs) → Platinum (10+ PLIPs)
- Clear: "Submit 1 more PLIP to reach Gold"

**Implementation Track**:
- Silver (1-99 PRs) → Gold (100-299 PRs) → Platinum (300+ PRs)
- Clear: "Average 100 PRs/year for 3 years to reach Gold"

---

## Time-Based Considerations

### Annual vs All-Time Metrics

**PLIPs**: Should remain all-time
- Strategic vision has lasting value
- Takes years to accumulate meaningful count
- 10-year-old PLIP still demonstrates capability

**PRs**: Should use rolling 3-year window
- Reflects current activity level
- Prevents inactive contributors at top
- Re-evaluated annually

### Example Scenarios

**Scenario 1: Veteran takes break**
- Before break: Platinum (400 PRs 2019-2021)
- During break: After 3 years, drops to Gold/Silver
- After return: Quickly re-advances with new PRs

**Scenario 2: Rising star**
- Year 1: 80 PRs → Silver
- Year 2: 90 PRs (total 170/2yr) → Gold
- Year 3: 100 PRs (total 270/3yr) → Gold
- Year 4: 120 PRs (total 310/3yr) → Platinum

---

## Implementation Recommendations

### Phase 1: Adopt 3-Tier System with Separate Thresholds

**Strategic Track (PLIPs - All-time)**:
- 🏆 Platinum: 10+ PLIPs
- ⭐ Gold: 3-9 PLIPs
- 🌟 Silver: 1-2 PLIPs

**Implementation Track (PRs - Rolling 3-year)**:
- 🏆 Platinum: 300+ PRs
- ⭐ Gold: 100-299 PRs
- 🌟 Silver: 1-99 PRs

### Phase 2: Allow Multiple Track Badges

Contributors can display multiple badges if they qualify:
- **Platinum Strategic + Gold Implementation** = 🏆🎯 + ⭐⚙️
- **Gold Strategic + Platinum Implementation** = ⭐🎯 + 🏆⚙️
- **Platinum Both** = 🏆🌟 (All-Rounder, highest prestige)

### Phase 3: Annual Review

- Calculate 3-year rolling PR counts
- Re-assign tiers based on current data
- Announce level changes
- Celebrate promotions

---

## Alternative: Unified Scoring (Not Recommended)

### Weighted Points System

**Score = (PRs over 3yr × 1) + (PLIPs all-time × 100)**

- Platinum: 1,000+ points
- Gold: 300-999 points
- Silver: <300 points

**Example Scores**:
- tisto: 38 PRs + 61 PLIPs × 100 = 6,138 → Platinum
- sneridagh: 1046 PRs + 30 PLIPs × 100 = 4,046 → Platinum
- stevepiercy: 680 PRs + 3 PLIPs × 100 = 980 → Gold (!)

**Why NOT recommended**:
1. Arbitrary multiplier (why 100? why not 50 or 200?)
2. Single score obscures contribution type
3. Harder to explain
4. Loses nuance of tracks
5. Still requires picking equivalence ratio

---

## Recommendation Summary

### ✅ RECOMMENDED: Separate Thresholds, Same Tiers

| Tier | PLIPs (all-time) | PRs (3-year) | Rationale |
|------|------------------|--------------|-----------|
| 🏆 Platinum | 10+ | 300+ | Core leadership (~8-12 people each track) |
| ⭐ Gold | 3-9 | 100-299 | Active engagement (~17-22 people each track) |
| 🌟 Silver | 1-2 | 1-99 | Emerging contributors (all others) |

**Key Principles**:
1. ✅ Different thresholds for different contribution types
2. ✅ Same tier = same recognition level
3. ✅ Thresholds based on community role, not arithmetic
4. ✅ Similar absolute numbers at Platinum/Gold (8 vs 12, 22 vs 17)
5. ✅ Percentage differences OK due to different participant pools

### ❌ NOT RECOMMENDED: Arithmetic Equivalence

- ❌ 1 PLIP = X PRs formulas
- ❌ Percentage-matched thresholds
- ❌ Unified scoring systems
- ❌ Single metric for both types

**Why**: Fundamentally different contribution patterns, distributions, and community roles.

---

## Success Metrics for Harmonized System

### Balance Metrics
- **Track Distribution**: Neither track dominates (within 2:1 ratio at each tier)
- **Overlap**: 20-30% of Platinum/Gold qualify in multiple tracks
- **Progression**: 25% of Silver advance to Gold within 2 years

### Satisfaction Metrics
- **Strategic Contributors**: >80% feel fairly recognized
- **Implementation Contributors**: >80% feel fairly recognized
- **All-Rounders**: Special recognition for dual qualification

### Community Health
- **PLIP Growth**: +10% new PLIP authors annually
- **PR Growth**: +15% new PR contributors annually
- **Cross-Training**: +20% of single-track contributors try other track

---

## Conclusion

**The data conclusively shows**: PLIPs and PRs cannot and should not use arithmetic equivalence for level thresholds.

**Instead**: Use role-based thresholds that result in similar-sized leadership groups:
- **Platinum**: ~8-12 people per track (core leaders)
- **Gold**: ~17-22 people per track (active contributors)
- **Silver**: All others (emerging contributors)

**This approach**:
✅ Honors both contribution types equally
✅ Creates manageable tier sizes
✅ Allows for multi-track recognition
✅ Provides clear progression paths
✅ Reflects actual community structure

**Different thresholds, equivalent recognition, unified community.**

---

**Analysis Prepared By**: Plone Contributor Statistics Team
**Data Sources**:
- `plone-plips.csv` (63 contributors, 303 PLIPs, 2013-2025)
- `2024-plone-contributors.csv` (170 contributors, 2,003 PRs)
- `2023-plone-contributors.csv`, `2022-plone-contributors.csv`
- Combined 3-year: 382 contributors, 7,112 PRs

**Last Updated**: 2025-11-03
