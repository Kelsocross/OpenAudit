# MAG Freight Analysis Tool

## Overview

The MAG Freight Analysis Tool is a Streamlit-based platform for auditing and analyzing freight invoices. It enables users to upload, process, and audit invoices using AI (GPT-5) to identify cost savings, assess carrier performance, and understand spending patterns. Key capabilities include PDF and Excel processing, data visualization, automated email reporting via SendGrid, and comprehensive analytics dashboards. The tool aims to provide significant business value by optimizing freight spending and improving operational efficiency.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The application is built with **Streamlit**, leveraging its multi-page application structure and session state for managing authentication and user preferences. It uses a wide layout with responsive components.

**Core Pages:**
- **Main (`app.py`):** Landing page with simplified passwordless login.
- **Dashboard (`pages/1_Dashboard.py`):** Key Performance Indicators (KPIs) and overview visualizations.
- **Upload Invoices (`pages/2_Upload_Invoices.py`):** Interface for PDF and Excel file uploads.
- **AI Analysis (`pages/3_AI_Analysis.py`):** AI-powered invoice analysis.
- **Analytics (`pages/4_Analytics.py`):** Advanced charts and freight audit analysis.
- **Email Reports (`pages/5_Email_Reports.py`):** Report generation and distribution.
- **Settings (`pages/6_Settings.py`):** Application configuration.

### Backend Architecture

**Authentication:**
- **Design:** Passwordless authentication using a simple "Login" button. All users are granted full access to all features without restriction, suitable for trusted internal use.
- **Implementation:** `st.session_state.authenticated = True` is set on login, and all pages auto-authenticate.

**PDF Processing Pipeline:**
- **Libraries:** `pdfplumber` for text extraction and `tabula` for table extraction.
- **Process:** Two-stage extraction (raw text then structured tables) with regex for key field extraction and carrier recognition.

**Excel Processing Pipeline:**
- **Libraries:** `pandas` with dynamic engine selection (`xlrd` for .xls, `openpyxl` for .xlsx/.xlsm).
- **Features:** Smart column detection, data validation, and optional surcharge file merging.

**File Merge Engine:**
- **Logic:** Robust multi-key matching (Tracking Number + Invoice Number) for merging shipment and surcharge data.
- **Flexibility:** Handles various column name formats and ensures graceful degradation if merge keys are absent.

**Freight Direction Classification:**
- **Feature:** Automatically classifies shipments as Inbound or Outbound based on shipper address.
- **Outbound Detection:** Identifies shipments from warehouse addresses (251 Gillum Dr, 1409 Coronet Dr) with pattern matching for various spellings.
- **Dashboard Display:** Shows separate cost and shipment count metrics for Inbound vs Outbound freight.
- **Export:** Freight Direction column included in all data exports for downstream analysis.

**Freight Audit Engine:**
- **Checks:** Implements 3 core audit checks: Late Deliveries (FedEx guaranteed services only), Duplicate Tracking, and Disputable Surcharges (40+ charge types with dimensional/weight verification).
- **Blank Surcharge Description Detection:** Automatically flags charges with blank or missing surcharge descriptions - FedEx must provide a reason for all charges. Single blanks flagged individually; multiple blanks consolidated into one finding with full refund estimate (100%).
- **Fuel Surcharge Validation:** Calculates fuel surcharge as percentage of Net Charge Amount (total shipment cost including all surcharges). For international shipments with multiple invoice lines (shipment + duty/tax lines), sums total Net Charge across all lines with the same tracking number to prevent false positives.
- **International Service Detection:** Identifies international shipments using service codes (OA, LO, IP, IE, IF, IG, SG, F1, FO, IX, XS) and keywords (INTERNATIONAL, INTL, GLOBAL, WORLD, EXPORT, IMPORT).
- **Filing Window Filtering:** Refund Recovery page automatically filters claims to only show those within FedEx filing windows:
  - Late Delivery (MBG): 15 days from delivery date
  - Billing Disputes (Surcharges, Duplicates): 180 days from invoice/shipment date
  - Lost/Damage Claims: 60 days from shipment date
  - Expired claims are excluded with a summary showing count and value of expired claims
  - Claims with missing date information are tracked separately with user-facing error message
