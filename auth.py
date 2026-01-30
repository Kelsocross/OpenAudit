import streamlit as st

def get_allowed_pages():
    """Get list of allowed pages - all pages available"""
    return [
        "Upload & Audit",
        "Refund Recovery", 
        "Q&A",
        "Dashboard",
        "Contract Review",
        "About OA"
    ]

def is_free_trial_user():
    """Check if user is on free trial - always False since all have full access"""
    return False

def check_page_access(page):
    """Check if user can access a page - always True"""
    return True

def get_current_user():
    """Get current user info"""
    return st.session_state.get('user', {
        'email': 'user@example.com',
        'name': 'User',
        'company_name': 'Your Company',
        'tier': 'Full'
    })

def get_auth_manager():
    """Get auth manager - returns the module itself for compatibility"""
    import sys
    return sys.modules[__name__]
