# Recommendation: Harmonized Contributor Level System

**Date**: 2025-11-03
**Status**: Final Recommendation
**Approval Needed**: Plone Framework Team, Foundation Board

---

## Executive Summary

After detailed analysis of **303 PLIPs from 63 contributors** and **7,112 PRs from 382 contributors** (3-year), we recommend a **unified 3-tier system with separate thresholds** for strategic (PLIP) and implementation (PR) contributions.

**Key Insight**: PLIPs and PRs have fundamentally different distributions and cannot use arithmetic equivalence (no valid "1 PLIP = X PRs" exists).

**Solution**: Role-based thresholds that create similar-sized leadership tiers (~8-12 Platinum, ~17-22 Gold per track).

---

## Recommended System: 3 Tiers, 2 Tracks

### Tier Definitions

| Tier | Strategic Track (PLIPs) | Implementation Track (PRs) | Recognition |
|------|-------------------------|----------------------------|-------------|
| **🏆 Platinum** | **10+ PLIPs** (all-time) | **300+ PRs** (3-year rolling) | Core Leaders |
| **⭐ Gold** | **3-9 PLIPs** (all-time) | **100-299 PRs** (3-year rolling) | Active Contributors |
| **🌟 Silver** | **1-2 PLIPs** (all-time) | **1-99 PRs** (3-year rolling) | Emerging Contributors |

### Current Distribution

| Tier | Strategic Contributors | Implementation Contributors | Example Contributors |
|------|------------------------|----------------------------|----------------------|
| **🏆 Platinum** | 8 people (12.7%) | 12 people (3.1%) | tisto, sneridagh, mauritsvanrees |
| **⭐ Gold** | 22 people (34.9%) | 17 people (4.5%) | pbauer, gforcada, davisagli |
| **🌟 Silver** | 33 people (52.4%) | 353 people (92.4%) | All newcomers & emerging |

**Total Unique Contributors**: ~419 people
**Multi-Track Qualifiers**: ~16 people (recognized leaders in both)

---

## Why Different Thresholds?

### The Data Shows Fundamental Differences

**PLIP Distribution** (Normal-ish):
```
Contributors: 63 (specialized, high barrier)
Median: 2 PLIPs
Top 10%: 10+ PLIPs
Concentration: Top 13% produce 60% of PLIPs
```

**PR Distribution** (Power Law):
```
Contributors: 382 (broad, lower barrier)
Median: 3 PRs
Top 10%: 100+ PRs
Concentration: Top 3% produce 77% of PRs
```

### Arithmetic Equivalence Fails

**Tested ratios**:
- ❌ 1 PLIP = 50 PRs → Only 1 person qualifies for Platinum PR (too restrictive)
- ❌ 1 PLIP = 20 PRs → Percentages don't align (1.3% vs 4.8%)
- ❌ 1 PLIP = 3.9 PRs (volume ratio) → Undervalues strategic work

**Conclusion**: No single multiplier works. Different contribution types require different thresholds.

---

## Rationale for Each Threshold

### 🏆 Platinum: 10 PLIPs / 300 PRs

**PLIPs (10+)**:
- 8 contributors qualify (tisto, sneridagh, bloodbare, ebrehault, thet, mauritsvanrees, tkimnguyen, jensens)
- Represents 60% of all PLIPs
- Typically requires 5-10 years of strategic engagement
- These ARE Plone's strategic architects

**PRs (300+ over 3yr = ~100/year)**:
- 12 contributors qualify
- Represents 77% of all PRs
- Similar absolute size to PLIP Platinum (8 vs 12)
- These ARE Plone's core maintainers

### ⭐ Gold: 3-9 PLIPs / 100-299 PRs

**PLIPs (3-9)**:
- 22 contributors qualify
- Natural break: 3+ shows sustained engagement vs 1-2 "testing"
- Represents 29% of all PLIPs

**PRs (100-299 over 3yr = ~33-100/year)**:
- 17 contributors qualify
- Similar absolute size to PLIP Gold (22 vs 17)
- Represents 16% of all PRs

### 🌟 Silver: 1-2 PLIPs / 1-99 PRs

**Inclusive entry level**:
- All remaining contributors welcomed
- Different percentages (52% vs 92%) reflect different accessibility
- Both represent "emerging" in their respective domains

---

## Key Benefits

### 1. Fair Recognition
- Strategic architects (tisto: 61 PLIPs) get Platinum
- Implementation champions (stevepiercy: 680 PRs) get Platinum
- **Same tier, same prestige, different paths**

### 2. Multiple Qualification Paths
Contributors can earn tier via:
- Strategic track only (🏆🎯)
- Implementation track only (🏆⚙️)
- Both tracks (🏆🌟 All-Rounder, highest prestige)

### 3. Clear Progression
- Strategic: "Submit 1 more PLIP to reach Gold" (clear target)
- Implementation: "Maintain 100 PRs/year for Gold" (clear target)

### 4. Manageable Tier Sizes
- Platinum: ~20 total people (8 strategic + 12 implementation)
- Gold: ~40 total people (22 strategic + 17 implementation)
- Silver: ~370 total people (all others)

---

## Implementation Plan

### Phase 1: Adoption (Month 1)
1. Framework Team approval
2. Foundation Board sign-off
3. Communication plan drafted

