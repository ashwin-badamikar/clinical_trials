"""
Test PostgreSQL connection directly.
"""
import os
import sys
import json
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sqlalchemy import create_engine, text

def main():
    """Test PostgreSQL connection."""
    # Load config
    config_path = os.path.join(current_dir, "config", "config.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    db_config = config["database"]
    
    # Create connection string
    connection_string = (
        f"postgresql://{db_config.get('user')}:{db_config.get('password')}"
        f"@{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}"
    )
    
    # Try to connect
    try:
        print("Attempting to connect to PostgreSQL...")
        engine = create_engine(connection_string)
        
        # Test connection with simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"Connected to PostgreSQL: {version}")
            
            # Check if tables exist
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname = 'public'
            """))
            tables = [row[0] for row in result]
            print(f"Tables in database: {tables}")
            
            # Check trial count
            if 'clinical_study' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM clinical_study"))
                count = result.scalar()
                print(f"Found {count} clinical trials in the database")
        
        print("PostgreSQL connection test successful!")
        
    except Exception as e:
        print(f"PostgreSQL connection failed: {str(e)}")

if __name__ == "__main__":
    main()