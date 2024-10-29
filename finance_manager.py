import mysql.connector
from datetime import datetime
import re
import bcrypt


class Database:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='12345678',
            database='finance_manager'
        )
        self.cursor = self.connection.cursor()

    def close(self):
        self.cursor.close()
        self.connection.close()

class UserManager:
    def __init__(self, db):
        self.db = db

    def validate_password(self, password):
        if (len(password) < 8 or
            not re.search(r'[A-Z]', password) or  
            not re.search(r'[a-z]', password) or  
            not re.search(r'[0-9]', password) or  
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):  
            return False
        return True

    def sign_up(self, first_name, last_name, date_of_birth, username, email, password):
        if not self.validate_password(password):
            print("Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character.\n")
            return

        self.db.cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if self.db.cursor.fetchone():
            print("Username or email already exists. Please choose a different one.\n")
            return

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        birth_date = datetime.strptime(date_of_birth, "%Y-%m-%d")  
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        try:
            self.db.cursor.execute(
                "INSERT INTO users (first_name, last_name, date_of_birth, username, email, password, age, date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (first_name, last_name, date_of_birth, username, email, hashed_password.decode('utf-8'), age, datetime.now())
            )
            self.db.connection.commit()
            print("Signup successful!\n")
        except mysql.connector.IntegrityError:
            print("Username or email already exists.\n")
        except Exception as e:
            print(f"An error occurred: {e}\n")

    def sign_in(self, username_or_email, password):
        self.db.cursor.execute(
            "SELECT id, password FROM users WHERE (username = %s OR email = %s)",
            (username_or_email, username_or_email)
        )
        user = self.db.cursor.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            print("Signin successful!")
            return user[0]  
        else:
            print("Invalid username/email or password.\n")
            return None

