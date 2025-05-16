"""
PostgreSQL database models for the Clinical Trial & Corporate Disclosure Extraction Pipeline.
"""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class ClinicalStudy(Base):
    """Model for the clinical_study table."""
    
    __tablename__ = 'clinical_study'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    nct_identifier = Column(String(20), unique=True, index=True)
    indication = Column(String(200))
    intervention = Column(String(500))
    
    # Intervention details
    interventional_drug_name = Column(String(200))
    interventional_drug_dose = Column(String(100))
    interventional_drug_frequency = Column(String(100))
    interventional_drug_formulation = Column(String(100))
    
    # Study arms
    intervention_arms = Column(Integer)
    placebo_arms = Column(Integer)
    
    # Participant information
    number_of_participants = Column(Integer)
    average_age = Column(Float)
    min_age = Column(Integer)
    max_age = Column(Integer)
    
    # Phase
    phase = Column(String(50))
    
    # Sponsor
    sponsor = Column(String(200))
    
    # Relationships
    endpoints = relationship("Endpoint", back_populates="clinical_study")
    baseline_measures = relationship("BaselineMeasure", back_populates="clinical_study")
    
    def __repr__(self):
        return f"<ClinicalStudy(nct_identifier='{self.nct_identifier}', title='{self.title}')>"


class Endpoint(Base):
    """Model for the endpoints table."""
    
    __tablename__ = 'endpoints'
    
    id = Column(Integer, primary_key=True)
    clinical_study_id = Column(Integer, ForeignKey('clinical_study.id'))
    
    name = Column(String(500))  # Increased from 200 to 500
    description = Column(Text)
    timepoint = Column(String(100))
    arm = Column(String(50))  # 'intervention' or 'placebo'
    
    average_value = Column(Float, nullable=True)
    upper_end = Column(Float, nullable=True)
    lower_end = Column(Float, nullable=True)
    statistical_significance = Column(String(100), nullable=True)
    
    # Relationship
    clinical_study = relationship("ClinicalStudy", back_populates="endpoints")
    
    def __repr__(self):
        return f"<Endpoint(name='{self.name}', arm='{self.arm}')>"


class BaselineMeasure(Base):
    """Model for the baseline_measures table."""
    
    __tablename__ = 'baseline_measures'
    
    id = Column(Integer, primary_key=True)
    clinical_study_id = Column(Integer, ForeignKey('clinical_study.id'))
    
    name = Column(String(500))  # Increased from 200 to 500
    description = Column(Text)
    arm = Column(String(50))  # 'intervention' or 'placebo'
    
    average_value = Column(Float, nullable=True)
    upper_end = Column(Float, nullable=True)
    lower_end = Column(Float, nullable=True)
    
    # Relationship
    clinical_study = relationship("ClinicalStudy", back_populates="baseline_measures")
    
    def __repr__(self):
        return f"<BaselineMeasure(name='{self.name}', arm='{self.arm}')>"


class SECFiling(Base):
    """Model for the sec_filings table."""
    
    __tablename__ = 'sec_filings'
    
    id = Column(Integer, primary_key=True)
    clinical_study_id = Column(Integer, ForeignKey('clinical_study.id'))
    
    cik = Column(String(20))
    accession_number = Column(String(100))  # Increased from 50 to 100
    filing_date = Column(String(500))       # Increased from 20 to 500
    form_type = Column(String(20))          # Increased from 10 to 20
    
    total_mentions = Column(Integer)
    name_mentions = Column(Integer)
    nct_mentions = Column(Integer)
    
    # Context excerpts as JSON
    contexts = Column(JSON)
    
    # Relationship
    clinical_study = relationship("ClinicalStudy")
    
    def __repr__(self):
        return f"<SECFiling(form_type='{self.form_type}', filing_date='{self.filing_date}')>"


class Publication(Base):
    """Model for the publications table."""
    
    __tablename__ = 'publications'
    
    id = Column(Integer, primary_key=True)
    clinical_study_id = Column(Integer, ForeignKey('clinical_study.id'))
    
    title = Column(String(1000))  # Increased from 500 to 1000
    link = Column(String(2000))   # Increased from 1000 to 2000
    snippet = Column(Text)
    source = Column(String(100))  # 'scientific_publication' or 'company_presentation'
    
    # Additional fields
    authors = Column(String(1000), nullable=True)  # Increased from 500 to 1000
    journal = Column(String(500), nullable=True)   # Increased from 200 to 500
    local_path = Column(String(2000), nullable=True)  # Increased from 1000 to 2000
    text_sample = Column(Text, nullable=True)
    
    # Relationship
    clinical_study = relationship("ClinicalStudy")
    
    def __repr__(self):
        return f"<Publication(title='{self.title}', source='{self.source}')>"