### Phase 2: Technical (Month 2)
1. Calculate all contributor tiers
2. Design tier/track badges
3. Update plone.org with tier pages
4. Email all contributors with their tier/track

### Phase 3: Recognition (Month 3)
1. Announce Platinum/Gold tiers
2. Blog post series featuring contributors
3. Launch tier-specific benefits
4. Conference recognition

### Phase 4: Programs (Month 4-6)
1. Platinum advisory committee
2. Gold mentorship program
3. Silver onboarding workshops
4. Annual tier review process

---

## Comparison: Before vs After

### Before (Inconsistent)

**PLIPs**: 5-level system (20/10/5/2/1)
- Top heavy: 4.8% at Level 1
- Works well for strategic contributions

**PRs**: No formal system
- Ad-hoc recognition
- Implementation work undervalued

### After (Harmonized)

**Both**: 3-tier system with separate thresholds
- PLIPs: 10/3-9/1-2
- PRs: 300/100-299/1-99
- Equal recognition at each tier
- Similar absolute numbers at Platinum/Gold

---

## Success Metrics (Year 1)

### Engagement
- [ ] +15% new PLIP submissions
- [ ] +10% new PR contributors
- [ ] 25% of Silver advance to Gold

### Recognition
- [ ] >80% contributor satisfaction with tier system
- [ ] 20-30% multi-track qualifiers at Platinum/Gold
- [ ] Zero complaints about unfairness

### Community
- [ ] Improved geographic diversity in Platinum
- [ ] Balanced growth across both tracks
- [ ] Clear communication of advancement paths

---

## Frequently Asked Questions

### Q: Why not use "1 PLIP = X PRs"?

**A**: Analysis shows no consistent ratio exists. Contributors specialize:
- sneridagh: 1 PLIP ≈ 35 PRs
- tisto: 1 PLIP ≈ 0.6 PRs
- No single multiplier captures both patterns

### Q: Why are the percentages different?

**A**: Different pool sizes and accessibility:
- PLIPs: 63 contributors (higher barrier, specialized)
- PRs: 382 contributors (lower barrier, broad)
- Similar ABSOLUTE numbers at each tier (goal achieved)

### Q: Can I qualify via both tracks?

**A**: Yes! Multi-track recognition:
- Platinum Strategic + Platinum Implementation = 🏆🌟 All-Rounder (highest prestige)
- Currently ~4 people qualify (sneridagh, mauritsvanrees, jensens, gforcada)

### Q: What if I'm inactive for a while?

**A**:
- PLIPs: Permanent (all-time count, strategic value persists)
- PRs: Rolling 3-year window with 1-year grace period
- Can quickly re-advance after returning

### Q: How do I advance?

**A**: Clear paths:
- Silver → Gold Strategic: Submit 1-2 more PLIPs
- Silver → Gold Implementation: Reach 100 PRs over 3 years
- Gold → Platinum Strategic: Reach 10 total PLIPs
- Gold → Platinum Implementation: Sustain 100+ PRs/year

---

## Decision Points

### Required Decisions

1. **Approve thresholds**:
   - [ ] Platinum: 10 PLIPs / 300 PRs (3yr)
   - [ ] Gold: 3-9 PLIPs / 100-299 PRs (3yr)
   - [ ] Silver: 1-2 PLIPs / 1-99 PRs (3yr)

2. **Approve 3-year rolling window for PRs**:
   - [ ] Yes, use rolling 3-year with annual review
   - [ ] No, use different timeframe: ___________

3. **Approve multi-track recognition**:
   - [ ] Yes, contributors can qualify via multiple tracks
   - [ ] No, assign single primary track only

4. **Approve implementation timeline**:
   - [ ] Launch in Q1 2025
   - [ ] Launch in Q2 2025
   - [ ] Different timeline: ___________

### Optional Enhancements

- [ ] Add 4th tier (Diamond) for exceptional contributors (20+ PLIPs, 1000+ PRs)
- [ ] Add track badges for documentation, community support
- [ ] Create "Emeritus" status for retired long-time contributors
- [ ] Add organization-level tiers alongside individual tiers

---

## Approval

**Recommended by**: Plone Contributor Statistics Analysis Team
**Date**: 2025-11-03

**Approved by**:

- [ ] Plone Framework Team: ___________________ Date: _______
- [ ] Plone Foundation Board: ___________________ Date: _______

**Implementation Owner**: ___________________________

**Target Launch Date**: ___________________________

---

## Supporting Documents

- `ANALYSIS-level-harmonization.md` - Detailed statistical analysis (70+ pages)
- `PROPOSAL-combined-contributor-levels.md` - Complete proposal with all options
- `plip-contributor-levels.md` - PLIP-only level analysis
- `report/github.md` - PR contribution statistics
- `plone-plips.csv` - PLIP data (303 PLIPs, 63 contributors)
- `2024-plone-contributors.csv` - PR data (2,003 PRs, 170 contributors)

---

**Next Steps After Approval**:

1. Week 1: Communicate to all contributors via email/blog
2. Week 2: Calculate and assign all tiers
3. Week 3: Design and deploy badges
4. Week 4: Update plone.org with tier pages
5. Month 2: Launch recognition programs
6. Month 3: First quarterly review

---

*This recommendation is based on rigorous statistical analysis of 12 years of PLIP data and 3 years of PR data, representing contributions from 400+ community members.*
