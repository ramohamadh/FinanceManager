import mysql.connector
from getpass import getpass
from datetime import datetime

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

    def sign_up(self, first_name, last_name, date_of_birth, username, email, password):
        try:
            self.db.cursor.execute(
                "INSERT INTO users (first_name, last_name, date_of_birth, username, email, password, date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (first_name, last_name, date_of_birth, username, email, password, datetime.now())
            )
            self.db.connection.commit()
            print("Signup successful!\n")
        except mysql.connector.IntegrityError:
            print("Username or email already exists.\n")
        except Exception as e:
            print(f"An error occurred: {e}\n")

    def sign_in(self, username_or_email, password):
        self.db.cursor.execute(
            "SELECT id FROM users WHERE (username = %s OR email = %s) AND password = %s",
            (username_or_email, username_or_email, password)
        )
        user = self.db.cursor.fetchone()
        if user:
            print("Signin successful!")
            return user[0]  # Returns user ID
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

    def update_income(self, index, amount, source):
        if amount < 0:
            print("Amount cannot be negative.\n")
            return
        self.db.cursor.execute(
            "UPDATE incomes SET amount = %s, source = %s WHERE id = %s AND user_id = %s",
            (amount, source, index, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Income record not found.\n")
        else:
            self.db.connection.commit()
            print("Income updated successfully.\n")

    def update_expense(self, index, amount, category, description):
        if amount < 0:
            print("Amount cannot be negative.\n")
            return
        self.db.cursor.execute(
            "UPDATE expenses SET amount = %s, category = %s, description = %s WHERE id = %s AND user_id = %s",
            (amount, category, description, index, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Expense record not found.\n")
        else:
            self.db.connection.commit()
            print("Expense updated successfully.\n")

    def delete_income(self, index):
        self.db.cursor.execute(
            "DELETE FROM incomes WHERE id = %s AND user_id = %s",
            (index, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Income record not found.\n")
        else:
            self.db.connection.commit()
            print("Income deleted successfully.\n")

    def delete_expense(self, index):
        self.db.cursor.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (index, self.user_id)
        )
        if self.db.cursor.rowcount == 0:
            print("Expense record not found.\n")
        else:
            self.db.connection.commit()
            print("Expense deleted successfully.\n")

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
        min_amount = float(input("Minimum Amount: "))
        max_amount = float(input("Maximum Amount: "))
        source = input("Source (leave blank for all): ")
        date = input("Date (YYYY-MM-DD, leave blank for all): ")

        query = "SELECT amount, source, date FROM incomes WHERE user_id = %s"
        params = [self.user_id]

        if source:
            query += " AND source LIKE %s"
            params.append(f"%{source}%")
        
        if date:
            query += " AND DATE(date) = %s"
            params.append(date)

        query += " AND amount BETWEEN %s AND %s"
        params.extend([min_amount, max_amount])

        self.db.cursor.execute(query, params)
        results = self.db.cursor.fetchall()

        if results:
            print("Search Results:")
            for result in results:
                print(f"Source: {result[1]}, Amount: ${result[0]:.2f}, Date: {result[2]}")
        else:
            print("No results found.")

    def search_expenses(self):
        print("\nSearch Expenses:")
        min_amount = float(input("Minimum Amount: "))
        max_amount = float(input("Maximum Amount: "))
        category = input("Category (leave blank for all): ")
        description = input("Description (leave blank for all): ")
        date = input("Date (YYYY-MM-DD, leave blank for all): ")

        query = "SELECT amount, category, description, date FROM expenses WHERE user_id = %s"
        params = [self.user_id]

        if category:
            query += " AND category LIKE %s"
            params.append(f"%{category}%")
        
        if description:
            query += " AND description LIKE %s"
            params.append(f"%{description}%")
        
        if date:
            query += " AND DATE(date) = %s"
            params.append(date)

        query += " AND amount BETWEEN %s AND %s"
        params.extend([min_amount, max_amount])

        self.db.cursor.execute(query, params)
        results = self.db.cursor.fetchall()

        if results:
            print("Search Results:")
            for result in results:
                print(f"Description: {result[2]}, Amount: ${result[0]:.2f}, Category: {result[1]}, Date: {result[3]}")
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
            first_name = input("First Name: ")
            last_name = input("Last Name: ")

            while True:
                date_of_birth = input("Date of Birth (YYYY-MM-DD): ")
                if len(date_of_birth) == 10 and date_of_birth[4] == '-' and date_of_birth[7] == '-' and date_of_birth[:4].isdigit() and date_of_birth[5:7].isdigit() and date_of_birth[8:].isdigit():
                    break
                else:
                    print("Invalid date format. Please enter again in YYYY-MM-DD format.")

            username = input("Username: ")
            email = input("Email: ")
            password = getpass("Password: ")
            user_manager.sign_up(first_name, last_name, date_of_birth, username, email, password)

        elif choice == '2':
            username_or_email = input("Username or Email: ")
            password = getpass("Password: ")
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
                    print("7. Display Financial Summary")
                    print("8. Search Incomes")
                    print("9. Search Expenses")
                    print("10. Logout")
                    option = input("Choose an option: ")

                    if option == '1':
                        amount = float(input("Amount: "))
                        source = input("Source: ")
                        finance_manager.add_income(amount, source)

                    elif option == '2':
                        amount = float(input("Amount: "))
                        category = input("Category: ")
                        description = input("Description: ")
                        finance_manager.add_expense(amount, category, description)

                    elif option == '3':
                        index = int(input("Income ID to update: "))
                        amount = float(input("New Amount: "))
                        source = input("New Source: ")
                        finance_manager.update_income(index, amount, source)

                    elif option == '4':
                        index = int(input("Expense ID to update: "))
                        amount = float(input("New Amount: "))
                        category = input("New Category: ")
                        description = input("New Description: ")
                        finance_manager.update_expense(index, amount, category, description)

                    elif option == '5':
                        index = int(input("Income ID to delete: "))
                        finance_manager.delete_income(index)

                    elif option == '6':
                        index = int(input("Expense ID to delete: "))
                        finance_manager.delete_expense(index)

                    elif option == '7':
                        finance_manager.display_financial_summary()

                    elif option == '8':
                        finance_manager.search_incomes()

                    elif option == '9':
                        finance_manager.search_expenses()

                    elif option == '10':
                        print("Logging out...\n")
                        break

                    else:
                        print("Invalid option, please try again.")

        elif choice == '3':
            print("Exiting...\n")
            break

        else:
            print("Invalid option, please try again.")

    db.close()

if __name__ == "__main__":
    main()