class FinanceManager:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id

    def add_income(self, amount, source):
        if amount < 0:
            print("Amount cannot be negative.\n")
            return
        self.db.cursor.execute(
            "INSERT INTO incomes (user_id, amount, source, date) VALUES (%s, %s, %s, %s)",
            (self.user_id, amount, source, datetime.now())
        )
        self.db.connection.commit()
        print(f"Income of {amount:.2f} from {source} added.\n")

    def add_expense(self, amount, category, description):
        if amount < 0:
            print("Amount cannot be negative.\n")
            return
        self.db.cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (%s, %s, %s, %s, %s)",
            (self.user_id, amount, category, description, datetime.now())
        )
        self.db.connection.commit()
        print(f"Expense of {amount:.2f} for {description} added under {category} category.\n")

    def update_income(self, income_id, new_amount, new_source):  
        print("\nUpdating income entry...")
        self.db.cursor.execute(
            "UPDATE incomes SET amount = %s, source = %s WHERE id = %s AND user_id = %s",
            (new_amount, new_source, income_id, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Income record not found or no changes made.\n")
        else:
            self.db.connection.commit()
            print("Income updated successfully.\n")

    def update_expense(self, expense_id, new_amount, new_category, new_description):
        print("\nUpdating expense entry...")
        self.db.cursor.execute(
            "UPDATE expenses SET amount = %s, category = %s, description = %s WHERE id = %s AND user_id = %s",
            (new_amount, new_category, new_description, expense_id, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Expense record not found or no changes made.\n")
        else:
            self.db.connection.commit()
            print("Expense updated successfully.\n")

    def delete_income(self, income_id):  
        print("\nSelect an income entry to delete:")
        self.db.cursor.execute(
            "DELETE FROM incomes WHERE id = %s AND user_id = %s",
            (income_id, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Income record not found.\n")
        else:
            self.db.connection.commit()
            print("Income deleted successfully.\n")

    def delete_expense(self, expense_id):
        print(f"\nDeleting expense with ID {expense_id}...")
        self.db.cursor.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (expense_id, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Expense record not found or no changes made.\n")
        else:
            self.db.connection.commit()
            print("Expense deleted successfully.\n")

    
    def display_incomes(self):
        self.db.cursor.execute("SELECT id, amount, source FROM incomes WHERE user_id = %s", (self.user_id,))
        incomes = self.db.cursor.fetchall()
        if incomes:
            for income in incomes:
                print(f"ID: {income[0]}, Source: {income[2]}, Amount: ${income[1]:.2f}")
        else:
            print("No income records found.\n")

    def display_expenses(self):
        self.db.cursor.execute("SELECT id, amount, category, description FROM expenses WHERE user_id = %s", (self.user_id,))
        expenses = self.db.cursor.fetchall()
        if expenses:
            for expense in expenses:
                print(f"ID: {expense[0]}, Description: {expense[3]}, Amount: ${expense[1]:.2f}, Category: {expense[2]}")
        else:
            print("No expense records found.\n")

    def display_financial_summary(self):
        print("\nFinancial Summary:")
        
        self.db.cursor.execute("SELECT amount, source, date FROM incomes WHERE user_id = %s", (self.user_id,))
        incomes = self.db.cursor.fetchall()
        
        print("Income Sources:")
        for income in incomes:
            print(f"Source: {income[1]}, Amount: ${income[0]:.2f}, Date: {income[2]}")

        self.db.cursor.execute("SELECT amount, description, category, date FROM expenses WHERE user_id = %s", (self.user_id,))
        expenses = self.db.cursor.fetchall()
        
        print("\nExpenses:")
        for expense in expenses:
            print(f"Description: {expense[1]}, Amount: ${expense[0]:.2f}, Category: {expense[2]}, Date: {expense[3]}")

        total_income = sum(income[0] for income in incomes)
        total_expenses = sum(expense[0] for expense in expenses)

        print(f"\nTotal Income: ${total_income:.2f}")
        print(f"Total Expenses: ${total_expenses:.2f}")
        print(f"Balance: ${total_income - total_expenses:.2f}\n")

    def search_incomes(self):
        print("\nSearch Incomes:")
        min_amount_input = input("Minimum Amount (leave blank for no minimum): ")
        max_amount_input = input("Maximum Amount (leave blank for no maximum): ")
        source = input("Source (leave blank for all): ")
        date = input("Date (YYYY-MM-DD, leave blank for all): ")

        query = "SELECT id, amount, source, date FROM incomes WHERE user_id = %s"
        params = [self.user_id]

        if source:
            query += " AND source LIKE %s"
            params.append(f"%{source}%")

        if date:
            query += " AND DATE(date) = %s"
            params.append(date)

        if min_amount_input.strip():  
            try:
                min_amount = float(min_amount_input)
                query += " AND amount >= %s"
                params.append(min_amount)
            except ValueError:
                print("Invalid minimum amount entered. Please enter a number or leave it blank.")

        if max_amount_input.strip():  
            try:
                max_amount = float(max_amount_input)
                query += " AND amount <= %s"
                params.append(max_amount)
            except ValueError:
                print("Invalid maximum amount entered. Please enter a number or leave it blank.")

        self.db.cursor.execute(query, params)
        results = self.db.cursor.fetchall()

        if results:
            print("Search Results:")
            for result in results:
                print(f"ID: {result[0]}, Source: {result[2]}, Amount: ${result[1]:.2f}, Date: {result[3]}")

            while True:
                action = input("\nWould you like to update (U), delete (D) an entry, or go back (B)? ").upper()
                if action == 'U':
                    index = int(input("Enter the ID of the income to update: "))
                    amount = float(input("Enter new amount: "))
                    source = input("Enter new source: ")
                    self.update_income(index, amount, source)
                elif action == 'D':
                    index = int(input("Enter the ID of the income to delete: "))
                    self.delete_income(index)
                elif action == 'B':
                    break
                else:
                    print("Invalid choice. Please try again.")
        else:
            print("No results found.")
    def search_expenses(self):
        print("\nSearch Expenses:")
        min_amount_input = input("Minimum Amount : ")
        max_amount_input = input("Maximum Amount : ")
        category = input("Category : ")
        date = input("Date (YYYY-MM-DD ): ")

        query = "SELECT id, amount, category, description, date FROM expenses WHERE user_id = %s"
        params = [self.user_id]

        if category:
            query += " AND category LIKE %s"
            params.append(f"%{category}%")

        if date:
            query += " AND DATE(date) = %s"
            params.append(date)

        if min_amount_input:
            min_amount = float(min_amount_input)
            query += " AND amount >= %s"
            params.append(min_amount)

        if max_amount_input:
            max_amount = float(max_amount_input)
            query += " AND amount <= %s"
            params.append(max_amount)

        self.db.cursor.execute(query, params)
        results = self.db.cursor.fetchall()

        if results:
            print("Search Results:")
            for result in results:
                print(f"ID: {result[0]}, Amount: ${result[1]:.2f}, Category: {result[2]}, Description: {result[3]}, Date: {result[4]}")

            while True:
                action = input("\nWould you like to update (U), delete (D) an entry, or go back (B)? ").upper()
                if action == 'U':
                    index = int(input("Enter the ID of the expense to update: "))
                    amount = float(input("Enter new amount: "))
                    category = input("Enter new category: ")
                    description = input("Enter new description: ")
                    self.update_expense(index, amount, category, description)
                elif action == 'D':
                    index = int(input("Enter the ID of the expense to delete: "))
                    self.delete_expense(index)
                elif action == 'B':
                    break
                else:
                    print("Invalid choice. Please try again.")
        else:
            print("No results found.")

def main():
    db = Database()
    user_manager = UserManager(db)

    while True:
        print("1. Sign Up")
        print("2. Sign In")
        print("3. Exit")
        choice = input("Choose an option: ")

        if choice == '1':
            while True:
                first_name = input("First Name: ").strip()
                if first_name and all(char.isalpha() or char.isspace() for char in first_name):
                    break
                print("Please enter a valid First Name.")

            while True:
                last_name = input("Last Name: ").strip()
                if last_name and all(char.isalpha() or char.isspace() for char in last_name):
                    break
                print("Please enter a valid Last Name.")

            while True:
                date_of_birth = input("Date of birth (YYYY-MM-DD): ")
                try:
                    birth_date = datetime.strptime(date_of_birth, "%Y-%m-%d")
                    today = datetime.today()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    if 18 <= age <= 80:
                        break  
                    else:
                        print("You must be between 18 and 80 years old to sign up.")  
                except ValueError:
                    print("Invalid date format. Please enter again in YYYY-MM-DD format.")
            
            while True:
                username = input("Username (6-15 characters): ").strip()
                if len(username) < 6 or len(username) > 15:
                    print("Username must be between 6 and 15 characters.")
                    continue
                if ' ' in username:
                    print("Username cannot contain spaces.")
                    continue
                if not re.match("^[A-Za-z0-9]+$", username):
                    print("Username can only contain letters and numbers.")
                    continue
                break

            while True:
                email = input("Email: ").strip()
                if email:
                    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                        break
                    else:
                        print("Invalid email format. Please enter a valid email.")
                else:
                    print("Email cannot be empty. Please enter a valid Email.")

            while True:
                password = input("Password: ")
                if password:
                    if not user_manager.validate_password(password):
                        print("Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character.\n")
                        continue
                    break

            user_manager.sign_up(first_name, last_name, date_of_birth, username, email, password)

        elif choice == '2':
            username_or_email = input("Username or Email: ").strip()
            if not username_or_email:  
                print("Username or Email cannot be empty. Please try again.")
                continue
            password = input("Password: ").strip()  
            if not password:
                print("Password cannot be empty. Please try again.")
                continue
            user_id = user_manager.sign_in(username_or_email, password)

            if user_id:
                finance_manager = FinanceManager(db, user_id)

                while True:
                    print("\n1. Add Income")
                    print("2. Add Expense")
                    print("3. Update Income")
                    print("4. Update Expense")
                    print("5. Delete Income")
                    print("6. Delete Expense")
                    print("7. Show Financial Summary")
                    print("8. Search")
                    print("9. Logout")
                    option = input("Choose an option: ")

                    if option == '1':  
                        while True:
                            amount_input = input("Enter income amount (or 'B' to go back): ")
                            if amount_input.upper() == 'B':
                                break  
                            try:
                                amount = float(amount_input)
                                if amount < 0:
                                    print("Amount cannot be negative. Please try again.")
                                    continue
                                source = input("Enter income source (or 'B' to go back): ")
                                if source.upper() == 'B':
                                    break  
                                finance_manager.add_income(amount, source)
                                break  
                            except ValueError:
                                print("Invalid input. Please enter a valid number.")

                    elif option == '2':  
                        while True:
                            amount_input = input("Enter expense amount (or 'B' to go back): ")
                            if amount_input.upper() == 'B':
                                break 
                            try:
                                amount = float(amount_input)
                                if amount < 0:
                                    print("Amount cannot be negative. Please try again.")
                                    continue
                                category = input("Enter expense category (or 'B' to go back): ")
                                if category.upper() == 'B':
                                    break  
                                description = input("Enter expense description (or 'B' to go back): ")
                                if description.upper() == 'B':
                                    break  
                                finance_manager.add_expense(amount, category, description)
                                break  
                            except ValueError:
                                print("Invalid input. Please enter a valid number.")

                    elif option == '3':  
                        while True:
                            print("\nSelect an income entry to update (or 'B' to go back):")
                            finance_manager.display_incomes()
                            income_id_input = input("Enter the ID of the income to update (or 'B' to go back): ")
                            if income_id_input.upper() == 'B':
                                break
                            try:
                                income_id = int(income_id_input)
                                new_amount = float(input("Enter new amount: "))  
                                new_source = input("Enter new source: ")  
                                finance_manager.update_income(income_id, new_amount, new_source)  
                                break
                            except ValueError:
                                print("Invalid input. Please enter valid data.")

                    elif option == '4':  
                        while True:
                            print("\nSelect an expense entry to update (or 'B' to go back):")
                            finance_manager.display_expenses()
                            expense_id_input = input("Enter the ID of the expense to update (or 'B' to go back): ")
                            if expense_id_input.upper() == 'B':
                                break
                            try:
                                expense_id = int(expense_id_input)
                                new_amount = float(input("Enter new amount: "))  
                                new_category = input("Enter new category: ")  
                                new_description = input("Enter new description: ")  
                                finance_manager.update_expense(expense_id, new_amount, new_category, new_description)  
                                break
                            except ValueError:
                                print("Invalid input. Please enter valid data.")
  
                    elif option == '5':  
                        while True:
                            print("\nSelect an income entry to delete (or 'B' to go back):")
                            finance_manager.display_incomes()
                            income_id_input = input("Enter the ID of the income to delete (or 'B' to go back): ")
                            if income_id_input.upper() == 'B':
                                break  
                            try:
                                income_id = int(income_id_input)
                                finance_manager.delete_income(income_id)
                                break  
                            except ValueError:
                                print("Invalid ID. Please enter a valid number.")
  
                    elif option == '6':  
                        while True:
                            print("\nSelect an expense entry to delete (or 'B' to go back):")
                            finance_manager.display_expenses()
                            expense_id_input = input("Enter the ID of the expense to delete (or 'B' to go back): ")
                            if expense_id_input.upper() == 'B':
                                break  
                            try:
                                expense_id = int(expense_id_input)
                                finance_manager.delete_expense(expense_id)
                                break  
                            except ValueError:
                                print("Invalid ID. Please enter a valid number.")
  
                    elif option == '7':  
                        while True:
                            print("\nDisplaying financial summary...")
                            finance_manager.display_financial_summary()
                            back_option = input("Press 'B' to go back: ")
                            if back_option.upper() == 'B':
                                break  

                    elif option == '8':
                        print("\n1. Search Incomes")
                        print("2. Search Expenses")
                        print("3. Back")
                        search_option = input("Choose an option: ")
                        if search_option == '1':
                            finance_manager.search_incomes()
                        elif search_option == '2':
                            finance_manager.search_expenses()
                        elif search_option == '3':
                            continue
                        else:
                            print("Invalid option. Please try again.\n")

                    elif option == '9':
                        break
                    else:
                        print("Invalid option. Please try again.\n")

        elif choice == '3':
            db.close()
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.\n")

if __name__ == "__main__":
    main()
