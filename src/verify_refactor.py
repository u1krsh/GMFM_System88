
import os
import sys
from pathlib import Path
import sqlite3
from datetime import date

# Add src to path
sys.path.append(str(Path("d:/COMPRO/GMFM/GMFM_System88/src")))

try:
    from gmfm_app.data.models import Student, Session
    from gmfm_app.data.database import init_db, DatabaseContext
    from gmfm_app.data.repositories import StudentRepository
    print("[OK] Imports successful")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

def test_migration_and_crud():
    print("Testing DB Migration and CRUD...")
    
    # Use a test database
    test_db_path = Path("test_students.db")
    if test_db_path.exists():
        os.remove(test_db_path)
        
    # Initialize DB (should create new 'students' table)
    init_db(test_db_path)
    print("[OK] init_db ran successfully")
    
    context = DatabaseContext(test_db_path)
    repo = StudentRepository(context)
    
    # Create Student
    student = Student(given_name="John", family_name="Doe", dob=date(2015, 1, 1), identifier="123")
    repo.create_student(student)
    print("[OK] Student created")
    
    # Read Student
    s = repo.get_student(1)
    if s and s.given_name == "John":
        print("[OK] Student retrieved")
    else:
        print("[FAIL] Student retrieval failed")
        
    # Verify Table Names
    with sqlite3.connect(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        if "students" in tables and "patients" not in tables:
             print("[OK] 'students' table exists, 'patients' does not")
        else:
             print(f"[FAIL] Table verification failed. Tables: {tables}")
             
    # Cleanup
    if test_db_path.exists():
        try:
            os.remove(test_db_path)
             # Also try to remove wal files if they exist
            if Path("test_students.db-wal").exists(): os.remove("test_students.db-wal")
            if Path("test_students.db-shm").exists(): os.remove("test_students.db-shm")
        except:
            pass
    print("[OK] Cleanup done")

if __name__ == "__main__":
    test_migration_and_crud()
