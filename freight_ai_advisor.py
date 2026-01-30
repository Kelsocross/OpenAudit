"""
OpenAudit AI Freight Advisor with pre-loaded Q&As
"""
import streamlit as st

class FreightAIAdvisor:
    """AI-powered freight advisor with pre-loaded Q&As"""
    
    def __init__(self):
        self.common_qas = [
            {
                "question": "What are demand charges?",
                "answer": "FedEx demand surcharges (also called demand charges) are extra fees applied during periods of unusually high shipping volume—think peak holiday seasons or times when their network is stretched thin. These charges help FedEx manage operational strain and maintain service reliability when demand spikes."
            },
            {
                "question": "How can I reduce freight costs for the size boxes we use?",
                "answer": "Focus on right-sizing your packaging to minimize dimensional weight charges. Use the smallest box possible, consider custom packaging for frequently shipped items, and review the DIM divisor (139 for FedEx/UPS). Switching from oversized boxes to properly sized ones can save 20-40% on shipping costs."
            },
            {
                "question": "How do dimensional weight calculations work?",
                "answer": "Dimensional weight = (Length × Width × Height) ÷ 139. Carriers bill whichever is higher: actual weight or dimensional weight. A 12×12×12 box has a dim weight of 12.4 lbs. If your actual package weighs 5 lbs, you'll be billed for 12.4 lbs."
            },
            {
                "question": "When should I dispute a late delivery charge?",
                "answer": "Dispute when: packages arrive after the service commitment (next day, 2-day, ground), weather wasn't a factor, and you have delivery confirmation showing the delay. FedEx/UPS typically offer full refunds for service failures. Keep tracking records as proof."
            },
            {
                "question": "What are the most common billing errors carriers make?",
                "answer": "Top errors include: incorrect dimensional weight calculations, duplicate charges, wrong zone assignments, unauthorized surcharges, and incorrect service levels. These account for 2-5% of total shipping costs and are often recoverable through auditing."
            },
            {
                "question": "What's the best packaging strategy to minimize dimensional weight?",
                "answer": "Use cube-shaped boxes when possible, eliminate void fill where safe, consider custom packaging for regular shipments, and review package dimensions regularly. A 1-inch reduction in any dimension can significantly impact costs on high-volume lanes."
            },
            {
                "question": "Why do I see 'Address Correction' charges on my invoices?",
                "answer": "Address correction fees ($10-15) occur when carriers modify incorrect addresses. Prevent these by using address validation tools, maintaining accurate customer databases, and training staff on proper address formatting. These fees are often disputable if addresses were correct."
            },
            {
                "question": "What shipping zones mean and why they matter for costs?",
                "answer": "Zones (1-8) determine shipping costs based on distance from origin to destination. Zone 2 might cost $8 while Zone 7 costs $25 for the same package. Verify zone assignments are correct and consider regional distribution centers to reduce average zones."
            },
            {
                "question": "How do I handle damaged package claims with carriers?",
                "answer": "Report damage within carrier time limits (typically 24-48 hours), document with photos, file claims promptly, and maintain proper packaging standards. Carriers are liable for damage in transit if packages were properly packed and declared."
            },
            {
                "question": "What documentation do I need for successful shipping disputes?",
                "answer": "Keep delivery confirmations, tracking histories, service receipts, photos of packages/damage, and correspondence with carriers. Document everything promptly and maintain organized records. Good documentation is crucial for successful claim recoveries."
            }
        ]
    
    def get_common_qas(self):
        """Get list of common Q&As"""
        return self.common_qas

def get_freight_ai_advisor():
    """Get freight AI advisor instance (singleton pattern)"""
    if 'freight_ai_advisor' not in st.session_state:
        st.session_state.freight_ai_advisor = FreightAIAdvisor()
    return st.session_state.freight_ai_advisor
