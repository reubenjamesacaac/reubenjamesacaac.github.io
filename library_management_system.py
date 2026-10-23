"""
LIBRARY MANAGEMENT SYSTEM
Python console application for VS Code.

Features:
- Librarian login
- Add, update, and delete book records
- Register students with 4-digit PINs
- Search books by title or author
- Borrow up to 3 books for 7 days
- Return books and calculate overdue fines (PHP 5 per day)
- View overdue report and transaction history
- Save records in library_data.json automatically

Demo librarian password: admin123
Run with: python library_management_system.py
"""

import json
import hashlib
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).with_name("library_data.json")
LIBRARIAN_PASSWORD = "admin123"  # Change this before using outside a class demo.
FINE_PER_DAY = 5.00
LOAN_DAYS = 7
MAX_BOOKS_PER_STUDENT = 3


def hash_pin(pin):
    """Return a SHA-256 hash of a student's PIN."""
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def load_data():
    """Load saved records, or create a starter data file if none exists."""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            for key in ("books", "students", "transactions"):
                data.setdefault(key, [])
            return data
        except (json.JSONDecodeError, OSError):
            print("Warning: The data file could not be read. Starting with empty records.")

    data = {"books": [], "students": [], "transactions": []}
    save_data(data)
    return data


def save_data(data):
    """Write all records to the local JSON file."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def ask_text(prompt):
    """Ask until the user enters non-empty text."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field cannot be empty. Please try again.")


def ask_int(prompt, minimum=None, maximum=None):
    """Ask for a whole number within the allowed range."""
    while True:
        value = input(prompt).strip()
        try:
            number = int(value)
            if minimum is not None and number < minimum:
                print(f"Enter a number that is at least {minimum}.")
                continue
            if maximum is not None and number > maximum:
                print(f"Enter a number no greater than {maximum}.")
                continue
            return number
        except ValueError:
            print("Please enter a valid whole number.")


def find_book(data, book_id):
    return next((book for book in data["books"] if book["book_id"] == book_id), None)


def find_student(data, student_id):
    return next((student for student in data["students"]
                 if student["student_id"].lower() == student_id.lower()), None)


def active_loans(data, student_id=None):
    loans = [txn for txn in data["transactions"] if txn["return_date"] is None]
    if student_id is not None:
        loans = [txn for txn in loans if txn["student_id"].lower() == student_id.lower()]
    return loans


def is_overdue(txn):
    return date.fromisoformat(txn["due_date"]) < date.today() and txn["return_date"] is None


def compute_fine(due_date_text, returned_on):
    due_date = date.fromisoformat(due_date_text)
    overdue_days = max(0, (returned_on - due_date).days)
    return overdue_days * FINE_PER_DAY


def print_books(books):
    if not books:
        print("No books found.")
        return
    print("-" * 88)
    print(f"{'ID':<6} {'TITLE':<32} {'AUTHOR':<25} {'AVAILABLE/TOTAL':<16}")
    print("-" * 88)
    for book in books:
        title = book["title"][:30]
        author = book["author"][:23]
        print(f"{book['book_id']:<6} {title:<32} {author:<25} "
              f"{book['available']}/{book['copies']:<14}")
    print("-" * 88)


def print_student_loans(data, student_id):
    loans = active_loans(data, student_id)
    if not loans:
        print("You have no books currently borrowed.")
        return
    print("\nYour current loans:")
    for txn in loans:
        book = find_book(data, txn["book_id"])
        title = book["title"] if book else "Unknown book"
        status = "OVERDUE" if is_overdue(txn) else "Borrowed"
        print(f"Book ID {txn['book_id']} | {title} | Due: {txn['due_date']} | {status}")


def add_book(data):
    print("\n--- ADD BOOK ---")
    title = ask_text("Book title: ")
    author = ask_text("Author: ")

    for book in data["books"]:
        if book["title"].casefold() == title.casefold() and book["author"].casefold() == author.casefold():
            print("That title and author already exist. Use Update Book Copies instead.")
            return

    copies = ask_int("Number of copies: ", minimum=1)
    new_id = max((book["book_id"] for book in data["books"]), default=0) + 1
    data["books"].append({
        "book_id": new_id, "title": title, "author": author,
        "copies": copies, "available": copies
    })
    save_data(data)
    print(f"Book added. New Book ID: {new_id}")


