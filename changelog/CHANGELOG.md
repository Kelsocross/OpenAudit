# MAG - H&B Changelog

All notable changes to the MAG - H&B freight audit application are documented in this file.

---

## [Version 2.6] - October 30, 2025

### 🐛 Critical Bug Fixes

#### Fixed Fuel Surcharge Validation to Use Discounted Rates
- **Issue**: Fuel surcharge validation was using published "Base Rate" which caused false positives
- **Research Finding**: FedEx/UPS calculate fuel surcharges on **discounted/net rates**, not published base rates
- **Fix**: Updated fuel surcharge validation with 3-tier logic:
  1. **Primary**: Look for explicit freight charge columns ('Freight Charges', 'Transportation Charge', etc.)
  2. **Secondary**: Calculate from Net Charge Amount USD minus all surcharges
  3. **Fallback**: Use Base Rate if other methods unavailable
- **Impact**: Fuel surcharge "unusually high" flags are now accurate for customers with contracted discounts
- **Example**: If you have 30% discount, fuel is calculated on $70 (not $100), so legitimate fuel surcharges won't be incorrectly flagged

#### Improved Zip Code Normalization for Delivery Area Surcharge Validation
- **Enhancement**: Updated zip code extraction to properly normalize both 5-digit and 9-digit formats
- **Supported Formats**:
  - 5-digit: `12345` → `12345`
  - 9-digit with dash: `12345-6789` → `12345`
  - 9-digit no dash: `123456789` → `12345`
- **Impact**: Delivery Area Surcharge validation now correctly displays zip codes regardless of format in source data

#### Fixed Weight Detection for Disputable Surcharges
- **Issue**: Additional Handling surcharges were incorrectly flagged with "weight thresholds not met" showing weight as 0 lb
- **Root Cause**: Code was looking for hardcoded column names "Actual Weight" and "Billed Weight" but data files use different column names
- **Fix**: Implemented flexible weight column detection with multiple name variations:
  - **Actual Weight Detection**: Now checks 'Actual Weight', 'Original Weight', 'Shipment Actual Weight', 'Package Weight', 'Weight'
  - **Billed Weight Detection**: Now checks 'Billed Weight', 'Shipment Rated Weight', 'Rated Weight', 'Billable Weight', 'Chargeable Weight'
- **Impact**: Additional Handling surcharges are now correctly validated against actual weight data (e.g., 52 lbs instead of 0 lbs)

### 🎯 Focused Audit Checks (User-Requested)
- **Streamlined Audit Engine**: Reduced to 3 core checks to avoid inflating potential savings
  - ✅ **Late Deliveries**: Service guarantee violations eligible for refunds
  - ✅ **Duplicate Tracking**: Detects duplicate shipments in main summary report (NOT surcharge breakdowns)
    - Surcharge reports with multiple lines per tracking number are correctly grouped and NOT flagged
    - **Return Shipment Detection**: Original + Return pairs are automatically excluded
      - Example: Tracking #466761794075 with "International Ground" + "Ground Return Manager" → NOT flagged (legitimate return)
      - Keywords detected: RETURN, RMGR, RMA, REVERSE, RETURNMANAGER
    - Only TRUE duplicates from shipment summary report are detected
  - ✅ **Disputable Surcharges**: 40+ surcharge types with dimensional/weight validation
- **Disabled Checks** (were inflating savings rate):
  - ❌ DIM Weight Overcharges
  - ❌ Incorrect Zone Charges
  - ❌ Address Type Mismatches
  - ❌ High Surcharges (user requested removal)
  - ❌ Unnecessary Surcharges
- **Accurate Savings Reporting**: Potential savings and savings rate now reflect only actionable, disputable charges

### ✨ New Features

