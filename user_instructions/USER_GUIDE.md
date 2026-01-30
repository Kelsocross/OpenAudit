# OpenAudit Platform User Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Upload & Audit](#upload--audit)
4. [Refund Recovery](#refund-recovery)
5. [Q&A](#qa)
6. [Dashboard](#dashboard)
7. [Contract Review](#contract-review)
8. [Tips & Best Practices](#tips--best-practices)

---

## Overview

**OpenAudit Platform** is a comprehensive freight audit and refund recovery platform designed to help you:
- Audit freight invoices for billing errors
- Identify overcharges and billing discrepancies
- Generate professional claims reports
- Submit claims to carriers (FedEx, UPS, etc.)
- Analyze shipping data and patterns
- Review and optimize carrier contracts
- Get AI-powered freight advice

---

## Getting Started

### Accessing the Application
1. Open the application in your web browser
2. You'll see the main navigation menu on the left sidebar with these main sections:
   - Upload & Audit
   - Refund Recovery
   - Q&A
   - Dashboard
   - Contract Review

### Navigation
- Click on any menu item in the left sidebar to access that section
- The active page will be highlighted in blue
- The OpenAudit logo appears at the top of the sidebar

### Data Security
**Zero Data Persistence Policy:**
- All uploaded shipping data is processed in-memory only
- No data is ever saved to disk or database
- Session data automatically clears after **1 hour** of inactivity
- All data is wiped when you close your browser tab
- **Clear All Data** button available in the sidebar for immediate data wipe

This ensures maximum security for your sensitive shipping information.

---

## Upload & Audit

This is where you upload your shipping invoices for automated auditing.

### Supported File Formats
- Excel files (.xlsx, .xls)
- CSV files (.csv)

### Required Data Columns
Your upload file should include the following information:
- **Tracking Number**: Unique shipment identifier
- **Carrier**: Shipping carrier (e.g., FedEx, UPS)
- **Service Type**: Service level used (e.g., Ground, Express)
- **Date**: Shipment date
- **Delivery Date**: Actual delivery date
- **Billed Amount**: Amount charged by carrier
- **Weight**: Package weight
- **Zone**: Shipping zone
- Additional columns like dimensions, surcharges, etc.

### How to Upload and Audit
1. Click the **"Browse files"** button or drag and drop your file
2. Once uploaded, the file will be validated automatically
3. If validation is successful, you'll see a preview of your data
4. Click **"Run Audit"** to analyze the shipment data
5. The system will identify billing errors, overcharges, and refund opportunities
6. Review the audit results displayed on screen

### Understanding Audit Results
After running an audit, you'll see:
- **Total shipments analyzed**
- **Potential savings identified**
- **Number of shipments with issues**
- **Breakdown by error type** (Late Delivery, Incorrect Zone, DIM Weight Overcharge, etc.)
- **Detailed findings table** showing each error with tracking number, error type, and refund estimate

---

## Refund Recovery

This section helps you manage and submit claims for identified billing errors.

### Viewing Actionable Errors
1. Navigate to the **Refund Recovery** page
2. You'll see all billing errors that can be claimed
3. Each error card shows:
   - Tracking number
   - Carrier and service type
   - Error type and dispute reason
   - Shipment date
   - Refund estimate amount

### Filtering Claims
- Use the **"Error Type"** filter to view specific types of errors
- Use the **"Carrier"** filter to view claims for a specific carrier
- Use the date range selector to filter claims by shipment date

### Submitting Claims

#### Option 1: Email Claims Report
1. Select the claims you want to submit using the checkboxes
2. Choose **"Email Claims Report"** from the submission method dropdown
3. Click **"Submit Selected Claims"**
4. An email draft will automatically open in your default email client with:
   - Subject line pre-filled
   - Detailed claim information in the email body (tracking numbers, error types, refund amounts)
   - Excel file will be downloaded (attach it manually to the email)
5. Add the carrier's email address as the recipient
6. Attach the downloaded Excel file
7. Review and send the email

#### Option 2: Bulk Upload to FedEx
1. Select the FedEx claims you want to submit
2. Choose **"Bulk Upload to FedEx"** from the submission method dropdown
3. Click **"Submit Selected Claims"**
4. An Excel file will be downloaded in FedEx's required format
5. You'll be automatically redirected to the FedEx login page
6. Log into your FedEx account
7. Navigate to the claims submission section
8. Upload the downloaded Excel file
9. Follow FedEx's on-screen instructions to complete the submission

### Excel File Format
The generated Excel file includes:
- Tracking Number
- Claim Type
- Claim Amount
- Ship Date
- Error Type
- Dispute Reason
- Service Type
- Carrier

---

## Q&A

Get intelligent insights and recommendations for your shipping operations through our Frequently Asked Questions page.

### How to Use
1. Navigate to the **Q&A** page
2. You'll see a chat interface powered by AI
3. Type your question or request in the message box
4. Examples of questions you can ask:
   - "How can I reduce my shipping costs?"
   - "What's the best carrier for expedited shipments?"
   - "Analyze my late delivery patterns"
   - "Suggest ways to optimize my packaging"
   - "What surcharges can I avoid?"

### Features
- Real-time AI responses
- Context-aware recommendations based on your shipping data
- Industry best practices and optimization strategies
- Cost-saving suggestions
- Carrier comparison insights

### Tips for Best Results
- Be specific with your questions
- Provide context when asking for recommendations
- Ask follow-up questions to dive deeper into topics
- Reference specific error types or carriers when relevant

---

## Dashboard

Get a comprehensive overview of your audit results and shipping performance.

### Key Metrics
The dashboard displays:
- **Total Charges Audited**: Total dollar amount of shipments analyzed
- **Potential Savings**: Total refund amount identified
- **Savings Rate**: Percentage of total charges that can be recovered
- **Shipments with Issues**: Count of problematic shipments

### Freight Direction Breakdown
**NEW FEATURE:** The dashboard now shows your shipping costs split by direction:

- **Inbound Freight**: Shipments coming TO your warehouses
  - Shows total cost and shipment count
  - All shipments not originating from your warehouse addresses

- **Outbound Freight**: Shipments FROM your warehouses
  - Shows total cost and shipment count
  - Automatically detected from warehouse addresses:
    - 251 Gillum Dr
    - 1409 Coronet Dr
  - Handles various spelling variations automatically

This breakdown helps you understand the split between incoming inventory and outgoing customer orders.

### Visualizations

#### Error Types Distribution
- Pie chart showing the breakdown of different error types
- Helps identify the most common billing issues
- Color-coded for easy interpretation

#### Savings by Category
- Horizontal bar chart showing potential savings by error type
- Identifies which errors represent the biggest refund opportunities
- Values displayed in dollar amounts

#### Overcharges Timeline
- Weekly view of overcharges and error frequency
- Bar chart shows weekly savings potential
- Line chart shows error count trends
- Helps identify patterns over time

### Detailed Findings Table
- Sortable and searchable table of all identified errors
- Columns include: Tracking Number, Carrier, Service Type, Date, Error Type, Refund Estimate
- Use search to find specific tracking numbers
- Click column headers to sort data

### Data Export
All exported data files now include a **"Freight Direction"** column showing whether each shipment was Inbound or Outbound. This allows for easy filtering and analysis in Excel or other tools.

---

## Contract Review

Analyze and optimize your carrier contracts.

### Contract Intelligence Platform
Upload your carrier contracts to receive:
- Comprehensive contract analysis
- Industry benchmark comparisons
- Custom negotiation strategies
- Rate optimization recommendations

### How to Upload a Contract
1. Navigate to the **Contract Review** page
2. Go to the **"Upload Contract"** tab
3. Click **"Browse files"** or drag and drop your contract file
4. Supported formats: PDF, XLSX, DOCX
5. Click **"Analyze Contract"** after upload

### Analysis Results
After analysis, you'll receive:

#### Contract Summary
- Key terms and conditions
- Rate structure breakdown
- Surcharge details
- Service commitments

#### Benchmark Comparison
- How your rates compare to industry standards
- Potential cost savings opportunities
- Service level comparisons

#### Negotiation Strategy
- Specific talking points for carrier negotiations
- Rate improvement opportunities
- Alternative service suggestions
- Leverage points based on your shipping volume

### Contract History
- View all previously analyzed contracts
- Track performance improvements over time
- Compare different carrier agreements
- Monitor rate changes

---

## Tips & Best Practices

### For Best Audit Results
1. **Upload Complete Data**: Ensure all required columns are included in your upload file
2. **Regular Audits**: Run audits monthly to stay on top of billing errors
3. **Clean Data**: Remove duplicate entries and ensure dates are properly formatted
4. **Include All Carriers**: Audit invoices from all your carriers for comprehensive savings

### For Claim Submissions
1. **Review Before Submitting**: Double-check selected claims before submission
2. **Organize by Carrier**: Submit claims separately for each carrier
3. **Keep Records**: Save copies of all submitted claim files
4. **Follow Up**: Track claim status with carriers after submission
5. **Batch Similar Claims**: Group similar error types together for faster processing

### For Contract Review
1. **Upload Current Contracts**: Use your most recent carrier agreements
2. **Compare Multiple Carriers**: Analyze contracts from different carriers to leverage competition
3. **Review Annually**: Reassess contracts at least once per year
4. **Use Benchmarks**: Reference industry benchmarks during negotiations
5. **Document Everything**: Keep analysis results for future negotiations

### Data Management
1. **Backup Your Files**: Keep original invoice files in a secure location
2. **Standardize Format**: Use consistent file formats for easier processing
3. **Update Regularly**: Upload new invoice data as soon as it's available
4. **Track Results**: Monitor your savings and ROI from the platform

### Getting Help
- Use the Q&A page for quick questions
- Review this user guide for detailed instructions
- Contact support if you encounter technical issues

---

## Frequently Asked Questions

**Q: What file formats are supported for invoice uploads?**
A: Excel (.xlsx, .xls) and CSV (.csv) files are supported.

**Q: How long does the audit process take?**
A: Most audits complete within a few seconds, depending on file size.

**Q: Can I submit claims for multiple carriers at once?**
A: Claims should be submitted separately by carrier. Use the carrier filter to organize claims.

**Q: What happens after I submit claims?**
A: The claims are sent to the carrier for review. You should receive responses within the carrier's standard processing timeframe (typically 30-60 days).

**Q: Can I edit claims after submission?**
A: No, once claims are submitted, they cannot be edited. Review carefully before submitting.

**Q: How accurate is the Q&A page?**
A: The AI provides industry best practices and data-driven recommendations. Always verify suggestions with your specific business needs.

**Q: Is my data secure?**
A: Yes! The app follows a **zero data persistence policy**. All uploaded shipping data is processed in-memory only and is NEVER saved to disk or database. Session data automatically clears after 1 hour of inactivity or when you close your browser tab. You can also manually clear all data using the "Clear All Data" button in the sidebar.

**Q: Can I export my audit results?**
A: Yes, audit results can be exported as Excel or CSV files. All exports now include a "Freight Direction" column showing whether each shipment was Inbound or Outbound.

**Q: What is the Freight Direction feature?**
A: The app automatically classifies shipments as Inbound (TO your warehouses) or Outbound (FROM your warehouses) based on the shipper address. This helps you analyze costs separately for incoming inventory vs. outgoing customer orders. The breakdown is displayed on the Dashboard and included in all data exports.

**Q: How long does my session stay active?**
A: Your session remains active for 1 hour of inactivity. After 1 hour without any interaction, all uploaded data is automatically cleared for security. The session timer resets each time you interact with the app.

---

## Support

For technical support or questions not covered in this guide, please contact your system administrator or support team.

---

**Version**: 1.6  
**Last Updated**: December 4, 2025  
**Application**: OpenAudit Platform Freight Audit & Refund Recovery

### Recent Updates (Version 1.6)
- **Blank Surcharge Description Detection**: Automatically identifies and flags charges with missing or blank descriptions - FedEx must provide a reason for all charges, making these disputable
- **Smart Duplicate Consolidation**: When multiple blank description charges appear on the same shipment, they are consolidated into a single finding with the total refund amount

### Previous Updates (Version 1.5)
- **Misc Charges Review Page Removed**: Simplified navigation by removing the Misc Charges Review page
- **Streamlined Interface**: Focus on core audit functionality

### Previous Updates (Version 1.4)
- **Fuel Surcharge Validation**: Enhanced fuel surcharge audit now calculates percentage based on Net Charge Amount (total shipment cost including all surcharges)
- **International Shipment Handling**: Fuel surcharge validation now properly handles international shipments with multiple invoice lines (shipment + duty/tax lines) by summing total charges across all lines with the same tracking number
- **Expanded International Detection**: Added comprehensive FedEx international service codes (OA, LO, IP, IE, IF, IG, SG, F1, FO, IX, XS) and keywords (INTERNATIONAL, INTL, GLOBAL, WORLD, EXPORT, IMPORT)
- **UI Cleanup**: Streamlined sidebar with cleaner "Clear All Data" button

### Previous Updates (Version 1.2)
- **Session Timeout Extended**: Data auto-clear timeout increased from 30 minutes to 1 hour
- **Freight Direction Classification**: Automatic Inbound/Outbound classification based on shipper address
- **Enhanced Dashboard**: New Freight Direction Breakdown showing costs split by Inbound vs Outbound freight
- **Export Enhancement**: All data exports now include "Freight Direction" column for downstream analysis