- **Dimension Variance Detection:** Automatically detects packaging inconsistencies in large orders:
  - **Minimum Threshold:** Only includes orders with 10+ shipments (orders must appear 10+ times)
  - Groups shipments by order number (Reference Notes Line 1)
  - Flags shipments with dimension variances exceeding 3 inches
  - Calculates typical dimensions (median) for each order
  - Identifies potential packaging errors or data entry issues
  - **Reference Number Filtering:** Automatically excludes:
    - Blank or "NO REFERENCE INFORMATION" entries
    - Numeric-only references with 1-4 digits (1-9999)
    - Very short references (1-3 characters)
    - References starting with: RM, EX, CR, O0, S1
    - Email addresses (containing @)
    - Scientific notation (Excel large numbers like 4.82906E+11)
    - References containing keywords: SAMPLE, PROTO, RETURN, TOOL, DIES, TEST
    - **Human names:** Comprehensive exclusion of common first names (100+ names)
    - Multi-word name patterns (title case like "Tammy Chang" or ALL CAPS like "JOHN SMITH")
    - Single-word alphabetic references that appear to be names (4-12 chars, title case)
  - **Display Format:** Shows unique reference numbers only (one row per order) with 5 columns: Reference Number, Shipment Date, Carrier, Count of size variances found, Order Total
  - **Integration:** Runs automatically during audit (no separate upload needed)
  - **Review:** Variances displayed on separate "Dimension Variance Review" page for quality control
  - **Exclusion:** Dimension variances are NOT added to findings or potential savings
- **Output:** Structured findings with refund estimates, detailed descriptions, and priority-ranked actionable errors.
- **Residential Detection:** Intelligent detection of residential surcharges applied to business addresses, checking BOTH recipient AND shipper information with comprehensive business indicator matching including:
  - Generic business keywords (LLC, INC, CORP, COMPANY, BUSINESS, OFFICE, WAREHOUSE, STORE, SHOP, CENTER, DISTRIBUTION)
  - Specific retail stores (SEPHORA, ULTA, NORDSTROM, BLOOMINGDALE, MACY, KOHLS, TARGET, MAC COSMETICS, DIOR, TOWER 28, L'OREAL, etc.)
  - Location-specific identifiers (MALL OF AMERICA, VALLEY FAIR, HOUSTON GALLERIA, 59TH STREET, MICHIGAN AVENUE, etc.)
  - Approved shipper names (HUNTER PHILLIPS, WILLIAM WESPY, FAB SHIPPING, JESSE MENG, AMYCE STOD DARD, MARK LOVELESS, MKT ALLIANCE, MARKETING ALLIANCE GROUP, MARKETING ALLIANCE)
  - Approved shipper companies (CREATIVE PLASTICS, CREATIVE PLASTIC, H & B)
  - Approved shipper addresses (251 GILLUM, 1409 CORONET, GILLUM DR, CORONET DR, etc.) - Also used for Outbound freight classification
  - Safe word-boundary matching for abbreviations (NRD, BLM) to prevent false positives
- **Residential Review:** Separate page for manual review of legitimate residential deliveries, automatically excluding shipments where EITHER the recipient OR shipper has business indicators (which are flagged as disputable instead). Provides detailed notes indicating whether recipient, shipper, or both sides have business indicators.

**AI Analysis Engine:**
- **Model:** OpenAI GPT-5 for invoice analysis and freight audit recommendations.
- **Output:** Structured JSON responses based on specialized prompt engineering.

**Data Visualization:**
- **Libraries:** Primarily `plotly` for interactive charts, with `matplotlib` and `seaborn` for additional options.
- **Features:** Time series trends, carrier distribution, geographic analysis, and audit breakdowns with consistent branding.

**Report Generation:**
- **Library:** `ReportLab` for creating professional, branded PDF reports including tables, charts, and KPI metrics.

**Data Storage:**
- **Database:** SQLite (`ratewise.db`) for embedded, single-file data storage.
- **Schema:** Includes `Invoices` table (metadata, extracted data, AI results) and `Email Reports` table (report metadata, status).
- **Connection:** Function-based connection retrieval without pooling.

### System Design Choices
- **UI/UX:** Focus on clean, emoji-free UI elements and page titles.
- **Technical Implementations:** Robust error handling, intelligent engine selection for file processing, and scalar-safe logic in data operations.

## External Dependencies

-   **OpenAI API:** GPT-5 for AI-powered invoice analysis and recommendations. Requires `OPENAI_API_KEY`.
-   **SendGrid:** For automated email report delivery. Requires `SENDGRID_API_KEY` and `FROM_EMAIL`.
-   **PDF Processing Libraries:** `pdfplumber` and `tabula-py` for PDF text and table extraction.
-   **Data Science Libraries:** `pandas`, `numpy`, `plotly`, `matplotlib`, `seaborn` for data manipulation, analysis, and visualization.
-   **Streamlit:** The core web application framework.
-   **ReportLab:** For PDF report generation.
-   **xlrd & openpyxl:** Python libraries for reading legacy and modern Excel files.