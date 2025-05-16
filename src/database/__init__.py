"""
Database connection utilities.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_engine(config):
    """
    Create a database engine from config.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        SQLAlchemy engine
    """
    db_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(db_url)

def get_session(engine):
    """
    Create a database session.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        SQLAlchemy session
    """
    Session = sessionmaker(bind=engine)
    return Session()