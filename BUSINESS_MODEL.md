# WASL Business Model & Financial Analysis

> ⚠ **IMPORTANT**: All financial figures in this document are **unverified assumptions**.
> They must be validated through market research, pilot testing, and real operational data
> before being used for any business decisions.

---

## Business Model Summary

WASL is a B2B SaaS platform that enables merchants to manage last-mile delivery logistics.

**Core model**: WASL earns a commission on each successful delivery.

**Target market**: Merchants in Alexandria, Egypt who receive orders through social media (Instagram, Facebook, WhatsApp) or their own stores and need a managed delivery solution.

**Not**: A consumer marketplace. Customers do not order through WASL.

---

## Revenue Streams

### Primary: Per-Delivery Commission (MVP)

| Parameter | Assumed Value | Validation Required |
|-----------|--------------|-------------------|
| Delivery fee charged to merchant | 15 EGP | Survey merchants and compare with competitors |
| Driver payout per delivery | 10 EGP | Survey drivers; compare with taxi/ride-hail earnings |
| Platform revenue per delivery | 5 EGP | Verify cost coverage before committing |
| Platform gross margin | 33% | Recalculate once real costs are known |

**Payment model**: Merchant collects cash from customer. Merchant settles delivery fees with WASL weekly.

### Secondary Revenue Streams (Deferred — Not MVP)

| Stream | Phase | Description |
|--------|-------|-------------|
| Merchant subscription | Phase 2 | 500–1,000 EGP/month for premium features |
| Surge pricing | Phase 2 | Peak-hour multiplier, platform keeps portion |
| Advertising | Phase 3+ | Featured merchant slots, promoted listings |
| Data products | Phase 3+ | Anonymised market insights |

---

## Unit Economics (Assumed — Unverified)

```
Per Delivery:
  Delivery fee collected from merchant:  15 EGP
  Driver payout:                        -10 EGP
  Payment processing (future):           -0.25 EGP (assumed)
  ─────────────────────────────────────────────
  Platform contribution margin:           4.75 EGP

Monthly Fixed Costs (Estimated):
  Infrastructure (hosting, DB, CDN):     1,500 EGP
  Communication (SMS, email):            1,000 EGP
  Third-party services (monitoring):       500 EGP
  Admin/support labour (part-time):      2,000 EGP
  Contingency (10%):                       500 EGP
  ─────────────────────────────────────────────
  Total estimated monthly fixed costs:   5,500 EGP
```

> These cost estimates have not been confirmed with actual invoices or quotes.

---

## Break-Even Analysis (Assumed)

```
Break-even orders per month = Fixed Costs ÷ Contribution Margin
                             = 5,500 ÷ 4.75
                             = ~1,158 orders/month
                             = ~39 orders/day

Target (conservative):       400 orders/day (10× break-even assumed)
```

> The 400 orders/day figure is an unvalidated target, not a confirmed market size.

---

## Volume Scenarios (All Figures Assumed)

| Scenario | Orders/day | Monthly Revenue (EGP) | Monthly Cost (EGP) | Monthly Profit (EGP) |
|----------|-----------|----------------------|-------------------|---------------------|
| Pilot | 50 | 7,500 | 5,500 | 2,000 |
| Early growth | 150 | 22,500 | 5,750 | 16,750 |
| Break-even target | 400 | 60,000 | 6,000 | 54,000 |
| Scale | 800 | 120,000 | 7,000 | 113,000 |

> All scenario figures are illustrative projections, not forecasts.

---

## Ramp-Up Timeline (Assumed)

| Month | Merchants | Drivers | Orders/day | Result |
|-------|-----------|---------|-----------|--------|
| 1 | 10 | 30 | 20 | Operating loss |
| 2 | 20 | 60 | 50 | Small profit |
| 3 | 40 | 120 | 100 | Growing profit |
| 6 | 100 | 250 | 400 | Target reached |
| 12 | 200+ | 500+ | 800+ | Scale phase |

> These timelines are hypothetical. Actual adoption depends on market conditions.

---

## Payment & Settlement Flows

### Cash on Delivery (MVP Only)

```
Customer → pays cash to driver on delivery
Driver   → holds collected cash
Weekly:
  Driver  → remits cash to WASL (or keeps net earnings)
  Merchant → receives delivery summary invoice from WASL
  Merchant → pays WASL commission (5 EGP × orders) via bank transfer
  WASL    → pays driver net earnings (10 EGP × deliveries)
```