def update_book(data):
    print_books(data["books"])
    book_id = ask_int("Enter Book ID to update: ", minimum=1)
    book = find_book(data, book_id)
    if not book:
        print("Book ID not found.")
        return

    borrowed_count = book["copies"] - book["available"]
    print(f"Current total copies: {book['copies']} | Currently borrowed: {borrowed_count}")
    new_total = ask_int("New TOTAL number of copies: ", minimum=borrowed_count)
    book["copies"] = new_total
    book["available"] = new_total - borrowed_count
    save_data(data)
    print("Book record updated.")


def delete_book(data):
    print_books(data["books"])
    book_id = ask_int("Enter Book ID to delete: ", minimum=1)
    book = find_book(data, book_id)
    if not book:
        print("Book ID not found.")
        return
    if book["available"] != book["copies"]:
        print("Cannot delete this book while one or more copies are borrowed.")
        return
    confirm = input(f"Delete '{book['title']}'? Type YES to confirm: ").strip()
    if confirm == "YES":
        data["books"].remove(book)
        save_data(data)
        print("Book deleted.")
    else:
        print("Delete cancelled.")


def register_student(data):
    print("\n--- REGISTER STUDENT ---")
    student_id = ask_text("Student ID: ")
    if find_student(data, student_id):
        print("That Student ID is already registered.")
        return

    name = ask_text("Full name: ")
    while True:
        pin = input("Create a 4-digit PIN: ").strip()
        if len(pin) == 4 and pin.isdigit():
            break
        print("PIN must contain exactly four digits.")

    data["students"].append({
        "student_id": student_id,
        "name": name,
        "pin_hash": hash_pin(pin)
    })
    save_data(data)
    print(f"Student {name} registered successfully.")


def search_books(data):
    keyword = ask_text("Enter a title or author keyword: ").casefold()
    matches = [book for book in data["books"]
               if keyword in book["title"].casefold()
               or keyword in book["author"].casefold()]
    print_books(matches)
    for book in matches:
        if book["available"] == 0:
            print(f"Notice: '{book['title']}' is currently unavailable.")


def borrow_book(data, student_id):
    loans = active_loans(data, student_id)
    if len(loans) >= MAX_BOOKS_PER_STUDENT:
        print("You cannot borrow more than three books at a time.")
        return
    if any(is_overdue(txn) for txn in loans):
        print("Please return your overdue book(s) before borrowing another.")
        return

    search_books(data)
    book_id = ask_int("Enter the Book ID you want to borrow: ", minimum=1)
    book = find_book(data, book_id)
    if not book:
        print("Book ID not found.")
        return
    if book["available"] < 1:
        print("No copies of this book are currently available.")
        return
    if any(txn["book_id"] == book_id for txn in loans):
        print("You already have this book checked out.")
        return

    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)
    txn_id = max((txn["transaction_id"] for txn in data["transactions"]), default=0) + 1
    data["transactions"].append({
        "transaction_id": txn_id,
        "student_id": student_id,
        "book_id": book_id,
        "borrow_date": today.isoformat(),
        "due_date": due.isoformat(),
        "return_date": None,
        "fine": 0.0
    })
    book["available"] -= 1
    save_data(data)
    print(f"Borrow successful! Due date: {due.isoformat()} (7 days from today).")


def return_book(data, student_id=None):
    loans = active_loans(data, student_id)
    if not loans:
        print("There are no books to return for this account.")
        return

    print("\n--- BOOKS TO RETURN ---")
    for txn in loans:
        book = find_book(data, txn["book_id"])
        title = book["title"] if book else "Unknown book"
        print(f"Transaction {txn['transaction_id']} | Book ID {txn['book_id']} | "
              f"{title} | Student ID {txn['student_id']} | Due {txn['due_date']}")

    txn_id = ask_int("Enter Transaction ID to return: ", minimum=1)
    txn = next((item for item in loans if item["transaction_id"] == txn_id), None)
    if not txn:
        print("That active transaction was not found.")
        return

    today = date.today()
    txn["return_date"] = today.isoformat()
    txn["fine"] = compute_fine(txn["due_date"], today)
    book = find_book(data, txn["book_id"])
    if book:
        book["available"] = min(book["copies"], book["available"] + 1)
    save_data(data)
    print("Book returned successfully.")
    print(f"Overdue fine: PHP {txn['fine']:.2f}")