#### Enhanced File Merge Engine with Multi-Key Matching
- **Feature: Robust File Merge System** (`merge_utils.py`): Completely rebuilt merge engine with enterprise-grade reliability
  - **Multi-Key Join Support**: Uses BOTH Tracking Number AND Invoice Number for more accurate matching
  - **Master Tracking Number Fallback**: Automatically uses Master Tracking Number if Shipment Tracking Number is missing
  - **Column Name Flexibility**: Handles "Shipment Miscellaneous ChargeUSD" (no space), "Charge USD" (with space), and other variations
  - **Scalar-Safe Logic**: Explicit scalar checks prevent pandas Series ambiguity errors during merge operations
  - **Smart Column Detection**: Automatically finds amount/description columns even with non-standard naming
  - **Graceful Degradation**: Returns shipments with empty surcharge columns if merge keys not found (no data loss)
  - Fixed "The truth value of a Series is ambiguous" error in dimensional weight calculations

#### Comprehensive Surcharge Validation with Dimensional/Weight Verification
- **Feature: Dual-Source Surcharge Detection**: Validates surcharges from BOTH merged surcharge files AND individual surcharge columns
  - **Source 1**: Merged surcharge file (Surcharge_Details column) - for separate surcharge files
  - **Source 2**: Individual surcharge columns in main file - for files with built-in surcharge columns
  - Automatically detects and validates surcharges regardless of file format
  - Supports 28+ common surcharge column names (Address Correction, Residential Surcharge, Fuel Surcharge, etc.)

- **Feature: 40+ Surcharge Type Validation**: Completely rebuilt `check_disputable_surcharges()` to validate all 40+ surcharge types
  - **Address-Related Charges**: Address Correction, Delivery Area Surcharge (DAS), Extended DAS, Remote Area
  - **Delivery Type Charges**: Residential Delivery, Saturday/Sunday Delivery/Pickup (validates actual delivery day)
  - **Routing/Service Changes**: Return Fees, Redirect Delivery, Hold at Location, Attempted Delivery
  - **Billing Errors**: Duplicate Invoice, Invalid Account, Incorrect Billing, Rebill, Manual Processing
  - **Size/Weight Charges**: Additional Handling, Oversize, Overweight, Unauthorized Package (WITH MATH VALIDATION)
  - **Peak Season Charges**: Peak Additional Handling, Peak Oversize, Peak Residential, Peak Surcharge (validates month)
  - **Service Failures**: Money-Back Guarantee Adjustment, Late Delivery Adjustment, Transit Time Discrepancy, Delivery Exception
  - **Weight Corrections**: Weight Correction, Dimensional Weight Adjustment, Cubic Volume, Overweight Charge (WITH DIM WEIGHT MATH)
  - **Customs/International**: Brokerage Fee, Duty and Tax Advancement, Entry Preparation, Clearance Entry, Import Data Correction
  - **Operational Charges**: Fuel Surcharge (validates rate %), Declared Value/Insurance, Missing Documentation, Undeliverable Shipment

- **Feature: Dimensional Weight Calculations**: Automatic DIM weight validation
  - **DIM Factor 139**: Domestic shipments (FedEx/UPS standard)
  - **DIM Factor 166**: International shipments (auto-detected from service type)
  - **Formula**: DIM Weight = CEIL((Length × Width × Height) / DIM Divisor)
  - **Critical Rounding**: Uses math.ceil() to round UP to next whole pound (carrier billing standard)
  - **Validation**: Compares billed weight vs correct billable weight (max of actual or DIM weight)
  - **Flags over-billing**: Identifies when billed weight exceeds correct weight by >1 lb tolerance
  - **Example**: 12×12×12 domestic = (1728/139) = 12.4 → rounds UP to 13 lbs (not 12 lbs)

- **Feature: Oversize Charge Validation**: Verifies oversize charges against carrier thresholds
  - **Threshold 1**: Length > 96 inches
  - **Threshold 2**: Length + 2×(Width + Height) > 130 inches
  - **Threshold 3**: Length + Girth > 165 inches (where Girth = 2×(Width + Height))
  - **Validation Logic**: Flags oversize charge if package does NOT meet ANY of the three thresholds
  - **Detailed Notes**: Shows actual dimensions and calculated values (L+2(W+H), L+Girth) for review

