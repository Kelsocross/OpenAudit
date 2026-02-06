import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
import io
import os
import re

from audit_engine import FreightAuditEngine
from data_validator import DataValidator
from data_visualizer import VisualizationManager
from utils import format_currency, calculate_savings_summary
import auth
from auth import get_auth_manager
from database import get_db_manager
from report_generator import ReportGenerator

# Page configuration
st.set_page_config(
    page_title="OpenAudit - Freight Audit Platform",
    page_icon="assets/oa_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== PERFORMANCE OPTIMIZATIONS ==============

@st.cache_resource
def get_cached_audit_engine(residential_patterns=None):
    """Cache the audit engine to avoid recreating on every page switch"""
    return FreightAuditEngine(residential_patterns=residential_patterns)

@st.cache_resource
def get_cached_visualization_manager():
    """Cache the visualization manager"""
    return VisualizationManager()

@st.cache_resource
def get_cached_data_validator():
    """Cache the data validator"""
    return DataValidator()

@st.cache_data
def get_logo_base64_cached():
    """Cache logo base64 encoding to avoid file reads on every render"""
    try:
        with open("attached_assets/image_1758140502894.png", "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

@st.cache_data(ttl=300)
def filter_by_filing_window_cached(_actionable_errors_hash: str, actionable_errors_json: str) -> tuple:
    """Cached version of filing window filter - uses hash for cache key"""
    actionable_errors = pd.read_json(io.StringIO(actionable_errors_json))
    return filter_by_filing_window(actionable_errors)

# Custom CSS for OpenAudit branding
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1F497D 0%, #7EA1C4 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #7EA1C4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .error-card {
        background: #fff5f5;
        border: 1px solid #feb2b2;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-card {
        background: #f0fff4;
        border: 1px solid #9ae6b4;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def get_logo_base64():
    """Convert logo image to base64 for HTML embedding - uses cached version"""
    return get_logo_base64_cached()

def display_header():
    """Display OpenAudit header with branding"""
    st.markdown("""
    <div class="main-header">
        <h1>OpenAudit</h1>
        <p>Freight Audit Platform - Maximize Your Shipping Savings</p>
    </div>
    """, unsafe_allow_html=True)

def filter_by_filing_window(actionable_errors: pd.DataFrame) -> tuple:
    """
    Filter actionable errors to only show claims within FedEx filing windows.
    Uses vectorized pandas operations for better performance.
    
    FedEx Claims Windows:
    - Overcharge/Billing Disputes: 180 days from invoice date
    - Late Delivery (MBG): 15 days from delivery date
    - Lost/Damage Claims: 60 days from shipment date
    
    Returns:
        Tuple of (filtered_df, expired_df, summary_dict)
    """
    if actionable_errors is None or actionable_errors.empty:
        return actionable_errors, pd.DataFrame(), {}
    
    today = pd.Timestamp.now().normalize()
    df = actionable_errors.copy()
    
    # Initialize classification columns
    df['_status'] = 'pending'
    df['_error_upper'] = df['Error Type'].fillna('').str.upper()
    
    # Parse all date columns once (vectorized)
    if 'Shipment Date' in df.columns:
        df['_shipment_date'] = pd.to_datetime(df['Shipment Date'], errors='coerce')
    else:
        df['_shipment_date'] = pd.NaT
        
    if 'Invoice Date' in df.columns:
        df['_invoice_date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
    else:
        df['_invoice_date'] = pd.NaT
        
    if 'Date' in df.columns:
        df['_date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        df['_date'] = pd.NaT
    
    # Extract delivery dates from Notes for Late Delivery claims (vectorized with apply - faster than iterrows)
    def extract_actual_date(notes):
        if pd.isna(notes):
            return pd.NaT
        match = re.search(r'Actual:\s*(\d{4}-\d{2}-\d{2}(?:[T\s][\d:]+(?:[+-]\d{2}:?\d{2}|Z)?)?|\d{1,2}/\d{1,2}/\d{4})', str(notes))
        if match:
            return pd.to_datetime(match.group(1), errors='coerce')
        return pd.NaT
    
    df['_delivery_date'] = df['Notes'].apply(extract_actual_date) if 'Notes' in df.columns else pd.NaT
    
    # Classify Late Delivery claims (15 days from delivery)
    late_mask = df['_error_upper'].str.contains('LATE DELIVERY', na=False)
    late_has_date = late_mask & df['_delivery_date'].notna()
    late_no_date = late_mask & df['_delivery_date'].isna()
    late_days = (today - df['_delivery_date']).dt.days
    df.loc[late_has_date & (late_days <= 15), '_status'] = 'within_window'
    df.loc[late_has_date & (late_days > 15), '_status'] = 'expired'
    df.loc[late_no_date, '_status'] = 'missing_date'
    
    # Classify Lost/Damage claims (60 days from shipment)
    lost_damage_mask = df['_error_upper'].str.contains('LOST|DAMAGE', na=False) & (df['_status'] == 'pending')
    lost_ref_date = df['_shipment_date'].fillna(df['_date'])
    lost_has_date = lost_damage_mask & lost_ref_date.notna()
    lost_no_date = lost_damage_mask & lost_ref_date.isna()
    lost_days = (today - lost_ref_date).dt.days
    df.loc[lost_has_date & (lost_days <= 60), '_status'] = 'within_window'
    df.loc[lost_has_date & (lost_days > 60), '_status'] = 'expired'
    df.loc[lost_no_date, '_status'] = 'missing_date'
    
    # Classify Billing Disputes (180 days from invoice)
    billing_mask = df['_error_upper'].str.contains('DISPUTABLE SURCHARGE|DUPLICATE', na=False) & (df['_status'] == 'pending')
    billing_ref_date = df['_invoice_date'].fillna(df['_date'])
    billing_has_date = billing_mask & billing_ref_date.notna()
    billing_no_date = billing_mask & billing_ref_date.isna()
    billing_days = (today - billing_ref_date).dt.days
    df.loc[billing_has_date & (billing_days <= 180), '_status'] = 'within_window'
    df.loc[billing_has_date & (billing_days > 180), '_status'] = 'expired'
    df.loc[billing_no_date, '_status'] = 'missing_date'
    
    # Default: 180 days for remaining pending claims
    default_mask = df['_status'] == 'pending'
    default_ref_date = df['_invoice_date'].fillna(df['_date'])
    default_has_date = default_mask & default_ref_date.notna()
    default_no_date = default_mask & default_ref_date.isna()
    default_days = (today - default_ref_date).dt.days
    df.loc[default_has_date & (default_days <= 180), '_status'] = 'within_window'
    df.loc[default_has_date & (default_days > 180), '_status'] = 'expired'
    df.loc[default_no_date, '_status'] = 'missing_date'
    
    # Create filtered DataFrames (drop temp columns)
    temp_cols = ['_status', '_error_upper', '_shipment_date', '_invoice_date', '_date', '_delivery_date']
    
    filtered_df = df[df['_status'] == 'within_window'].drop(columns=temp_cols, errors='ignore').copy()
    expired_df = df[df['_status'] == 'expired'].drop(columns=temp_cols, errors='ignore').copy()
    missing_date_df = df[df['_status'] == 'missing_date'].drop(columns=temp_cols, errors='ignore').copy()
    
    # Calculate summary
    summary = {
        'total_original': len(actionable_errors),
        'total_original_value': actionable_errors['Refund Estimate'].sum(),
        'within_window': len(filtered_df),
        'within_window_value': filtered_df['Refund Estimate'].sum() if not filtered_df.empty else 0,
        'expired': len(expired_df),
        'expired_value': expired_df['Refund Estimate'].sum() if not expired_df.empty else 0,
        'missing_date': len(missing_date_df),
        'missing_date_value': missing_date_df['Refund Estimate'].sum() if not missing_date_df.empty else 0
    }
    
    return filtered_df, expired_df, summary

def display_data_requirements():
    """Display data upload requirements and instructions"""
    with st.expander("Data Upload Requirements", expanded=False):
        st.markdown("""
        ### Required Data Format
        Upload your shipment data as **CSV** or **Excel** files with the following columns:

        **Required Columns:**
        - `Carrier` - FedEx, UPS, etc.
        - `Service Type` - Ground, Express, Priority, etc.
        - `Shipment Date` - Date format (YYYY-MM-DD or MM/DD/YYYY)
        - `Tracking Number` - Unique tracking identifier
        - `Zone` - Shipping zone (1-8)
        - `Total Charges` - Total amount charged (e.g., "Net Charge Amount USD")

        **Recommended Columns:**
        - `Delivery Date` - Actual delivery date
        - `Origin ZIP` - Sender ZIP code
        - `Destination ZIP` - Recipient ZIP code
        - `Address Type` - Residential or Commercial
        - `Base Rate` - Base shipping rate (if available separately from Total Charges)
        - `Surcharges` - Additional fees
        - `Actual Weight` - Package weight in lbs
        - `DIM Weight` - Dimensional weight
        - `Length`, `Width`, `Height` - Package dimensions in inches

        **Optional Columns:**
        - `Declared Value` - Insurance value
        - `Fuel Surcharge` - Fuel charges
        - `Residential Surcharge` - Residential delivery fee
        - `Address Correction` - Address correction fees
        
        **Note:** If your file uses "Net Charge Amount USD" as the total amount paid (including freight, surcharges, and discounts), it will automatically map to "Total Charges".
        
        ---
        
        ### Surcharge Report Requirements
        If uploading a separate Surcharge Report file (Merge Files mode), it only needs these columns:
        
        - `Carriers` - FedEx, UPS, etc.
        - `Service` - Service name
        - `Service Type` - Ground, Express, Priority, etc.
        - `Service Description` - Description of service
        - `Shipment Date` - Date of shipment
        - `Shipment Tracking Number` - Tracking identifier to match with shipment data
        - `Surcharge Description` - Type of surcharge applied
        - `Shipment Miscellaneous Charge` - Surcharge amount
        """)

def main():
    # Initialize database
    db = get_db_manager()

    # SECURITY: Centralized list of sensitive session keys to clear
    SENSITIVE_SESSION_KEYS = [
        'uploaded_data', 'audit_results', 'actionable_errors', 
        'selected_claims', 'email_draft_data', 'current_session_id', 
        'trigger_email_draft', 'trigger_fedex_redirect', 'claims_excel_file',
        'claims_excel_filename', 'ltl_data', 'ltl_findings', 'ltl_summary'
    ]

    # Initialize session state
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = None
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'actionable_errors' not in st.session_state:
        st.session_state.actionable_errors = None
    if 'selected_claims' not in st.session_state:
        st.session_state.selected_claims = []
    if 'trigger_email_draft' not in st.session_state:
        st.session_state.trigger_email_draft = False
    if 'trigger_fedex_redirect' not in st.session_state:
        st.session_state.trigger_fedex_redirect = False
    if 'email_draft_data' not in st.session_state:
        st.session_state.email_draft_data = None
    if 'residential_patterns' not in st.session_state:
        st.session_state.residential_patterns = [
            "residential",
            "residential surcharge",
            "residential delivery",
            "delivery area surcharge - residential",
            "das - residential",
            "das residential",
            "home delivery",
            "address correction - residential",
            "residential area surcharge",
            "residential area",
            "res surcharge",
            "resi",
            "home del"
        ]
    
    # SECURITY: Session timeout tracking
    import time
    
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
    
    # Check if session has timed out (1 hour of inactivity)
    current_time = time.time()
    timeout_seconds = 60 * 60  # 1 hour
    
    if current_time - st.session_state.last_activity > timeout_seconds:
        # Clear all sensitive data on timeout
        for key in SENSITIVE_SESSION_KEYS:
            if key in st.session_state:
                del st.session_state[key]
        # Reset last activity and rerun to reinitialize session state properly
        st.session_state.last_activity = time.time()
        st.warning("⏱️ Session timed out after 1 hour of inactivity. All data has been cleared for security.")
        st.rerun()
    
    # Update last activity timestamp
    st.session_state.last_activity = current_time
    
    # SECURITY: Discreet security notice
    st.caption("🔒 Secure session: Data auto-clears after 1 hour or when tab closes")

    # Sidebar for navigation
    with st.sidebar:
        # Subtle OA branding
        st.markdown("""
        <div style="text-align: center; margin: -10px 0 -5px 0;">
            <span style="font-size: 72px; font-weight: 700; color: white; letter-spacing: 8px; line-height: 1;">OA</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation menu
        allowed_pages = auth.get_allowed_pages()
        page = st.radio(
            "Navigation",
            allowed_pages,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Warehouse Addresses Configuration
        with st.expander("⚙️ Warehouse Settings", expanded=False):
            st.markdown("**Configure Your Warehouse Addresses**")
            st.caption("Enter addresses to classify shipments as Outbound (FROM your warehouses) vs Inbound (TO your warehouses)")
            
            # Initialize warehouse addresses in session state
            if 'warehouse_addresses' not in st.session_state:
                st.session_state.warehouse_addresses = []
            
            # Text area for entering addresses (one per line)
            addresses_text = st.text_area(
                "Warehouse Addresses (one per line)",
                value="\n".join(st.session_state.warehouse_addresses),
                height=100,
                placeholder="Example:\n567 Lawerance Dr\n123 Main Street",
                help="Enter your warehouse or distribution center addresses. Shipments FROM these addresses will be classified as Outbound."
            )
            
            if st.button("Save Addresses", use_container_width=True):
                # Parse addresses from text area
                new_addresses = [addr.strip() for addr in addresses_text.split('\n') if addr.strip()]
                st.session_state.warehouse_addresses = new_addresses
                st.success(f"Saved {len(new_addresses)} warehouse address(es)")
                st.rerun()
            
            if st.session_state.warehouse_addresses:
                st.caption(f"Currently configured: {len(st.session_state.warehouse_addresses)} address(es)")
        
        st.markdown("---")
        
        # Clear All Data Button
        if st.button("Clear All Data", type="secondary", help="Immediately wipe all session data", use_container_width=True):
            # Clear all uploaded data from session (uses centralized SENSITIVE_SESSION_KEYS)
            for key in SENSITIVE_SESSION_KEYS:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("All data cleared!")
            st.rerun()

        # Show upgrade message for free trial users
        if auth.is_free_trial_user():
            st.markdown("---")
            st.markdown("**🚀 Upgrade for Full Access**")
            st.markdown("*Get access to all features including:*")
            st.markdown("• Refund Recovery & Claims")
            st.markdown("• PDF Report Generation")
            st.markdown("• Data Export")
            st.markdown("• Email Automation")
            st.markdown("• Contract Analysis")
            st.markdown("• AI Freight Advisor")

    # Display main header conditionally (skip for Q&A, Contract Review, and About OA)
    if page not in ["Q&A", "Contract Review", "About OA"]:
        display_header()

    # Main content area with access control
    if page == "Upload & Audit":
        upload_and_audit_page()
    elif page == "Refund Recovery":
        if auth.check_page_access(page):
            refund_recovery_page()
        else:
            show_upgrade_required_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Generate Report":
        if auth.check_page_access(page):
            generate_report_page()
        else:
            show_upgrade_required_page()
    elif page == "Export Data":
        if auth.check_page_access(page):
            export_data_page()
        else:
            show_upgrade_required_page()
    elif page == "Audit History":
        if auth.check_page_access(page):
            audit_history_page()
        else:
            show_upgrade_required_page()
    elif page == "Contract Review":
        if auth.check_page_access(page):
            contract_review_page()
        else:
            show_upgrade_required_page()
    elif page == "Q&A":
        if auth.check_page_access(page):
            ai_freight_advisor_page()
        else:
            show_upgrade_required_page()
    elif page == "About OA":
        about_oa_page()

def about_oa_page():
    """About OpenAudit page - explains what the system does"""
    st.markdown("""
    <div class="main-header">
        <h1>About OpenAudit</h1>
        <p>Your Freight Audit & Recovery Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    ## What is OpenAudit?
    
    OpenAudit is a freight audit platform that helps businesses identify billing errors, 
    recover overcharges, and optimize their shipping costs. By analyzing your shipping data, 
    we find discrepancies between what you were quoted and what you were actually charged.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📦 Upload & Audit
        Upload your shipping invoices and let OpenAudit automatically scan for:
        - **Duplicate charges** - Same shipment billed multiple times
        - **Rate discrepancies** - Charges that don't match your contracted rates
        - **Invalid surcharges** - Fees that shouldn't have been applied
        - **Weight/dimension errors** - Billing based on incorrect package measurements
        - **Service failures** - Late deliveries that qualify for refunds
        
        Simply upload your carrier invoice data (CSV or Excel format) and the system 
        will identify potential billing errors within seconds.
        """)
        
        st.markdown("""
        ### 💰 Refund Recovery
        Once errors are identified, OpenAudit helps you:
        - Track which errors have been disputed
        - Monitor claim status with carriers
        - Calculate total recovery amounts
        - Generate dispute documentation
        """)
        
        st.markdown("""
        ### 📊 Dashboard
        Get a clear view of your shipping spend with:
        - Total charges and potential savings
        - Error breakdown by category
        - Carrier performance comparisons
        - Trend analysis over time
        """)
    
    with col2:
        st.markdown("""
        ### ❓ Q&A
        Find answers to common freight and shipping questions:
        - Browse frequently asked questions about freight auditing
        - Learn about common carrier surcharges and fees
        - Understand billing terms and industry terminology
        - Get tips for reducing shipping costs
        
        A helpful resource for both beginners and experienced shipping professionals.
        """)
        
        st.markdown("""
        ### 📋 Contract Review
        Leverage AI to analyze your carrier contracts:
        - Extract key rates and terms
        - Identify areas for negotiation
        - Compare rates against industry benchmarks
        - Get recommendations for contract improvements
        
        Upload your carrier agreement PDFs and receive actionable insights.
        """)
        
        st.markdown("""
        ### ⚙️ Warehouse Settings
        Configure your warehouse addresses in the sidebar to automatically classify 
        shipments as **Inbound** (coming to your facilities) or **Outbound** 
        (shipping from your facilities). This helps you analyze freight costs 
        by direction and identify optimization opportunities.
        """)
    
    st.markdown("---")
    
    st.markdown("""
    ## Getting Started
    
    1. **Configure Warehouses** - Add your warehouse addresses in the sidebar settings
    2. **Upload Data** - Go to "Upload & Audit" and upload your carrier invoice data
    3. **Review Results** - Check the Dashboard for an overview of identified errors
    4. **Recover Funds** - Use Refund Recovery to track and dispute billing errors
    5. **Ask Questions** - Use Q&A to get insights about your shipping data
    """)
    
    st.info("💡 **Tip:** Your data is never stored on any server or cloud. It is processed entirely in memory during your session and is automatically cleared when you close the tab or after 1 hour of inactivity.")

def show_upgrade_required_page():
    """Show upgrade required message for free trial users"""
    st.header("🚀 Upgrade Required")

    st.markdown("""
    <div style="background: linear-gradient(90deg, #1F497D 0%, #FFA947 100%); color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h3 style="color: white; margin: 0;">This feature requires a paid subscription</h3>
        <p style="margin: 0.5rem 0 0 0;">You're currently using the free trial with limited access</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔓 **Your Current Access (Free Trial)**")
        st.markdown("✅ Upload & Audit shipment data")
        st.markdown("✅ View dashboard with basic analytics")
        st.markdown("❌ Download reports and data")
        st.markdown("❌ Generate professional PDFs")
        st.markdown("❌ Access refund recovery tools")
        st.markdown("❌ Email automation")
        st.markdown("❌ Contract analysis")
        st.markdown("❌ AI freight advisor")

    with col2:
        st.markdown("### ✨ **Full Access Benefits**")
        st.markdown("• **Professional PDF Reports** - Share with management")
        st.markdown("• **Automated Refund Claims** - Recover overcharges automatically")
        st.markdown("• **Email Automation** - Stay informed with scheduled reports")
        st.markdown("• **Contract Analysis** - Optimize your carrier agreements")
        st.markdown("• **AI Freight Advisor** - Get expert shipping recommendations")
        st.markdown("• **Data Export** - Download all your findings")
        st.markdown("• **Audit History** - Track your savings over time")

    st.markdown("---")
    st.markdown("### 💰 **Ready to unlock the full power of OpenAudit?**")
    st.info("Contact us to upgrade your account and start saving more on shipping costs!")

    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("🚀 Upgrade Now", type="primary", width="stretch"):
            st.markdown("📧 **Contact us at:** sales@ratewiseconsulting.com")
            st.markdown("📞 **Call us to upgrade:** Available during business hours")

def upload_and_audit_page():
    """Handle file upload and initial audit"""
    st.header(" Upload Shipment Data")

    display_data_requirements()

    # File upload options
    upload_mode = st.radio(
        "Upload Method",
        ["Single File (Shipment Details Only)", "Merge Files (Shipment Details + Surcharge Report)"],
        help="Choose whether to upload just shipment data or merge with separate surcharge file"
    )

    if upload_mode == "Single File (Shipment Details Only)":
        # Original single file upload
        uploaded_file = st.file_uploader(
            "Choose a CSV or Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="Upload your FedEx/UPS shipment data for audit analysis"
        )
        surcharge_file = None

    else:
        # Dual file upload for merging
        st.markdown("### Upload Both Files for Merging")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Shipment Details File**")
            uploaded_file = st.file_uploader(
                "Shipment Details",
                type=['csv', 'xlsx', 'xls'],
                help="Main shipment data file with tracking numbers, weights, costs, etc.",
                key="shipment_file"
            )

        with col2:
            st.markdown("**Surcharge Report File**")
            surcharge_file = st.file_uploader(
                "Surcharge Report", 
                type=['csv', 'xlsx', 'xls'],
                help="Surcharge file with tracking numbers and surcharge amounts",
                key="surcharge_file"
            )

        if uploaded_file is not None and surcharge_file is not None:
            st.info("Both files uploaded! The surcharge amounts will be merged with shipment details by tracking number.")
            st.warning("Note: If your shipment file's 'Net Charge Amount' already includes surcharges and discounts, the merged surcharge data will be informational only. It will NOT be added to your total charges to avoid double-counting.")

    if uploaded_file is not None:
        try:
            # Load data
            validator = get_cached_data_validator()

            # Handle file merging if surcharge file is present
            if upload_mode == "Merge Files (Shipment Details + Surcharge Report)" and surcharge_file is not None:
                merge_result, error_message = validator.merge_shipment_and_surcharge_files(uploaded_file, surcharge_file)
                if merge_result is not None:
                    df = merge_result
                    st.success(f"Files merged successfully! Found {len(df)} shipments with updated surcharge totals.")
                else:
                    st.error(f"File merge failed: {error_message}")
                    st.info("Please check that your surcharge file contains tracking numbers and surcharge amounts, then try again.")
                    return
            else:
                df = validator.load_file(uploaded_file)

            if df is not None:
                if upload_mode == "Single File (Shipment Details Only)":
                    st.success(f"File uploaded successfully! Found {len(df)} shipments.")

                # Display data preview
                with st.expander("Data Preview", expanded=True):
                    st.dataframe(df.head(10), width="stretch")

                # Validate required columns
                validation_results = validator.validate_columns(df)

                if validation_results.get('is_valid', False):
                    st.success("All required columns found!")

                    # Clean and prepare data (pass warehouse addresses for freight direction classification)
                    warehouse_addresses = st.session_state.get('warehouse_addresses', [])
                    cleaned_df = validator.clean_data(df, warehouse_addresses=warehouse_addresses)
                    st.session_state.uploaded_data = cleaned_df
                    
                    # Display notification about placeholder delivery dates
                    if 'Delivery Status' in cleaned_df.columns:
                        missing_count = (cleaned_df['Delivery Status'] == 'Missing Delivery Date').sum()
                        if missing_count > 0:
                            st.info(f"ℹ️ {missing_count} shipment(s) with missing or placeholder delivery dates (1900-01-01) are excluded from on-time KPIs.")

                    # Run audit button
                    if st.button("Run Freight Audit", type="primary"):
                        with st.spinner("Running comprehensive freight audit..."):
                            # Use residential patterns from session state
                            audit_engine = FreightAuditEngine(residential_patterns=st.session_state.residential_patterns)
                            audit_results = audit_engine.run_full_audit(cleaned_df)
                            st.session_state.audit_results = audit_results

                            # Filter actionable errors for refund claims
                            actionable_errors = audit_engine.get_actionable_errors(audit_results['findings'])
                            st.session_state.actionable_errors = actionable_errors

                            # SECURITY POLICY: NO DATA PERSISTENCE
                            # Your data is NEVER saved to any database or disk
                            # All data exists only in your browser session (cleared when you close the tab)
                            
                            # Display success message with actionable errors summary
                            if not actionable_errors.empty:
                                total_actionable_savings = actionable_errors['Refund Estimate'].sum()
                                st.success(f"✅ Audit completed! Found {len(actionable_errors)} actionable errors with ${total_actionable_savings:,.2f} in potential refunds.")
                                st.info("Visit the Refund Recovery page to submit claims for these errors.")
                            else:
                                st.success("✅ Audit completed! Check the Dashboard for results.")
                            
                            st.success("🔒 **Security**: Your data is secure and NOT saved to any database. Session data clears automatically when you close your browser.")

                        st.rerun()

                else:
                    st.error("Missing required columns:")
                    missing_cols = validation_results.get('missing_columns', [])
                    for missing_col in missing_cols:
                        st.error(f"• {missing_col}")

                    st.info("Please ensure your file contains all required columns.")

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

def refund_recovery_page():
    """Handle refund claim submission and tracking"""
    
    # Handle email draft trigger
    if st.session_state.trigger_email_draft and st.session_state.email_draft_data:
        import streamlit.components.v1 as components
        components.html(f"""
        <script>
            window.location.href = '{st.session_state.email_draft_data}';
        </script>
        """, height=0)
        st.session_state.trigger_email_draft = False
        st.session_state.email_draft_data = None
    
    # Handle FedEx redirect trigger
    if st.session_state.trigger_fedex_redirect:
        import streamlit.components.v1 as components
        components.html("""
        <script>
            window.open('https://www.fedex.com/secure-login/en-us/#/credentials', '_blank');
        </script>
        """, height=0)
        st.session_state.trigger_fedex_redirect = False
    
    st.header("Refund Recovery")

    # Check if actionable errors are available
    if st.session_state.actionable_errors is None or st.session_state.actionable_errors.empty:
        st.markdown("""
        <div class="error-card">
            <h3>No Actionable Errors Found</h3>
            <p>Please run a freight audit on the Upload & Audit page to identify potential refund opportunities.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Go to Upload & Audit", type="primary"):
            st.rerun()
        return

    raw_actionable_errors = st.session_state.actionable_errors
    
    # Filter by FedEx filing windows
    actionable_errors, expired_errors, filing_summary = filter_by_filing_window(raw_actionable_errors)
    
    # Show filing window info
    st.info("""
    **FedEx Claim Filing Windows:**
    - Late Delivery (MBG): 15 days from delivery date
    - Billing Disputes (Surcharges, Duplicates): 180 days from invoice date
    - Lost/Damage Claims: 60 days from shipment date
    """)
    
    # Show expired claims warning if any
    if filing_summary.get('expired', 0) > 0:
        st.warning(f"""
        **{filing_summary['expired']} claims excluded** - Filing window expired
        (Expired value: {format_currency(filing_summary['expired_value'])})
        """)
    
    # Show warning about claims with missing date info
    if filing_summary.get('missing_date', 0) > 0:
        st.error(f"""
        **{filing_summary['missing_date']} claims excluded** - Missing date information
        (Value: {format_currency(filing_summary['missing_date_value'])})
        
        These claims could not be evaluated because date information is missing. Check your data for Late Delivery claims without delivery dates.
        """)
    
    # Check if any claims remain after filtering
    if actionable_errors.empty:
        st.markdown("""
        <div class="error-card">
            <h3>No Claims Within Filing Window</h3>
            <p>All identified errors have exceeded their filing deadlines. Upload more recent shipment data to find actionable claims.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary section
    st.subheader("Claim Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_claims = len(actionable_errors)
        st.markdown(f"""
        <div class="metric-card">
            <h3>Eligible Claims</h3>
            <h2 style="color: #1F497D;">{total_claims}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        total_potential = actionable_errors['Refund Estimate'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <h3>Potential Recovery</h3>
            <h2 style="color: #7EA1C4;">{format_currency(total_potential)}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        high_priority = len(actionable_errors[actionable_errors['Claim Priority'] == 'High'])
        st.markdown(f"""
        <div class="metric-card">
            <h3>High Priority</h3>
            <h2 style="color: #d32f2f;">{high_priority}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        ready_to_submit = len(actionable_errors[actionable_errors['Claim Status'] == 'Ready to Submit'])
        st.markdown(f"""
        <div class="metric-card">
            <h3>Ready to Submit</h3>
            <h2 style="color: #2e7d32;">{ready_to_submit}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Filters and sorting
    st.subheader("Filter Claims")

    col1, col2, col3 = st.columns(3)

    with col1:
        error_types = ['All'] + list(actionable_errors['Error Type'].unique()) if not actionable_errors.empty else ['All']
        selected_error_type = st.selectbox("Error Type", error_types)

    with col2:
        priorities = ['All'] + list(actionable_errors['Claim Priority'].unique()) if not actionable_errors.empty else ['All']
        selected_priority = st.selectbox("Priority Level", priorities)

    with col3:
        min_refund = st.number_input("Min Refund Amount ($)", min_value=0.0, value=0.0)

    # Apply filters
    filtered_claims = actionable_errors.copy()

    if selected_error_type != 'All':
        filtered_claims = filtered_claims[filtered_claims['Error Type'] == selected_error_type]

    if selected_priority != 'All':
        filtered_claims = filtered_claims[filtered_claims['Claim Priority'] == selected_priority]

    if min_refund > 0:
        filtered_claims = filtered_claims[filtered_claims['Refund Estimate'] >= min_refund]

    st.markdown("---")

    # Claims table with selection
    st.subheader("Actionable Claims")

    if not filtered_claims.empty:
        # Sort by refund amount (highest first)
        filtered_claims = filtered_claims.sort_values('Refund Estimate', ascending=False)

        # Reset selected claims when filtering changes
        current_filter_key = f"{selected_error_type}_{selected_priority}_{min_refund}"
        if st.session_state.get('last_filter_key') != current_filter_key:
            st.session_state.selected_claims = []
            st.session_state.last_filter_key = current_filter_key

        # Select all checkbox
        select_all = st.checkbox("Select All Claims", key="select_all_claims")

        # Handle select all functionality
        if select_all:
            st.session_state.selected_claims = list(filtered_claims.index)

        # Display claims in a clean format
        for idx, (index, claim) in enumerate(filtered_claims.iterrows()):
            with st.container():
                col1, col2 = st.columns([1, 10])

                with col1:
                    # Individual checkbox
                    is_individually_selected = index in st.session_state.selected_claims
                    checkbox_value = st.checkbox("", key=f"claim_{idx}", value=is_individually_selected)

                    # Update selection state
                    if checkbox_value and index not in st.session_state.selected_claims:
                        st.session_state.selected_claims.append(index)
                    elif not checkbox_value and index in st.session_state.selected_claims:
                        st.session_state.selected_claims.remove(index)

                with col2:
                    # Priority color coding
                    priority_colors = {
                        'High': '#d32f2f',
                        'Medium': '#f57c00', 
                        'Low': '#388e3c'
                    }
                    priority_color = priority_colors.get(claim['Claim Priority'], '#666666')

                    st.markdown(f"""
                    <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid {priority_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <strong style="color: #1F497D; font-size: 1.1em;">Tracking: {claim['Tracking Number']}</strong>
                            <span style="background: {priority_color}; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8em;">{claim['Claim Priority']} Priority</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 0.5rem 0;">
                            <div><strong>Error Type:</strong> {claim['Error Type']}</div>
                            <div><strong>Carrier:</strong> {claim['Carrier']}</div>
                            <div><strong>Service:</strong> {claim['Service Type']}</div>
                        </div>
                        <div style="margin: 0.5rem 0;">
                            <strong>Dispute Reason:</strong> {claim['Dispute Reason']}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span><strong>Date:</strong> {claim['Date']}</span>
                            <span style="color: #7EA1C4; font-size: 1.2em; font-weight: bold;">Refund: {format_currency(claim['Refund Estimate'])}</span>
                        </div>
                        {f"<div style='color: #666; font-size: 0.9em; margin-top: 0.5rem;'><strong>Notes:</strong> {claim.get('Notes', 'N/A')}</div>" if claim.get('Notes') else ""}
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")

        # Claim submission section
        if st.session_state.selected_claims:
            st.subheader("Submit Claims")

            # Calculate totals for selected claims
            selected_df = filtered_claims.loc[st.session_state.selected_claims]

            total_selected = len(selected_df)
            total_recovery = selected_df['Refund Estimate'].sum()

            col1, col2 = st.columns(2)

            with col1:
                st.info(f" **Selected Claims:** {total_selected}")
                st.info(f" **Total Recovery:** {format_currency(total_recovery)}")

            with col2:
                claim_method = st.radio(
                    "Submission Method:",
                    ["Email Claims Report", "Bulk Upload to FedEx", "Download Dispute Package"],
                    help="Choose how you'd like to submit these claims"
                )

            # Submit button
            if st.button(" Submit Selected Claims", type="primary", width="stretch"):
                # Simulate claim submission
                submitted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Get current user information
                auth = get_auth_manager()
                user = auth.get_current_user()

                # Prepare claims data
                claims_data = []
                for _, claim in selected_df.iterrows():
                    claim_record = {
                        'tracking_number': claim['Tracking Number'],
                        'error_type': claim['Error Type'],
                        'refund_estimate': claim['Refund Estimate'],
                        'submission_method': claim_method,
                        'submitted_at': submitted_time,
                        'status': 'Submitted',
                        'carrier': claim['Carrier'],
                        'ship_date': claim.get('Date', ''),
                        'service_type': claim.get('Service Type', ''),
                        'dispute_reason': claim.get('Dispute Reason', ''),
                        'notes': claim.get('Notes', '')
                    }
                    claims_data.append(claim_record)

                # Generate Excel file for Email Claims Report or FedEx Bulk Upload
                if claim_method in ["Email Claims Report", "Bulk Upload to FedEx"]:
                    # Create FedEx bulk upload format Excel file
                    excel_data = []
                    for claim in claims_data:
                        excel_data.append({
                            'Tracking Number': claim['tracking_number'],
                            'Claim Type': claim['error_type'],
                            'Claim Amount': claim['refund_estimate'],
                            'Ship Date': claim['ship_date'],
                            'Shipper Name': user.get('company_name', ''),
                            'Recipient Name': '',
                            'Package Description': claim['error_type'],
                            'Customer Reference': claim['tracking_number'],
                            'Declared Value': claim['refund_estimate'],
                            'Notes/Comments': f"{claim['dispute_reason']}. {claim['notes']}"
                        })
                    
                    excel_df = pd.DataFrame(excel_data)
                    
                    # Create Excel file in memory
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        excel_df.to_excel(writer, index=False, sheet_name='Claims')
                    excel_file = output.getvalue()
                    
                    # Store in session state for download
                    st.session_state.claims_excel_file = excel_file
                    st.session_state.claims_excel_filename = f"FedEx_Claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                # Success message with download button
                st.success(f"""
                 **Claims Prepared Successfully!**

                - **Number of Claims:** {total_selected}
                - **Total Recovery Amount:** {format_currency(total_recovery)}
                - **Submission Method:** {claim_method}
                - **Submitted At:** {submitted_time}
                """)

                if claim_method == "Email Claims Report":
                    st.info("""
                     **Email Draft Opening:**
                    1. Download the Excel file below
                    2. Your email client will open automatically with a pre-filled message
                    3. Attach the downloaded Excel file to the email
                    4. Add the recipient email address
                    5. Send the email
                    """)
                    
                    # Download button
                    st.download_button(
                        label=" Download Claims Excel",
                        data=st.session_state.claims_excel_file,
                        file_name=st.session_state.claims_excel_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    # Create mailto link for email draft
                    subject = f"Freight Claims Submission - {total_selected} Claims - {format_currency(total_recovery)}"
                    
                    # Build detailed claim list
                    claims_details = []
                    for idx, claim in enumerate(claims_data, 1):
                        claim_detail = f"""
Claim #{idx}:
  • Tracking Number: {claim['tracking_number']}
  • Carrier: {claim['carrier']}
  • Service Type: {claim['service_type']}
  • Date: {claim['ship_date']}
  • Error Type: {claim['error_type']}
  • Dispute Reason: {claim['dispute_reason']}
  • Refund Amount: {format_currency(claim['refund_estimate'])}"""
                        claims_details.append(claim_detail)
                    
                    body = f"""Hello,

Please find attached {total_selected} freight claims for review and processing.

SUMMARY:
- Total Claims: {total_selected}
- Total Recovery Amount: {format_currency(total_recovery)}
- Submission Date: {submitted_time}

DETAILED CLAIM INFORMATION:
{''.join(claims_details)}

The attached Excel file contains all claim details in a structured format for easy processing.

Thank you,
{user.get('name', 'User')}
{user.get('company_name', '')}"""
                    
                    # URL encode the subject and body
                    import urllib.parse
                    mailto_link = f"mailto:?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                    
                    # Store email draft data and trigger flag
                    st.session_state.email_draft_data = mailto_link
                    st.session_state.trigger_email_draft = True
                
                elif claim_method == "Bulk Upload to FedEx":
                    st.info("""
                     **Redirecting to FedEx:**
                    1. Download the Excel file below (formatted for FedEx bulk claims)
                    2. FedEx login page will open in a new tab
                    3. After logging in, navigate to "File Batch Claims"
                    4. Upload the Excel file you downloaded
                    5. Review and submit your batch claims
                    
                    **Note:** You may need to add supporting documentation (photos, invoices) after upload.
                    """)
                    
                    # Download button
                    st.download_button(
                        label=" Download FedEx Bulk Upload File",
                        data=st.session_state.claims_excel_file,
                        file_name=st.session_state.claims_excel_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    # Trigger FedEx redirect
                    st.session_state.trigger_fedex_redirect = True

                # Update claim status in actionable_errors
                st.session_state.actionable_errors.loc[st.session_state.selected_claims, 'Claim Status'] = 'Submitted'

                # Clear selected claims after successful submission
                st.session_state.selected_claims = []

        else:
            st.info(" Select claims above to submit them for recovery.")

    else:
        st.warning("No claims match your filter criteria.")


def dashboard_page():
    """Display audit results dashboard"""
    st.header("Audit Dashboard")

    if st.session_state.audit_results is None:
        st.warning("No audit results available. Please upload and audit data first.")
        return

    audit_results = st.session_state.audit_results

    # Savings Summary
    st.subheader("Savings Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>Total Charges Audited</h3>
            <h2 style="color: #1F497D;">""" + format_currency(audit_results['summary']['total_charges']) + """</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>Potential Savings</h3>
            <h2 style="color: #7EA1C4;">""" + format_currency(audit_results['summary']['total_savings']) + """</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        savings_rate = (audit_results['summary']['total_savings'] / audit_results['summary']['total_charges'] * 100) if audit_results['summary']['total_charges'] > 0 else 0
        st.markdown("""
        <div class="metric-card">
            <h3>Savings Rate</h3>
            <h2 style="color: #1F497D;">""" + f"{savings_rate:.1f}%" + """</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>Shipments with Issues</h3>
            <h2 style="color: #7EA1C4;">""" + str(audit_results['summary']['affected_shipments']) + """</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Freight Direction Breakdown (Inbound vs Outbound)
    if st.session_state.uploaded_data is not None and 'Freight Direction' in st.session_state.uploaded_data.columns:
        st.markdown("---")
        st.subheader("Freight Direction Breakdown")
        
        uploaded_data = st.session_state.uploaded_data
        
        # Calculate inbound/outbound metrics
        direction_summary = uploaded_data.groupby('Freight Direction').agg({
            'Total Charges': 'sum',
            'Tracking Number': 'count'
        }).reset_index()
        direction_summary.columns = ['Direction', 'Total Cost', 'Shipment Count']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Inbound metrics
            inbound_data = direction_summary[direction_summary['Direction'] == 'Inbound']
            if not inbound_data.empty:
                inbound_cost = inbound_data['Total Cost'].iloc[0]
                inbound_count = inbound_data['Shipment Count'].iloc[0]
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Inbound Freight</h3>
                    <h2 style="color: #1F497D;">{format_currency(inbound_cost)}</h2>
                    <p style="color: #7EA1C4; font-size: 16px; margin-top: 10px;">{inbound_count:,} shipments</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <h3>Inbound Freight</h3>
                    <h2 style="color: #1F497D;">$0.00</h2>
                    <p style="color: #7EA1C4; font-size: 16px; margin-top: 10px;">0 shipments</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Outbound metrics
            outbound_data = direction_summary[direction_summary['Direction'] == 'Outbound']
            if not outbound_data.empty:
                outbound_cost = outbound_data['Total Cost'].iloc[0]
                outbound_count = outbound_data['Shipment Count'].iloc[0]
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Outbound Freight</h3>
                    <h2 style="color: #7EA1C4;">{format_currency(outbound_cost)}</h2>
                    <p style="color: #1F497D; font-size: 16px; margin-top: 10px;">{outbound_count:,} shipments</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <h3>Outbound Freight</h3>
                    <h2 style="color: #7EA1C4;">$0.00</h2>
                    <p style="color: #1F497D; font-size: 16px; margin-top: 10px;">0 shipments</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Visualizations
    viz_manager = get_cached_visualization_manager()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Error Types Distribution")
        error_chart = viz_manager.create_error_distribution_chart(audit_results['findings'])
        st.plotly_chart(error_chart, width="stretch")

    with col2:
        st.subheader("Savings by Category")
        savings_chart = viz_manager.create_savings_by_category_chart(audit_results['findings'])
        st.plotly_chart(savings_chart, width="stretch")

    # Timeline chart
    st.subheader("Overcharges Timeline")
    timeline_chart = viz_manager.create_timeline_chart(audit_results['findings'])
    st.plotly_chart(timeline_chart, width="stretch")

    # Detailed findings table
    st.subheader("Detailed Audit Findings")

    if not audit_results['findings'].empty:
        # Advanced filter options
        with st.expander(" Advanced Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                error_types = ['All'] + list(audit_results['findings']['Error Type'].unique())
                selected_error = st.selectbox("Error Type", error_types)

            with col2:
                carriers = ['All'] + list(audit_results['findings']['Carrier'].unique()) if 'Carrier' in audit_results['findings'].columns else ['All']
                selected_carrier = st.selectbox("Carrier", carriers)

            with col3:
                service_types = ['All'] + list(audit_results['findings']['Service Type'].unique()) if 'Service Type' in audit_results['findings'].columns else ['All']
                selected_service = st.selectbox("Service Type", service_types)

            with col4:
                min_savings = st.number_input("Min Refund ($)", min_value=0.0, value=0.0)
                max_savings = st.number_input("Max Refund ($)", min_value=0.0, value=10000.0)

            # Date range filter
            col1, col2, col3 = st.columns(3)
            with col1:
                if 'Date' in audit_results['findings'].columns:
                    dates = pd.to_datetime(audit_results['findings']['Date'], errors='coerce')
                    min_date = dates.min().date() if not dates.isna().all() else datetime.now().date() - timedelta(days=365)
                    max_date = dates.max().date() if not dates.isna().all() else datetime.now().date()

                    start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
                    end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

            # Text search
            with col2:
                search_text = st.text_input("Search Tracking Numbers", placeholder="Enter tracking number...")

            with col3:
                dispute_reason_search = st.text_input("Search Dispute Reasons", placeholder="Enter keywords...")

        # Sort options
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox("Sort By", ["Date", "Refund Estimate", "Error Type", "Carrier", "Tracking Number"])
        with col2:
            sort_order = st.selectbox("Sort Order", ["Descending", "Ascending"])

        # Apply filters
        filtered_findings = audit_results['findings'].copy()

        # Error type filter
        if selected_error != 'All':
            filtered_findings = filtered_findings[filtered_findings['Error Type'] == selected_error]

        # Carrier filter
        if selected_carrier != 'All' and 'Carrier' in filtered_findings.columns:
            filtered_findings = filtered_findings[filtered_findings['Carrier'] == selected_carrier]

        # Service type filter
        if 'selected_service' in locals() and selected_service != 'All' and 'Service Type' in filtered_findings.columns:
            filtered_findings = filtered_findings[filtered_findings['Service Type'] == selected_service]

        # Refund amount filters
        if min_savings > 0:
            filtered_findings = filtered_findings[filtered_findings['Refund Estimate'] >= min_savings]

        if 'max_savings' in locals() and max_savings < 10000:
            filtered_findings = filtered_findings[filtered_findings['Refund Estimate'] <= max_savings]

        # Date range filter
        if 'start_date' in locals() and 'end_date' in locals() and 'Date' in filtered_findings.columns:
            dates = pd.to_datetime(filtered_findings['Date'], errors='coerce')
            filtered_findings = filtered_findings[
                (dates >= pd.to_datetime(start_date)) & 
                (dates <= pd.to_datetime(end_date))
            ]

        # Text search filters
        if 'search_text' in locals() and search_text and 'Tracking Number' in filtered_findings.columns:
            filtered_findings = filtered_findings[
                filtered_findings['Tracking Number'].astype(str).str.contains(search_text, case=False, na=False)
            ]

        if 'dispute_reason_search' in locals() and dispute_reason_search and 'Dispute Reason' in filtered_findings.columns:
            filtered_findings = filtered_findings[
                filtered_findings['Dispute Reason'].astype(str).str.contains(dispute_reason_search, case=False, na=False)
            ]

        # Sort the results
        if not filtered_findings.empty and sort_by in filtered_findings.columns:
            ascending = sort_order == "Ascending"
            if sort_by == "Refund Estimate":
                filtered_findings = filtered_findings.sort_values(by=sort_by, ascending=ascending)
            elif sort_by == "Date":
                filtered_findings['sort_date'] = pd.to_datetime(filtered_findings['Date'], errors='coerce')
                filtered_findings = filtered_findings.sort_values(by='sort_date', ascending=ascending)
                filtered_findings = filtered_findings.drop('sort_date', axis=1)
            else:
                filtered_findings = filtered_findings.sort_values(by=sort_by, ascending=ascending)

        # Display filtered results
        st.dataframe(
            filtered_findings,
            width="stretch",
            column_config={
                "Refund Estimate": st.column_config.NumberColumn(
                    "Refund Estimate",
                    format="$%.2f"
                ),
                "Date": st.column_config.DateColumn(
                    "Date",
                    format="MM/DD/YYYY"
                )
            }
        )

        st.info(f"Showing {len(filtered_findings)} of {len(audit_results['findings'])} findings")

    else:
        st.success("🎉 No issues found in your shipment data!")

def generate_report_page():
    """Generate and download PDF dispute report"""
    st.header("📄 Generate Dispute Report")

    if st.session_state.audit_results is None:
        st.warning("No audit results available. Please upload and audit data first.")
        return

    audit_results = st.session_state.audit_results

    # Report configuration
    st.subheader(" Report Configuration")

    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input("Company Name", value="Your Company")
        report_date = st.date_input("Report Date", value=datetime.now().date())

    with col2:
        include_summary = st.checkbox("Include Executive Summary", value=True)
        group_by_carrier = st.checkbox("Group by Carrier", value=True)

    # Generate report button
    if st.button("📄 Generate PDF Report", type="primary"):
        with st.spinner("Generating PDF dispute report..."):
            try:
                pdf_generator = ReportGenerator()
                pdf_buffer = pdf_generator.generate_dispute_report(
                    audit_results,
                    company_name=company_name,
                    report_date=datetime.combine(report_date, datetime.min.time()),
                    include_summary=include_summary,
                    group_by_carrier=group_by_carrier
                )

                # Download button
                st.download_button(
                    label="📥 Download Dispute Report",
                    data=pdf_buffer.getvalue(),
                    file_name=f"OpenAudit_Dispute_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

                st.success(" PDF report generated successfully!")

            except Exception as e:
                st.error(f" Error generating PDF: {str(e)}")

    # Preview report summary
    if not audit_results['findings'].empty:
        st.subheader(" Report Preview")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Report Summary:**")
            st.write(f"• Total Findings: {len(audit_results['findings'])}")
            st.write(f"• Total Potential Savings: {format_currency(audit_results['summary']['total_savings'])}")
            st.write(f"• Report Date: {report_date}")

        with col2:
            st.markdown("**Error Breakdown:**")
            error_counts = audit_results['findings']['Error Type'].value_counts()
            for error_type, count in error_counts.items():
                st.write(f"• {error_type}: {count}")

def export_data_page():
    """Export audit results to CSV"""
    st.header(" Export Data")

    if st.session_state.audit_results is None:
        st.warning("No audit results available. Please upload and audit data first.")
        return

    audit_results = st.session_state.audit_results

    st.subheader("💾 Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Available Exports:**")
        st.write("• Audit Findings (CSV)")
        st.write("• Summary Report (CSV)")
        st.write("• Raw Data with Flags (CSV)")

    with col2:
        export_format = st.selectbox("Export Format", ["CSV", "Excel"])
        include_raw_data = st.checkbox("Include Original Data", value=True)

    # Export buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(" Export Findings"):
            csv_buffer = io.StringIO()
            audit_results['findings'].to_csv(csv_buffer, index=False)

            st.download_button(
                label="📥 Download Findings CSV",
                data=csv_buffer.getvalue(),
                file_name=f"ratewise_findings_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col2:
        if st.button(" Export Summary"):
            summary_df = pd.DataFrame([audit_results['summary']])
            csv_buffer = io.StringIO()
            summary_df.to_csv(csv_buffer, index=False)

            st.download_button(
                label="📥 Download Summary CSV",
                data=csv_buffer.getvalue(),
                file_name=f"ratewise_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col3:
        if st.button(" Export All Data") and include_raw_data:
            if st.session_state.uploaded_data is not None:
                csv_buffer = io.StringIO()
                st.session_state.uploaded_data.to_csv(csv_buffer, index=False)

                st.download_button(
                    label="📥 Download Raw Data CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"ratewise_raw_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

def audit_history_page():
    """Display audit history and trends"""
    st.header(" Audit History")

    auth = get_auth_manager()
    user = auth.get_current_user()

    # Check if in demo mode
    if st.session_state.get('demo_mode', False):
        st.warning("Running in demo mode - audit history is not available.")
        st.info("To access audit history, please ensure database connectivity and restart the application.")
        return

    try:
        db = get_db_manager()
        # Get user statistics
        stats = db.get_user_statistics(user['id'])
    except Exception as e:
        st.error(" Unable to connect to database to retrieve history.")
        st.info(" You can still use the current session features in the Dashboard and Generate Report pages.")
        return

    # Display overall statistics
    st.subheader(" Your OpenAudit Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Audits", stats['total_audits'])

    with col2:
        st.metric("Charges Audited", format_currency(stats['total_charges_audited']))

    with col3:
        st.metric("Savings Identified", format_currency(stats['total_savings_identified']))

    with col4:
        avg_savings = (stats['total_savings_identified'] / stats['total_charges_audited'] * 100) if stats['total_charges_audited'] > 0 else 0
        st.metric("Avg Savings Rate", f"{avg_savings:.1f}%")

    st.markdown("---")

    # Get audit history
    audit_history = db.get_user_audit_history(user['id'])

    if not audit_history:
        st.info(" No audit history yet. Upload your first shipment data to get started!")
        return

    st.subheader(" Recent Audits")

    # Create history table
    history_data = []
    for session in audit_history:
        history_data.append({
            'Date': session.created_at.strftime('%Y-%m-%d %H:%M'),
            'Filename': session.filename,
            'Total Charges': f"${session.total_charges:,.2f}",
            'Savings Found': f"${session.total_savings:,.2f}",
            'Savings Rate': f"{session.savings_rate:.1f}%",
            'Affected Shipments': session.affected_shipments,
            'Total Shipments': session.total_shipments,
            'Session ID': session.id
        })

    if history_data:
        import pandas as pd
        history_df = pd.DataFrame(history_data)

        # Display table with selection
        selected_indices = st.dataframe(
            history_df.drop('Session ID', axis=1),
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Show details for selected audit
        if hasattr(selected_indices, 'selection') and selected_indices.selection.rows:
            selected_idx = selected_indices.selection.rows[0]
            selected_session_id = history_data[selected_idx]['Session ID']

            st.subheader(" Audit Details")

            # Get detailed audit session
            session_details = db.get_audit_session_details(selected_session_id, user['id'])

            if session_details:
                session = session_details['session']
                findings = session_details['findings']

                # Display session summary
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Audit Date:** {session.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**Filename:** {session.filename}")
                    st.markdown(f"**Total Charges:** {format_currency(session.total_charges)}")
                    st.markdown(f"**Total Savings:** {format_currency(session.total_savings)}")

                with col2:
                    st.markdown(f"**Savings Rate:** {session.savings_rate:.1f}%")
                    st.markdown(f"**Total Shipments:** {session.total_shipments:,}")
                    st.markdown(f"**Affected Shipments:** {session.affected_shipments:,}")
                    st.markdown(f"**Error Rate:** {(session.affected_shipments/session.total_shipments*100) if session.total_shipments > 0 else 0:.1f}%")

                # Display findings
                if findings:
                    st.subheader(" Audit Findings")

                    findings_data = []
                    for finding in findings:
                        findings_data.append({
                            'Error Type': finding.error_type,
                            'Tracking Number': finding.tracking_number,
                            'Date': finding.shipment_date.strftime('%Y-%m-%d') if finding.shipment_date else '',
                            'Carrier': finding.carrier,
                            'Service Type': finding.service_type,
                            'Dispute Reason': finding.dispute_reason,
                            'Refund Estimate': f"${finding.refund_estimate:.2f}",
                            'Notes': finding.notes
                        })

                    findings_df = pd.DataFrame(findings_data)
                    st.dataframe(findings_df, width="stretch", hide_index=True)

                    # Option to regenerate report for this session
                    if st.button("📄 Generate Report for This Audit", key=f"report_{selected_session_id}"):
                        # Convert findings back to the format expected by PDF generator
                        findings_for_pdf = pd.DataFrame([{
                            'Error Type': f.error_type,
                            'Tracking Number': f.tracking_number,
                            'Date': f.shipment_date.strftime('%Y-%m-%d') if f.shipment_date else '',
                            'Carrier': f.carrier,
                            'Service Type': f.service_type,
                            'Dispute Reason': f.dispute_reason,
                            'Refund Estimate': f.refund_estimate,
                            'Notes': f.notes
                        } for f in findings])

                        audit_results_for_pdf = {
                            'findings': findings_for_pdf,
                            'summary': {
                                'total_charges': session.total_charges,
                                'total_savings': session.total_savings,
                                'affected_shipments': session.affected_shipments,
                                'total_shipments': session.total_shipments,
                                'savings_rate': session.savings_rate
                            }
                        }

                        try:
                            pdf_generator = ReportGenerator()
                            pdf_buffer = pdf_generator.generate_dispute_report(
                                audit_results_for_pdf,
                                company_name=user['company_name'] or "Your Company",
                                report_date=datetime.combine(session.created_at.date(), datetime.min.time()),
                                include_summary=True,
                                group_by_carrier=True
                            )

                            st.download_button(
                                label="📥 Download Historical Report",
                                data=pdf_buffer.getvalue(),
                                file_name=f"OpenAudit_Historical_Report_{session.created_at.strftime('%Y%m%d')}.pdf",
                                mime="application/pdf"
                            )

                        except Exception as e:
                            st.error(f" Error generating historical report: {str(e)}")
                else:
                    st.info("No specific findings recorded for this audit session.")

    # Load previous audit into current session
    if st.button("🔄 Load Selected Audit into Current Session"):
        if hasattr(selected_indices, 'selection') and selected_indices.selection.rows:
            selected_idx = selected_indices.selection.rows[0]
            selected_session_id = history_data[selected_idx]['Session ID']

            session_details = db.get_audit_session_details(selected_session_id, user['id'])

            if session_details:
                findings = session_details['findings']
                session = session_details['session']

                # Convert back to audit results format
                findings_df = pd.DataFrame([{
                    'Error Type': f.error_type,
                    'Tracking Number': f.tracking_number,
                    'Date': f.shipment_date.strftime('%Y-%m-%d') if f.shipment_date else '',
                    'Carrier': f.carrier,
                    'Service Type': f.service_type,
                    'Dispute Reason': f.dispute_reason,
                    'Refund Estimate': f.refund_estimate,
                    'Notes': f.notes
                } for f in findings])

                audit_results = {
                    'findings': findings_df,
                    'summary': {
                        'total_charges': session.total_charges,
                        'total_savings': session.total_savings,
                        'affected_shipments': session.affected_shipments,
                        'total_shipments': session.total_shipments,
                        'savings_rate': session.savings_rate
                    }
                }

                st.session_state.audit_results = audit_results
                st.success(" Audit loaded! You can now view it in the Dashboard or generate reports.")
        else:
            st.warning("Please select an audit session first.")

def contract_review_page():
    """Contract Review and Negotiation Strategy page"""
    auth = get_auth_manager()
    user = auth.get_current_user()

    st.markdown("""
    <div style="background: linear-gradient(90deg, #1F497D 0%, #7EA1C4 100%); color: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; text-align: center;">
        <h3 style="color: white; margin: 0;"> Contract Intelligence Platform</h3>
        <p style="margin: 0.5rem 0 0 0;">Upload your carrier contract to receive a comprehensive analysis, industry benchmark comparison, and custom negotiation strategy</p>
    </div>
    """, unsafe_allow_html=True)

    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([" Upload Contract", " Analysis Results", " Strategy", " History"])

    with tab1:
        st.subheader(" Upload Carrier Contract")

        col1, col2 = st.columns([2, 1])

        with col1:
            # File upload
            uploaded_file = st.file_uploader(
                "Choose your contract file",
                type=['pdf', 'xlsx', 'xls', 'csv'],
                help="Upload your carrier contract, rate sheet, or master agreement"
            )

            if uploaded_file:
                # Contract information form
                with st.form("contract_info_form"):
                    st.write("**Contract Information**")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        contract_name = st.text_input(
                            "Contract Name*", 
                            value=uploaded_file.name.split('.')[0],
                            help="A name to identify this contract"
                        )

                        carrier = st.selectbox(
                            "Carrier*",
                            ["FedEx", "UPS", "DHL", "USPS", "Other"],
                            help="Select your carrier"
                        )

                    with col_b:
                        contract_type = st.selectbox(
                            "Contract Type",
                            ["Rate Sheet", "Master Agreement", "Amendment", "Other"],
                            help="Type of contract document"
                        )

                        annual_spend = st.number_input(
                            "Estimated Annual Spend ($)",
                            min_value=0,
                            value=100000,
                            step=10000,
                            help="Your estimated annual shipping spend with this carrier"
                        )

                    submitted = st.form_submit_button(" Analyze Contract", type="primary")

                    if submitted and uploaded_file and contract_name and carrier:
                        try:
                            with st.spinner(" Analyzing your contract... This may take a few minutes."):
                                # Import contract analysis modules
                                from contract_parser import get_contract_parser
                                from contract_benchmarks import get_benchmark_engine
                                from contract_strategy_generator import get_strategy_generator

                                # Parse the contract
                                parser = get_contract_parser()
                                file_extension = uploaded_file.name.split('.')[-1].lower()
                                contract_terms = parser.parse_contract_file(
                                    uploaded_file.getvalue(),
                                    file_extension,
                                    uploaded_file.name
                                )

                                # Get industry benchmarks
                                benchmark_engine = get_benchmark_engine()
                                benchmark = benchmark_engine.get_benchmark_for_company(
                                    carrier, annual_spend
                                )

                                # Convert contract terms to dict for comparison
                                terms_dict = {
                                    'base_discount_pct': contract_terms.base_discount_pct,
                                    'dim_divisor': contract_terms.dim_divisor,
                                    'fuel_surcharge_pct': contract_terms.fuel_surcharge_pct,
                                    'residential_surcharge': contract_terms.residential_surcharge,
                                    'delivery_area_surcharge': contract_terms.delivery_area_surcharge
                                }

                                # Compare to benchmarks
                                comparison_results = benchmark_engine.compare_contract_to_benchmark(
                                    terms_dict, benchmark
                                )

                                # Calculate health score
                                health_score, health_score_numeric = benchmark_engine.calculate_contract_health_score(
                                    comparison_results
                                )

                                # Calculate savings potential
                                savings_potential = benchmark_engine.estimate_annual_savings_potential(
                                    comparison_results, annual_spend
                                )

                                # Generate recommendations
                                recommendations = benchmark_engine.generate_negotiation_recommendations(
                                    comparison_results, benchmark
                                )

                                # Store results in session state
                                st.session_state.contract_analysis = {
                                    'contract_info': {
                                        'name': contract_name,
                                        'carrier': carrier,
                                        'type': contract_type,
                                        'annual_spend': annual_spend,
                                        'filename': uploaded_file.name
                                    },
                                    'contract_terms': terms_dict,
                                    'extraction_confidence': contract_terms.extraction_confidence,
                                    'benchmark_comparison': comparison_results,
                                    'health_score': health_score,
                                    'health_score_numeric': health_score_numeric,
                                    'savings_potential': savings_potential,
                                    'recommendations': recommendations,
                                    'benchmark_data': benchmark
                                }

                                # Save to database if possible
                                try:
                                    db = get_db_manager()
                                    # Note: Would implement database saving here
                                    st.success(" Contract analysis completed successfully!")
                                except Exception as e:
                                    st.success(" Contract analysis completed! (Results saved locally)")

                                st.info(" Switch to the 'Analysis Results' tab to view your contract evaluation.")

                        except Exception as e:
                            st.error(f" Error analyzing contract: {str(e)}")
                            st.info("Please ensure your file contains contract terms in a readable format.")

                    elif submitted:
                        if not uploaded_file:
                            st.error("Please upload a contract file.")
                        elif not contract_name:
                            st.error("Please enter a contract name.")
                        elif not carrier:
                            st.error("Please select a carrier.")

        with col2:
            st.markdown("###  **Supported Formats**")
            st.markdown("""
            - **PDF**: Rate sheets, contracts
            - **Excel**: Pricing tables, rate sheets  
            - **CSV**: Rate data exports

            ###  **What We Extract**
            - Base discount percentages
            - DIM weight divisors
            - Fuel surcharge rates
            - Residential delivery fees
            - Extended area surcharges
            - Zone-based pricing

            ### ⭐ **What You Get**
            - Contract health score (A-F)
            - Industry benchmark comparison
            - Potential savings analysis
            - Professional negotiation strategy
            - Talking points and recommendations
            """)

    with tab2:
        st.subheader(" Contract Analysis Results")

        if 'contract_analysis' not in st.session_state:
            st.info(" Please upload and analyze a contract first using the 'Upload Contract' tab.")
        else:
            analysis = st.session_state.contract_analysis

            # Contract health score display
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Contract Health Score", 
                    analysis['health_score'],
                    f"{analysis['health_score_numeric']:.1f}/100"
                )

            with col2:
                total_savings = analysis['savings_potential'].get('total_annual_savings', 0)
                st.metric(
                    "Savings Potential", 
                    format_currency(total_savings),
                    f"{analysis['savings_potential'].get('savings_percentage', 0):.1f}%"
                )

            with col3:
                confidence = analysis.get('extraction_confidence', 0) * 100
                st.metric(
                    "Data Confidence",
                    f"{confidence:.0f}%",
                    help="How confident we are in the extracted contract terms"
                )

            with col4:
                improvement_areas = len([r for r in analysis.get('recommendations', []) if r.get('priority') == 'high'])
                st.metric(
                    "High Priority Issues",
                    str(improvement_areas),
                    help="Number of high-priority negotiation opportunities"
                )

            st.markdown("---")

            # Detailed analysis
            if analysis['benchmark_comparison']:
                st.subheader(" Benchmark Comparison")

                # Create comparison table
                comparison_data = []
                for term, data in analysis['benchmark_comparison'].items():
                    term_name = term.replace('_', ' ').title()
                    current = data.get('current', 'N/A')
                    best = data.get('best_in_class', 'N/A')
                    performance = data.get('performance_tier', 'Unknown').title()

                    # Format values based on term type
                    if 'discount' in term or 'surcharge' in term and 'pct' in term:
                        current = f"{current}%" if current != 'N/A' else 'N/A'
                        best = f"{best}%" if best != 'N/A' else 'N/A'
                    elif 'surcharge' in term and isinstance(current, (int, float)):
                        current = f"${current:.2f}" if current != 'N/A' else 'N/A'
                        best = f"${best:.2f}" if best != 'N/A' else 'N/A'

                    comparison_data.append([term_name, str(current), str(best), performance])

                comparison_df = pd.DataFrame(
                    comparison_data, 
                    columns=['Contract Term', 'Your Current', 'Industry Best', 'Performance']
                )

                st.dataframe(comparison_df, hide_index=True, width="stretch")

            # Key findings
            st.subheader(" Key Findings")

            findings_col1, findings_col2 = st.columns(2)

            with findings_col1:
                st.write("**Strengths:**")
                strengths = []
                for term, data in analysis['benchmark_comparison'].items():
                    if data.get('performance_tier') in ['excellent', 'good']:
                        term_name = term.replace('_', ' ').title()
                        strengths.append(f" {term_name} - {data['performance_tier'].title()}")

                if strengths:
                    for strength in strengths:
                        st.write(strength)
                else:
                    st.write("No significant strengths identified")

            with findings_col2:
                st.write("**Areas for Improvement:**")
                improvements = []
                for term, data in analysis['benchmark_comparison'].items():
                    if data.get('performance_tier') in ['poor', 'fair']:
                        term_name = term.replace('_', ' ').title()
                        improvements.append(f" {term_name} - {data['performance_tier'].title()}")

                if improvements:
                    for improvement in improvements:
                        st.write(improvement)
                else:
                    st.write("No major issues identified")

    with tab3:
        st.subheader(" Negotiation Strategy")

        if 'contract_analysis' not in st.session_state:
            st.info(" Please upload and analyze a contract first using the 'Upload Contract' tab.")
        else:
            analysis = st.session_state.contract_analysis

            # Action buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📄 Generate Strategy PDF", type="primary"):
                    try:
                        with st.spinner("Generating comprehensive negotiation strategy..."):
                            from contract_strategy_generator import get_strategy_generator

                            strategy_gen = get_strategy_generator()
                            pdf_data = strategy_gen.generate_negotiation_strategy(
                                analysis,
                                user.get('name', 'User'),
                                user.get('company_name', 'Your Company')
                            )

                            st.download_button(
                                label="📥 Download Strategy PDF",
                                data=pdf_data,
                                file_name=f"Contract_Strategy_{analysis['contract_info']['name']}.pdf",
                                mime="application/pdf"
                            )
                            st.success(" Strategy PDF generated successfully!")

                    except Exception as e:
                        st.error(f" Error generating PDF: Please try again.")

            with col2:
                if st.button(" Email Strategy", type="secondary"):
                    st.info(" Email functionality will be available in the next update.")

            with col3:
                if st.button(" Copy Key Points", type="secondary"):
                    st.info(" Copy functionality will be available in the next update.")

            st.markdown("---")

            # Display recommendations
            st.subheader(" Negotiation Recommendations")

            recommendations = analysis.get('recommendations', [])

            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec.get('priority', 'medium'), '🔵')

                    with st.expander(f"{priority_emoji} {rec.get('category', 'Recommendation')} ({rec.get('priority', 'medium').title()} Priority)"):
                        col_a, col_b = st.columns(2)

                        with col_a:
                            st.write(f"**Current:** {rec.get('current', 'N/A')}")
                            st.write(f"**Target:** {rec.get('target', 'N/A')}")

                        with col_b:
                            st.write(f"**Estimated Impact:** {rec.get('estimated_savings', 'TBD')}")

                        st.write(f"**Negotiation Talking Point:**")
                        st.info(rec.get('talking_point', 'Negotiate for better terms'))

                        st.write(f"**Business Justification:**")
                        st.write(rec.get('justification', 'Cost optimization opportunity'))
            else:
                st.info("No specific recommendations available. Your contract terms appear to be competitive.")

    with tab4:
        st.subheader(" Contract History & Tracking")

        # Placeholder for contract history
        st.info(" Contract history tracking will display your previous contract analyses and performance over time.")

        # Sample timeline chart
        st.write("**Contract Performance Timeline** (Sample)")

        try:
            from contract_visualization import get_visualization_manager
            viz_manager = get_visualization_manager()

            timeline_chart = viz_manager.create_contract_timeline_comparison()
            st.plotly_chart(timeline_chart, width="stretch")

        except Exception:
            st.info(" Performance charts will be available after analyzing your first contract.")

def ai_freight_advisor_page():
    """OpenAudit AI Freight Advisor page with commonly asked questions"""
    from freight_ai_advisor import get_freight_ai_advisor

    # Initialize the advisor
    advisor = get_freight_ai_advisor()

    # Custom CSS for modern, responsive design
    st.markdown("""
    <style>
    .advisor-header {
        background: linear-gradient(135deg, #1F497D 0%, #7EA1C4 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .qa-item {
        background: white;
        border-left: 4px solid #7EA1C4;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="advisor-header">
        <h1>OpenAudit Q&A</h1>
        <p>Your smart freight auditing assistant for uncovering savings and optimizing shipping costs</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader(" Frequently Asked Freight Questions")
    st.markdown("*Click any question below for an instant expert answer:*")

    # Display pre-loaded Q&As in collapsible format
    for i, qa in enumerate(advisor.get_common_qas()):
        with st.expander(f"❓ {qa['question']}", expanded=False):
            st.markdown(f"**Answer:** {qa['answer']}")

            # Add relevant tips or follow-ups for key topics
            if "demand charges" in qa['question'].lower():
                st.info(" **Pro Tip:** Keep delivery confirmations and photos of correct addresses to dispute invalid demand charges.")
            elif "dimensional weight" in qa['question'].lower():
                st.info(" **Pro Tip:** Use the formula (L×W×H)÷139 to calculate dimensional weight before shipping.")
            elif "negotiate" in qa['question'].lower():
                st.info(" **Pro Tip:** Prepare shipping volume data and competitor quotes before negotiation calls.")

if __name__ == "__main__":
    main()
