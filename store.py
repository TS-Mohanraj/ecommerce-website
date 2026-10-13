"""SQLite schema, migrations, and seed data for Sun Auto Centre."""

from __future__ import annotations

import os
import sqlite3
import psycopg2
from pathlib import Path

from werkzeug.security import generate_password_hash


PRODUCTS = (
    ("CASTROL", "Castrol Engine Oil", "High-quality engine oil for smooth and reliable engine performance.", 650, "castrol engine oil.jpg"),
    ("CASTROL", "Castrol Premium Engine Oil", "Premium protection designed for better performance and engine durability.", 850, "primiem engine oil.jpg.png"),
    ("CASTROL", "Castrol Chain Cleaner", "Helps remove dirt, grease and road grime from motorcycle chains.", 399, "Castrol Chain Cleaner.jpg.png"),
    ("CASTROL", "Castrol Chain Lubricant", "Provides smooth chain performance and helps reduce wear.", 449, "Castrol Chain lubricant.png"),
    ("MOTUL", "Motul Engine Oil", "High-performance engine oil for smooth and reliable motorcycle performance.", 750, "motul engine oil.png"),
    ("MOTUL", "Motul C1 Chain Clean", "Powerful cleaner that removes dirt and grease from motorcycle chains.", 399, "moto chain cleanser.jpg"),
    ("MOTUL", "Motul C2 Chain Lube", "Long-lasting lubricant for smooth and reliable chain performance.", 449, "chain lubricant.jpg"),
    ("MOTUL", "Motul Bike Care", "Premium bike care product to help keep your motorcycle clean and protected.", 499, "motul bike product.webp"),
    ("HERO", "Hero Engine Guard", "Strong protection for your motorcycle engine during everyday rides.", 2499, "engine-guard.jpg"),
    ("HERO", "Hero Side Stand", "Strong and reliable side stand designed for daily motorcycle use.", 899, "hero side stand.jpg"),
    ("HERO", "Hero Body Graphics & Stickers", "Stylish graphics and stickers to customize your motorcycle.", 599, "Hero Body Graphics & Stickers.jpg"),
    ("HERO", "Hero Tank Pad", "Helps protect the fuel tank from scratches and everyday wear.", 399, "Hero tank pad.jpg"),
    ("HERO", "Hero Motorcycle Visor", "Stylish visor designed to improve wind protection.", 1099, "visor.jpg"),
    ("HERO", "Hero Genuine Spare Parts", "Genuine replacement parts for reliable motorcycle maintenance.", None, "hero genuine parts.jpg"),
    ("TVS", "TVS Engine Guard", "Strong protection designed to help protect your motorcycle engine.", 2499, "TVS Engine Guard.jpg"),
    ("TVS", "TVS Side Stand", "Strong and durable side stand suitable for daily motorcycle use.", 899, "tvs-side-stand.jpg"),
    ("TVS", "TVS Tank Pad", "Helps protect the motorcycle fuel tank from scratches and wear.", 399, "tvs-tank-pad.jpg"),
    ("TVS", "TVS Motorcycle Visor", "Stylish visor designed to provide better wind protection.", 1099, "TVS Motorcycle Visor.jpg"),
    ("TVS", "TVS Genuine Spare Parts", "Genuine replacement spare parts for reliable motorcycle maintenance.", None, "tvs-spare-parts.jpg"),
    ("ACCESSORIES", "Motorcycle Mobile Holder", "Strong and secure mobile holder suitable for multiple motorcycle brands.", 799, "mobile holder.jpg"),
    ("ACCESSORIES", "Motorcycle Foot Mat", "Durable foot mat designed for improved comfort and protection.", 499, "footmat.jpg"),
    ("ACCESSORIES", "Motorcycle Luggage Accessories", "Useful luggage accessories designed for carrying items safely.", 1499, "lugguage accessaaries.jpg"),
)


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _add_column(connection: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    if name not in _columns(connection, table):
        connection.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')


def _is_werkzeug_hash(password: str) -> bool:
    return password.startswith(("scrypt:", "pbkdf2:"))


def _migrate_legacy_owners(connection: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "owners" not in tables:
        return

    owner_columns = _columns(connection, "owners")
    if not {"username", "password"}.issubset(owner_columns):
        raise RuntimeError("Cannot migrate the legacy owners table: username/password columns are missing.")

    for owner in connection.execute("SELECT username, password FROM owners").fetchall():
        username = str(owner["username"] or "").strip()
        password = owner["password"]
        if not username or not isinstance(password, str) or not password:
            raise RuntimeError("Cannot migrate the legacy owners table: an account has invalid credentials.")

        password_hash = password if _is_werkzeug_hash(password) else generate_password_hash(password)
        existing = connection.execute(
            "SELECT id, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            if existing["role"] != "admin":
                raise RuntimeError("Cannot migrate the legacy owners table: the username belongs to a non-admin account.")
            connection.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (password_hash, existing["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO users (name, phone, password, address, username, role)
                VALUES (?, ?, ?, '', ?, 'admin')
                """,
                (username, f"admin:{username}", password_hash, username),
            )

    connection.execute("DROP TABLE owners")


def initialize_database(path: str | Path) -> None:
    """Create the current schema and migrate the earlier Flask/Node database."""
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    price REAL CHECK (price IS NULL OR price >= 0),
                    image TEXT,
                    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    address TEXT NOT NULL DEFAULT '',
                    username TEXT UNIQUE,
                    role TEXT NOT NULL DEFAULT 'customer'
                        CHECK (role IN ('customer', 'admin')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    address TEXT
                );

                CREATE TABLE IF NOT EXISTS addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    label TEXT NOT NULL DEFAULT 'Delivery',
                    recipient_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 1 CHECK (is_default IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS cart_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cart_id INTEGER NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 999),
                    UNIQUE (cart_id, product_id)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER REFERENCES customers(id),
                    user_id INTEGER REFERENCES users(id),
                    total REAL NOT NULL CHECK (total >= 0),
                    status TEXT NOT NULL DEFAULT 'Pending',
                    order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    delivered_at TEXT,
                    delivery_address TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    price REAL NOT NULL CHECK (price >= 0)
                );

                CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    customer_id INTEGER REFERENCES customers(id),
                    user_id INTEGER REFERENCES users(id),
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Requested',
                    return_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (order_id, user_id)
                );

                """
            )

            # Existing products/customers/orders tables predate the current schema.
            _add_column(connection, "products", "stock", "INTEGER NOT NULL DEFAULT 0")
            _add_column(connection, "products", "is_active", "INTEGER NOT NULL DEFAULT 1")
            _add_column(connection, "products", "created_at", "TEXT NOT NULL DEFAULT '1970-01-01 00:00:00'")
            _add_column(connection, "products", "updated_at", "TEXT NOT NULL DEFAULT '1970-01-01 00:00:00'")
            _add_column(connection, "users", "username", "TEXT")
            _add_column(connection, "orders", "user_id", "INTEGER REFERENCES users(id)")
            _add_column(connection, "orders", "delivered_at", "TEXT")
            _add_column(connection, "orders", "delivery_address", "TEXT NOT NULL DEFAULT ''")
            _add_column(connection, "returns", "user_id", "INTEGER REFERENCES users(id)")
            _add_column(connection, "returns", "updated_at", "TEXT")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_returns_user_id ON returns(user_id)")

            _migrate_legacy_owners(connection)

            for user in connection.execute("SELECT id, password FROM users").fetchall():
                password = user["password"]
                if not _is_werkzeug_hash(password):
                    connection.execute(
                        "UPDATE users SET password = ? WHERE id = ?",
                        (generate_password_hash(password), user["id"]),
                    )

            # Upgrade legacy customer passwords in-place and preserve their IDs so
            # existing orders continue to belong to the same accounts.
            for customer in connection.execute("SELECT * FROM customers").fetchall():
                password = customer["password"]
                if not _is_werkzeug_hash(password):
                    password = generate_password_hash(password)
                    connection.execute(
                        "UPDATE customers SET password = ? WHERE id = ?",
                        (password, customer["id"]),
                    )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO users (id, name, phone, password, address, role)
                    VALUES (?, ?, ?, ?, ?, 'customer')
                    """,
                    (
                        customer["id"],
                        customer["name"],
                        customer["phone"],
                        password,
                        customer["address"] or "",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO addresses (user_id, recipient_name, phone, address)
                    SELECT ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM addresses WHERE user_id = ? AND is_default = 1
                    )
                    """,
                    (
                        customer["id"],
                        customer["name"],
                        customer["phone"],
                        customer["address"] or "",
                        customer["id"],
                    ),
                )

            connection.execute(
                """
                UPDATE orders
                SET user_id = customer_id
                WHERE user_id IS NULL AND customer_id IS NOT NULL
                """
            )
            connection.execute(
                """
                UPDATE returns
                SET user_id = customer_id
                WHERE user_id IS NULL AND customer_id IS NOT NULL
                """
            )
            connection.execute(
                """
                UPDATE returns
                SET updated_at = COALESCE(updated_at, return_date, CURRENT_TIMESTAMP)
                """
            )

            # Seed missing catalog entries by their stable brand/name pair. Existing
            # product IDs, prices, image paths, stock, and order snapshots are intact.
            for brand, name, description, price, image in PRODUCTS:
                connection.execute(
                    """
                    INSERT INTO products (brand, name, description, price, image)
                    SELECT ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM products WHERE lower(brand) = lower(?) AND lower(name) = lower(?)
                    )
                    """,
                    (brand, name, description, price, image, brand, name),
                )
    finally:
        connection.close()
