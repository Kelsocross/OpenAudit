from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import io
import pandas as pd
import streamlit as st

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for the report"""
        # Custom title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f77b4')
        ))
        
        # Custom heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        # Custom subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#34495e')
        ))
        
        # Summary box style
        self.styles.add(ParagraphStyle(
            name='SummaryBox',
            parent=self.styles['Normal'],
            fontSize=12,
            leftIndent=20,
            rightIndent=20,
            spaceBefore=10,
            spaceAfter=10,
            backColor=colors.HexColor('#f8f9fa'),
            borderColor=colors.HexColor('#1f77b4'),
            borderWidth=1
        ))
    
    def generate_audit_report(self, report_data, invoice_data=None):
        """Generate comprehensive audit report PDF"""
        try:
            # Create buffer for PDF
            buffer = io.BytesIO()
            
            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build story (content)
            story = []
            
            # Title page
            story.extend(self._create_title_page(report_data))
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._create_executive_summary(report_data))
            
            # Financial impact
            story.extend(self._create_financial_impact_section(report_data))
            
            # Findings details
            story.extend(self._create_findings_section(report_data))
            
            # Action priorities
            story.extend(self._create_action_priorities_section(report_data))
            
            # Invoice details if provided
            if invoice_data:
                story.extend(self._create_invoice_details_section(invoice_data))
            
            # Appendix
            story.extend(self._create_appendix_section())
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            return buffer.getvalue()
            
        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")
            return None
    
    def _create_title_page(self, report_data):
        """Create title page"""
        story = []
        
        # Title
        story.append(Paragraph("OPENAUDIT FREIGHT AUDIT REPORT", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # Subtitle
        story.append(Paragraph("Comprehensive Freight Invoice Analysis", self.styles['Heading2']))
        story.append(Spacer(1, 0.5*inch))
        
        # Report date
        story.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary metrics table
        metrics_data = [
            ['Metric', 'Value'],
            ['Total Invoices Analyzed', f"{report_data.get('total_invoices', 0):,}"],
            ['Total Potential Savings', f"${report_data.get('total_potential_savings', 0):,.2f}"],
            ['Average Audit Score', f"{report_data.get('average_audit_score', 0):.1f}/100"],
            ['Total Findings', f"{report_data.get('total_findings', 0):,}"]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 0.5*inch))
        
        # Company info
        story.append(Paragraph("Powered by OpenAudit Platform", self.styles['Normal']))
        story.append(Paragraph("AI-Driven Freight Audit & Cost Optimization", self.styles['Normal']))
        
        return story
    
    def _create_executive_summary(self, report_data):
        """Create executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        summary_text = report_data.get('executive_summary', 
            'This comprehensive freight audit analysis has been completed to identify cost optimization opportunities and process improvements.')
        
        story.append(Paragraph(summary_text, self.styles['SummaryBox']))
        story.append(Spacer(1, 0.2*inch))
        
        # Key highlights
        story.append(Paragraph("Key Highlights:", self.styles['CustomSubHeading']))
        
        key_findings = report_data.get('key_findings', [])
        for finding in key_findings:
            story.append(Paragraph(f"• {finding}", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_financial_impact_section(self, report_data):
        """Create financial impact section"""
        story = []
        
        story.append(Paragraph("Financial Impact Analysis", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        financial_impact = report_data.get('financial_impact', {})
        
        # Financial impact table
        financial_data = [
            ['Financial Metric', 'Value', 'Impact'],
            ['Total Potential Savings', f"${financial_impact.get('total_potential_savings', 0):,.2f}", 'High'],
            ['Percentage of Spend', f"{financial_impact.get('percentage_of_spend', 0):.1f}%", 'Medium'],
            ['Estimated Payback Period', financial_impact.get('payback_period', 'N/A'), 'Immediate']
        ]
        
        financial_table = Table(financial_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(financial_table)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_findings_section(self, report_data):
        """Create findings section"""
        story = []
        
        story.append(Paragraph("Detailed Findings", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        findings_by_category = report_data.get('findings_by_category', {})
        
        # Findings summary table
        if findings_by_category:
            findings_data = [['Category', 'Count']]
            for category, count in findings_by_category.items():
                findings_data.append([category.replace('_', ' ').title(), str(count)])
            
            findings_table = Table(findings_data, colWidths=[2*inch, 1*inch])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ebf3fd')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(findings_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Individual findings details would go here
        story.append(Paragraph("Finding categories represent different types of audit issues identified during the analysis.", 
                              self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_action_priorities_section(self, report_data):
        """Create action priorities section"""
        story = []
        
        story.append(Paragraph("Action Priorities", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        action_priorities = report_data.get('action_priorities', [])
        
        if action_priorities:
            # Action priorities table
            action_data = [['Priority', 'Action', 'Impact', 'Timeline']]
            
            for action in action_priorities:
                action_data.append([
                    action.get('priority', 'Medium').upper(),
                    action.get('action', 'N/A'),
                    action.get('impact', 'N/A'),
                    action.get('timeline', 'N/A')
                ])
            
            action_table = Table(action_data, colWidths=[1*inch, 2.5*inch, 1.5*inch, 1*inch])
            action_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fadbd8')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            
            story.append(action_table)
        else:
            story.append(Paragraph("No specific action priorities identified in this analysis.", 
                                  self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Next steps
        story.append(Paragraph("Recommended Next Steps:", self.styles['CustomSubHeading']))
        
        next_steps = report_data.get('next_steps', [])
        if next_steps:
            for step in next_steps:
                story.append(Paragraph(f"• {step}", self.styles['Normal']))
        else:
            story.append(Paragraph("• Review findings with logistics team", self.styles['Normal']))
            story.append(Paragraph("• Prioritize high-impact opportunities", self.styles['Normal']))
            story.append(Paragraph("• Implement recommended changes", self.styles['Normal']))
            story.append(Paragraph("• Monitor results and adjust strategy", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_invoice_details_section(self, invoice_data):
        """Create invoice details section"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("Invoice Analysis Details", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        # Create invoice summary table
        if isinstance(invoice_data, list) and invoice_data:
            # Multiple invoices
            invoice_summary_data = [['Invoice #', 'Date', 'Carrier', 'Amount', 'Status']]
            
            for invoice in invoice_data[:10]:  # Limit to first 10 for space
                invoice_summary_data.append([
                    str(invoice.get('invoice_number', 'N/A')),
                    str(invoice.get('invoice_date', 'N/A')),
                    str(invoice.get('carrier', 'N/A')),
                    f"${invoice.get('total_amount', 0):,.2f}",
                    str(invoice.get('status', 'Processed'))
                ])
            
            if len(invoice_data) > 10:
                invoice_summary_data.append(['...', f'({len(invoice_data) - 10} more)', '...', '...', '...'])
        
        else:
            # Single invoice or summary
            invoice_summary_data = [
                ['Field', 'Value'],
                ['Total Invoices', str(len(invoice_data) if isinstance(invoice_data, list) else 1)],
                ['Analysis Complete', 'Yes'],
                ['Findings Generated', 'Yes']
            ]
        
        invoice_table = Table(invoice_summary_data)
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#d5f4e6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_appendix_section(self):
        """Create appendix section"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("Appendix", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        # Methodology
        story.append(Paragraph("Methodology", self.styles['CustomSubHeading']))
        story.append(Paragraph(
            "This report was generated using OpenAudit Platform's AI-powered freight audit system. "
            "The analysis includes automated invoice processing, pattern recognition, and industry benchmarking "
            "to identify cost optimization opportunities.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Disclaimer
        story.append(Paragraph("Disclaimer", self.styles['CustomSubHeading']))
        story.append(Paragraph(
            "This analysis is based on information provided and industry standards. "
            "Actual savings may vary based on implementation and market conditions. "
            "Recommendations should be evaluated in context of your specific business requirements.",
            self.styles['Normal']
        ))
        
        return story
    
    def generate_invoice_summary_report(self, invoices_df):
        """Generate invoice summary report"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            
            # Title
            story.append(Paragraph("Invoice Summary Report", self.styles['CustomTitle']))
            story.append(Spacer(1, 0.3*inch))
            
            # Summary statistics
            total_invoices = len(invoices_df)
            total_amount = invoices_df['total_amount'].sum() if 'total_amount' in invoices_df.columns else 0
            avg_amount = invoices_df['total_amount'].mean() if 'total_amount' in invoices_df.columns else 0
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Invoices', f"{total_invoices:,}"],
                ['Total Amount', f"${total_amount:,.2f}"],
                ['Average Amount', f"${avg_amount:,.2f}"],
                ['Report Date', datetime.now().strftime('%Y-%m-%d')]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Detailed invoice list (first 50)
            story.append(Paragraph("Invoice Details", self.styles['CustomHeading']))
            
            if not invoices_df.empty:
                invoice_data = [['ID', 'Invoice #', 'Date', 'Carrier', 'Amount']]
                
                for _, row in invoices_df.head(50).iterrows():
                    invoice_data.append([
                        str(row.get('id', 'N/A')),
                        str(row.get('invoice_number', 'N/A')),
                        str(row.get('invoice_date', 'N/A')),
                        str(row.get('carrier', 'N/A')),
                        f"${row.get('total_amount', 0):,.2f}"
                    ])
                
                if len(invoices_df) > 50:
                    invoice_data.append(['...', f'({len(invoices_df) - 50} more)', '...', '...', '...'])
                
                invoice_table = Table(invoice_data, colWidths=[0.5*inch, 1*inch, 1*inch, 1.5*inch, 1*inch])
                invoice_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(invoice_table)
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            st.error(f"Invoice summary report generation failed: {str(e)}")
            return None
