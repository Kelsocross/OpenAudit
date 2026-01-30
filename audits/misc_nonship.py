"""
FedEx Miscellaneous Non-Shipment Charge Detection Module

This module detects and categorizes FedEx miscellaneous charges that are not
actual shipments (e.g., address corrections, duties/taxes, paper invoice fees).
"""

import re
from typing import Dict, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# Column mapping from FedEx export to normalized names
# Includes both raw FedEx column names AND normalized names from data_validator.py
COLS = {
    "OPCO": "opco",
    "Carrier": "opco",
    "Service Type": "service_type",
    "Service Description": "service_desc",
    "Pay Type": "pay_type",
    "Shipment Date (mm/dd/yyyy)": "ship_date",
    "Shipment Date": "ship_date",
    "Shipment Delivery Date (mm/dd/yyyy)": "deliv_date",
    "Delivery Date": "deliv_date",
    "Shipment Tracking Number": "tracking",
    "Tracking Number": "tracking",
    "Recipient Name": "ship_to",
    "Charge Description": "desc",
    "Shipment Miscellaneouse Charge USD": "amount",
    "Shipment Miscellaneous Charge USD": "amount",
    "Charge Amount USD": "amount",
    "Invoice Number": "invoice"
}

# Pay type to category mapping (lowercase keys for matching)
MISC_PAYTYPE_MAP = {
    "other4": "Misc Adjustment",
    "other3": "Misc Adjustment",
    "adjustment": "Manual Adjustment",
    "miscfee": "Misc Fee",
    "paperinvoice": "Paper Invoice Fee",
    "dutytax": "Duties/Taxes",
    "addresscorrection": "Address Correction"
}

# Threshold for classification (adjust for tuning)
MISC_SCORE_THRESHOLD = 3


def parse_date_safe(s) -> pd.Timestamp:
    """
    Safely parse date string to pd.Timestamp.
    Treats 1900-01-01 as NaT (null/missing).
    
    Args:
        s: Date string or value
        
    Returns:
        pd.Timestamp or pd.NaT
    """
    if pd.isna(s):
        return pd.NaT
    
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt) and dt.year == 1900:
            return pd.NaT
        return dt
    except:
        return pd.NaT


