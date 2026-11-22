from database import get_connection, setup_database, update_stock
from exceptions import (
    ShopError,
    ProductNotFoundError,
    InvalidProductError,
    OutOfStockError,
    EmptyCartError,
    InvalidPaymentError,
    InsufficientBalanceError,
)
from maintenance import MaintenanceLogin, MaintenancePanel
from dashboard import OwnerDashboard
from exceptions import ShopError
from database import get_connection, update_stock, record_sale



class Products:
    def get_products(self):
        product = []
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sku, product_name, brand, category, pack_size, price_inr, quantity FROM chocolates"
            )
            rows = cursor.fetchall()
            for row in rows:
                price = float(row["Price_INR"]) if row["price_inr"] is not None else None
                product.append({
                    "id": str(row["sku"]).strip(),
                    "name": str(row["product_name"]).strip(),
                    "brand": str(row["brand"]).strip(),
                    "category": str(row["category"]).strip(),
                    "size": str(row["pack_size"]).strip(),
                    "price": price,
                    "qty": int(row["quantity"]),
                })
        finally:
            conn.close()
        return product

    def _print_table(self, items):
        if not items:
            print("No chocolates found!")
            return
        print("-" * 104)
        print(f"{'ID':<6}{'Name':<34}{'Brand':<12}{'Category':<22}{'Size':<10}{'Price':<11}{'Qty':<5}")
        print("-" * 104)
        for p in items:
            price_display = f"{p['price']:.2f}" if p["price"] is not None else "CHECK_MRP"
            print(
                f"{p['id']:<6}{p['name']:<34}{p['brand']:<12}"
                f"{p['category']:<22}{p['size']:<10}{price_display:<11}{p['qty']:<5}"
            )
        print("-" * 104)

    def show_products(self):
        products = self.get_products()
        self._print_table(products)

    def search_product(self, keyword):
        if not keyword:
            raise InvalidProductError("Search keyword cannot be empty.")
        all_products = self.get_products()
        matches = [
            p for p in all_products
            if keyword.lower() in p["name"].lower() or keyword.lower() in p["brand"].lower()
        ]
        print(f"\n--- Search Results for '{keyword}' ---")
        self._print_table(matches)


class Add_to_cart:
    def __init__(self, shop):
        self.shop = shop
        self.cart = []
        self.total = 0.0

    def reset_cart(self):
        self.cart.clear()
        self.total = 0.0
        print("Cart has been reset.")

    def add_items(self):
        products = self.shop.get_products()
        pid = input("Enter product ID: ").strip()
        if not pid:
            raise InvalidProductError("Product ID cannot be empty.")

        try:
            qty = int(input("Enter qty: ").strip())
        except ValueError:
            raise InvalidProductError("Quantity must be a valid whole number.")

        if qty <= 0:
            raise InvalidProductError("Quantity must be greater than zero.")

        for p in products:
            if p["id"] == pid:
                if p["price"] is None:
                    raise InvalidProductError(
                        f"'{p['name']}' ({p['size']}) is marked CHECK_MRP and cannot be purchased yet."
                    )

                in_cart_qty = sum(item["qty"] for item in self.cart if item["id"] == pid)
                if qty + in_cart_qty > p["qty"]:
                    available = p["qty"] - in_cart_qty
                    raise OutOfStockError(
                        f"Only {available} units available in stock for '{p['name']}' ({p['size']})."
                    )

                for item in self.cart:
                    if item["id"] == pid:
                        item["qty"] += qty
                        self.total += p["price"] * qty
                        print(f"Updated '{p['name']}' quantity in cart.")
                        return

                self.cart.append({
                    "id": p["id"],
                    "name": p["name"],
                    "size": p["size"],
                    "price": p["price"],
                    "qty": qty,
                })
                self.total += p["price"] * qty
                print(f"Added '{p['name']}' ({p['size']}) to cart.")
                return

        raise ProductNotFoundError(f"Product ID '{pid}' not found.")

    def show_cart(self):
        if not self.cart:
            raise EmptyCartError("Your cart is currently empty.")

        print("-" * 76)
        print(f"{'ID':<6}{'Name':<34}{'Size':<10}{'Price':<10}{'Qty':<8}{'Amount'}")
        print("-" * 76)
        for item in self.cart:
            amount = item["price"] * item["qty"]
            print(
                f"{item['id']:<6}{item['name']:<34}{item['size']:<10}"
                f"{item['price']:<10.2f}x {item['qty']:<6}= {amount:.2f}"
            )
        print("-" * 76)
        print(f"{'Total:':<68}₹{self.total:.2f}")
        print("-" * 76)

    def complete_checkout(self, payment_method="Cash"):
        """Logs sales and deducts purchased quantities in a single transaction."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            for item in self.cart:
                sku = item["id"]
                product_name = item["name"]
                unit_price = item["price"]
                qty = item["qty"]
                total_amount = unit_price * qty

                
                cursor.execute("SELECT brand FROM chocolates WHERE sku = ?", (sku,))
                row = cursor.fetchone()
                brand = row["brand"] if row and row["brand"] else "N/A"

                
                cursor.execute(
                    """
                    INSERT INTO sales (sku, product_name, brand, unit_price, quantity, total_amount, payment_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sku, product_name, brand, unit_price, qty, total_amount, payment_method),
                )

                
                cursor.execute(
                    "UPDATE chocolates SET quantity = quantity - ? WHERE sku = ?",
                    (qty, sku),
                )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        self.reset_cart()


