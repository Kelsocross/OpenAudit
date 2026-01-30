"""
Utility functions for OpenAudit application
"""
import pandas as pd
from typing import Dict, Any

def format_currency(amount: float) -> str:
    """
    Format a number as currency
    
    Args:
        amount: The amount to format
        
    Returns:
        Formatted currency string
    """
    try:
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def calculate_savings_summary(audit_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate summary statistics from audit results
    
    Args:
        audit_results: Dictionary containing audit findings
        
    Returns:
        Dictionary with summary statistics
    """
    summary = {
        'total_charges': 0,
        'total_savings': 0,
        'affected_shipments': 0,
        'total_shipments': 0,
        'savings_rate': 0
    }
    
    try:
        if 'summary' in audit_results:
            summary = audit_results['summary']
        elif 'findings' in audit_results:
            findings_df = pd.DataFrame(audit_results['findings'])
            if not findings_df.empty:
                summary['total_savings'] = findings_df['Refund Estimate'].sum()
                summary['affected_shipments'] = len(findings_df)
                
        # Calculate savings rate
        if summary['total_charges'] > 0:
            summary['savings_rate'] = (summary['total_savings'] / summary['total_charges']) * 100
            
    except Exception as e:
        print(f"Error calculating savings summary: {e}")
        
    return summary
