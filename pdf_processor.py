import fitz
import tabula
import pandas as pd
import re
from datetime import datetime
import streamlit as st

class PDFProcessor:
    def __init__(self):
        self.common_carriers = [
            'UPS', 'FedEx', 'DHL', 'USPS', 'Yellow Freight', 'Con-way', 'ABF Freight',
            'SAIA', 'Old Dominion', 'Estes Express', 'XPO Logistics', 'R+L Carriers',
            'Southeastern Freight Lines', 'Central Transport', 'TForce Freight'
        ]
        
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF using PyMuPDF (fitz)"""
        try:
            text = ""
            if hasattr(pdf_file, 'read'):
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
            else:
                pdf_bytes = pdf_file
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                page_text = str(page.get_text())
                if page_text:
                    text += page_text + "\n"
            doc.close()
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def extract_tables_from_pdf(self, pdf_file):
        """Extract tables from PDF using tabula"""
        try:
            # Extract all tables from PDF
            tables = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, pandas_options={'header': None})  # type: ignore
            return tables
        except Exception as e:
            st.warning(f"Could not extract tables: {str(e)}")
            return []

    def parse_invoice_data(self, text, tables=None):
        """Parse invoice data from extracted text and tables"""
        invoice_data = {
            'invoice_number': self.extract_invoice_number(text),
            'invoice_date': self.extract_invoice_date(text),
            'carrier': self.extract_carrier(text),
            'total_amount': self.extract_total_amount(text),
            'origin': self.extract_origin(text),
            'destination': self.extract_destination(text),
            'weight': self.extract_weight(text),
            'distance': self.extract_distance(text),
            'service_type': self.extract_service_type(text),
            'line_items': self.extract_line_items(text, tables) if tables else []
        }
        
        return invoice_data

    def extract_invoice_number(self, text):
        """Extract invoice number from text"""
        patterns = [
            r'Invoice\s*#?\s*:?\s*([A-Za-z0-9\-]+)',
            r'Bill\s*#?\s*:?\s*([A-Za-z0-9\-]+)',
            r'Reference\s*#?\s*:?\s*([A-Za-z0-9\-]+)',
            r'PRO\s*#?\s*:?\s*([A-Za-z0-9\-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_invoice_date(self, text):
        """Extract invoice date from text"""
        patterns = [
            r'Invoice\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Bill\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse the date
                    for date_format in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']:
                        try:
                            return datetime.strptime(date_str, date_format).date()
                        except ValueError:
                            continue
                except:
                    pass
        return None

    def extract_carrier(self, text):
        """Extract carrier name from text"""
        text_upper = text.upper()
        
        for carrier in self.common_carriers:
            if carrier.upper() in text_upper:
                return carrier
        
        # Try to find carrier using pattern matching
        patterns = [
            r'Carrier\s*:?\s*([A-Za-z\s&]+?)(?:\n|$)',
            r'Shipper\s*:?\s*([A-Za-z\s&]+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def extract_total_amount(self, text):
        """Extract total amount from text"""
        patterns = [
            r'Total\s*:?\s*\$?([0-9,]+\.?\d*)',
            r'Amount\s*Due\s*:?\s*\$?([0-9,]+\.?\d*)',
            r'Balance\s*:?\s*\$?([0-9,]+\.?\d*)',
            r'Grand\s*Total\s*:?\s*\$?([0-9,]+\.?\d*)',
            r'\$([0-9,]+\.\d{2})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Get the last (likely largest) amount found
                    amount_str = matches[-1].replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        return None

    def extract_origin(self, text):
        """Extract origin location from text"""
        patterns = [
            r'Origin\s*:?\s*([A-Za-z\s,]+?)(?:\n|Destination)',
            r'From\s*:?\s*([A-Za-z\s,]+?)(?:\n|To)',
            r'Ship\s*From\s*:?\s*([A-Za-z\s,]+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_destination(self, text):
        """Extract destination location from text"""
        patterns = [
            r'Destination\s*:?\s*([A-Za-z\s,]+?)(?:\n|$)',
            r'To\s*:?\s*([A-Za-z\s,]+?)(?:\n|$)',
            r'Ship\s*To\s*:?\s*([A-Za-z\s,]+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_weight(self, text):
        """Extract weight from text"""
        patterns = [
            r'Weight\s*:?\s*([0-9,]+\.?\d*)\s*(?:lbs?|pounds?)',
            r'([0-9,]+\.?\d*)\s*(?:lbs?|pounds?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight_str = match.group(1).replace(',', '')
                    return float(weight_str)
                except ValueError:
                    continue
        return None

    def extract_distance(self, text):
        """Extract distance from text"""
        patterns = [
            r'Distance\s*:?\s*([0-9,]+\.?\d*)\s*(?:miles?|mi)',
            r'([0-9,]+\.?\d*)\s*(?:miles?|mi)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    distance_str = match.group(1).replace(',', '')
                    return float(distance_str)
                except ValueError:
                    continue
        return None

    def extract_service_type(self, text):
        """Extract service type from text"""
        service_types = [
            'Ground', 'Air', 'Express', 'Standard', 'Overnight', 'Next Day',
            'Two Day', '2-Day', 'LTL', 'FTL', 'Expedited', 'Economy'
        ]
        
        text_upper = text.upper()
        for service in service_types:
            if service.upper() in text_upper:
                return service
        return None

    def extract_line_items(self, text, tables):
        """Extract line items from tables or text"""
        line_items = []
        
        if tables:
            for table in tables:
                if isinstance(table, pd.DataFrame) and not table.empty:
                    # Try to identify tables with charge information
                    for _, row in table.iterrows():
                        row_text = ' '.join([str(cell) for cell in row if pd.notna(cell)])
                        
                        # Look for monetary amounts in the row
                        amount_match = re.search(r'\$?([0-9,]+\.?\d*)', row_text)
                        if amount_match:
                            try:
                                amount = float(amount_match.group(1).replace(',', ''))
                                line_items.append({
                                    'description': row_text,
                                    'amount': amount
                                })
                            except ValueError:
                                pass
        
        return line_items

    def process_invoice(self, pdf_file):
        """Main method to process invoice PDF"""
        try:
            # Extract text
            text = self.extract_text_from_pdf(pdf_file)
            if not text:
                return None
            
            # Extract tables
            tables = self.extract_tables_from_pdf(pdf_file)
            
            # Parse invoice data
            invoice_data = self.parse_invoice_data(text, tables)
            
            # Add raw text for reference
            invoice_data['raw_text'] = text
            
            return invoice_data
            
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return None

    def validate_invoice_data(self, invoice_data):
        """Validate extracted invoice data"""
        issues = []
        
        if not invoice_data.get('invoice_number'):
            issues.append("Invoice number not found")
        
        if not invoice_data.get('invoice_date'):
            issues.append("Invoice date not found")
        
        if not invoice_data.get('total_amount'):
            issues.append("Total amount not found")
        
        if not invoice_data.get('carrier'):
            issues.append("Carrier information not found")
        
        return issues