class Payment:
    def __init__(self, cart_object):
        self.cart_object = cart_object

    def choice(self):
        if not self.cart_object.cart or self.cart_object.total == 0:
            raise EmptyCartError("Your cart is empty. Nothing to pay.")

        print("\nSelect payment method:")
        print("1 for UPI")
        print("2 for Cash")
        print("3 for Card")

        method = input("Enter your choice (1, 2, or 3): ").strip()
        if method == "1":
            self.upi()
        elif method == "2":
            self.cash()
        elif method == "3":
            self.card()
        else:
            raise InvalidPaymentError("Invalid choice. Please enter 1, 2, or 3.")

    def upi(self):
        upi_id = input("Enter UPI ID (example: name@123): ").strip()
        if "@" not in upi_id or len(upi_id) < 3:
            raise InvalidPaymentError("Invalid UPI ID format.")
        print(f"Payment of ₹{self.cart_object.total:.2f} received via UPI ({upi_id}). Thank you!")
        self.cart_object.complete_checkout("UPI")   

    def cash(self):
        for attempt in range(1, 4):
            try:
                given = float(input(f"Total is ₹{self.cart_object.total:.2f}. Enter given cash: ").strip())
            except ValueError:
                raise InvalidPaymentError("Cash amount must be a valid number.")

            if given < self.cart_object.total:
                shortfall = self.cart_object.total - given
                if attempt == 3:
                    raise InsufficientBalanceError(
                        f"Maximum attempts reached! Cash payment failed (short by ₹{shortfall:.2f})."
                    )
                print(f"Insufficient cash! You need to add ₹{shortfall:.2f} (Attempt {attempt}/3).")
                continue

            change = given - self.cart_object.total
            print(f"Payment of ₹{self.cart_object.total:.2f} received in Cash. Change returned: ₹{change:.2f}")
            print("Thank you!")
            self.cart_object.complete_checkout("Cash")  
            return

    def card(self):
        card_no = input("Enter last 4 digits of card (example: 1234): ").strip()
        if len(card_no) != 4 or not card_no.isdigit():
            raise InvalidPaymentError("Invalid card number! Must be 4 digits.")
        print(f"Payment of ₹{self.cart_object.total:.2f} approved on Card ending in {card_no}. Thank you!")
        self.cart_object.complete_checkout("Card")   # <-- Pass "Card"



class User:
    def __init__(self):
        setup_database()
        self.shop = Products()
        self.cart = Add_to_cart(self.shop)
        self.payment = Payment(self.cart)

    def show_options(self):
        print("\nYour options are:")
        print("1 for show products")
        print("2 for search product")
        print("3 for add to cart")
        print("4 for show cart")
        print("8 for Owner Dashboard")  
        print("5 for payment")
        print("6 for maintenance / refill login")
        print("7 for exit")

    def get_choice(self):
        self.show_options()
        return input("Enter your choice: ").strip()

    def run(self):
        while True:
            try:
                choice = self.get_choice()
                if choice == "1":
                    self.shop.show_products()
                elif choice == "2":
                    keyword = input("Enter chocolate name or brand: ").strip()
                    self.shop.search_product(keyword)
                elif choice == "3":
                    self.cart.add_items()
                elif choice == "8":
                    OwnerDashboard().run() 
                elif choice == "4":
                    self.cart.show_cart()
                elif choice == "5":
                    self.payment.choice()
                
                elif choice == "6":
                    auth = MaintenanceLogin()
                    if auth.login():
                        panel = MaintenancePanel(self.shop, auth.logged_in_user)
                        panel.run()
                elif choice == "7":
                    print("Thank you, visit again!")
                    break
                else:
                    print("Invalid choice. Please enter 1 to 8.")
            except ShopError as e:
                print(f"\n[Error] {e}")


if __name__ == "__main__":
    try:
        user = User()
        user.run()
    except ShopError as e:
        print(f"[Startup Error] {e}")
