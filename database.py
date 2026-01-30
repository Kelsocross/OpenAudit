"""
Database models and connection manager for OpenAudit application
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional
import json

Base = declarative_base()

class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    audit_sessions = relationship("AuditSession", back_populates="user")
    contract_reviews = relationship("ContractReview", back_populates="user")

class AuditSession(Base):
    """Audit session model to store audit history"""
    __tablename__ = 'audit_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    total_charges = Column(Float, default=0.0)
    total_savings = Column(Float, default=0.0)
    affected_shipments = Column(Integer, default=0)
    total_shipments = Column(Integer, default=0)
    savings_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # JSON field for storing audit summary
    audit_summary = Column(Text)  # Stores JSON data

    # Relationships
    user = relationship("User", back_populates="audit_sessions")
    findings = relationship("AuditFinding", back_populates="audit_session")

class AuditFinding(Base):
    """Individual audit findings"""
    __tablename__ = 'audit_findings'

    id = Column(Integer, primary_key=True)
    audit_session_id = Column(Integer, ForeignKey('audit_sessions.id'), nullable=False)
    error_type = Column(String(100), nullable=False)
    tracking_number = Column(String(100), nullable=False)
    shipment_date = Column(DateTime)
    carrier = Column(String(50))
    service_type = Column(String(100))
    dispute_reason = Column(Text)
    refund_estimate = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_session = relationship("AuditSession", back_populates="findings")

class AIPromptUsage(Base):
    """Track AI prompt usage per user per month"""
    __tablename__ = 'ai_prompt_usage'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    month = Column(Date, nullable=False)  # First day of the month
    prompt_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")

class ContractReview(Base):
    """Contract review and analysis model"""
    __tablename__ = 'contract_reviews'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    contract_name = Column(String(200), nullable=False)
    carrier = Column(String(50), nullable=False)  # FedEx, UPS, etc.
    contract_type = Column(String(50), default='rate_sheet')  # rate_sheet, master_agreement
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String(300))
    file_type = Column(String(20))  # pdf, xlsx, csv

    # Contract terms extracted
    base_discount_pct = Column(Float)  # Overall discount percentage
    dim_divisor = Column(Integer)  # Dimensional weight divisor
    fuel_surcharge_pct = Column(Float)  # Fuel surcharge percentage
    residential_surcharge = Column(Float)  # Residential delivery surcharge
    delivery_area_surcharge = Column(Float)  # Extended delivery area surcharge

    # Zone-specific rates (stored as JSON)
    zone_rates = Column(JSON)  # Zone-based pricing structure
    service_discounts = Column(JSON)  # Service-specific discount percentages

    # Analysis results
    health_score = Column(String(1))  # A, B, C, D, F
    health_score_numeric = Column(Float)  # 0-100 score
    estimated_lost_savings = Column(Float)  # Annual lost savings estimate
    benchmark_comparison = Column(JSON)  # Detailed comparison data

    # Strategy and recommendations
    negotiation_strategy = Column(Text)  # Generated strategy text
    key_recommendations = Column(JSON)  # Array of recommendation objects

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="contract_reviews")

class ContractBenchmark(Base):
    """Industry benchmark data for contract comparison"""
    __tablename__ = 'contract_benchmarks'

    id = Column(Integer, primary_key=True)
    carrier = Column(String(50), nullable=False)
    company_size = Column(String(20))  # small, medium, large
    industry = Column(String(100))  # retail, manufacturing, etc.

    # Benchmark values (industry best practices)
    best_discount_pct = Column(Float)  # Best achievable discount
    average_discount_pct = Column(Float)  # Industry average
    best_dim_divisor = Column(Integer)  # Best dimensional weight divisor
    standard_fuel_surcharge = Column(Float)  # Standard fuel surcharge
    typical_residential_surcharge = Column(Float)
    typical_delivery_area_surcharge = Column(Float)

    # Zone rate benchmarks (stored as JSON)
    benchmark_zone_rates = Column(JSON)

    # Metadata
    data_source = Column(String(100))  # Where benchmark data came from
    last_updated = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Database connection and session management"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Add connection pool settings and SSL handling
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            connect_args={"sslmode": "prefer"}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get database session"""
        return self.SessionLocal()

    def save_audit_session(self, user_id: int, filename: str, audit_results: dict, findings_df) -> int:
        """Save audit session and findings to database"""
        session = self.get_session()
        try:
            # Create audit session
            audit_session = AuditSession(
                user_id=user_id,
                filename=filename,
                total_charges=audit_results['summary']['total_charges'],
                total_savings=audit_results['summary']['total_savings'],
                affected_shipments=audit_results['summary']['affected_shipments'],
                total_shipments=audit_results['summary']['total_shipments'],
                savings_rate=audit_results['summary']['savings_rate'],
                audit_summary=json.dumps(audit_results['summary'])
            )

            session.add(audit_session)
            session.flush()  # Get the ID

            # Save findings
            if not findings_df.empty:
                for _, row in findings_df.iterrows():
                    finding = AuditFinding(
                        audit_session_id=audit_session.id,
                        error_type=row['Error Type'],
                        tracking_number=str(row['Tracking Number']),
                        shipment_date=datetime.strptime(row['Date'], '%Y-%m-%d') if row['Date'] else None,
                        carrier=str(row.get('Carrier', '')),
                        service_type=str(row.get('Service Type', '')),
                        dispute_reason=str(row['Dispute Reason']),
                        refund_estimate=float(row['Refund Estimate']),
                        notes=str(row.get('Notes', ''))
                    )
                    session.add(finding)

            session.commit()
            return int(audit_session.id)

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_audit_history(self, user_id: int, limit: int = 50):
        """Get audit history for a user"""
        session = self.get_session()
        try:
            audit_sessions = session.query(AuditSession)\
                .filter(AuditSession.user_id == user_id)\
                .order_by(AuditSession.created_at.desc())\
                .limit(limit)\
                .all()

            return audit_sessions
        finally:
            session.close()

    def get_audit_session_details(self, session_id: int, user_id: int):
        """Get detailed audit session with findings"""
        session = self.get_session()
        try:
            audit_session = session.query(AuditSession)\
                .filter(AuditSession.id == session_id, AuditSession.user_id == user_id)\
                .first()

            if not audit_session:
                return None

            findings = session.query(AuditFinding)\
                .filter(AuditFinding.audit_session_id == session_id)\
                .all()

            return {
                'session': audit_session,
                'findings': findings
            }
        finally:
            session.close()

    def create_or_get_user(self, email: str, name: str, company_name: Optional[str] = None):
        """Create or get user by email"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.email == email).first()

            if not user:
                user = User(
                    email=email,
                    name=name,
                    company_name=company_name
                )
                session.add(user)
                session.commit()
            else:
                # Update user info if provided
                if name:
                    user.name = name
                if company_name:
                    user.company_name = company_name
                user.updated_at = datetime.utcnow()
                session.commit()

            return user
        finally:
            session.close()

    def get_user_statistics(self, user_id: int):
        """Get user statistics for dashboard"""
        session = self.get_session()
        try:
            from sqlalchemy import func

            stats = session.query(
                func.count(AuditSession.id).label('total_audits'),
                func.sum(AuditSession.total_charges).label('total_charges_audited'),
                func.sum(AuditSession.total_savings).label('total_savings_identified'),
                func.sum(AuditSession.affected_shipments).label('total_affected_shipments'),
                func.sum(AuditSession.total_shipments).label('total_shipments_processed')
            ).filter(AuditSession.user_id == user_id).first()

            if stats:
                return {
                    'total_audits': int(stats.total_audits) if stats.total_audits else 0,
                    'total_charges_audited': float(stats.total_charges_audited) if stats.total_charges_audited else 0.0,
                    'total_savings_identified': float(stats.total_savings_identified) if stats.total_savings_identified else 0.0,
                    'total_affected_shipments': int(stats.total_affected_shipments) if stats.total_affected_shipments else 0,
                    'total_shipments_processed': int(stats.total_shipments_processed) if stats.total_shipments_processed else 0
                }
            else:
                return {
                    'total_audits': 0,
                    'total_charges_audited': 0.0,
                    'total_savings_identified': 0.0,
                    'total_affected_shipments': 0,
                    'total_shipments_processed': 0
                }
        finally:
            session.close()

# Global database manager instance
db_manager = None

def get_db_manager():
    """Get or create database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        db_manager.create_tables()
    return db_manager
    