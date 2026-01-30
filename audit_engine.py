import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import math
from typing import Dict, List, Tuple, Any
from audits.misc_nonship import normalize, build_misc_views

class FreightAuditEngine:
    """Comprehensive freight audit engine for detecting shipping overcharges and errors"""

    def __init__(self, residential_patterns=None):
        # FedEx service codes that have money-back guarantees
        # Only these services will be checked for late deliveries
        self.fedex_guaranteed_service_codes = {
            'PO',  # FedEx Priority Overnight
            'FO',  # FedEx First Overnight
            'SO',  # FedEx Standard Overnight
            'ES',  # FedEx 2Day
            'OA',  # FedEx International Priority
            'LO',  # FedEx Intl Priority Express
            'IP'   # International Priority (duplicate of OA)
        }
        
        # Standard delivery times by service description (business days)
        # Only for guaranteed services
        self.service_delivery_times = {
            # FedEx GUARANTEED services only
            'FEDEX_2DAY': 2,
            'FEDEX_STANDARD_OVERNIGHT': 1,
            'FEDEX_PRIORITY_OVERNIGHT': 1,
            'FEDEX_INTERNATIONAL_PRIORITY': 1,
            'INTERNATIONAL_PRIORITY': 1,
            'FEDEX_FIRST_OVERNIGHT': 1,
            'FEDEX_INTL_PRIORITY_EXPRESS': 1,
            
            # UPS services (if needed later)
            'UPS_NEXT_DAY_AIR': 1,
            'UPS_NEXT_DAY_AIR_SAVER': 1,
            'UPS_2ND_DAY_AIR': 2,
        }

        # DIM divisors by carrier
        self.dim_divisors = {'FEDEX': 139, 'UPS': 139}

        # Common surcharge thresholds
        self.high_surcharge_threshold = 0.25  # 25% of base rate

        # ZIP code to zone mapping (simplified - in production, use full database)
        self.zone_mapping = self._initialize_zone_mapping()
        
        # Residential surcharge detection patterns (configurable)
        self.residential_patterns = residential_patterns if residential_patterns else [
            "residential surcharge",
            "residential delivery",
            "delivery area surcharge - residential",
            "das - residential",
            "das residential",
            "home delivery",
            "address correction - residential",
            "residential area surcharge",
            "residential area"
        ]
        
        # Business indicators - generic keywords + specific retail store names + approved shippers
        # These indicate business addresses that should NOT be flagged as residential
        # Using word-boundary matching to avoid false positives (e.g., "MAC" shouldn't match "MacArthur")
        self.business_indicators = [
            # Generic business keywords (word-boundary safe)
            'LLC', 'INC', 'CORP', 'COMPANY', 'BUSINESS', 'OFFICE', 
            'WAREHOUSE', 'STORE', 'SHOP', 'CENTER', 'DISTRIBUTION',
            
            # Specific retail stores and locations
            'SEPHORA', 'ULTA', 'NORDSTROM', 'BLOOMINGDALE', 'MACY',
            'KOHLS', 'TARGET', 'MAC COSMETICS', 
            'DIOR', 'TOWER 28', 'L\'OREAL', 'LOREAL',
            'MALL OF AMERICA', 'VALLEY FAIR', 'HOUSTON GALLERIA', 
            'SANTA ANITA', 'NORTH PARK', 'CHESTNUT HILL', 'CERRITOS',
            'CORAL GABLES', 'DADELAND', 'AVENTURA',
            'MILLSTREAM', 'BELLEVUE', 'BERKELEY',
            'WES HARNESS',
            
            # Approved shipper names (customer-specific)
            'HUNTER PHILLIPS', 'WILLIAM WESPY', 'FAB SHIPPING', 'JESSE MENG',
            'AMYCE STOD DARD', 'MARK LOVELESS', 'MKT ALLIANCE',
            'MARKETING ALLIANCE GROUP', 'MARKETING ALLIANCE',
            
            # Approved shipper companies (customer-specific)  
            'CREATIVE PLASTICS', 'CREATIVE PLASTIC', 'H & B',
            
            # Approved shipper addresses (customer-specific)
            '251 GILLUM', 'GILLUM DR', 'GILLUM DRIVE', 'GILLU I DRIVE',
            '1409 CORONET', 'CORONET DR', 'CORONET DRIVE'
        ]
        
        # Short abbreviations that need exact word-boundary matching
        # These are separated to use stricter matching logic
        # Only include abbreviations unlikely to appear in street/address names
        self.business_abbrev = ['NRD', 'BLM']

    def _initialize_zone_mapping(self) -> Dict[str, Dict[str, int]]:
        return {
            'FEDEX': {'10001': 2, '90210': 8, '60601': 4, '30301': 3, '77001': 5, '98101': 7, '02101': 1, '33101': 6},
            'UPS':   {'10001': 2, '90210': 8, '60601': 4, '30301': 3, '77001': 5, '98101': 7, '02101': 1, '33101': 6}
        }
    
    def _has_business_indicators(self, dest_info: str) -> bool:
        """
        Check if destination info contains business indicators.
        Uses word-boundary matching for short abbreviations to avoid false positives.
        
        Args:
            dest_info: Destination information (company name, recipient, address, etc.) in UPPERCASE
        
        Returns:
            True if business indicators found, False otherwise
        """
        # Check longer business indicators (substring matching is safe)
        for indicator in self.business_indicators:
            if indicator in dest_info:
                return True
        
        # Check short abbreviations with word boundaries (avoid matching "MacArthur" as "MAC")
        for abbrev in self.business_abbrev:
            # Use regex word boundary \b to match complete words only
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            if re.search(pattern, dest_info):
                return True
        
        return False

    # -------------------------- helper getters (new) --------------------------

    def _get_first(self, row: pd.Series, candidates: List[str], default=None):
        for c in candidates:
            if c in row.index:
                v = row.get(c)
                if pd.notna(v) and str(v).strip() != "":
                    return v
        return default

    def _get_date(self, row: pd.Series, candidates: List[str]):
        raw = self._get_first(row, candidates)
        if raw is None: 
            return pd.NaT
        return pd.to_datetime(raw, errors='coerce')

    def _get_text(self, row: pd.Series, candidates: List[str]) -> str:
        v = self._get_first(row, candidates, "")
        return "" if v is None else str(v)

    def _get_zip(self, row: pd.Series) -> str:
        """
        Extract and normalize zip code to 5 digits.
        Handles both 5-digit (12345) and 9-digit (12345-6789 or 123456789) formats.
        """
        zip_candidates = [
            'Recipient Postal Code','Recipient Zip','Destination ZIP','Destination Zip',
            'Recipient PostalCode','Postal Code','Recipient Postal'
        ]
        z = self._get_text(row, zip_candidates)
        if not z:
            return ""
        
        # Remove any non-digit characters except dash
        z_clean = str(z).strip()
        
        # Handle 9-digit with dash (12345-6789)
        if '-' in z_clean:
            return z_clean.split('-')[0][:5]
        
        # Handle any format - just take first 5 digits
        digits_only = ''.join(c for c in z_clean if c.isdigit())
        return digits_only[:5]

    def _get_address(self, row: pd.Series) -> str:
        addr_candidates = [
            'Destination Address','Recipient Address','Recipient Original Address',
            'Ship To Address','Delivery Address'
        ]
        return self._get_text(row, addr_candidates)
    
    def _get_full_destination_info(self, row: pd.Series) -> str:
        """
        Get full destination information including company name, address, city, state
        for business indicator detection.
        """
        fields = [
            'Recipient Company Name', 'Recipient Name', 'Consignee',
            'Recipient Address', 'Destination Address', 'Recipient Original Address',
            'Recipient City', 'Recipient State/Province', 'Recipient Postal Code'
        ]
        parts = []
        for field in fields:
            if field in row.index and pd.notna(row[field]):
                val = str(row[field]).strip()
                if val:
                    parts.append(val)
        return ' '.join(parts)
    
    def _get_full_shipper_info(self, row: pd.Series) -> str:
        """
        Get full shipper information including company name, shipper name, and address
        for business indicator detection.
        """
        fields = [
            'Shipper Company Name', 'Shipper Name', 'Shipper',
            'Shipper Address', 'Origin Address', 'Ship From Address',
            'Shipper City', 'Shipper State', 'Shipper Postal Code'
        ]
        parts = []
        for field in fields:
            if field in row.index and pd.notna(row[field]):
                val = str(row[field]).strip()
                if val:
                    parts.append(val)
        return ' '.join(parts)

    def _normalize_tracking(self, x) -> str:
        if pd.isna(x): return ""
        return str(x).strip().replace(" ", "").replace("-", "").upper()

    def _get_float_value(self, row: pd.Series, col_candidates: List[str]) -> float:
        for col in col_candidates:
            if col in row.index and pd.notna(row[col]):
                try:
                    val_str = str(row[col]).strip().replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                    if val_str:
                        return float(val_str)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def _get_dimension(self, row: pd.Series, dimension_type: str) -> float:
        column_candidates = {
            'length': ['Dimmed Length','Length','Length (in)','Pkg Length','Package Length','Len'],
            'width':  ['Dimmed Width','Width','Width (in)','Pkg Width','Package Width','Wid'],
            'height': ['Dimmed Height','Height','Height (in)','Pkg Height','Package Height','Hgt']
        }
        for col_name in column_candidates.get(dimension_type.lower(), []):
            if col_name in row.index:
                value = row[col_name]
                try:
                    if pd.notna(value):
                        str_val = str(value).strip()
                        if str_val:
                            numeric_val = pd.to_numeric(str_val, errors='coerce')
                            # Ensure scalar value to avoid Series ambiguity
                            if pd.notna(numeric_val):
                                float_val = float(numeric_val)
                                if float_val > 0:
                                    return float_val
                except (ValueError, TypeError):
                    continue
        return 0.0

    def _is_return_service(self, service_description: str) -> bool:
        """
        Detect if a service description indicates a return shipment.
        
        Examples:
        - "Ground Return Manager" → True (RETURN keyword)
        - "RMGR" → True (Return Manager abbreviation)
        - "International Ground" → False (regular shipment)
        """
        if not service_description or pd.isna(service_description):
            return False
        
        service_upper = str(service_description).upper()
        return_keywords = ['RETURN', 'RMGR', 'RMA', 'REVERSE', 'RETURNMANAGER']
        return any(keyword in service_upper for keyword in return_keywords)

    def _is_original_plus_return_pair(self, duplicate_rows: pd.DataFrame) -> bool:
        """
        Check if duplicate tracking numbers are a legitimate Original + Return pair.
        
        Examples:
        - Tracking #466761794075:
          - Line 1: Service Type = "SG" (Standard Ground - original shipment)
          - Line 2: Service Type = "RMGR" (Return Manager - return shipment)
        
        - Tracking #466761794075:
          - Line 1: Service Description = "International Ground" (original shipment)
          - Line 2: Service Description = "Ground Return Manager" (return shipment)
        
        This is NOT a duplicate billing error - it's a legitimate return.
        Returns True if this is an Original + Return pair, False if it's a true duplicate.
        """
        if len(duplicate_rows) != 2:
            # More than 2 lines or only 1 line - not a simple Original + Return pair
            return False
        
        # Check Service Description/Type column (multiple possible column names)
        service_col = None
        for col in ['Service Description', 'Service Type', 'Service', 'Svc Desc', 'Service Code', 'Svc Type', 'Svc Code']:
            if col in duplicate_rows.columns:
                service_col = col
                break
        
        if service_col is None:
            # Can't determine service type - assume true duplicate
            return False
        
        # Get service descriptions
        services = duplicate_rows[service_col].tolist()
        service1 = services[0] if len(services) > 0 else ''
        service2 = services[1] if len(services) > 1 else ''
        
        # Check if one is return and one is regular
        is_return = [self._is_return_service(service1), self._is_return_service(service2)]
        
        # If exactly one is a return and one is not, this is a legitimate Original + Return pair
        if sum(is_return) == 1:
            return True
        
        return False

    # -------------------------- main API --------------------------

    def detect_residential_surcharges(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect shipments with residential delivery surcharges.
        EXCLUDES residential surcharges applied to business addresses - those stay in main audit
        as disputable surcharges.
        
        Returns a copy of df with two new columns:
        - has_residential_surcharge (bool)
        - residential_surcharge_sources (list of matching patterns)
        """
        df_copy = df.copy()
        df_copy['has_residential_surcharge'] = False
        df_copy['residential_surcharge_sources'] = [[] for _ in range(len(df_copy))]
        
        # Check multiple potential surcharge fields (expanded to cover common variations)
        surcharge_fields = [
            'Surcharge_Details', 'Service Description', 'Service Type',
            'Charge Description', 'Charge Type', 'Net Charge Title',
            'Accessorial Charge', 'Surcharge Description', 'Surcharge Type',
            'Residential Surcharge', 'Delivery Area Surcharge', 'Additional Charges'
        ]
        
        for idx, row in df_copy.iterrows():
            has_residential = False
            
            # Check all surcharge fields for residential patterns
            for field in surcharge_fields:
                if field in row.index and pd.notna(row[field]):
                    field_value = str(row[field]).lower()
                    
                    # Check if any residential pattern matches
                    for pattern in self.residential_patterns:
                        if pattern.lower() in field_value:
                            has_residential = True
                            break
                    if has_residential:
                        break
            
            # Simplified source - just indicate "Residential Delivery" once
            matched_sources = ["Residential Delivery"] if has_residential else []
            
            # If residential pattern matched, check if it's a business address
            if matched_sources:
                # Get full destination info (company name + recipient name + address + city + state)
                dest_info = self._get_full_destination_info(row).upper()
                
                # Get full shipper info (company name + shipper name + address)
                shipper_info = self._get_full_shipper_info(row).upper()
                
                # Check if EITHER destination OR shipper has business indicators
                # (uses word-boundary matching for safety)
                is_recipient_business = self._has_business_indicators(dest_info)
                is_shipper_business = self._has_business_indicators(shipper_info)
                
                # Mark as residential for review if EITHER recipient OR shipper is NOT a business
                # Only exclude from residential review if BOTH are businesses (B2B with residential surcharge = disputable)
                # This ensures we catch all shipments where at least one side is residential
                if not is_recipient_business or not is_shipper_business:
                    df_copy.at[idx, 'has_residential_surcharge'] = True
                    df_copy.at[idx, 'residential_surcharge_sources'] = matched_sources
        
        return df_copy
    
    def run_full_audit(self, df: pd.DataFrame) -> Dict[str, Any]:
        # First, detect residential surcharges
        df_with_residential = self.detect_residential_surcharges(df)
        
        # Split data into main audit (excluding residential) and residential review
        residential_mask = df_with_residential['has_residential_surcharge'] == True
        residential_df = df_with_residential[residential_mask].copy()
        main_audit_df = df_with_residential[~residential_mask].copy()
        
        # Run audits ONLY on non-residential shipments
        findings = []
        # Only run the 3 checks requested by user to avoid inflating savings
        findings.extend(self.check_late_deliveries(main_audit_df))
        findings.extend(self.check_duplicate_tracking(main_audit_df))
        findings.extend(self.check_disputable_surcharges(main_audit_df))
        
        # Detect miscellaneous non-shipment charges (automatic - no separate upload needed)
        # NOTE: Misc charges are detected but NOT added to findings or potential savings
        # They are stored separately for review purposes only
        misc_summary = {}
        misc_queue = pd.DataFrame()
        misc_by_category = pd.DataFrame()
        try:
            # Use a deep copy to ensure misc detection doesn't affect core audit logic
            df_misc_copy = df.copy(deep=True)
            # Normalize data and detect misc charges
            df_normalized = normalize(df_misc_copy)
            misc_queue, misc_by_category, misc_by_month, misc_summary = build_misc_views(df_normalized)
        except Exception as e:
            # If misc detection fails, continue with regular audit
            print(f"Warning: Misc charges detection failed: {e}")
        
        # Disabled checks (were inflating potential savings and savings rate):
        # findings.extend(self.check_dim_weight_overcharges(main_audit_df))
        # findings.extend(self.check_incorrect_zones(main_audit_df))
        # findings.extend(self.check_address_type_mismatches(main_audit_df))
        # findings.extend(self.check_high_surcharges(main_audit_df))  # User requested removal
        # findings.extend(self.check_unnecessary_surcharges(main_audit_df))
        
        findings_df = pd.DataFrame(findings)
        summary = self.calculate_summary(main_audit_df, findings_df)
        
        return {
            'findings': findings_df, 
            'summary': summary, 
            'audit_date': datetime.now().isoformat(),
            'residential_shipments': residential_df,
            'main_audit_data': main_audit_df,
            'total_shipments': len(df),
            'residential_count': len(residential_df),
            'main_audit_count': len(main_audit_df),
            'misc_charges_queue': misc_queue,
            'misc_charges_summary': misc_summary,
            'misc_charges_by_category': misc_by_category
        }

    def get_actionable_errors(self, findings_df: pd.DataFrame) -> pd.DataFrame:
        if findings_df.empty:
            return findings_df
        # Include only the 3 core audit checks (Misc charges are NOT included in potential savings)
        actionable_error_types = [
            'Late Delivery','Duplicate Tracking','Disputable Surcharge'
        ]
        actionable = findings_df[findings_df['Error Type'].isin(actionable_error_types)].copy()
        if not actionable.empty:
            actionable['Claim Status'] = 'Ready to Submit'
            actionable['Claim Priority'] = 'Medium'
            high_value_threshold = 50.0
            low_value_threshold = 10.0
            actionable.loc[actionable['Refund Estimate'] >= high_value_threshold,'Claim Priority'] = 'High'
            actionable.loc[actionable['Refund Estimate'] < low_value_threshold,'Claim Priority'] = 'Low'
        return actionable

    # -------------------------- checks (unchanged except below) --------------------------

    def check_late_deliveries(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        for _, row in df.iterrows():
            try:
                service_desc = str(row.get('Service Description', '')).upper().replace(' ', '_')
                service_type = str(row.get('Service Type', '')).upper().replace(' ', '_')
                carrier = str(row.get('Carrier', '')).upper()
                
                # For FedEx, check if service code is guaranteed before proceeding
                if 'FEDEX' in carrier:
                    # Service Type column often contains the service code (e.g., 'PO', 'ES', 'FO')
                    service_code = str(row.get('Service Type', '')).strip().upper()
                    if service_code not in self.fedex_guaranteed_service_codes:
                        continue  # Skip non-guaranteed FedEx services
                
                expected_days = self.service_delivery_times.get(service_desc) or \
                                self.service_delivery_times.get(f"{carrier}_{service_type}")
                if expected_days is None:
                    continue
                ship_date = pd.to_datetime(row.get('Shipment Date'), errors='coerce') or \
                            pd.to_datetime(row.get('Shipment Date (mm/dd/yyyy)'), errors='coerce')
                delivery_date = pd.to_datetime(row.get('Delivery Date'), errors='coerce') or \
                                pd.to_datetime(row.get('Shipment Delivery Date (mm/dd/yyyy)'), errors='coerce')
                if pd.isna(ship_date) or pd.isna(delivery_date):
                    continue
                expected_delivery = self._add_business_days(ship_date, expected_days)
                if delivery_date > expected_delivery:
                    days_late = (delivery_date - expected_delivery).days
                    total_charges = float(row.get('Total Charges', 0) or 0)
                    base_rate = float(row.get('Base Rate', 0) or 0)
                    billed_amount = float(row.get('Billed Amount', 0) or 0)
                    refund_estimate = total_charges or base_rate or billed_amount
                    findings.append({
                        'Error Type': 'Late Delivery',
                        'Tracking Number': row.get('Tracking Number', ''),
                        'Date': ship_date.strftime('%Y-%m-%d'),
                        'Carrier': row.get('Carrier', ''),
                        'Service Type': row.get('Service Type', ''),
                        'Dispute Reason': f'Package delivered {days_late} day(s) late',
                        'Refund Estimate': refund_estimate,
                        'Notes': f'Expected: {expected_delivery.strftime("%Y-%m-%d")}, Actual: {delivery_date.strftime("%Y-%m-%d")}'
                    })
            except Exception:
                continue
        return findings

    def check_dim_weight_overcharges(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        for _, row in df.iterrows():
            try:
                carrier = str(row.get('Carrier', '')).upper()
                divisor = self.dim_divisors['FEDEX'] if 'FEDEX' in carrier else \
                          self.dim_divisors['UPS']   if 'UPS' in carrier else None
                if divisor is None:
                    continue
                length = float(row.get('Length', 0) or 0)
                width = float(row.get('Width', 0) or 0)
                height = float(row.get('Height', 0) or 0)
                if length <= 0 or width <= 0 or height <= 0:
                    continue
                calculated_dim = (length * width * height) / divisor
                billed_dim = float(row.get('DIM Weight', 0) or 0)
                # Flexible weight column detection
                actual_wt_candidates = ['Actual Weight', 'Original Weight', 'Shipment Actual Weight', 'Package Weight', 'Weight']
                actual_weight = self._get_float_value(row, actual_wt_candidates)
                if abs(calculated_dim - billed_dim) > 0.5:
                    correct_billable_weight = max(calculated_dim, actual_weight)
                    billed_weight = max(billed_dim, actual_weight)
                    if correct_billable_weight < billed_weight:
                        total_charges = float(row.get('Total Charges', 0) or 0)
                        weight_diff_ratio = (billed_weight - correct_billable_weight) / billed_weight
                        refund_estimate = total_charges * weight_diff_ratio
                        findings.append({
                            'Error Type': 'DIM Weight Overcharge',
                            'Tracking Number': row.get('Tracking Number', ''),
                            'Date': pd.to_datetime(row.get('Shipment Date'), errors='coerce').strftime('%Y-%m-%d'),
                            'Carrier': row.get('Carrier', ''),
                            'Service Type': row.get('Service Type', ''),
                            'Dispute Reason': 'Incorrect DIM weight calculation',
                            'Refund Estimate': refund_estimate,
                            'Notes': f'Calculated: {calculated_dim:.1f} lbs, Billed: {billed_dim:.1f} lbs'
                        })
            except Exception:
                continue
        return findings

    def check_duplicate_tracking(self, df: pd.DataFrame) -> List[Dict]:
        """
        Check for duplicate tracking numbers in the SHIPMENT SUMMARY data.
        
        IMPORTANT: This function expects that surcharges have already been grouped by tracking number.
        When merging with a surcharge report, the merge_utils.merge_shipments_and_surcharges()
        function groups all surcharges per tracking number, so the final DataFrame has ONE line
        per tracking number. This means:
        
        - Surcharge report with 6 lines for tracking #479341655337 → GROUPED into 1 line (NOT a duplicate)
        - Shipment summary with 2 lines for tracking #479341655337 → TRUE DUPLICATE (will be flagged)
        
        This function only detects actual duplicate shipments from the main shipment file.
        """
        findings = []
        if df.empty or 'Tracking Number' not in df.columns:
            return findings
        AMT_TOL = 0.01
        df_work = df.copy()
        df_work['_key_tracking'] = df_work['Tracking Number'].apply(self._normalize_tracking)
        df_work['_carrier'] = df_work['Carrier'].fillna('Unknown').astype(str).str.upper() if 'Carrier' in df_work.columns else 'Unknown'
        freight_candidates = ['Freight Charges','Base Rate','Freight','Transportation Charge']
        misc_candidates    = ['Surcharges','Miscellaneous Charges','Additional Charges','Misc']
        duty_candidates    = ['Duty and Tax','Duty & Tax','Duties','Taxes','Customs Charges']
        discount_candidates= ['Discount','Discounts','Credit']

        has_duty_columns = any(col in df_work.columns for col in duty_candidates)
        has_freight_columns = any(col in df_work.columns for col in freight_candidates)

        freight_amts, misc_amts, duty_amts, discount_amts, net_amts = [], [], [], [], []
        for _, row in df_work.iterrows():
            freight = self._get_float_value(row, freight_candidates)
            misc    = self._get_float_value(row, misc_candidates)
            duty    = self._get_float_value(row, duty_candidates)
            discount= abs(self._get_float_value(row, discount_candidates))
            net     = row.get('Total Charges', 0)
            if pd.notna(net):
                try: net = float(str(net).replace('$','').replace(',',''))
                except: net = freight + misc + duty - discount
            else:
                net = freight + misc + duty - discount
            if not has_duty_columns and not has_freight_columns:
                if freight == 0 and misc == 0 and duty == 0 and net > 0:
                    freight = net
            freight_amts.append(freight); misc_amts.append(misc); duty_amts.append(duty); discount_amts.append(discount); net_amts.append(net)

        df_work['_freight']=freight_amts; df_work['_misc']=misc_amts; df_work['_duty']=duty_amts; df_work['_discount']=discount_amts; df_work['_net']=net_amts

        freight_like = df_work['_freight'] + df_work['_misc'] + df_work['_discount']
        is_transport = (freight_like > AMT_TOL) & (df_work['_duty'].abs() < AMT_TOL)
        is_duty_tax  = (df_work['_duty'].abs() > AMT_TOL) & ((df_work['_freight'].abs() + df_work['_misc'].abs()) < AMT_TOL)
        is_credit    = (df_work['_net'] < -AMT_TOL)
        df_work['_class'] = np.select([is_transport,is_duty_tax,is_credit], ['TRANSPORT','DUTY_TAX','CREDIT_ADJUST'], default='MISC')
        df_work['_group_key'] = df_work['_carrier'] + '||' + df_work['_key_tracking']

        tracking_counts = df_work['_key_tracking'].value_counts()
        duplicates = tracking_counts[tracking_counts > 1]
        if duplicates.empty: return findings

        for tracking_num in duplicates.index:
            if not tracking_num: continue
            duplicate_rows = df_work[df_work['_key_tracking'] == tracking_num]
            
            # Check if this is a legitimate Original + Return shipment pair
            # Example: "International Ground" + "Ground Return Manager" with same tracking number
            if self._is_original_plus_return_pair(duplicate_rows):
                continue  # Skip - this is NOT a duplicate billing error
            
            transport_rows = duplicate_rows[duplicate_rows['_class'] == 'TRANSPORT']
            duty_tax_rows  = duplicate_rows[duplicate_rows['_class'] == 'DUTY_TAX']
            num_transport = len(transport_rows); num_duty_tax = len(duty_tax_rows)
            if num_transport == 1 and num_duty_tax == 1:
                continue
            if num_transport > 1:
                transport_nets = transport_rows['_net'].tolist()
                unique_amounts = len(set([round(x,2) for x in transport_nets]))
                if unique_amounts > 1:
                    total_transport = sum(transport_nets)
                    refund_estimate = total_transport - max(transport_nets)
                    dispute_reason = f'Multiple freight charges ({num_transport} lines with different amounts)'
                else:
                    refund_estimate = transport_nets[0] * (num_transport - 1)
                    dispute_reason = f'Duplicate freight billing ({num_transport} identical charges)'
                freight_total = sum(transport_nets)
                duty_tax_total = sum(duty_tax_rows['_net'].tolist()) if num_duty_tax > 0 else 0
                net_landed = freight_total + duty_tax_total
                first_row = duplicate_rows.iloc[0]
                findings.append({
                    'Error Type': 'Duplicate Tracking',
                    'Tracking Number': first_row['Tracking Number'],
                    'Date': pd.to_datetime(first_row.get('Shipment Date'), errors='coerce').strftime('%Y-%m-%d') if pd.notna(first_row.get('Shipment Date')) else '',
                    'Carrier': first_row.get('Carrier', ''),
                    'Service Type': first_row.get('Service Type', ''),
                    'Dispute Reason': dispute_reason,
                    'Refund Estimate': refund_estimate,
                    'Notes': f'Transport: {num_transport}, Duty/Tax: {num_duty_tax}, Landed: ${net_landed:.2f}'
                })
        return findings

    def check_incorrect_zones(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        for _, row in df.iterrows():
            try:
                carrier = str(row.get('Carrier', '')).upper()
                origin_zip = str(row.get('Origin ZIP', ''))[:5]
                dest_zip = str(row.get('Destination ZIP', ''))[:5]
                billed_zone = int(row.get('Zone', 0) or 0)
                if carrier in self.zone_mapping:
                    expected_zone = self.zone_mapping[carrier].get(dest_zip)
                    if expected_zone and expected_zone != billed_zone:
                        base_rate = float(row.get('Base Rate', 0) or 0)
                        zone_diff = billed_zone - expected_zone
                        if zone_diff > 0:
                            refund_estimate = base_rate * 0.1 * zone_diff
                            findings.append({
                                'Error Type': 'Incorrect Zone',
                                'Tracking Number': row.get('Tracking Number', ''),
                                'Date': pd.to_datetime(row.get('Shipment Date'), errors='coerce').strftime('%Y-%m-%d'),
                                'Carrier': row.get('Carrier', ''),
                                'Service Type': row.get('Service Type', ''),
                                'Dispute Reason': 'Incorrect zone assignment',
                                'Refund Estimate': refund_estimate,
                                'Notes': f'Billed Zone: {billed_zone}, Correct Zone: {expected_zone}'
                            })
            except Exception:
                continue
        return findings

    def check_address_type_mismatches(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        business_keywords = ['LLC','INC','CORP','COMPANY','BUSINESS','OFFICE','WAREHOUSE','STORE','SHOP','CENTER','DISTRIBUTION']
        for _, row in df.iterrows():
            try:
                address_type = str(row.get('Address Type', '')).upper()
                dest_address = self._get_address(row)
                residential_surcharge = float(row.get('Residential Surcharge', 0) or 0)
                has_business_keywords = any(k in dest_address.upper() for k in business_keywords)
                if has_business_keywords and address_type == 'RESIDENTIAL' and residential_surcharge > 0:
                    findings.append({
                        'Error Type': 'Address Type Mismatch',
                        'Tracking Number': row.get('Tracking Number', ''),
                        'Date': pd.to_datetime(row.get('Shipment Date')).strftime('%Y-%m-%d'),
                        'Carrier': row.get('Carrier', ''),
                        'Service Type': row.get('Service Type', ''),
                        'Dispute Reason': 'Residential surcharge on business address',
                        'Refund Estimate': residential_surcharge,
                        'Notes': 'Business keywords found in address'
                    })
            except Exception:
                continue
        return findings

    def check_high_surcharges(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        ABS = 50.0
        PCT = 0.20
        for _, row in df.iterrows():
            try:
                def safe_float(v):
                    if pd.isna(v): return 0.0
                    try: return float(v)
                    except: return 0.0
                surcharges = safe_float(row.get('Surcharges', 0))
                if surcharges == 0: surcharges = safe_float(row.get('Additional_Surcharges', 0))
                if surcharges == 0:
                    for col in ['Fuel Surcharge','Residential Surcharge','Address Correction','Declared Value Charge']:
                        surcharges += safe_float(row.get(col, 0))
                base_rate = safe_float(row.get('Base Rate', 0))
                total_charges = safe_float(row.get('Total Charges', 0))
                if surcharges == 0: continue
                flagged = False; reason = ''; notes = ''
                if base_rate > 0 and surcharges/base_rate > self.high_surcharge_threshold:
                    flagged = True; reason = f'Surcharges exceed {self.high_surcharge_threshold*100:.0f}% of base rate'
                    notes = f'{surcharges:.2f} / {base_rate:.2f}'
                if not flagged and surcharges > ABS:
                    flagged = True; reason = f'Surcharges exceed ${ABS:.0f} threshold'; notes = f'${surcharges:.2f}'
                if not flagged and base_rate == 0 and total_charges > 0 and (surcharges/total_charges) > PCT:
                    flagged = True; reason = f'Surcharges exceed {PCT*100:.0f}% of total charges'
                    notes = f'${surcharges:.2f} of ${total_charges:.2f}'
                if not flagged and surcharges >= 10.0 and 'Additional_Surcharges' in row.index and safe_float(row.get('Additional_Surcharges',0))>0:
                    flagged = True; reason = 'Merged surcharge for review'; notes = f'${surcharges:.2f} (merged)'
                if flagged:
                    findings.append({
                        'Error Type': 'High Surcharges',
                        'Tracking Number': row.get('Tracking Number', ''),
                        'Date': pd.to_datetime(row.get('Shipment Date'), errors='coerce').strftime('%Y-%m-%d'),
                        'Carrier': row.get('Carrier', ''), 'Service Type': row.get('Service Type', ''),
                        'Dispute Reason': reason, 'Refund Estimate': surcharges * 0.5, 'Notes': notes
                    })
            except Exception:
                continue
        return findings

    def check_unnecessary_surcharges(self, df: pd.DataFrame) -> List[Dict]:
        findings = []
        for _, row in df.iterrows():
            try:
                address_correction = float(row.get('Address Correction', 0) or 0)
                declared_value = float(row.get('Declared Value', 0) or 0)
                declared_value_charge = float(row.get('Declared Value Charge', 0) or 0)
                if address_correction > 0:
                    findings.append({
                        'Error Type': 'Unnecessary Surcharge',
                        'Tracking Number': row.get('Tracking Number', ''),
                        'Date': pd.to_datetime(row.get('Shipment Date')).strftime('%Y-%m-%d'),
                        'Carrier': row.get('Carrier', ''), 'Service Type': row.get('Service Type', ''),
                        'Dispute Reason': 'Address correction fee', 'Refund Estimate': address_correction,
                        'Notes': 'Address correction fees are often disputable'
                    })
                if declared_value_charge > 0 and declared_value < 100:
                    findings.append({
                        'Error Type': 'Unnecessary Surcharge',
                        'Tracking Number': row.get('Tracking Number', ''),
                        'Date': pd.to_datetime(row.get('Shipment Date')).strftime('%Y-%m-%d'),
                        'Carrier': row.get('Carrier', ''), 'Service Type': row.get('Service Type', ''),
                        'Dispute Reason': 'Declared value charge on low-value package',
                        'Refund Estimate': declared_value_charge,
                        'Notes': f'Declared value: ${declared_value:.2f}'
                    })
            except Exception:
                continue
        return findings

    # -------------------------- FIXED/UPGRADED: disputable surcharges --------------------------

    def check_disputable_surcharges(self, df: pd.DataFrame) -> List[Dict]:
        """
        Validate common disputable surcharges with robust parsing, correct thresholds,
        and tolerant column/label handling.
        """
        findings = []

        # Canonicalization map (patterns → canonical label)
        CANON = [
            (r'ADDRESS\s*CORR', 'ADDRESS CORRECTION'),
            # Removed: Delivery Area Surcharge (DAS) - not worth disputing
            # DAS (Delivery Area Surcharge) Residential must come BEFORE general Residential
            (r'DAS.*RES(IDENTIAL)?|DELIVERY\s*AREA.*RES(IDENTIAL)?', 'DAS RESIDENTIAL'),
            (r'\bRES(|IDENTIAL)\b|RES\s*SURCHARGE', 'RESIDENTIAL SURCHARGE'),
            (r'SAT(URDAY)?\s*DEL(IVERY)?', 'SATURDAY DELIVERY'),
            (r'SAT(URDAY)?\s*PICKUP', 'SATURDAY PICKUP'),
            (r'SUNDAY\s*DEL(IVERY)?|WEEKEND', 'SUNDAY/WEEKEND CHARGE'),
            (r'RETURN\s*(FEE|TO SHIPPER|RTS)', 'RETURN FEE'),
            (r'REDIRECT|DELIVERY\s*CHANGE|ADDRESS\s*CHANGE', 'REDIRECT DELIVERY FEE'),
            (r'HOLD\s*(AT)?\s*LOCATION|WILL\s*CALL', 'HOLD AT LOCATION FEE'),
            (r'DUPLICATE\s*INVOICE|INVALID\s*ACCOUNT|INCORRECT\s*BILL(ING)?|REBILL|MANUAL\s*PROCESS', 'BILLING ERROR FEE'),
            # Demand/Peak Additional Handling must come BEFORE general Additional Handling
            # Additional Handling for Package/Packaging is legitimate (cylinders, unusual shapes)
            (r"AD(D'?|DL)?(ITIONAL)?\s*HANDLING.*(PACKAGE|PACKAGING)", 'AHS PACKAGING'),
            (r'DEMAND.*ADDITIONAL.*HANDLING', 'DEMAND ADDITIONAL HANDLING'),
            (r"AD(D'?|DL)?(ITIONAL)?\s*HANDLING|AHS|NON[-\s]*MACHINABLE", 'ADDITIONAL HANDLING SURCHARGE'),
            # Demand/Peak Oversize must come BEFORE general Oversize
            (r'DEMAND.*OVERSIZE', 'DEMAND OVERSIZE'),
            (r'OVERSIZE|OVER\s*SIZE|LARGE\s*PACKAGE', 'OVERSIZE CHARGE'),
            (r'UNAUTH(ORIZED)?\s*PACKAGE', 'UNAUTHORIZED PACKAGE CHARGE'),
            (r'PEAK\s*ADDITIONAL\s*HANDLING', 'PEAK ADDITIONAL HANDLING'),
            (r'PEAK\s*OVERSIZE', 'PEAK OVERSIZE'),
            (r'PEAK\s*RESIDENTIAL', 'PEAK RESIDENTIAL'),
            (r'\bPEAK\b', 'PEAK SURCHARGE'),
            (r'MONEY[-\s]*BACK|LATE\s*DELIVERY|SERVICE\s*FAILURE|TRANSIT\s*TIME|DELIVERY\s*EXCEPTION', 'SERVICE FAILURE ADJUSTMENT'),
            (r'WEIGHT\s*CORRECTION', 'WEIGHT CORRECTION'),
            (r'DIM(ENSIONAL)?\s*WEIGHT|CUBIC\s*VOLUME', 'DIM WEIGHT ADJUSTMENT'),
            (r'OVERWEIGHT', 'OVERWEIGHT CHARGE'),
            (r'BROKERAGE|DUTY\s*AND\s*TAX|ENTRY\s*PREPARATION|CLEARANCE\s*ENTRY|IMPORT\s*DATA\s*CORRECTION', 'CUSTOMS/BROKERAGE FEE'),
            (r'INVALID\s*PICKUP|ATTEMPTED\s*DELIVERY|UNDELIVERABLE|DELIVERY\s*ATTEMPT', 'FAILED PICKUP/DELIVERY FEE'),
            (r'FUEL|FUEL\s*SURCHARGE|FSC', 'FUEL SURCHARGE'),
            (r'DECLARED\s*VALUE|DV\s*CHARGE|INSURANCE', 'DECLARED VALUE CHARGE'),
            (r'MISSING\s*DOC', 'MISSING DOCUMENTATION FEE')
        ]

        def canonize(label: str) -> str:
            u = str(label).upper().strip()
            for pat, name in CANON:
                if re.search(pat, u):
                    return name
            return u  # fallback

        # Flexible parse of merged surcharge detail strings
        def parse_merged(text: str) -> List[Tuple[str, float]]:
            if not text or str(text).strip().lower() == 'nan':
                return []
            raw = str(text)
            # split on pipes/semicolons/commas
            parts = re.split(r'\s*[|;,]\s*', raw)
            out = []
            for p in parts:
                if not p.strip():
                    continue
                # Accept "Label: $12.34" or "Label $12.34" - also handle blank labels like ": $12.34" or just "$12.34"
                # First try to match with a label
                m = re.search(r'(.+?)[\s:]\s*\$?\s*(-?\d+(?:\.\d+)?)', p)
                if m:
                    label_text = m.group(1).strip()
                    # Check if the label is blank or just whitespace/punctuation
                    if not label_text or label_text in [':', '-', '.', '']:
                        desc = 'BLANK DESCRIPTION CHARGE'
                    else:
                        desc = canonize(label_text)
                    try:
                        amt = float(m.group(2))
                        if amt != 0:
                            out.append((desc, amt))
                    except:
                        continue
                else:
                    # Try to match just a dollar amount with no label (blank description)
                    m2 = re.search(r'^\s*[:;]?\s*\$?\s*(-?\d+(?:\.\d+)?)\s*$', p)
                    if m2:
                        try:
                            amt = float(m2.group(1))
                            if amt != 0:
                                out.append(('BLANK DESCRIPTION CHARGE', amt))
                        except:
                            continue
            return out

        # Column candidates to pull context
        delivery_date_candidates = ['Actual Delivery Date','Shipment Delivery Date (mm/dd/yyyy)','Delivery Date']
        service_candidates = ['Service Type','Service Description']
        surcharge_columns = [
            'Address Correction','Residential Surcharge',
            # Removed: 'Delivery Area Surcharge','Extended Delivery Area' - not worth disputing
            'Saturday Delivery','Saturday Pickup','Sunday Delivery','Return Fee','Redirect Fee',
            'Hold at Location','Additional Handling','Oversize Charge','Overweight Charge','Peak Surcharge',
            'Peak Additional Handling','Peak Oversize','Peak Residential','Fuel Surcharge','Declared Value Charge',
            'Brokerage Fee','Duty and Tax','Entry Preparation','Clearance Entry','Missing Documentation',
            'Attempted Delivery','Undeliverable','Weight Correction','DIM Weight Adjustment','Unauthorized Package'
        ]
        
        # Pre-calculate total Net Charge per tracking number for international shipments
        # (International shipments have 2+ lines: shipment + duty/tax lines)
        tracking_total_net_charge = {}
        net_charge_cols = ['Net Charge Amount USD', 'Net Charge', 'Total Charges']
        for _, row in df.iterrows():
            tracking = row.get('Tracking Number', '')
            if not tracking:
                continue
            net_charge = self._get_float_value(row, net_charge_cols)
            if tracking not in tracking_total_net_charge:
                tracking_total_net_charge[tracking] = 0.0
            tracking_total_net_charge[tracking] += net_charge
        
        for _, row in df.iterrows():
            try:
                tracking = row.get('Tracking Number', '')
                ship_date = pd.to_datetime(row.get('Shipment Date'), errors='coerce')
                carrier = str(row.get('Carrier', '')).upper()
                service_type = str(self._get_first(row, service_candidates, '') or '')
                
                # Skip RMGR (Return Manager) service types - these are legitimate returns and should not be flagged as duplicate surcharges
                if 'RMGR' in service_type.upper():
                    continue
                
                # dims/weight
                L = self._get_dimension(row, 'length'); W = self._get_dimension(row, 'width'); H = self._get_dimension(row, 'height')
                dims = sorted([L, W, H], reverse=True)
                longest, second, third = (dims + [0,0,0])[:3]
                
                # Flexible weight column detection (handle multiple column name variations)
                actual_wt_candidates = ['Actual Weight', 'Original Weight', 'Shipment Actual Weight', 'Package Weight', 'Weight']
                billed_wt_candidates = ['Billed Weight', 'Shipment Rated Weight', 'Rated Weight', 'Billable Weight', 'Chargeable Weight']
                
                actual_wt = self._get_float_value(row, actual_wt_candidates)
                billed_wt = self._get_float_value(row, billed_wt_candidates)
                dim_divisor = 166 if ('INTERNATIONAL' in service_type.upper() or 'INTL' in service_type.upper()) else 139
                dim_wt = math.ceil((L*W*H)/dim_divisor) if all(x>0 for x in [L,W,H]) else 0
                girth = 2*(second + third)
                # parse merged surcharges
                surcharge_details_value = row.get('Surcharge_Details', '')
                merged = parse_merged(surcharge_details_value)
                # parse individual columns
                indiv = []
                for col in surcharge_columns:
                    if col in row.index:
                        try:
                            amt = float(row.get(col, 0) or 0)
                            if amt != 0:
                                indiv.append((canonize(col), amt))
                        except:
                            continue
                surcharges = merged + indiv
                if not surcharges:
                    continue

                # capture delivery date for weekend checks
                delivery_date = self._get_date(row, delivery_date_candidates)

                # for duplicate detection
                from collections import Counter, defaultdict
                seen_desc = []
                bucket = defaultdict(float)
                
                # Pre-count blank description charges to avoid double-flagging
                # If there are multiple blanks, we'll only flag via duplicate detection
                blank_desc_count = sum(1 for d, a in surcharges if d == 'BLANK DESCRIPTION CHARGE')

                for desc, amount in surcharges:
                    seen_desc.append(desc)
                    dispute_reason = None
                    refund_estimate = 0.0
                    notes = ''
                    
                    # 0) Blank Description Charge - FedEx must provide reason for all charges
                    # Only flag individually if there's exactly one; duplicates handled by duplicate detection
                    if desc == 'BLANK DESCRIPTION CHARGE':
                        if blank_desc_count == 1:
                            dispute_reason = 'Charge with no description - FedEx must provide reason for all charges'
                            refund_estimate = amount
                            notes = 'Blank/missing surcharge description'
                        # If blank_desc_count > 1, skip individual finding - duplicate detection will handle it
                    # 1) Address Correction
                    elif desc == 'ADDRESS CORRECTION':
                        dispute_reason = 'Address correction fee - verify original label; often disputable'
                        refund_estimate = amount * 0.8
                    # Removed: DAS (Delivery Area Surcharge) - not worth disputing
                    # 2) Residential
                    elif desc == 'RESIDENTIAL SURCHARGE':
                        dest_info = self._get_full_destination_info(row).upper()
                        shipper_info = self._get_full_shipper_info(row).upper()
                        
                        # Check if recipient has business indicators
                        is_recipient_business = self._has_business_indicators(dest_info)
                        is_shipper_business = self._has_business_indicators(shipper_info)
                        
                        # Flag as disputable if recipient has business indicators (retail stores, business addresses)
                        if is_recipient_business:
                            dispute_reason = 'Residential surcharge applied to business address'
                            refund_estimate = amount
                            if is_shipper_business:
                                notes = f'Both recipient and shipper have business indicators (B2B)'
                            else:
                                notes = f'Recipient address has business indicators'
                    # 4) Weekend
                    elif desc in ('SATURDAY DELIVERY','SATURDAY PICKUP','SUNDAY/WEEKEND CHARGE'):
                        if pd.notna(delivery_date) and delivery_date.weekday() < 5:
                            dispute_reason = 'Weekend surcharge but delivery/pickup occurred on weekday'
                            refund_estimate = amount
                            notes = f'Date: {delivery_date.strftime("%A")}'
                    # 5) Return / Redirect / Hold
                    elif desc in ('RETURN FEE','REDIRECT DELIVERY FEE','HOLD AT LOCATION FEE'):
                        dispute_reason = f'{desc} - verify customer/carrier request vs. error'
                        refund_estimate = amount * 0.6
                    # 6) Billing Error Fee
                    elif desc == 'BILLING ERROR FEE':
                        dispute_reason = 'Billing error should not be passed to customer'
                        refund_estimate = amount
                    # 7) Additional Handling (FIX: ≥50 lb threshold)
                    elif desc == 'ADDITIONAL HANDLING SURCHARGE':
                        needs_handling = (
                            (longest > 48) or (second > 30) or ((longest + girth) > 105) or (actual_wt >= 50)
                        )
                        if not needs_handling and longest > 0:
                            dispute_reason = 'Additional Handling charged but size/weight thresholds not met'
                            refund_estimate = amount
                            notes = f'Dims {longest:.1f}x{second:.1f}x{third:.1f}", Wt {actual_wt:.1f} lb'
                    # 8) Oversize / Large Package (normalized, carrier-agnostic)
                    elif desc == 'OVERSIZE CHARGE':
                        length_plus_girth = longest + girth
                        is_oversize = (longest > 96) or (length_plus_girth > 130)
                        if not is_oversize and longest > 0:
                            dispute_reason = 'Oversize charge applied but thresholds not met'
                            refund_estimate = amount
                            notes = f'L={longest:.1f}", L+G={length_plus_girth:.1f}" (thresholds: >96" OR >130")'
                    # 9) Unauthorized
                    elif desc == 'UNAUTHORIZED PACKAGE CHARGE':
                        dispute_reason = 'Unauthorized package charge — verify proper authorization/labels'
                        refund_estimate = amount * 0.8
                    # 10) Peak surcharges
                    elif desc in ('PEAK ADDITIONAL HANDLING','PEAK OVERSIZE','PEAK RESIDENTIAL','PEAK SURCHARGE'):
                        if pd.notna(ship_date) and ship_date.month not in [11,12,1]:
                            dispute_reason = 'Peak surcharge outside typical peak season (Nov–Jan)'
                            refund_estimate = amount * 0.7
                        elif any(p in service_type.upper() for p in ['OVERNIGHT','PRIORITY','EXPRESS']):
                            dispute_reason = 'Peak surcharge on premium service — review reasonableness'
                            refund_estimate = amount * 0.4
                    # 11) Service failure type
                    elif desc == 'SERVICE FAILURE ADJUSTMENT':
                        dispute_reason = 'Service failure should be refunded, not charged'
                        refund_estimate = amount
                    # 12) Weight-related (DIM/Overweight)
                    elif desc in ('WEIGHT CORRECTION','DIM WEIGHT ADJUSTMENT','OVERWEIGHT CHARGE'):
                        if dim_wt > 0 and billed_wt > 0:
                            correct_billable = max(round(actual_wt), dim_wt)
                            over = billed_wt - correct_billable
                            if over > 1:
                                dispute_reason = f'Billed weight appears {over:.0f} lb over correct billable'
                                refund_estimate = amount * 0.8
                                notes = f'Actual {actual_wt:.1f}, DIM {dim_wt} (ceil), Billed {billed_wt:.0f}'
                        if desc == 'OVERWEIGHT CHARGE' and 0 < actual_wt < 150:
                            dispute_reason = f'Overweight charge but actual weight {actual_wt:.1f} lb (<150 lb threshold)'
                            refund_estimate = amount
                    # 13) Customs/Brokerage (Skip for international shipments - these fees are legitimate)
                    elif desc == 'CUSTOMS/BROKERAGE FEE':
                        # Check if this is an international shipment
                        # Complete list of FedEx international service codes
                        service_upper = service_type.upper()
                        intl_codes = ['OA', 'LO', 'IP', 'IE', 'IF', 'IG', 'SG', 'F1', 'FO', 'IX', 'XS']
                        is_international = any(indicator in service_upper for indicator in 
                                             ['INTERNATIONAL', 'INTL', 'GLOBAL', 'WORLD', 'EXPORT', 'IMPORT']) or \
                                          any(service_upper.startswith(code) or f' {code}' in service_upper or code == service_upper 
                                              for code in intl_codes)
                        if not is_international:
                            # Only flag customs/brokerage fees for domestic shipments
                            dispute_reason = 'Customs/brokerage fee — verify necessity and accuracy'
                            refund_estimate = amount * 0.5
                    # 14) Failed pickup/delivery
                    elif desc == 'FAILED PICKUP/DELIVERY FEE':
                        dispute_reason = 'Failed delivery/pickup — verify carrier attempts & contact info'
                        refund_estimate = amount * 0.7
                    # 15) Fuel
                    elif desc == 'FUEL SURCHARGE':
                        # FedEx calculates fuel surcharge on the Net Charge Amount (total shipment cost)
                        # which includes freight + all surcharges
                        # For international shipments, sum Net Charge across all lines with same tracking
                        # (international shipments have 2+ lines: shipment + duty/tax lines)
                        service_upper = service_type.upper()
                        # Complete list of FedEx international service codes
                        intl_service_codes = ['OA', 'LO', 'IP', 'IE', 'IF', 'IG', 'SG', 'F1', 'FO', 'IX', 'XS']
                        is_international = any(indicator in service_upper for indicator in 
                                             ['INTERNATIONAL', 'INTL', 'GLOBAL', 'WORLD', 'EXPORT', 'IMPORT']) or \
                                          any(service_upper.startswith(code) or f' {code}' in service_upper or code == service_upper 
                                              for code in intl_service_codes)
                        
                        if is_international and tracking in tracking_total_net_charge:
                            # Use total Net Charge across all lines for this tracking number
                            net_charge = tracking_total_net_charge[tracking]
                        else:
                            # Domestic: use single row Net Charge
                            net_charge = self._get_float_value(row, ['Net Charge Amount USD', 'Net Charge', 'Total Charges'])
                        
                        # Fallback to Base Rate if Net Charge not available
                        if net_charge == 0:
                            net_charge = float(row.get('Base Rate', 0) or 0)
                        
                        if net_charge > 0:
                            pct = (amount / net_charge) * 100
                            if pct > 30:
                                dispute_reason = f'Fuel surcharge unusually high ({pct:.1f}% of net charge)'
                                refund_estimate = amount * 0.3
                                notes = f'FSC ${amount:.2f} / Net Charge ${net_charge:.2f}'
                    # 16) Declared value
                    elif desc == 'DECLARED VALUE CHARGE':
                        dv = float(row.get('Declared Value', 0) or 0)
                        if dv < 100:
                            dispute_reason = f'Declared value charge on low-value package (${dv:.2f})'
                            refund_estimate = amount
                    # 17) Missing documentation
                    elif desc == 'MISSING DOCUMENTATION FEE':
                        dispute_reason = 'Missing documentation fee — verify paperwork actually missing'
                        refund_estimate = amount * 0.7

                    if dispute_reason:
                        findings.append({
                            'Error Type': 'Disputable Surcharge',
                            'Tracking Number': tracking,
                            'Date': ship_date.strftime('%Y-%m-%d') if pd.notna(ship_date) else '',
                            'Carrier': carrier,
                            'Service Type': service_type,
                            'Dispute Reason': dispute_reason,
                            'Refund Estimate': float(refund_estimate),
                            'Notes': f'{desc} ${amount:.2f}' + (f' | {notes}' if notes else '')
                        })

                    bucket[desc] += float(amount)

                # Duplicate surcharge detection on canonical desc
                counts = Counter(seen_desc)
                for desc, cnt in counts.items():
                    if cnt > 1:
                        total_amt = bucket[desc]
                        
                        # Special handling for blank description duplicates - full refund since all are disputable
                        if desc == 'BLANK DESCRIPTION CHARGE':
                            refund_est = total_amt  # Full refund for all blank description charges
                            dispute_msg = f'Multiple charges ({cnt}x) with blank descriptions - FedEx must provide reason for all charges'
                            notes_msg = f'Blank description charges billed {cnt}x, total ${total_amt:.2f}'
                        else:
                            refund_est = total_amt * (cnt-1)/cnt  # keep one occurrence for regular duplicates
                            dispute_msg = f'Duplicate surcharge appears {cnt} times'
                            notes_msg = f'{desc} billed {cnt}x, total ${total_amt:.2f}'
                        
                        findings.append({
                            'Error Type': 'Disputable Surcharge',
                            'Tracking Number': row.get('Tracking Number', ''),
                            'Date': ship_date.strftime('%Y-%m-%d') if pd.notna(ship_date) else '',
                            'Carrier': carrier, 'Service Type': service_type,
                            'Dispute Reason': dispute_msg,
                            'Refund Estimate': float(refund_est),
                            'Notes': notes_msg
                        })

            except Exception:
                continue

        # Consolidate duplicate surcharge findings by tracking number
        # Group findings where same tracking number has multiple duplicate surcharge entries
        consolidated = []
        dup_surcharge_findings = [f for f in findings if f.get('Dispute Reason', '').startswith('Duplicate surcharge')]
        other_findings = [f for f in findings if not f.get('Dispute Reason', '').startswith('Duplicate surcharge')]
        
        if dup_surcharge_findings:
            from collections import defaultdict
            by_tracking = defaultdict(list)
            for finding in dup_surcharge_findings:
                tracking = finding.get('Tracking Number', '')
                by_tracking[tracking].append(finding)
            
            for tracking, group in by_tracking.items():
                if len(group) == 1:
                    # Only one duplicate surcharge entry for this tracking number
                    consolidated.append(group[0])
                else:
                    # Multiple duplicate surcharge entries - consolidate them
                    total_refund = sum(f['Refund Estimate'] for f in group)
                    all_notes = [f['Notes'] for f in group]
                    combined_notes = ' | '.join(all_notes)
                    
                    # Use the first entry as template
                    consolidated.append({
                        'Error Type': 'Disputable Surcharge',
                        'Tracking Number': tracking,
                        'Date': group[0].get('Date', ''),
                        'Carrier': group[0].get('Carrier', ''),
                        'Service Type': group[0].get('Service Type', ''),
                        'Dispute Reason': f'Duplicate surcharge appears {len(group)} times',
                        'Refund Estimate': float(total_refund),
                        'Notes': combined_notes
                    })
        
        # Combine consolidated duplicate surcharges with other findings
        return other_findings + consolidated

    # -------------------------- summary & utils --------------------------

    def calculate_summary(self, original_df: pd.DataFrame, findings_df: pd.DataFrame) -> Dict[str, Any]:
        total_charges = original_df['Total Charges'].sum()
        total_savings = findings_df['Refund Estimate'].sum() if not findings_df.empty else 0
        affected_shipments = len(findings_df['Tracking Number'].unique()) if not findings_df.empty else 0
        total_shipments = len(original_df)
        return {
            'total_charges': total_charges,
            'total_savings': total_savings,
            'affected_shipments': affected_shipments,
            'total_shipments': total_shipments,
            'savings_rate': (total_savings / total_charges * 100) if total_charges > 0 else 0,
            'affected_rate': (affected_shipments / total_shipments * 100) if total_shipments > 0 else 0
        }

    def _add_business_days(self, start_date: datetime, business_days: int) -> datetime:
        current_date = start_date
        days_added = 0
        while days_added < business_days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:
                days_added += 1
        return current_date