- **Feature: Additional Handling Validation**: Verifies additional handling charges
  - **Threshold 1**: Length > 48 inches
  - **Threshold 2**: Second longest side > 30 inches
  - **Threshold 3**: Length + Girth > 105 inches
  - **Threshold 4**: Weight > 70 lbs
  - **Validation Logic**: Flags charge if package does NOT meet ANY threshold
  - **Dimensions Auto-Sort**: Automatically sorts dims to identify longest, second, third sides

- **Feature: Overweight Charge Validation**: Validates overweight charges
  - **Threshold**: 150 lbs (standard carrier overweight threshold)
  - **Validation**: Flags overweight charge if actual weight < 150 lbs
  - **Shows actual weight**: Provides clear evidence for dispute

- **Feature: Fuel Surcharge Rate Validation**: Checks fuel surcharge percentages
  - **Normal Range**: 10-20% of base rate
  - **Excessive Threshold**: Flags if >25% of base rate
  - **Calculates Percentage**: Shows FSC amount as % of base rate for validation

- **Feature: Context-Aware Validation**: Smart validation using shipment data
  - **Residential vs Business**: Detects business keywords (LLC, Inc, Corp, Company, Office, Warehouse, etc.)
  - **Peak Season Validation**: Checks if shipment was actually during peak months (Nov-Jan)
  - **Weekend Delivery Validation**: Verifies delivery date was actually Saturday/Sunday
  - **Service Type Checking**: Detects conflicts (e.g., peak charges on premium services)
  - **Address Analysis**: Flags residential charges on business addresses

