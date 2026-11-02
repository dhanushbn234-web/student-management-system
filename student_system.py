import os
import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    """
    Creates a database connection to the SQLite database specified by db_file.
    If the file does not exist, SQLite will automatically create it.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(f"Database Connection Error: {e}")
    return conn

def create_table(conn):
    """
    Creates the students table within the connected database if it does not
    already exist.
    """
    sql_create_students_table = """
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        grade TEXT,
        email TEXT
    );
    """
    sql_create_attendance_table = """
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        class_id TEXT NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('present', 'absent', 'late', 'excused')),
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, attendance_date, class_id),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql_create_students_table)
        cursor.execute(sql_create_attendance_table)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_date_class ON attendance(attendance_date, class_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_student ON attendance(student_id);")
        conn.commit()
    except Error as e:
        print(f"Error creating table: {e}")

def add_student(conn):
    """
    Prompts the user for details and inserts a new student record into the database.
    Includes validation for numeric values and handle primary key conflicts.
    """
    print("\n--- Add New Student ---")
    student_id = input("Enter Student ID (Unique): ").strip()
    if not student_id:
        print("Error: Student ID cannot be empty.")
        return

    name = input("Enter Student Name: ").strip()
    if not name:
        print("Error: Student Name cannot be empty.")
        return

    # Validate age input
    try:
        age = int(input("Enter Age: ").strip())
        if age <= 0:
            print("Error: Age must be a positive number.")
            return
    except ValueError:
        print("Error: Age must be a valid integer.")
        return

    grade = input("Enter Grade/Class (e.g., Grade 10, A+): ").strip()
    email = input("Enter Email Address: ").strip()

    sql_insert_student = """
    INSERT INTO students (id, name, age, grade, email)
    VALUES (?, ?, ?, ?, ?);
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql_insert_student, (student_id, name, age, grade, email))
        conn.commit()
        print(f"Success: Student record for '{name}' added successfully!")
    except sqlite3.IntegrityError:
        print(f"Error: A student with ID '{student_id}' already exists.")
    except Error as e:
        print(f"Database Error: {e}")

def view_all_students(conn):
    """
    Fetches and prints all student records from the database in a formatted text layout.
    """
    print("\n--- View All Students ---")
    sql_select_all = "SELECT * FROM students;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select_all)
        rows = cursor.fetchall()

        if not rows:
            print("No student records found in the database.")
            return

        # Header formatting
        print(f"{'ID':<10} | {'Name':<20} | {'Age':<5} | {'Grade':<10} | {'Email':<25}")
        print("-" * 78)
        for row in rows:
            print(f"{row[0]:<10} | {row[1]:<20} | {row[2]:<5} | {row[3]:<10} | {row[4]:<25}")
    except Error as e:
        print(f"Database Error: {e}")

def search_student(conn):
    """
    Searches for student records by unique Student ID or Student Name.
    Supports partial name matching and displays all matching results.
    """
    print("\n--- Search Student ---")
    search_query = input("Enter Student ID or Name to search: ").strip()
    
    if not search_query:
        print("Search query cannot be empty.")
        return

    sql_search = """
    SELECT id, name, age, grade, email 
    FROM students 
    WHERE id = ? OR LOWER(name) LIKE ?;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql_search, (search_query, f"%{search_query.lower()}%"))
        rows = cursor.fetchall()

        if rows:
            print(f"\nFound {len(rows)} matching record(s):")
            print("-" * 80)
            print(f"{'ID':<12} | {'Name':<22} | {'Age':<5} | {'Grade':<14} | {'Email':<25}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:<12} | {row[1]:<22} | {str(row[2]):<5} | {str(row[3]):<14} | {str(row[4] or 'N/A'):<25}")
            print("-" * 80)
        else:
            print(f"No student record found matching '{search_query}'.")
    except Error as e:
        print(f"Database Error: {e}")

def update_student(conn):
    """
    Modifies an existing student record. Allows updating specific fields while leaving
    others unchanged if input is skipped.
    """
    print("\n--- Update Student Details ---")
    student_id = input("Enter Student ID to update: ").strip()
    
    # Check if the student exists first
    sql_check = "SELECT * FROM students WHERE id = ?;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (student_id,))
        current_data = cursor.fetchone()

        if not current_data:
            print(f"No student record found with ID '{student_id}'.")
            return

        print(f"\nModifying details for {current_data[1]} (Leave blank to keep current value):")
        
        new_name = input(f"New Name [{current_data[1]}]: ").strip() or current_data[1]
        
        age_input = input(f"New Age [{current_data[2]}]: ").strip()
        if age_input:
            try:
                new_age = int(age_input)
                if new_age <= 0:
                    print("Error: Age must be positive. Update canceled.")
                    return
            except ValueError:
                print("Error: Age must be a valid integer. Update canceled.")
                return
        else:
            new_age = current_data[2]

        new_grade = input(f"New Grade [{current_data[3]}]: ").strip() or current_data[3]
        new_email = input(f"New Email [{current_data[4]}]: ").strip() or current_data[4]

        sql_update = """
        UPDATE students
        SET name = ?, age = ?, grade = ?, email = ?
        WHERE id = ?;
        """
        cursor.execute(sql_update, (new_name, new_age, new_grade, new_email, student_id))
        conn.commit()
        print("Success: Student record updated successfully!")
    except Error as e:
        print(f"Database Error: {e}")

def delete_student(conn):
    """
    Removes a student record completely from the database using their Student ID.
    """
    print("\n--- Delete Student Record ---")
    student_id = input("Enter Student ID to delete: ").strip()
    
    # Verify existence before trying to delete
    sql_check = "SELECT name FROM students WHERE id = ?;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (student_id,))
        row = cursor.fetchone()

        if not row:
            print(f"No student record found with ID '{student_id}'.")
            return

        confirm = input(f"Are you sure you want to permanently delete student '{row[0]}'? (yes/no): ").strip().lower()
        if confirm == 'yes':
            sql_delete = "DELETE FROM students WHERE id = ?;"
            cursor.execute(sql_delete, (student_id,))
            conn.commit()
            print("Success: Student record deleted permanently.")
        else:
            print("Deletion canceled.")
    except Error as e:
        print(f"Database Error: {e}")

def main():
    """
    Main execution loop managing user interaction and database session longevity.
    """
    database_name = "student_records.db"
    
    # Establish connection and set up schema
    conn = create_connection(database_name)
    if conn is not None:
        create_table(conn)
    else:
        print("Critical Error: Database initialization failed. Exiting application.")
        return

    while True:
        print("\n=================================")
        print("    STUDENT MANAGEMENT SYSTEM    ")
        print("=================================")
        print("1. Add Student Record")
        print("2. View All Students")
        print("3. Search Student by ID or Name")
        print("4. Update Student Details")
        print("5. Delete Student Record")
        print("6. Exit Application")
        print("=================================")
        
        choice = input("Select an option (1-6): ").strip()
        
        if choice == '1':
            add_student(conn)
        elif choice == '2':
            view_all_students(conn)
        elif choice == '3':
            search_student(conn)
        elif choice == '4':
            update_student(conn)
        elif choice == '5':
            delete_student(conn)
        elif choice == '6':
            print("\nClosing database connection... Goodbye!")
            conn.close()
            break
        else:
            print("Invalid Choice: Please input a number from 1 to 6.")

if __name__ == "__main__":
    main()
