"""
Database configuration and session management
SQLite database with SQLAlchemy ORM
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from ..core.config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_migrations():
    """
    Run database migrations to add new columns to existing tables.
    This handles adding columns that were added to models after initial DB creation.
    """
    from sqlalchemy import text, inspect
    
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        
        # Check if documents table exists
        if 'documents' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('documents')]
            
            # Add ml_predicted_sensitivity column if missing
            if 'ml_predicted_sensitivity' not in existing_columns:
                print("Adding ml_predicted_sensitivity column to documents table...")
                db.execute(text("ALTER TABLE documents ADD COLUMN ml_predicted_sensitivity VARCHAR(20)"))
            
            # Add ml_confidence column if missing
            if 'ml_confidence' not in existing_columns:
                print("Adding ml_confidence column to documents table...")
                db.execute(text("ALTER TABLE documents ADD COLUMN ml_confidence FLOAT"))
            
            # Add sensitivity_mismatch column if missing
            if 'sensitivity_mismatch' not in existing_columns:
                print("Adding sensitivity_mismatch column to documents table...")
                db.execute(text("ALTER TABLE documents ADD COLUMN sensitivity_mismatch BOOLEAN DEFAULT 0"))
            
            db.commit()
            print("Database migrations completed successfully")
        
    except Exception as e:
        print(f"Migration error (may be ignorable): {e}")
        db.rollback()
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    """
    from . import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
    
    # Run migrations to add any new columns
    run_migrations()
    
    # Seed default users
    seed_default_users()


def seed_default_users():
    """
    Create default users for testing if they don't exist
    """
    from .models import User, UserRole
    from ..core.security import get_password_hash
    
    db = SessionLocal()
    try:
        # Check if users already exist
        existing = db.query(User).first()
        if existing:
            print("Users already exist, skipping seeding")
            return
        
        # Default users matching README demo credentials
        default_users = [
            {
                "user_id": "USR001",
                "username": "jsmith",
                "email": "jsmith@company.com",
                "full_name": "John Smith",
                "hashed_password": get_password_hash("password123"),
                "department": "FINANCE",
                "role": UserRole.USER,
                "is_active": True,
            },
            {
                "user_id": "USR002",
                "username": "mjohnson",
                "email": "mjohnson@company.com",
                "full_name": "Mary Johnson",
                "hashed_password": get_password_hash("password123"),
                "department": "HR",
                "role": UserRole.USER,
                "is_active": True,
            },
            {
                "user_id": "USR003",
                "username": "miketyson",
                "email": "miketyson@company.com",
                "full_name": "Mike Tyson",
                "hashed_password": get_password_hash("password123"),
                "department": "LEGAL",
                "role": UserRole.USER,
                "is_active": True,
            },
            {
                "user_id": "USR004",
                "username": "sundarpichai",
                "email": "sundarpichai@company.com",
                "full_name": "Sundar Pichai",
                "hashed_password": get_password_hash("password123"),
                "department": "IT",
                "role": UserRole.USER,
                "is_active": True,
            },
            {
                "user_id": "USR005",
                "username": "analyst",
                "email": "analyst@company.com",
                "full_name": "Security Analyst",
                "hashed_password": get_password_hash("analyst123"),
                "department": "IT",
                "role": UserRole.ANALYST,
                "is_active": True,
            },
            {
                "user_id": "USR006",
                "username": "admin",
                "email": "admin@company.com",
                "full_name": "System Administrator",
                "hashed_password": get_password_hash("admin123"),
                "department": "IT",
                "role": UserRole.ADMIN,
                "is_active": True,
            },
        ]
        
        for user_data in default_users:
            user = User(**user_data)
            db.add(user)
        
        db.commit()
        print(f"Created {len(default_users)} default users")
    except Exception as e:
        db.rollback()
        print(f"Error seeding users: {e}")
    finally:
        db.close()
    
    # Seed documents after users
    seed_default_documents()


def seed_default_documents():
    """
    Create default documents by scanning the storage folder structure.
    Documents are loaded from: backend/storage/documents/{DEPARTMENT}/
    """
    from .models import Document, SensitivityLevel
    from pathlib import Path
    import hashlib
    
    db = SessionLocal()
    try:
        # Check if documents already exist
        existing = db.query(Document).first()
        if existing:
            print("Documents already exist, skipping seeding")
            return
        
        # Document storage path
        storage_dir = Path(__file__).parent.parent / "storage" / "documents"
        
        # Sensitivity mapping based on keywords in filename
        def get_sensitivity(filename: str, department: str) -> SensitivityLevel:
            filename_lower = filename.lower()
            if any(word in filename_lower for word in ['salary', 'financial', 'budget', 'nda', 'merger', 'architecture', 'network']):
                return SensitivityLevel.CONFIDENTIAL
            elif any(word in filename_lower for word in ['public', 'announcement', 'api']):
                return SensitivityLevel.PUBLIC
            return SensitivityLevel.INTERNAL
        
        documents_created = 0
        doc_counter = 1
        
        # Scan each department folder
        for department in ['HR', 'FINANCE', 'LEGAL', 'IT']:
            dept_folder = storage_dir / department
            if not dept_folder.exists():
                dept_folder.mkdir(parents=True, exist_ok=True)
                continue
            
            # Scan for document files
            for file_path in dept_folder.glob("*.txt"):
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Extract original filename from the stored filename
                    # Format: DOC001_filename.ext.txt -> filename.ext
                    stored_name = file_path.stem  # Remove .txt
                    if '_' in stored_name:
                        parts = stored_name.split('_', 1)
                        original_filename = parts[1] if len(parts) > 1 else stored_name
                    else:
                        original_filename = stored_name
                    
                    # Generate document ID
                    doc_id = f"DOC{doc_counter:03d}"
                    
                    # Calculate hash
                    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                    
                    # Get file size
                    file_size = len(content.encode('utf-8'))
                    
                    # Create preview (first 200 chars)
                    content_preview = content[:200].replace('\n', ' ').strip() + "..."
                    
                    doc = Document(
                        document_id=doc_id,
                        filename=original_filename,
                        filepath=f"/documents/{department.lower()}/{original_filename}",
                        department=department,
                        sensitivity=get_sensitivity(original_filename, department),
                        original_hash=content_hash,
                        current_hash=content_hash,
                        file_size_bytes=file_size,
                        content_preview=content_preview,
                        full_content=content,
                        original_content=content,
                    )
                    db.add(doc)
                    documents_created += 1
                    doc_counter += 1
                    
                except Exception as e:
                    print(f"Error loading document {file_path}: {e}")
                    continue
        
        db.commit()
        print(f"Created {documents_created} documents from storage folder")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding documents: {e}")
    finally:
        db.close()


def drop_db():
    """
    Drop all database tables (use with caution)
    """
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped")