### Settlement Cycle

| Party | Frequency | Method (MVP) |
|-------|-----------|-------------|
| Merchant pays WASL | Weekly (every Sunday) | Bank transfer or cash |
| WASL pays driver | Weekly (every Friday) | Cash handoff or bank transfer |

### Reconciliation

- Every delivered order creates two immutable `financial_transactions` records
- Weekly `settlement_records` aggregate transactions for the period
- Admin verifies settlement totals against transaction log before processing
- Discrepancies logged as support tickets for investigation

---

## Market Sizing (Assumed — Unverified)

| Segment | Estimated Count | Source |
|---------|----------------|--------|
| Alexandria restaurants | ~3,000 | Unverified estimate |
| Retail shops | ~5,000 | Unverified estimate |
| Pharmacies | ~500 | Unverified estimate |
| Other merchants | ~5,000 | Unverified estimate |
| **Total addressable** | **~13,500** | **Requires validation** |

**Year 1 penetration target**: 1% (~135 merchants) — unverified

---

## Key Assumptions Requiring Validation

All items below must be confirmed through research and pilot data before they can be treated as facts.

| # | Assumption | How to Validate |
|---|-----------|----------------|
| 1 | Delivery fee of 15 EGP is acceptable to merchants | Survey 20+ merchants |
| 2 | Driver payout of 10 EGP is competitive | Survey 50+ drivers; compare ride-hail rates |
| 3 | Average order value is ~150 EGP | Sample 100+ real orders |
| 4 | Delivery takes 30–45 minutes on average | Measure in pilot |
| 5 | Order completion rate ≥ 95% | Track in pilot |
| 6 | Monthly fixed costs ≤ 6,000 EGP | Confirm with actual invoices |
| 7 | 13,500 addressable merchants in Alexandria | Verify with business directory |
| 8 | Break-even at 400 orders/day achievable in 6 months | Monitor pilot growth |
| 9 | Cash payment collection rate ≥ 90% | Track in pilot |
| 10 | Merchant monthly churn ≤ 5% | Measure after Month 2 |

---

## Competitive Landscape (Unverified)

| Competitor | Type | Assumed Commission | WASL Advantage |
|-----------|------|-------------------|---------------|
| Talabat | Consumer marketplace | 25–35% of order value | Lower cost, B2B focus |
| Uber Eats | Consumer marketplace | Similar to Talabat | Merchant-first workflow |
| Local operators | Manual dispatch | Variable | Technology + tracking |

> Competitor commission rates are estimates and must be verified before using in sales material.

---

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Delivery fee too high | Low merchant adoption | Medium | Test with pilot; adjust |
| Driver payout uncompetitive | Cannot recruit drivers | High | Benchmark before launch |
| Cash collection failures | Revenue shortfall | Medium | Strict weekly settlement |
| Competitor response | Price pressure | High | Focus on service quality |
| Order completion drops | Merchant churn | Medium | Monitor KPIs weekly |
| Fixed costs underestimated | Losses extend | Medium | Track monthly, adjust |

---

## Monetisation Phases

| Phase | Months | Revenue Model |
|-------|--------|--------------|
| 0 — Pilot | 1–3 | Per-delivery commission only (5 EGP assumed) |
| 1 — Validation | 4–6 | Commission + refine pricing based on data |
| 2 — Tiers | 7–12 | Add merchant subscriptions |
| 3 — Scale | Year 2 | Surge pricing, advertising, data products |

---

## Validation Roadmap

### Before Launch
- [ ] Interview 20+ merchants about current delivery costs and pain points
- [ ] Interview 30+ drivers about compensation expectations
- [ ] Map top 3 competitors and confirm their commission rates
- [ ] Confirm infrastructure costs with Railway/Supabase pricing pages

### Pilot Phase (Month 1–2)
- [ ] Track actual delivery times (target: 30–45 min)
- [ ] Track actual payment collection rates
- [ ] Record real fixed and variable costs
- [ ] Survey merchant satisfaction monthly

### Go/No-Go Decision (Month 3)
- [ ] Compare actual unit economics to assumptions in this document
- [ ] Adjust financial model with real data
- [ ] Decide on pricing changes, if any
- [ ] Confirm expansion plan or pivot
