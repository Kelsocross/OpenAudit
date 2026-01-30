"""
Unit tests for FedEx miscellaneous non-shipment charge detection
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from audits.misc_nonship import normalize, build_misc_views, is_valid_tracking, parse_date_safe

# Try to import pytest, but allow running without it
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    print("Warning: pytest not installed, running tests directly")


def test_parse_date_safe():
    """Test date parsing with 1900-01-01 handling"""
    # Normal date
    result = parse_date_safe("2025-09-16")
    assert pd.notna(result)
    assert result.year == 2025
    
    # 1900 date should become NaT
    result = parse_date_safe("1900-01-01")
    assert pd.isna(result)
    
    # Invalid date
    result = parse_date_safe("invalid")
    assert pd.isna(result)


def test_is_valid_tracking():
    """Test tracking number validation"""
    assert is_valid_tracking("123456789012") is True  # 12 digits
    assert is_valid_tracking("123456789012345") is True  # 15 digits
    assert is_valid_tracking("1234567890123456789012") is True  # 22 digits
    
    assert is_valid_tracking("5416334") is False  # Too short
    assert is_valid_tracking("ABC123456789") is False  # Contains letters
    assert is_valid_tracking("") is False  # Empty
    assert is_valid_tracking(None) is False  # None


def test_misc_non_shipment_detection():
    """Test detection of miscellaneous non-shipment charges"""
    # Create test data with the exact case from spec
    data = {
        "OPCO": ["Express"],
        "Service Type": [""],
        "Service Description": [""],
        "Pay Type": ["Other4"],
        "Shipment Date (mm/dd/yyyy)": ["2025-09-16"],
        "Shipment Delivery Date (mm/dd/yyyy)": ["1900-01-01"],
        "Shipment Tracking Number": ["5416334"],
        "Shipment Miscellaneouse Charge USD": [42.00]  # Updated column name
    }
    df = pd.DataFrame(data)
    
    # Normalize
    result = normalize(df)
    
    # Assertions
    assert len(result) == 1
    row = result.iloc[0]
    
    # Should be classified as misc non-shipment
    assert row['is_misc_non_shipment'] == True, "Should detect as misc non-shipment"
    
    # Category should be one of the valid categories
    valid_categories = ["Misc Adjustment", "Address Correction", "Paper Invoice Fee", "Duties/Taxes"]
    assert row['misc_category'] in valid_categories, f"Category should be in {valid_categories}"
    
    # Confidence should be reasonable
    assert 0.4 <= row['misc_confidence'] <= 1.0, "Confidence should be between 0.4 and 1.0"
    
    # Amount should be parsed correctly
    assert row['amount_num'] == 42.00


def test_valid_shipment_not_flagged():
    """Test that valid shipments are NOT flagged as misc"""
    # Create a valid shipment
    data = {
        "OPCO": ["Ground"],
        "Service Type": ["GROUND"],
        "Service Description": ["FedEx Ground"],
        "Pay Type": ["Package"],
        "Shipment Date (mm/dd/yyyy)": ["2025-09-16"],
        "Shipment Delivery Date (mm/dd/yyyy)": ["2025-09-18"],
        "Shipment Tracking Number": ["123456789012"],  # Valid 12-digit
        "Shipment Miscellaneouse Charge USD": [15.50],  # Updated column name
        "Recipient Name": ["ACME Corp"]
    }
    df = pd.DataFrame(data)
    
    # Normalize
    result = normalize(df)
    
    # Assertions
    assert len(result) == 1
    row = result.iloc[0]
    
    # Should NOT be classified as misc non-shipment
    assert row['is_misc_non_shipment'] == False, "Valid shipment should not be flagged as misc"
    
    # Score should be low
    assert row['misc_score'] < 3, "Misc score should be below threshold"


def test_duties_tax_detection():
    """Test detection and categorization of duties/taxes"""
    data = {
        "OPCO": ["Express"],
        "Service Type": [""],
        "Service Description": [""],
        "Pay Type": ["Other4"],
        "Shipment Date (mm/dd/yyyy)": ["2025-09-16"],
        "Shipment Delivery Date (mm/dd/yyyy)": ["1900-01-01"],
        "Shipment Tracking Number": ["ABC123"],
        "Shipment Miscellaneouse Charge USD": [25.00],  # Updated column name
        "Charge Description": ["Import VAT adjustment"]
    }
    df = pd.DataFrame(data)
    
    # Normalize
    result = normalize(df)
    
    # Should categorize as Duties/Taxes based on description
    assert result.iloc[0]['misc_category'] == "Duties/Taxes"


def test_build_misc_views():
    """Test summary views generation"""
    # Create mixed data
    data = {
        "OPCO": ["Express", "Ground", "Express"],
        "Service Type": ["", "GROUND", ""],
        "Service Description": ["", "FedEx Ground", ""],
        "Pay Type": ["Other4", "Package", "Adjustment"],
        "Shipment Date (mm/dd/yyyy)": ["2025-09-16", "2025-09-16", "2025-10-15"],
        "Shipment Delivery Date (mm/dd/yyyy)": ["1900-01-01", "2025-09-18", "1900-01-01"],
        "Shipment Tracking Number": ["5416334", "123456789012", "ABC"],
        "Shipment Miscellaneouse Charge USD": [42.00, 15.50, 30.00]  # Updated column name
    }
    df = pd.DataFrame(data)
    
    # Normalize and build views
    df_norm = normalize(df)
    queue, by_cat, by_month, summary = build_misc_views(df_norm)
    
    # Check queue (should have 2 misc charges)
    assert len(queue) >= 2, "Should have at least 2 misc charges"
    
    # Check summary
    assert summary['count_misc'] >= 2
    assert summary['sum_misc'] > 0
    assert summary['avg_misc'] > 0
    
    # Check by_cat
    assert not by_cat.empty
    assert 'misc_category' in by_cat.columns
    assert 'total' in by_cat.columns
    
    # Check by_month
    if not by_month.empty:
        assert 'month' in by_month.columns
        assert 'total' in by_month.columns


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__, "-v"])
    else:
        # Run tests manually
        print("Running tests manually...")
        try:
            test_parse_date_safe()
            print("✓ test_parse_date_safe")
            
            test_is_valid_tracking()
            print("✓ test_is_valid_tracking")
            
            test_misc_non_shipment_detection()
            print("✓ test_misc_non_shipment_detection")
            
            test_valid_shipment_not_flagged()
            print("✓ test_valid_shipment_not_flagged")
            
            test_duties_tax_detection()
            print("✓ test_duties_tax_detection")
            
            test_build_misc_views()
            print("✓ test_build_misc_views")
            
            print("\nAll tests passed! ✅")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
