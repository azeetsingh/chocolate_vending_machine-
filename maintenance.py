import getpass
import sqlite3
from database import get_connection, update_stock
from dashboard import OwnerDashboard
from exceptions import (
    ShopError,
    ProductNotFoundError,
    InvalidProductError,
    InventoryError,
    DatabaseConnectionError,
    AuthenticationError,
)


class MaintenanceLogin:
    CREDENTIALS = {
        "admin": "choco@123",
        "refill": "refill@2026",
    }

    def __init__(self, max_attempts=3):
        self.max_attempts = max_attempts
        self.logged_in_user = None

    def _read_password(self):
        try:
            return getpass.getpass("Enter Password: ").strip()
        except Exception:
            return input("Enter Password: ").strip()

    def login(self):
        print("\n--- Maintenance / Owner Login ---")
        for attempt in range(1, self.max_attempts + 1):
            username = input("Enter Staff ID: ").strip()
            password = self._read_password()

            if username in self.CREDENTIALS and self.CREDENTIALS[username] == password:
                self.logged_in_user = username
                print(f"\nAccess Granted! Welcome, '{username}'.")
                return True

            remaining = self.max_attempts - attempt
            if remaining > 0:
                print(f"Invalid credentials. {remaining} attempt(s) remaining.\n")

        raise AuthenticationError("Maximum login attempts exceeded. Returning to main menu.")


class MaintenancePanel:
    def __init__(self, shop, staff_name):
        self.shop = shop
        self.staff_name = staff_name

    def show_menu(self):
        print(f"\n=== Maintenance Panel ({self.staff_name}) ===")
        print("1 for view low-stock items (< 10 units)")
        print("2 for refill / update stock quantity")
        print("3 for update product price (fix CHECK_MRP)")
        print("4 for view all inventory")
        if self.staff_name == "admin":
            print("5 for Owner Dashboard & Reports")
            print("6 for logout")
        else:
            print("5 for logout")

    def view_low_stock(self, threshold=10):
        low_items = [p for p in self.shop.get_products() if p["qty"] < threshold]
        print(f"\n--- Low Stock Alert (< {threshold} units) ---")
        self.shop._print_table(low_items)

    def refill_stock(self):
        pid = input("Enter product ID to refill: ").strip()
        products = {p["id"]: p for p in self.shop.get_products()}
        if pid not in products:
            raise ProductNotFoundError(f"Product ID '{pid}' not found.")

        item = products[pid]
        print(f"Selected: {item['name']} ({item['size']}) | Current Stock: {item['qty']}")
        try:
            added_qty = int(input("Enter quantity to add: ").strip())
        except ValueError:
            raise InventoryError("Added quantity must be a valid whole number.")

        if added_qty <= 0:
            raise InventoryError("Added quantity must be greater than zero.")

        new_qty = item["qty"] + added_qty
        update_stock(pid, new_qty)
        print(f"Stock updated! '{item['name']}' now has {new_qty} units.")

    def update_price(self):
        pid = input("Enter product ID to set/update price: ").strip()
        products = {p["id"]: p for p in self.shop.get_products()}
        if pid not in products:
            raise ProductNotFoundError(f"Product ID '{pid}' not found.")

        item = products[pid]
        current = f"₹{item['price']:.2f}" if item["price"] is not None else "CHECK_MRP"
        print(f"Selected: {item['name']} ({item['size']}) | Current Price: {current}")
        try:
            new_price = float(input("Enter new MRP (INR): ").strip())
        except ValueError:
            raise InvalidProductError("Price must be a valid number.")

        if new_price <= 0:
            raise InvalidProductError("Price must be greater than zero.")

        conn = get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE chocolates SET price_inr = ? WHERE sku = ?",
                    (new_price, pid),
                )
        except sqlite3.Error as e:
            raise DatabaseConnectionError(f"Failed to update price: {e}")
        finally:
            conn.close()

        print(f"Price updated! '{item['name']}' is now ₹{new_price:.2f}.")

    def run(self):
        while True:
            try:
                self.show_menu()
                choice = input("Enter maintenance choice: ").strip()
                if choice == "1":
                    self.view_low_stock()
                elif choice == "2":
                    self.refill_stock()
                elif choice == "3":
                    self.update_price()
                elif choice == "4":
                    self.shop.show_products()
                elif choice == "5" and self.staff_name == "admin":
                    dashboard = OwnerDashboard()
                    dashboard.run()
                elif (choice == "6" and self.staff_name == "admin") or (
                    choice == "5" and self.staff_name != "admin"
                ):
                    print(f"Logged out '{self.staff_name}'.")
                    break
                else:
                    max_opt = 6 if self.staff_name == "admin" else 5
                    print(f"Invalid choice. Please enter 1 to {max_opt}.")
            except ShopError as e:
                print(f"\n[Maintenance Error] {e}")
