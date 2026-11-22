import sqlite3
import os
from exceptions import (
    DatabaseConnectionError,
    CorruptedDataError,
    DuplicateProductError,
    InventoryError,
    ProductNotFoundError,
)

DB_NAME = "choco.db"

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseConnectionError(f"Could not connect to database: {e}")


def setup_database():
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chocolates (
                    sku TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    category TEXT NOT NULL,
                    pack_size TEXT NOT NULL,
                    price_inr REAL,
                    quantity INTEGER NOT NULL
                )
            """)
            # Add inside setup_database() right after creating the chocolates table:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)


            cursor.execute("SELECT COUNT(*) FROM chocolates")
            if cursor.fetchone()[0] == 0 and os.path.exists("chocolate.txt"):
                with open("chocolate.txt", "r", encoding="utf-8") as file:
                    next(file, None)  # Skip header row
                    for line_num, line in enumerate(file, start=2):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            sku, name, brand, category, pack_size, price, qty = line.split("|")
                            raw_price = price.strip()
                            price_val = None if raw_price == "CHECK_MRP" else float(raw_price)
                            qty_val = int(qty.strip())
                        except ValueError:
                            raise CorruptedDataError(
                                f"Invalid data format on line {line_num} in chocolate.txt"
                            )

                        try:
                            cursor.execute(
                                """
                                INSERT INTO chocolates 
                                (sku, product_name, brand, category, pack_size, price_inr, quantity)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    sku.strip(),
                                    name.strip(),
                                    brand.strip(),
                                    category.strip(),
                                    pack_size.strip(),
                                    price_val,
                                    qty_val,
                                ),
                            )
                        except sqlite3.IntegrityError:
                            raise DuplicateProductError(f"Duplicate SKU '{sku.strip()}' in chocolate.txt")

                print("Successfully imported chocolate.txt into choco.db!")
    except sqlite3.Error as e:
        raise DatabaseConnectionError(f"Database setup failed: {e}")
    finally:
        conn.close()


def update_stock(sku, new_quantity):
    if new_quantity < 0:
        raise InventoryError(f"Stock cannot be negative (attempted: {new_quantity}).")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chocolates SET quantity = ? WHERE sku = ?",
                (new_quantity, sku),
            )
            if cursor.rowcount == 0:
                raise ProductNotFoundError(f"No chocolate found with SKU '{sku}'.")
    except sqlite3.Error as e:
        raise DatabaseConnectionError(f"Failed to update stock: {e}")
    finally:
        conn.close()


def record_sale(sku, product_name, brand, quantity, unit_price, payment_method):
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            total_amount = quantity * unit_price
            cursor.execute(
                """
                INSERT INTO sales (sku, product_name, brand, quantity, unit_price, total_amount, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sku, product_name, brand, quantity, unit_price, total_amount, payment_method),
            )
    except sqlite3.Error as e:
        raise DatabaseConnectionError(f"Failed to record sale: {e}")
    finally:
        conn.close()

