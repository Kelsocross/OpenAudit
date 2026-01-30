# OpenAudit Platform - Audit Logic & Expected Outcomes

**Version:** 2.0  
**Last Updated:** January 2026  
**System:** OpenAudit Platform

---

## Overview

OpenAudit analyzes FedEx shipping invoices to identify billing errors and potential refunds. The platform performs three core audit checks that generate actionable findings, plus additional informational analyses for quality control.

---

## Core Audit Checks

These checks identify billing errors that can be disputed with carriers for refunds.

### 1. Late Delivery Detection

**What It Checks:**  
Identifies shipments that were delivered after the carrier's guaranteed delivery commitment.

**Eligible Services (FedEx Only):**  
Only guaranteed services are checked:
- PO - FedEx Priority Overnight (next day by 10:30 AM)
- FO - FedEx First Overnight (next day by 8:30 AM)
- SO - FedEx Standard Overnight (next day by 3:00 PM)
- ES - FedEx 2Day (2 business days)
- OA/IP - FedEx International Priority
- LO - FedEx International Priority Express

**Logic:**
1. Calculate expected delivery date based on shipment date + service commitment
2. Compare expected date to actual delivery date
3. Flag if delivery occurred after expected date

**Expected Refund Rate:** 95-100%  
FedEx's Money-Back Guarantee provides full refunds for late deliveries on guaranteed services.

**Filing Window:** 15 days from delivery date

---

### 2. Duplicate Tracking Detection

**What It Checks:**  
Identifies the same tracking number billed multiple times (excluding legitimate patterns).

**Logic:**
1. Group shipments by normalized tracking number
2. Classify each line as TRANSPORT, DUTY_TAX, or CREDIT
3. Flag tracking numbers with multiple TRANSPORT charges

**Legitimate Patterns (Not Flagged):**
- Transport line + Duty/Tax line (landed cost split for international)
- Original shipment + Return Manager (RMGR) service

**Expected Refund Rate:** 90-100%  
Clear billing errors are typically approved.

**Filing Window:** 180 days from invoice date

---

### 3. Disputable Surcharges

**What It Checks:**  
Identifies surcharges that may be incorrectly applied and can be disputed.

**Surcharge Categories Validated:**

| Surcharge Type | Validation Logic | Expected Refund |
|----------------|------------------|-----------------|
| **Residential on Business** | Flags residential surcharges applied to addresses with business indicators (LLC, INC, retail stores, etc.) | 100% if proven commercial |
| **Additional Handling** | Checks if package meets threshold: longest side >48", second side >30", L+Girth >105", or weight ≥50 lbs | 100% if thresholds not met |
| **Oversize** | Checks if package exceeds limits: longest side >96" or L+Girth >130" | 100% if limits not exceeded |
| **Address Correction** | Flags for review - often applied in error | 80% with documentation |
| **Fuel Surcharge** | Flags if fuel surcharge exceeds 30% of net charge | 30% of excess amount |
| **Blank Description** | Flags charges with missing/blank description - FedEx must provide reason for all charges | 100% |

**Business Indicators for Residential Disputes:**
- Generic: LLC, INC, CORP, COMPANY, BUSINESS, OFFICE, WAREHOUSE, STORE
- Retail: SEPHORA, ULTA, NORDSTROM, MACY, TARGET, MAC COSMETICS, etc.
- Location names: MALL OF AMERICA, VALLEY FAIR, etc.

**Filing Window:** 180 days from invoice date

---

## Informational Analyses

These analyses provide insights but are NOT included in potential savings calculations.

### Residential Surcharge Review

**Purpose:** Show shipments with residential surcharges for confirmation.

**Logic:**
1. Detect all shipments with residential surcharge patterns
2. Exclude those with business indicators (moved to Disputable Surcharges)
3. Present remaining for manual review

**Output:** Helps confirm legitimate residential deliveries vs. missed disputes.

---

## Freight Direction Classification

**Purpose:** Classify shipments as Inbound or Outbound based on shipper address.

**Logic:**
- Outbound: Shipper address matches configured warehouse addresses
- Inbound: All other shipments

**Configurable:** Users can set their warehouse addresses in Settings.

**Output:** Dashboard shows cost breakdown by direction; included in all exports.

---

## Data Requirements

### Required Fields
- Tracking Number
- Carrier
- Service Type
- Shipment Date
- Zone
- Total Charges

### Optional Fields (Enable Additional Checks)
- Delivery Date (for late delivery detection)
- Dimensions (for surcharge validation)
- Surcharge Details (for disputable surcharge detection)
- Reference Notes (for dimension variance grouping)

---

## Summary Statistics

After each audit, OpenAudit calculates:

| Metric | Description |
|--------|-------------|
| **Total Charges Audited** | Sum of all shipment charges processed |
| **Potential Savings** | Sum of refund estimates from all findings |
| **Savings Rate** | Potential Savings ÷ Total Charges × 100 |
| **Affected Shipments** | Count of shipments with at least one error |
| **Total Shipments** | Count of all shipments processed |

---

## Claim Submission

OpenAudit identifies disputes but does not automatically file claims. Users must:

1. Review findings on the Refund Recovery page
2. Select claims to submit
3. Choose submission method:
   - **Email Report:** Generates formatted email with Excel attachment
   - **FedEx Bulk Upload:** Creates Excel file in FedEx's required format

---

## Filing Windows Summary

| Claim Type | Window | Notes |
|------------|--------|-------|
| Late Delivery (MBG) | 15 days | From delivery date |
| Billing Disputes | 180 days | From invoice/shipment date |
| Lost/Damage Claims | 60 days | From shipment date |

Claims outside these windows are automatically filtered on the Refund Recovery page.

---

## Limitations

1. **Guaranteed Services Only:** Late delivery detection only works for FedEx services with Money-Back Guarantee
2. **Data Dependent:** Accuracy depends on completeness of uploaded data
3. **No Holiday Calendar:** Business day calculations exclude weekends but not holidays
4. **Manual Submission:** Claims must be manually filed with carriers
5. **Estimate Accuracy:** Refund estimates are projections; actual approvals may vary

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | January 2026 | Simplified documentation to reflect current functionality |
| 1.6 | December 2025 | Added blank surcharge description detection |
| 1.5 | December 2025 | Removed Misc Charges Review page |
| 1.4 | November 2025 | Enhanced fuel surcharge validation for international shipments |
| 1.3 | November 2025 | Added dimension variance detection |
| 1.2 | November 2025 | Added freight direction classification |
