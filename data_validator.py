import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import re
from datetime import datetime

class DataValidator:
    """Validate and clean uploaded shipment data"""
    
    def __init__(self):
        self.required_columns = [
            'Carrier',
            'Service Type', 
            'Shipment Date',
            'Tracking Number',
            'Zone',
            'Total Charges'
        ]
        
        self.optional_columns = [
            'Base Rate',  # Moved from required - some files only have Net Charge Amount (which includes freight + misc - discounts)
            'Service Description',
            'Delivery Date',
            'Origin ZIP',
            'Destination ZIP',
            'Address Type',
            'Surcharges',
            'Actual Weight',
            'DIM Weight',
            'Length',
            'Width',
            'Height',
            'Declared Value',
            'Fuel Surcharge',
            'Residential Surcharge',
            'Address Correction',
            'Declared Value Charge',
            'Destination Address'
        ]
        
        self.column_mappings = {
            # Common variations of column names
            'carrier': 'Carrier',
            'service_type': 'Service Type',
            'service': 'Service Type',
            'service_description': 'Service Description',
            'shipment_date': 'Shipment Date',
            'ship_date': 'Shipment Date',
            'shipment_date__mm_dd_yyyy': 'Shipment Date',  # Handle "Shipment Date (mm/dd/yyyy)"
            'tracking_number': 'Tracking Number',
            'tracking_num': 'Tracking Number',
            'tracking': 'Tracking Number',
            'shipment_tracking_number': 'Tracking Number',  # Handle "Shipment Tracking Number"
            'zone': 'Zone',
            'shipping_zone': 'Zone',
            'pricing_zone': 'Zone',  # Handle "Pricing Zone"
            'total_charges': 'Total Charges',
            'total_charge': 'Total Charges',
            'amount': 'Total Charges',
            'net_charge_amount_usd': 'Total Charges',  # Map to Total Charges - this is the actual amount paid
            'base_rate': 'Base Rate',
            'base_charge': 'Base Rate',
            'shipment_freight_charge_amount_usd': 'Base Rate',  # Map to Base Rate - this is freight charges only
            'delivery_date': 'Delivery Date',
            'delivered_date': 'Delivery Date',
            'shipment_delivery_date__mm_dd_yyyy': 'Delivery Date',  # Handle "Shipment Delivery Date (mm/dd/yyyy)"
            'origin_zip': 'Origin ZIP',
            'origin_zipcode': 'Origin ZIP',
            'destination_zip': 'Destination ZIP',
            'dest_zip': 'Destination ZIP',
            'destination_zipcode': 'Destination ZIP',
            'address_type': 'Address Type',
            'surcharges': 'Surcharges',
            'surcharge': 'Surcharges',
            'actual_weight': 'Actual Weight',
            'weight': 'Actual Weight',
            'dim_weight': 'DIM Weight',
            'dimensional_weight': 'DIM Weight',
            'length': 'Length',
            'width': 'Width',
            'height': 'Height'
        }
    
    def load_file(self, uploaded_file) -> Optional[pd.DataFrame]:
        """Load CSV or Excel file"""
        try:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(uploaded_file)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            return df
            
        except Exception as e:
            raise Exception(f"Error loading file: {str(e)}")
    
    def merge_shipment_and_surcharge_files(self, shipment_file, surcharge_file) -> tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Merge shipment details with surcharge data by tracking number
        
        Uses the robust merge_utils.merge_shipments_and_surcharges() function which:
        - Handles Invoice Number as a secondary join key for better matching
        - Supports Master Tracking Number fallback
        - Handles "Shipment Miscellaneous ChargeUSD" column name variations
        - Avoids pandas Series ambiguity errors with explicit scalar checks
        
        Returns:
            tuple: (merged_dataframe, error_message)
                   - If successful: (dataframe, None)
                   - If failed: (None, error_message)
        """
        try:
            from merge_utils import merge_shipments_and_surcharges
            
            # Load both files
            shipment_df = self.load_file(shipment_file)
            surcharge_df = self.load_file(surcharge_file)
            
            if shipment_df is None:
                return None, "Failed to load shipment details file"
            if surcharge_df is None:
                return None, "Failed to load surcharge report file"
            
            # Use the new robust merge function
            merged_df = merge_shipments_and_surcharges(shipment_df, surcharge_df)
            
            # Normalize column names after merge to ensure consistency
            merged_df = self._normalize_column_names(merged_df)
            
            return merged_df, None
            
        except Exception as e:
            return None, f"Error during file merge: {str(e)}"
    
    def validate_columns(self, df: pd.DataFrame) -> Dict[str, Union[bool, List[str]]]:
        """Validate that required columns are present"""
        # Normalize column names
        normalized_df = self._normalize_column_names(df)
        
        # Check for required columns
        missing_columns = []
        for required_col in self.required_columns:
            if required_col not in normalized_df.columns:
                missing_columns.append(required_col)
        
        return {
            'is_valid': len(missing_columns) == 0,
            'missing_columns': missing_columns,
            'found_columns': list(normalized_df.columns)
        }
    
    def clean_data(self, df: pd.DataFrame, warehouse_addresses: list = None) -> pd.DataFrame:
        """Clean and standardize the data
        
        Args:
            df: DataFrame with shipment data
            warehouse_addresses: Optional list of warehouse addresses for freight direction classification
        """
        # Normalize column names
        df = self._normalize_column_names(df)
        
        # Clean data types
        df = self._clean_data_types(df)
        
        # Clean and validate specific columns
        df = self._clean_carriers(df)
        df = self._clean_service_types(df)
        df = self._clean_dates(df)
        df = self._clean_tracking_numbers(df)
        df = self._clean_numeric_columns(df)
        df = self._clean_zip_codes(df)
        
        # Add freight direction classification (Inbound vs Outbound)
        df = self._classify_freight_direction(df, warehouse_addresses)
        
        return df
    
    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names using mapping"""
        df = df.copy()
        
        # Create mapping for current columns
        column_mapping = {}
        for col in df.columns:
            # Clean column name (lowercase, remove spaces/special chars)
            clean_col = re.sub(r'[^a-zA-Z0-9]', '_', col.lower()).strip('_')
            
            # Check if it matches any of our mappings
            if clean_col in self.column_mappings:
                column_mapping[col] = self.column_mappings[clean_col]
            elif col in self.required_columns + self.optional_columns:
                column_mapping[col] = col
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _clean_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert data types"""
        df = df.copy()
        
        # Numeric columns
        numeric_columns = [
            'Zone', 'Total Charges', 'Base Rate', 'Surcharges', 
            'Actual Weight', 'DIM Weight', 'Length', 'Width', 'Height',
            'Declared Value', 'Fuel Surcharge', 'Residential Surcharge',
            'Address Correction', 'Declared Value Charge'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Date columns
        date_columns = ['Shipment Date', 'Delivery Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def _clean_carriers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize carrier names"""
        if 'Carrier' not in df.columns:
            return df
        
        df = df.copy()
        
        # Standardize carrier names
        carrier_mapping = {
            'fedex': 'FEDEX',
            'fed ex': 'FEDEX',
            'federal express': 'FEDEX',
            'ups': 'UPS',
            'united parcel service': 'UPS',
            'usps': 'USPS',
            'us postal service': 'USPS',
            'dhl': 'DHL'
        }
        
        if 'Carrier' in df.columns:
            df['Carrier'] = df['Carrier'].astype(str).str.lower().str.strip()
            df['Carrier'] = df['Carrier'].replace(carrier_mapping).fillna(df['Carrier'].str.upper())
        
        return df
    
    def _clean_service_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize service type names"""
        if 'Service Type' not in df.columns:
            return df
        
        df = df.copy()
        
        # Clean service type names
        if 'Service Type' in df.columns:
            df['Service Type'] = df['Service Type'].astype(str).str.upper().str.strip()
        
        # Common service type mappings
        service_mapping = {
            'GROUND': 'GROUND',
            'FEDEX GROUND': 'GROUND',
            'UPS GROUND': 'GROUND',
            'EXPRESS SAVER': 'EXPRESS_SAVER',
            '3 DAY': '3_DAY_SELECT',
            '2 DAY': '2_DAY',
            'NEXT DAY': 'NEXT_DAY_AIR',
            'OVERNIGHT': 'STANDARD_OVERNIGHT',
            'PRIORITY OVERNIGHT': 'PRIORITY_OVERNIGHT'
        }
        
        df['Service Type'] = df['Service Type'].replace(service_mapping).fillna(df['Service Type'])
        
        return df
    
    def _clean_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate date columns"""
        date_columns = ['Shipment Date', 'Delivery Date']
        
        for col in date_columns:
            if col in df.columns:
                # Try multiple date format parsing approaches
                # First, try pandas' automatic inference
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # If still have null values, try specific common formats
                null_mask = df[col].isnull()
                if null_mask.sum() > 0:
                    # Try YYYY-MM-DD format specifically (like 2025-07-24)
                    df.loc[null_mask, col] = pd.to_datetime(df.loc[null_mask, col], 
                                                          format='%Y-%m-%d', errors='coerce')
                    
                    # Update null mask after YYYY-MM-DD attempt
                    null_mask = df[col].isnull()
                    if null_mask.sum() > 0:
                        # Try MM/DD/YYYY format
                        df.loc[null_mask, col] = pd.to_datetime(df.loc[null_mask, col], 
                                                              format='%m/%d/%Y', errors='coerce')
                        
                        # Update null mask after MM/DD/YYYY attempt
                        null_mask = df[col].isnull()
                        if null_mask.sum() > 0:
                            # Try DD/MM/YYYY format
                            df.loc[null_mask, col] = pd.to_datetime(df.loc[null_mask, col], 
                                                                  format='%d/%m/%Y', errors='coerce')
        
        # Clean placeholder delivery dates
        df = self._clean_placeholder_delivery_dates(df)
        
        return df
    
    def _clean_placeholder_delivery_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect and clean placeholder delivery dates like 1900-01-01, 1899-12-31
        These are fake placeholders indicating missing delivery information
        """
        if 'Delivery Date' not in df.columns:
            return df
        
        df = df.copy()
        
        # Define placeholder dates to detect (year < 2000 indicates placeholder)
        # Common placeholders: 1900-01-01, 1899-12-31, 01/01/1900, etc.
        placeholder_mask = pd.notna(df['Delivery Date']) & (df['Delivery Date'].dt.year < 2000)
        
        # Replace placeholder dates with NaT (Not a Time - pandas missing date value)
        if placeholder_mask.sum() > 0:
            df.loc[placeholder_mask, 'Delivery Date'] = pd.NaT
        
        # Create Delivery Status column
        df = self._create_delivery_status_column(df)
        
        return df
    
    def _create_delivery_status_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create Delivery Status column based on delivery date validity"""
        if 'Delivery Date' not in df.columns:
            return df
        
        df = df.copy()
        
        # Create Delivery Status column
        # If delivery date is missing or invalid, mark as "Missing Delivery Date", otherwise "Ready"
        df['Delivery Status'] = df['Delivery Date'].apply(
            lambda x: 'Missing Delivery Date' if pd.isna(x) else 'Ready'
        )
        
        return df
    
    def _clean_tracking_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean tracking numbers"""
        if 'Tracking Number' not in df.columns:
            return df
        
        df = df.copy()
        
        # Clean tracking numbers - remove spaces and special characters
        if 'Tracking Number' in df.columns:
            df['Tracking Number'] = df['Tracking Number'].astype(str).str.replace(r'[^A-Za-z0-9]', '', regex=True)
        
        return df
    
    def _clean_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean numeric columns - remove currency symbols, etc."""
        numeric_columns = [
            'Total Charges', 'Base Rate', 'Surcharges', 
            'Fuel Surcharge', 'Residential Surcharge',
            'Address Correction', 'Declared Value Charge', 'Declared Value'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                # Remove currency symbols and convert to float
                df[col] = df[col].astype(str).str.replace(r'[$,]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
        
        return df
    
    def _clean_zip_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean ZIP code columns"""
        zip_columns = ['Origin ZIP', 'Destination ZIP']
        
        for col in zip_columns:
            if col in df.columns:
                # Convert to string and extract first 5 digits
                df[col] = df[col].astype(str).str.extract(r'(\d{5})')[0]
        
        return df
    
    def _classify_freight_direction(self, df: pd.DataFrame, warehouse_addresses: list = None) -> pd.DataFrame:
        """
        Classify freight as Inbound or Outbound based on shipper address.
        
        Outbound: Shipments from configured warehouse addresses
        Inbound: All other shipments
        
        Args:
            df: DataFrame with shipment data
            warehouse_addresses: List of warehouse address strings to match for Outbound classification
        """
        df = df.copy()
        
        # Build outbound patterns from configured warehouse addresses
        outbound_patterns = []
        
        if warehouse_addresses:
            for addr in warehouse_addresses:
                # Escape special regex characters and create flexible pattern
                addr_clean = addr.strip().upper()
                # Create pattern that matches the address with flexible spacing
                escaped = re.escape(addr_clean)
                # Allow flexible whitespace
                pattern = escaped.replace(r'\ ', r'\s+')
                outbound_patterns.append(pattern)
        
        # If no addresses configured, freight direction won't be classified
        if not outbound_patterns:
            df['Freight Direction'] = 'Unknown'
            return df
        
        # Get shipper address fields (similar to audit_engine logic)
        def get_shipper_address(row):
            """Get full shipper address from all available fields"""
            address_parts = []
            
            # Check various shipper address field names
            for field in ['Shipper Address', 'Origin Address', 'Ship From Address',
                         'Shipper Company Name', 'Shipper Name', 'Shipper City',
                         'Shipper State', 'Origin City', 'Origin State']:
                if field in df.columns and pd.notna(row.get(field)):
                    address_parts.append(str(row.get(field)))
            
            return ' '.join(address_parts).upper()
        
        # Apply classification
        def classify_direction(row):
            shipper_address = get_shipper_address(row)
            
            # Check if address matches any outbound pattern
            for pattern in outbound_patterns:
                if re.search(pattern, shipper_address):
                    return 'Outbound'
            
            return 'Inbound'
        
        # Add Freight Direction column
        df['Freight Direction'] = df.apply(classify_direction, axis=1)
        
        return df
    
    def get_data_quality_report(self, df: pd.DataFrame) -> Dict[str, Union[int, Dict]]:
        """Generate data quality report"""
        report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_data': {},
            'data_types': {},
            'value_ranges': {}
        }
        
        # Missing data analysis
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            report['missing_data'][col] = {
                'missing_count': int(missing_count),
                'missing_percentage': float(missing_count / len(df) * 100)
            }
        
        # Data type analysis
        for col in df.columns:
            report['data_types'][col] = str(df[col].dtype)
        
        # Value ranges for numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if not df[col].empty:
                report['value_ranges'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'median': float(df[col].median())
                }
        
        return report
