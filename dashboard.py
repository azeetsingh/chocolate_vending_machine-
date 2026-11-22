import sqlite3
from database import get_connection
from exceptions import ShopError, DatabaseConnectionError


class OwnerDashboard:
    def _fetch_all(self, query, params=()): # optional parameter for reduce error in sql db (placeholder of blank) 
        conn = get_connection()
        try:
            cursor = conn.cursor() # curser lika a waiter take request  and give answer from db 
            cursor.execute(query, params)
            return cursor.fetchall() #grabs every matching row from the database and hands the complete list back to your code.
        except sqlite3.Error as e:
            raise DatabaseConnectionError(f"Dashboard query failed: {e}")
        finally:
            conn.close()

    def _fetch_one(self, query, params=()):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            raise DatabaseConnectionError(f"Dashboard query failed: {e}")
        finally:
            conn.close()

    def show_summary(self):
        sales_row = self._fetch_one(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(quantity), 0) AS units, COALESCE(SUM(total_amount), 0) AS revenue FROM sales"
        )
        inv_row = self._fetch_one(
            "SELECT COUNT(*) AS total_skus, COALESCE(SUM(quantity), 0) AS total_units, COALESCE(SUM(quantity * COALESCE(price_inr, 0)), 0) AS stock_value FROM chocolates"
        )
        out_of_stock = self._fetch_one("SELECT COUNT(*) AS cnt FROM chocolates WHERE quantity = 0")["cnt"]
        unpriced = self._fetch_one("SELECT COUNT(*) AS cnt FROM chocolates WHERE price_inr IS NULL")["cnt"]

        print("\n" + "=" * 62)
        print("              OWNER VENDING MACHINE DASHBOARD")
        print("=" * 62)
        print(f" Total Revenue Earned      : ₹{sales_row['revenue']:.2f}")
        print(f" Total Items Sold          : {sales_row['units']} units ({sales_row['orders']} line items)")
        print("-" * 62)
        print(f" Active Product SKUs       : {inv_row['total_skus']}")
        print(f" Remaining Machine Stock   : {inv_row['total_units']} units")
        print(f" Current Inventory Value   : ₹{inv_row['stock_value']:.2f}")
        print(f" Out-of-Stock SKUs         : {out_of_stock}")
        print(f" Unpriced (CHECK_MRP) SKUs : {unpriced}")
        print("=" * 62)

    def top_selling_products(self, limit=5):
        rows = self._fetch_all(
            """
            SELECT sku, product_name, brand, SUM(quantity) AS total_sold, SUM(total_amount) AS revenue
            FROM sales
            GROUP BY sku, product_name, brand
            ORDER BY total_sold DESC
            LIMIT ?
            """,
            (limit,),
        )
        print(f"\n--- Top {limit} Best-Selling Chocolates ---")
        if not rows:
            print("No sales recorded yet.")
            return
        print("-" * 78)
        print(f"{'SKU':<8}{'Product Name':<34}{'Brand':<12}{'Sold':<8}{'Revenue'}")
        print("-" * 78)
        for r in rows:
            print(f"{r['sku']:<8}{r['product_name']:<34}{r['brand']:<12}{r['total_sold']:<8}₹{r['revenue']:.2f}")
        print("-" * 78)

    def payment_breakdown(self):
        rows = self._fetch_all(
            """
            SELECT payment_method, COUNT(*) AS txns, SUM(total_amount) AS revenue
            FROM sales
            GROUP BY payment_method
            ORDER BY revenue DESC
            """
        )
        print("\n--- Revenue by Payment Method ---")
        if not rows:
            print("No transactions recorded yet.")
            return
        print("-" * 50)
        print(f"{'Method':<18}{'Items Paid':<15}{'Total Revenue'}")
        print("-" * 50)
        for r in rows:
            print(f"{r['payment_method']:<18}{r['txns']:<15}₹{r['revenue']:.2f}")
        print("-" * 50)

    def recent_transactions(self, limit=10):
        rows = self._fetch_all(
            """
            SELECT sale_id, product_name, quantity, total_amount, payment_method, sold_at
            FROM sales
            ORDER BY sale_id DESC
            LIMIT ?
            """,
            (limit,),
        )
        print(f"\n--- Last {limit} Sales Transactions ---")
        if not rows:
            print("No transactions recorded yet.")
            return
        print("-" * 86)
        print(f"{'ID':<6}{'Product':<32}{'Qty':<6}{'Amount':<12}{'Method':<10}{'Date/Time'}")
        print("-" * 86)
        for r in rows:
            print(
                f"{r['sale_id']:<6}{r['product_name']:<32}{r['quantity']:<6}"
                f"₹{r['total_amount']:<11.2f}{r['payment_method']:<10}{r['sold_at']}"
            )
        print("-" * 86)

    def run(self):
        while True:
            try:
                print("\n=== Owner Report & Analytics Menu ===")
                print("1 for Executive Summary (Revenue & Stock Value)")
                print("2 for Top 5 Best-Selling Chocolates")
                print("3 for Payment Method Breakdown (UPI / Cash / Card)")
                print("4 for Recent Sales History")
                print("5 for Back")

                choice = input("Enter report choice: ").strip()
                if choice == "1":
                    self.show_summary()
                elif choice == "2":
                    self.top_selling_products()
                elif choice == "3":
                    self.payment_breakdown()
                elif choice == "4":
                    self.recent_transactions()
                elif choice == "5":
                    break
                else:
                    print("Invalid choice. Please enter 1 to 5.")
            except ShopError as e:
                print(f"\n[Dashboard Error] {e}")
