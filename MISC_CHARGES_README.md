# FedEx Miscellaneous Charges Detection Feature

## Overview

The FedEx Miscellaneous Charges Detection feature automatically identifies and categorizes non-shipment charges in your FedEx billing data, such as:

- **Address Corrections**: Fees for incorrect/incomplete addresses
- **Duties/Taxes**: Import duties, VAT, customs charges
- **Paper Invoice Fees**: Charges for paper billing
- **Misc Adjustments**: General adjustments and corrections

## Quick Start

### 1. Run Tests

```bash
make test
```

All 6 tests should pass successfully.

### 2. Start the Application

```bash
make run
# OR
streamlit run pages/03_Misc_Charges.py --server.port 5000
```

### 3. Upload Sample Data

Navigate to the **Misc Charges Detection** page and upload the sample file:
- `sample_data/fedex_misc_sample.xlsx`

This file contains 3 test cases:
1. A miscellaneous charge (will be flagged)
2. A valid FedEx Ground shipment (will NOT be flagged)
3. A duties/taxes charge (will be flagged)

## How It Works

### Detection Algorithm

The system uses a **6-feature scoring system** to identify miscellaneous charges:

1. **Service Blank**: Service Type and Service Description are empty
2. **Delivery Missing**: Delivery Date is 1900-01-01 (FedEx placeholder)
3. **Pay Type Misc**: Pay Type indicates non-standard billing
4. **Ship-To Missing**: Recipient Name is blank
5. **Non-Standard Tracking**: Tracking number is not 12, 15, or 22 digits
6. **Express OPCO**: Charge is from Express division

**Threshold**: A charge needs a score of **≥3** to be flagged as miscellaneous.

### Categorization

Flagged charges are automatically categorized based on keywords:

| Category | Keywords (Pay Type or Description) |
|----------|-----------------------------------|
| Address Correction | address, correction, correction fee |
| Duties/Taxes | dutytax, tax, vat, duty, customs, tariff, import |
| Paper Invoice Fee | paper, invoice fee, billing fee |
| Misc Adjustment | (default category) |

### Confidence Score

Confidence ranges from 0.0 to 1.0 based on the number of features matched:
- **1.0**: All 6 features matched
- **0.83**: 5 features matched
- **0.67**: 4 features matched
- **0.50**: 3 features matched (minimum)

## Using the Interface

### Main Features

1. **File Upload**: Upload CSV or Excel files with FedEx billing data
2. **Summary Metrics**: View total misc charges detected, amounts, and averages
3. **Rollup Reports**:
   - By Category: See totals grouped by charge type
   - By Month: Track trends over time
4. **Exceptions Queue**: Detailed list of all detected charges
5. **Filters**:
   - Confidence Threshold: Show only high-confidence detections
   - Category Filter: Focus on specific charge types

### Triage Workflow

Use the built-in triage helper to:

1. **Verify** each charge in FedEx Billing Online
2. **Determine Disposition**:
   - Dispute: Incorrect/unauthorized charge
   - Rebill: Valid but needs reallocation
   - Accept: Valid and properly allocated
3. **Export for Tracking**: Download filtered results as CSV
4. **Document Decisions**: Add owner, due date, and notes

### Download Options

Three CSV exports available:
1. **Exceptions Queue**: Full list of detected charges (filterable)
2. **By Category**: Summary grouped by charge type
3. **By Month**: Time-series analysis

## Expected File Format

Your FedEx export file should include these columns:

**Required:**
- OPCO
- Service Type
- Service Description
- Pay Type
- Shipment Date (mm/dd/yyyy)
- Shipment Delivery Date (mm/dd/yyyy)
- Shipment Tracking Number
- Shipment Miscellaneouse Charge USD (or Shipment Miscellaneous Charge USD or Charge Amount USD)

**Optional (improves detection):**
- Recipient Name
- Charge Description
- Invoice Number

## Testing with Sample Data

The included sample file (`sample_data/fedex_misc_sample.xlsx`) demonstrates:

**Row 1 - Misc Charge (Will be flagged)**:
- OPCO: Express
- Service Type: (empty)
- Pay Type: Other4
- Delivery Date: 01/01/1900
- Tracking: 5416334 (7 digits, non-standard)
- Amount: $42.00
- **Expected**: Flagged as "Misc Adjustment" with confidence 1.0

**Row 2 - Valid Shipment (Will NOT be flagged)**:
- OPCO: Ground
- Service Type: FEDEX_GROUND
- Pay Type: Bill_Sender_Prepaid
- Delivery Date: 09/17/2025 (valid)
- Tracking: 123456789012 (12 digits, standard)
- Amount: $15.50
- **Expected**: Not flagged (score below threshold)

**Row 3 - Duties/Taxes (Will be flagged)**:
- OPCO: Express
- Service Type: (empty)
- Pay Type: DutyTax
- Delivery Date: 01/01/1900
- Tracking: 98765 (5 digits, non-standard)
- Amount: $35.75
- Charge Description: "Import VAT charges"
- **Expected**: Flagged as "Duties/Taxes" with high confidence

## Integration with MAG Freight Analysis

This feature complements the existing freight audit capabilities:

- **Late Deliveries**: Service guarantee violations
- **Duplicate Tracking**: Duplicate billing errors
- **Disputable Surcharges**: 40+ charge types validation
- **Misc Charges**: Non-shipment charge detection (NEW)

All features maintain **zero data persistence** - uploaded data is never saved to disk or database.

## Troubleshooting

### No charges detected?
- Verify your file has the required columns
- Check that charges meet the threshold (score ≥3)
- Lower the confidence threshold in the sidebar

### Too many false positives?
- Increase the confidence threshold (try 0.7 or 0.8)
- Use category filters to focus on specific types
- Review the feature weights in `audits/misc_nonship.py`

### Want to customize detection?
Edit `audits/misc_nonship.py`:
- Modify `MISC_THRESHOLD` (default: 3)
- Adjust category keywords in `categorize_misc()`
- Add custom pay type patterns

## Technical Details

**Files Created:**
- `audits/misc_nonship.py`: Core detection module
- `pages/03_Misc_Charges.py`: Streamlit UI
- `tests/test_misc_nonship.py`: Unit tests
- `sample_data/fedex_misc_sample.xlsx`: Sample data
- `Makefile`: Build automation

**Dependencies:**
All required packages already in `pyproject.toml`:
- pandas
- numpy
- streamlit
- openpyxl

**Testing:**
```bash
# Run unit tests
make test

# Or directly
python3 tests/test_misc_nonship.py
```

## Support

For questions or issues:
1. Review the test cases in `tests/test_misc_nonship.py`
2. Check the sample data format in `sample_data/`
3. Consult the triage helper in the Streamlit interface