def show_overdue_report(data):
    overdue = [txn for txn in active_loans(data) if is_overdue(txn)]
    if not overdue:
        print("There are no overdue books.")
        return
    print("\n--- OVERDUE REPORT ---")
    for txn in overdue:
        book = find_book(data, txn["book_id"])
        student = find_student(data, txn["student_id"])
        days_late = (date.today() - date.fromisoformat(txn["due_date"])).days
        print(f"Transaction {txn['transaction_id']} | "
              f"{book['title'] if book else 'Unknown book'} | "
              f"{student['name'] if student else txn['student_id']} | "
              f"Due {txn['due_date']} | {days_late} day(s) late | "
              f"Estimated fine PHP {days_late * FINE_PER_DAY:.2f}")


def show_transactions(data):
    if not data["transactions"]:
        print("No transaction records yet.")
        return
    print("\n--- TRANSACTION HISTORY ---")
    for txn in sorted(data["transactions"], key=lambda item: item["transaction_id"], reverse=True):
        book = find_book(data, txn["book_id"])
        student = find_student(data, txn["student_id"])
        status = "Returned" if txn["return_date"] else ("Overdue" if is_overdue(txn) else "Borrowed")
        print(f"TXN-{txn['transaction_id']:04d} | "
              f"{book['title'] if book else 'Deleted book'} | "
              f"{student['name'] if student else txn['student_id']} | "
              f"Borrowed {txn['borrow_date']} | Due {txn['due_date']} | "
              f"Returned {txn['return_date'] or '-'} | {status} | "
              f"Fine PHP {txn['fine']:.2f}")


def librarian_menu(data):
    while True:
        print("\n===== LIBRARIAN MENU =====")
        print("1. Add book")
        print("2. Update book copies")
        print("3. Delete book")
        print("4. Register student")
        print("5. Search books")
        print("6. Process a return")
        print("7. View overdue report")
        print("8. View transaction history")
        print("9. View all books")
        print("0. Log out")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_book(data)
        elif choice == "2":
            update_book(data)
        elif choice == "3":
            delete_book(data)
        elif choice == "4":
            register_student(data)
        elif choice == "5":
            search_books(data)
        elif choice == "6":
            return_book(data)
        elif choice == "7":
            show_overdue_report(data)
        elif choice == "8":
            show_transactions(data)
        elif choice == "9":
            print_books(data["books"])
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose again.")


def student_menu(data, student):
    while True:
        print(f"\n===== STUDENT MENU: {student['name']} =====")
        print("1. Search books")
        print("2. Borrow a book")
        print("3. Return a book")
        print("4. View my borrowed books")
        print("5. View all books")
        print("0. Log out")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            search_books(data)
        elif choice == "2":
            borrow_book(data, student["student_id"])
        elif choice == "3":
            return_book(data, student["student_id"])
        elif choice == "4":
            print_student_loans(data, student["student_id"])
        elif choice == "5":
            print_books(data["books"])
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose again.")


def librarian_login(data):
    password = input("Librarian password: ")
    if password == LIBRARIAN_PASSWORD:
        print("Librarian login successful.")
        librarian_menu(data)
    else:
        print("Incorrect librarian password.")


def student_login(data):
    student_id = ask_text("Student ID: ")
    student = find_student(data, student_id)
    if not student:
        print("Student ID not found. Ask the librarian to register you.")
        return
    pin = input("4-digit PIN: ").strip()
    if hash_pin(pin) != student["pin_hash"]:
        print("Incorrect PIN.")
        return
    print(f"Welcome, {student['name']}!")
    student_menu(data, student)


def main():
    data = load_data()
    print("=" * 48)
    print("       LIBRARY MANAGEMENT SYSTEM")
    print("          PHINMA COC - DEMO")
    print("=" * 48)

    while True:
        print("\n===== MAIN MENU =====")
        print("1. Librarian login")
        print("2. Student login")
        print("0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            librarian_login(data)
        elif choice == "2":
            student_login(data)
        elif choice == "0":
            save_data(data)
            print("Records saved. Goodbye!")
            break
        else:
            print("Invalid option. Please choose again.")


if __name__ == "__main__":
    main()