def is_valid_tracking(x) -> bool:
    """
    Check if tracking number matches standard FedEx patterns.
    
    Valid patterns:
    - 12 digits
    - 15 digits
    - 22 digits
    
    Args:
        x: Tracking number value
        
    Returns:
        True if valid tracking format, False otherwise
    """
    if pd.isna(x):
        return False
    
    s = str(x).strip()
    return bool(re.match(r'^(\d{12}|\d{15}|\d{22})$', s))


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize FedEx export data and detect miscellaneous non-shipment charges.
    
    Process:
    1. Rename columns using COLS mapping
    2. Normalize text fields (lowercase, strip)
    3. Parse and normalize dates
    4. Create feature flags for detection
    5. Calculate misc_score and classify
    6. Assign category based on description keywords or pay type
    
    Args:
        df: Raw FedEx export DataFrame
        
    Returns:
        Normalized DataFrame with classification columns added
    """
    # Create a copy - preserve ALL original columns
    dfn = df.copy()
    
    # Helper function to get column value by checking multiple possible names
    def get_column(df, possible_names, default=''):
        for name in possible_names:
            if name in df.columns:
                return df[name]
        return pd.Series([default] * len(df), index=df.index)
    
    # Create normalized columns WITHOUT renaming originals
    # This preserves "Tracking Number" and "Shipment Date" for display
    dfn['opco'] = get_column(dfn, ['Carrier', 'OPCO']).fillna('').astype(str).str.strip().str.lower()
    dfn['service_type'] = get_column(dfn, ['Service Type']).fillna('').astype(str).str.strip().str.lower()
    dfn['service_desc'] = get_column(dfn, ['Service Description']).fillna('').astype(str).str.strip().str.lower()
    dfn['pay_type'] = get_column(dfn, ['Pay Type']).fillna('').astype(str).str.strip().str.lower()
    dfn['ship_to'] = get_column(dfn, ['Recipient Name']).fillna('').astype(str).str.strip()
    dfn['desc'] = get_column(dfn, ['Charge Description']).fillna('').astype(str).str.strip().str.lower()
    
    # Get tracking and date from original columns (preserve original values)
    tracking_col = get_column(dfn, ['Tracking Number', 'Shipment Tracking Number'])
    date_col = get_column(dfn, ['Shipment Date', 'Shipment Date (mm/dd/yyyy)'])
    deliv_col = get_column(dfn, ['Delivery Date', 'Shipment Delivery Date (mm/dd/yyyy)'])
    
    dfn['tracking'] = tracking_col.fillna('').astype(str).str.strip()
    dfn['ship_date'] = date_col
    dfn['deliv_date'] = deliv_col
    
    # Parse dates
    dfn['ship_date_norm'] = dfn['ship_date'].apply(parse_date_safe)
    dfn['deliv_date_norm'] = dfn['deliv_date'].apply(parse_date_safe)
    
    # Normalize amount - check multiple possible column names
    # Priority: Shipment Miscellaneouse Charge USD (with typo) > Shipment Miscellaneous Charge USD > Charge Amount USD
    amount_col = None
    for possible_col in ['Shipment Miscellaneouse Charge USD', 
                         'Shipment Miscellaneous Charge USD', 
                         'Charge Amount USD']:
        if possible_col in df.columns:
            amount_col = possible_col
            break
    
    if amount_col:
        dfn['amount_num'] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0.0)
    elif 'amount' in dfn.columns:
        dfn['amount_num'] = pd.to_numeric(dfn['amount'], errors='coerce').fillna(0.0)
    else:
        dfn['amount_num'] = 0.0
    
    # Feature flags for detection
    dfn['is_service_blank'] = (dfn['service_type'] == '') & (dfn['service_desc'] == '')
    dfn['is_deliv_missing'] = dfn['deliv_date_norm'].isna()
    dfn['is_paytype_misc'] = dfn['pay_type'].apply(
        lambda x: str(x).strip() == '' or 'other4' in str(x).lower()
    )
    dfn['is_shipto_missing'] = (dfn['ship_to'] == '') | dfn['ship_to'].isna()
    dfn['is_nonstandard_tracking'] = ~dfn['tracking'].apply(is_valid_tracking)
    
    # Calculate misc score (sum of flags) - 5 factors, threshold of 3
    feature_cols = ['is_service_blank', 'is_deliv_missing', 'is_paytype_misc',
                    'is_shipto_missing', 'is_nonstandard_tracking']
    dfn['misc_score'] = dfn[feature_cols].sum(axis=1)
    
    # Classification
    dfn['is_misc_non_shipment'] = dfn['misc_score'] >= MISC_SCORE_THRESHOLD
    
    # Calculate confidence (score / number of features)
    num_features = len(feature_cols)
    dfn['misc_confidence'] = (dfn['misc_score'] / num_features).round(2)
    
    # Assign category based on description keywords or pay type
    def assign_category(row):
        desc = str(row.get('desc', '')).lower()
        
        # Check description keywords first
        if 'address correction' in desc:
            return 'Address Correction'
        
        if any(keyword in desc for keyword in ['dutie', 'vat', 'tax']):
            return 'Duties/Taxes'
        
        if 'paper' in desc and 'invoice' in desc:
            return 'Paper Invoice Fee'
        
        # Fall back to pay type mapping
        pay_type = str(row.get('pay_type', '')).lower()
        for key, category in MISC_PAYTYPE_MAP.items():
            if key in pay_type:
                return category
        
        return 'Misc Adjustment'
    
    dfn['misc_category'] = dfn.apply(assign_category, axis=1)
    
    return dfn


def build_misc_views(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Build summary views for miscellaneous charges analysis.
    
    Args:
        df: Normalized DataFrame from normalize()
        
    Returns:
        Tuple of:
        - queue: DataFrame of misc non-shipment entries
        - by_cat: Summary by category (category, count, total)
        - by_month: Summary by month (month, total)
        - summary: Dict with count_misc, sum_misc, avg_misc
    """
    # Exception queue - all misc non-shipment entries
    queue = df[df['is_misc_non_shipment']].copy()
    
    # By category rollup
    if not queue.empty:
        by_cat = queue.groupby('misc_category').agg(
            count=('misc_category', 'size'),
            total=('amount_num', 'sum')
        ).reset_index()
        by_cat = by_cat.sort_values('total', ascending=False)
    else:
        by_cat = pd.DataFrame(columns=['misc_category', 'count', 'total'])
    
    # By month rollup
    if not queue.empty and 'ship_date_norm' in queue.columns:
        queue_with_date = queue[queue['ship_date_norm'].notna()].copy()
        if not queue_with_date.empty:
            queue_with_date['month'] = queue_with_date['ship_date_norm'].dt.to_period('M').astype(str)
            by_month = queue_with_date.groupby('month').agg(
                total=('amount_num', 'sum')
            ).reset_index()
            by_month = by_month.sort_values('month')
        else:
            by_month = pd.DataFrame(columns=['month', 'total'])
    else:
        by_month = pd.DataFrame(columns=['month', 'total'])
    
    # Summary stats
    summary = {
        'count_misc': len(queue),
        'sum_misc': queue['amount_num'].sum() if not queue.empty else 0.0,
        'avg_misc': queue['amount_num'].mean() if not queue.empty else 0.0
    }
    
    return queue, by_cat, by_month, summary