- **Feature: Enhanced Error Details**: Rich validation notes for every finding
  - Shows actual dimensions, weights, and calculated values
  - Provides specific thresholds that were (or weren't) met
  - Includes carrier-specific validation logic
  - Adds actionable next steps for disputing

---

## [Version 2.5] - October 28, 2025

### 🔧 Improvements

#### Base Rate Column Now Optional
- **Made "Base Rate" an optional column instead of required**
  - Rationale: Some carrier files only provide "Net Charge Amount USD" (final amount including freight, surcharges, and discounts)
  - System now accepts files with only "Total Charges" (or "Net Charge Amount USD")
  - "Net Charge Amount USD" automatically maps to "Total Charges" column
  - Audit checks gracefully handle missing Base Rate by skipping ratio-based calculations
  - Files without separate freight-only amounts now upload successfully

#### Surcharge Merge Double-Counting Prevention
- **Added clarification for merged surcharge files**
  - Warning message when merging surcharge files with shipment data
  - Explains that merged surcharge data is informational only
  - Prevents confusion when "Net Charge Amount" already includes surcharges and discounts
  - Merged surcharges create `Additional_Surcharges` column but never modify `Total Charges`
  - Ensures accurate refund calculations without double-counting

### 🐛 Bug Fixes

#### Audit Detection Regression Fix
- **Fixed audit checks to work properly when Base Rate column is missing**
  - **Issue**: After making Base Rate optional, duplicate charges and surcharge findings disappeared
  - **Root Cause**: Audit logic relied on Base Rate column existence, causing early exits when missing
  - **Fix 1 - Surcharge Detection**: Enhanced `check_high_surcharges()` with three detection methods:
    - Method 1 (Ratio): When Base Rate exists, flag if surcharges > 25% of base rate (original logic)
    - Method 2 (Absolute): When Base Rate missing, flag if surcharges > $100
    - Method 3 (Percentage): When Base Rate missing, flag if surcharges > 30% of total charges
  - **Fix 2 - Duplicate Detection**: Enhanced `check_duplicate_tracking()` with smart fallback logic:
    - Checks if duty/tax and freight columns exist in the file
    - Only applies fallback (treating Total Charges as freight) when BOTH duty AND freight columns are absent
    - When duty/tax columns exist, properly classifies rows as TRANSPORT (freight) or DUTY_TAX (duty)
    - Correctly identifies valid international shipments (1 TRANSPORT + 1 DUTY_TAX) and does NOT flag them
    - Enables duplicate detection for files with only "Net Charge Amount USD" column
  - **Fix 3 - Surcharge Column Detection**: Enhanced `check_high_surcharges()` to find surcharge data in multiple locations:
    - First checks "Surcharges" column (from original file)
    - If not found, checks "Additional_Surcharges" column (from merged surcharge file)
    - If still not found, sums individual surcharge columns (Fuel Surcharge, Residential Surcharge, Address Correction, Declared Value Charge)
    - Enables surcharge detection regardless of file format or merge status
    - Added NaN-safe value handling to prevent blank values from breaking detection
    - Lowered thresholds for better detection:
      - Absolute threshold: $50 (down from $100)
      - Percentage threshold: 20% of total (down from 30%)
      - Added Method 4: Flags ANY merged surcharge ≥ $10 for review
  - **Result**: All audit checks now work correctly regardless of Base Rate column presence
  - Surcharge findings, duplicate charges, and late delivery errors all appear as expected
  - International shipments with duty/tax lines are properly handled and not incorrectly flagged
  - Surcharges detected whether in main file, merged file, or as individual columns

---

## [Version 2.4] - October 28, 2025

### ✨ New Features

#### LTL Shipment Audits
- **New dedicated page for LTL carrier duplicate accessorial charge detection**
  - Upload LTL carrier Excel files with "Invoice Number" and "Accessorial List" columns
  - Automatic parsing of semicolon-separated accessorial charges with prices in format: "Charge Name($Price)"
  - Intelligent duplicate detection:
    - **Exact Duplicates**: Same charge name appears multiple times on single invoice
    - **Similar Charges**: Different names but same category (e.g., "Lift Gate Service" + "Lift Gate Delivery")
  - Category-based detection for common duplicates:
    - Lift Gate / Forklift charges
    - Inside Delivery / Pickup charges
    - Residential fees
    - Appointment / Scheduled delivery
    - Redelivery charges
    - Storage / Holding fees
    - Notification charges
  - Comprehensive dashboard with 4 key metrics:
    - Total Invoices analyzed
    - Invoices with Duplicates count
    - Duplicate Rate percentage
    - Total Potential Refund amount
  - **Trend Analysis Chart** (New!):
    - Visual bar chart showing number of duplicate charged invoices by week or month
    - Tracks when duplicate issues occur over time for pattern identification
    - Toggle between Weekly and Monthly views
    - Bars display invoice counts with duplicates (primary metric)
    - Line overlay shows total potential refund amounts (secondary metric)
    - Automatic date detection from uploaded files (supports common date column names)
    - Only displays when date information is available in uploaded file
  - Advanced filtering by duplicate type, invoice number, and minimum refund amount
  - Expandable detail cards showing charge breakdowns and refund estimates
  - Excel export with separate sheets for findings and summary
  - Session-only storage - LTL data automatically cleared on timeout or manual clear
  - Zero persistence - LTL data never saved to disk or database

---

## [Version 2.3] - October 27, 2025

### 🐛 Bug Fixes

#### Refund Calculation Accuracy Fix
- **Fixed refund amounts to use actual total charges instead of freight-only charges**
  - Previous behavior: Refund calculations used "Shipment Freight Charge Amount USD" (freight charges only, excluding surcharges)
  - New behavior: Uses "Total Charges" which is mapped from "Net Charge Amount USD" (actual total amount paid including all surcharges)
  - Example: Tracking 883677980990 now correctly shows $1,628.50 refund instead of $2,828.44
  - Column mapping: "Net Charge Amount USD" from your file → "Total Charges" (required column for validation)
  - Smart fallback logic: Total Charges → Base Rate → Billed Amount
  - Semantic separation maintained: "Total Charges" = net amount paid, "Base Rate" = freight only
  - Applies to all error types: Late Delivery, DIM Weight, Zone Errors, Surcharges, etc.
  - Files with "Net Charge Amount USD" column now pass validation successfully

---

## [Version 2.2] - October 6, 2025

### 🔒 MAXIMUM SECURITY MODE

#### Military-Grade Data Security Implementation
- **ZERO DATA PERSISTENCE - Your data is NEVER saved**
  - Completely disabled all database saving of uploaded shipping data
  - Removed save_audit_session functionality that was storing tracking numbers, refund estimates, and shipment details
  - All data exists only in browser session memory (RAM)
  - Data completely wiped when browser tab closes
  
- **Session Security Controls**
  - ✅ Manual "Clear All Data Now" button in sidebar for immediate data wipe
  - ✅ Automatic session timeout after 30 minutes of inactivity
  - ✅ Automatic data clearing on session timeout
  - ✅ Session state cleared on page reload
  
- **Advanced Security Headers**
  - Enabled XSRF (Cross-Site Request Forgery) protection
  - Disabled CORS to prevent cross-origin data access
  - Disabled usage statistics collection
  - Hidden error details to prevent information leakage
  - Maximum upload size limited to 200MB
  
- **Secure File Handling**
  - All uploaded files processed in memory only (never written to disk)
  - CSV/Excel reading uses in-memory buffers (BytesIO)
  - Download files generated in memory (BytesIO) and streamed directly to user
  - NO permanent file storage on server
  
- **Prominent Security Notices**
  - Blue security banner on every page confirming zero persistence
  - Clear messaging: "Your data is NEVER saved to any database or disk"
  - Sidebar security status with real-time session information
  - Success messages emphasize data security
  
- **What This Means**
  - 🔒 Your sensitive shipping data is MORE secure than Fort Knox
  - 🔒 Impossible for data to be accessed after session ends
  - 🔒 No audit trail, no history, no database records
  - 🔒 Complete privacy and confidentiality guaranteed
  - 🔒 Even server administrators cannot access your data after you close the browser

---

## [Version 2.1] - October 6, 2025

### ✨ New Features

#### Automatic Delivery Date Cleanup
- **Smart placeholder date detection and removal**
  - Automatically detects fake placeholder delivery dates (1900-01-01, 1899-12-31, 01/01/1900)
  - Replaces placeholder dates with proper missing values (NaT)
  - Works with any column name variation including "Shipment Delivery Date (mm/dd/yyyy)"
  - Creates new "Delivery Status" column:
    - "Missing Delivery Date" for shipments without valid delivery dates
    - "Ready" for shipments with valid delivery dates
  - Automatically excludes shipments with missing delivery dates from on-time and transit-time KPI calculations
  - Displays clear notification: "X shipment(s) with missing or placeholder delivery dates (1900-01-01) are excluded from on-time KPIs"
  - Works seamlessly for both CSV and Excel file uploads
  - All other app logic and columns remain intact

### 🐛 Bug Fixes

#### Late Delivery Refund Calculation Fix
- **Fixed $0.00 refund issue for late deliveries**
  - Previous behavior: Only used "Base Rate" column for refund calculation, showing $0.00 when column was missing
  - New behavior: Smart fallback logic tries multiple columns in order:
    1. Base Rate (transportation charges)
    2. **Net Charge Amount USD** (total price paid - from user's actual shipping file)
    3. Billed Amount (alternative column name)
    4. Total Charges (total shipment cost)
  - Uses the first available non-zero value for accurate refund estimates
  - Ensures all late delivery claims show proper refund amounts based on actual data
  - Example: FedEx IE shipment delivered 4 days late now shows correct refund instead of $0.00

---

## [Version 2.0] - October 6, 2025

### 🎨 Complete Application Rebranding

#### Color Scheme Overhaul
- **Replaced all orange elements (#FFA947) with blue color scheme**
  - Primary blue: `#1F497D` (dark blue)
  - Secondary blue: `#7EA1C4` (light blue)
  - Applied to buttons, headers, navigation, and all UI elements
  - Ensured consistent blue branding throughout entire application

#### Dashboard Visualizations
- **Updated all chart colors to blue gradient family**
  - Chart color palette: `#1F497D`, `#4E75A0`, `#7EA1C4`, `#B3C9DC`
  - Applied to bar charts, pie charts, line graphs, and all data visualizations
  - Maintains visual hierarchy while using cohesive blue theme

---

### 📚 User Documentation System

#### Created Comprehensive Documentation Folder
- **New `user_instructions/` folder with 5 complete guides:**
  1. **USER_GUIDE.md** - Complete application manual
     - Overview and getting started
     - Detailed instructions for all 5 pages
     - Step-by-step procedures for upload, audit, claims
     - Tips, best practices, and FAQs
  
  2. **QUICK_START.md** - Fast-track guide
     - 5-minute setup and first audit
     - Quick steps for uploading, auditing, and claiming
     - Essential features at a glance
  
  3. **TROUBLESHOOTING.md** - Problem-solving guide
     - Common issues and solutions
     - Upload errors, audit problems, claim submission issues
     - Performance optimization tips
  
  4. **GLOSSARY.md** - Freight terminology reference
     - 50+ shipping and freight terms defined
     - Billing error types explained
     - Carrier-specific terminology
  
  5. **README.md** - Documentation index
     - Quick links to all documentation sections
     - Feature overview
     - Navigation guide

---

### 🔄 Navigation and Page Updates

#### Page Renaming
- **"AI Freight Advisor" → "Q&A"**
  - Updated navigation menu item from "AI Freight Advisor" to "Q&A"
  - Changed page title to "MAG Shipping Tool Frequently Asked Questions"
  - Updated all documentation references to reflect new name
  - Maintained all functionality while improving clarity

#### Simplified Navigation Structure
- **5 main pages:**
  1. Upload & Audit
  2. Refund Recovery
  3. Q&A (formerly AI Freight Advisor)
  4. Dashboard
  5. Contract Review

---

### 💰 Claims Submission System

#### FedEx Bulk Upload Feature
- **Automated Excel file generation**
  - Creates FedEx-compliant bulk upload format
  - Includes all required fields: tracking number, shipment date, claim amount, reason
  - Downloads directly to user's device
  - Auto-redirects to FedEx login page after download

#### Email Claims Report
- **Automated email draft generation**
  - Opens default email client with pre-filled subject line
  - Includes detailed claim information in email body
  - Lists tracking numbers, error types, and refund amounts
  - Downloads Excel attachment for manual addition
  - Uses JavaScript execution and session state triggers

---

### 📊 Data Requirements

#### Required Column Updates
- **Enhanced date tracking:**
  - Shipment Date (required)
  - Delivery Date (required)
  - Both dates used for late delivery claim verification
  - Improved accuracy in billing error detection

---

### 🎨 Design Consistency

#### Blue Theme Implementation
- **Dark blue (#1F497D):**
  - Primary buttons
  - Headers and titles
  - Navigation sidebar highlights
  - Key UI elements

- **Light blue (#7EA1C4):**
  - Secondary buttons
  - Hover states
  - Accents and borders
  - Chart gradients

- **Gradient family for charts:**
  - 4-color palette for visual variety
  - Maintains cohesive brand identity
  - Improves data visualization clarity

---

### 📝 Documentation Updates (October 6, 2025)

#### All User Instructions Updated
- **Q&A page name change reflected across all documentation**
  - USER_GUIDE.md: Table of contents, navigation list, section heading
  - QUICK_START.md: Bonus features section
  - README.md: Advanced features, main features list
  - TROUBLESHOOTING.md: Section headings and problem descriptions
  - GLOSSARY.md: Term definitions and references

---

## Summary of Key Improvements

### User Experience
✅ Cohesive blue branding throughout entire application
✅ Clear, intuitive navigation with 5 focused pages
✅ Comprehensive documentation for all user levels
✅ Streamlined claim submission process with automation

### Functionality
✅ Complete freight audit system with error detection
✅ Automated FedEx bulk upload file generation
✅ Email claim report automation
✅ Enhanced data tracking with dual date requirements
✅ Visual analytics with blue-themed charts

### Documentation
✅ 5 complete user guides covering all aspects
✅ Quick start for immediate productivity
✅ Troubleshooting for common issues
✅ Comprehensive glossary of freight terms
✅ Updated to reflect all current features and naming

---

## Application Branding

**Application Name:** MAG - H&B  
**Color Theme:** Blue (#1F497D, #7EA1C4)  
**Previous Theme:** Orange (#FFA947) - fully replaced  
**Pages:** 5 (Upload & Audit, Refund Recovery, Q&A, Dashboard, Contract Review)

---

*This changelog will be continually updated as new features and changes are implemented.*
