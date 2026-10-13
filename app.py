from __future__ import annotations

import os
import re
import secrets
import sqlite3
import psycopg2
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import click
from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from store import initialize_database

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError)
DB_ERRORS = (sqlite3.Error, psycopg2.Error)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "database" / "products.db"
INSTANCE_DIR = BASE_DIR / "instance"


def _persistent_secret() -> str:
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    key_file = INSTANCE_DIR / "secret_key"
    try:
        return key_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        key = secrets.token_urlsafe(48)
        try:
            key_file.write_text(key, encoding="utf-8")
        except FileExistsError:
            return key_file.read_text(encoding="utf-8").strip()
        return key


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    application = Flask(__name__, instance_path=str(INSTANCE_DIR))

    application.config.from_mapping(
        SECRET_KEY=_persistent_secret(),
        DATABASE=str(DEFAULT_DATABASE),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        application.config.update(test_config)
    # --- INTHA IF-ELSE CONDITION-AH MATTUM PODUNGA ---
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if not DATABASE_URL:
        initialize_database(application.config["DATABASE"])

    def connection() -> Any:
        if "db" not in g:
            if DATABASE_URL:
                from store import get_db_connection
                g.db = get_db_connection()
            else:
                db = sqlite3.connect(application.config["DATABASE"], timeout=10)
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA foreign_keys = ON")
                db.execute("PRAGMA busy_timeout = 10000")
                g.db = db
        return g.db

    application.extensions["db_connection"] = connection

    @application.teardown_appcontext
    def close_connection(_error: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            if _error is not None:
                db.rollback()
            db.close()

    def csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    @application.context_processor

    def template_context() -> dict[str, Any]:
        return {
            "csrf_token": csrf_token,
            "current_user": {
                "id": session.get("user_id"),
                "name": session.get("user_name"),
                "role": session.get("role"),
            }
            if session.get("user_id")
            else None,
        }

    @application.before_request
    def protect_state_changes() -> None:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            supplied = request.headers.get("X-CSRF-Token", "")
            expected = session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(supplied, expected):
                abort(400, description="The form expired. Refresh the page and try again.")

    def api_error(message: str, status: int = 400):
        return jsonify({"message": message}), status

    def payload() -> dict[str, Any]:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    def customer_required(function: Callable):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if session.get("role") != "customer" or not session.get("user_id"):
                return api_error("Please log in to continue.", 401)
            return function(*args, **kwargs)

        return wrapped

    def admin_required(function: Callable):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if session.get("role") != "admin" or not session.get("user_id"):
                return api_error("Administrator login required.", 401)
            return function(*args, **kwargs)

        return wrapped

    def customer_page(function: Callable):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if session.get("role") != "customer" or not session.get("user_id"):
                return redirect(url_for("customer_login", next=request.path))
            return function(*args, **kwargs)

        return wrapped

    def admin_page(function: Callable):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if session.get("role") != "admin" or not session.get("user_id"):
                return redirect(url_for("admin_login"))
            return function(*args, **kwargs)

        return wrapped

    def normalize_text(value: Any, field: str, maximum: int = 200, required: bool = True) -> str | None:
        if value is None:
            if required:
                raise ValueError(f"{field} is required.")
            return None
        text = str(value).strip()
        if required and not text:
            raise ValueError(f"{field} is required.")
        if len(text) > maximum:
            raise ValueError(f"{field} must be {maximum} characters or fewer.")
        return text or None

    def valid_phone(value: Any) -> str:
        phone = normalize_text(value, "Mobile number", 20)
        if not re.fullmatch(r"[0-9]{10}", phone or ""):
            raise ValueError("Enter a valid 10-digit mobile number.")
        return phone

    def valid_quantity(value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError("Quantity must be a whole number between 1 and 999.")
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be a whole number between 1 and 999.") from None
        if str(value).strip() != str(quantity) or not 1 <= quantity <= 999:
            raise ValueError("Quantity must be a whole number between 1 and 999.")
        return quantity

    def valid_id(value: Any, field: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"Invalid {field}.")
        try:
            identifier = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {field}.") from None
        if str(value).strip() != str(identifier) or identifier < 1:
            raise ValueError(f"Invalid {field}.")
        return identifier

    def valid_price(value: Any, allow_contact: bool = True) -> float | None:
        if value is None or value == "":
            if allow_contact:
                return None
            raise ValueError("This product does not have a checkout price.")
        try:
            price = float(value)
        except (TypeError, ValueError):
            raise ValueError("Price must be a valid non-negative number.") from None
        if not (0 <= price < 100_000_000):
            raise ValueError("Price must be a valid non-negative number.")
        return round(price, 2)

    def valid_stock(value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError("Stock must be a whole number between 0 and 1,000,000.")
        try:
            stock = int(value)
        except (TypeError, ValueError):
            raise ValueError("Stock must be a whole number between 0 and 1,000,000.") from None
        if str(value).strip() != str(stock) or not 0 <= stock <= 1_000_000:
            raise ValueError("Stock must be a whole number between 0 and 1,000,000.")
        return stock

    def current_user_id() -> int:
        return int(session["user_id"])

    def order_data(order: sqlite3.Row) -> dict[str, Any]:
        items = connection().execute(
            """
            SELECT product_id, product_name, quantity, price
            FROM order_items WHERE order_id = ? ORDER BY id
            """,
            (order["id"],),
        ).fetchall()
        result = dict(order)
        result["items"] = [dict(item) for item in items]
        delivery_time = order["delivered_at"]
        result["return_eligible"] = False
        result["return_deadline"] = None
        if order["status"].lower() == "delivered" and delivery_time:
            try:
                delivered = datetime.fromisoformat(delivery_time.replace("Z", "+00:00"))
                if delivered.tzinfo is None:
                    delivered = delivered.replace(tzinfo=timezone.utc)
                deadline = delivered + timedelta(days=7)
                result["return_deadline"] = deadline.isoformat()
                result["return_eligible"] = datetime.now(timezone.utc) <= deadline
            except ValueError:
                application.logger.warning("Order %s has an invalid delivery timestamp.", order["id"])
        return result

    # Customer storefront.
    @application.get("/")
    @application.get("/home.html")
    def home():
        return render_template("home.html")

    @application.get("/products")
    @application.get("/products.html")
    def products_page():
        return render_template("products.html")

    @application.get("/products/<int:product_id>")
    def product_detail(product_id: int):
        product = connection().execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()
        if not product:
            abort(404)
        return render_template("product-detail.html", product=product)

    @application.get("/cart")
    @application.get("/cart.html")
    @customer_page
    def cart_page():
        return render_template("cart.html")

    @application.get("/customer-login")
    def customer_login():
        return render_template("customer-login.html")

    @application.get("/customer-register")
    def customer_register():
        return render_template("customer-register.html")

    @application.get("/customer-account")
    @customer_page
    def customer_account():
        return render_template("customer-account.html")

    @application.get("/customer-orders")
    @customer_page
    def customer_orders():
        return render_template("customer-orders.html")

    @application.get("/customer-returns")
    @customer_page
    def customer_returns():
        return render_template("customer-returns.html")

    @application.get("/admin/login")
    @application.get("/owner-login")
    def admin_login():
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return render_template("owner-login.html")

    @application.get("/admin")
    @application.get("/owner-dashboard")
    @admin_page
    def admin_dashboard():
        return render_template("owner-dashboard.html")

    @application.get("/api/products")
    def get_products():
        rows = connection().execute(
            """
            SELECT id, brand, name, description, price, image, stock
            FROM products
            WHERE is_active = 1
            ORDER BY id
            """
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    @application.get("/api/products/<int:product_id>")
    def get_product(product_id: int):
        row = connection().execute(
            """
            SELECT id, brand, name, description, price, image, stock
            FROM products WHERE id = ? AND is_active = 1
            """,
            (product_id,),
        ).fetchone()
        if not row:
            return api_error("Product not found.", 404)
        return jsonify(dict(row))

    # Customer account and session APIs.
    @application.post("/api/customer/register")
    def register_customer():
        data = payload()
        try:
            name = normalize_text(data.get("name"), "Name", 100)
            phone = valid_phone(data.get("phone"))
            password = data.get("password")
            address = normalize_text(data.get("address"), "Address", 500)
            if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
                return api_error("Password must be between 8 and 128 characters.")
        except ValueError as error:
            return api_error(str(error))

        db = connection()
        try:
            with db:
                cursor = db.execute(
                    """
                    INSERT INTO users (name, phone, password, address, role)
                    VALUES (?, ?, ?, ?, 'customer')
                    """,
                    (name, phone, generate_password_hash(password), address),
                )
                user_id = cursor.lastrowid
                db.execute(
                    "INSERT INTO customers (id, name, phone, password, address) VALUES (?, ?, ?, ?, ?)",
                    (
                        user_id,
                        name,
                        phone,
                        db.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()["password"],
                        address,
                    ),
                )
                db.execute(
                    "INSERT INTO addresses (user_id, recipient_name, phone, address) VALUES (?, ?, ?, ?)",
                    (user_id, name, phone, address),
                )
                db.execute("INSERT INTO cart (user_id) VALUES (?)", (user_id,))
        except DB_INTEGRITY_ERRORS:
            return api_error("That mobile number is already registered.", 409)
        return jsonify({"message": "Registration successful. Please log in."}), 201

    @application.post("/api/customer/login")
    def login_customer():
        data = payload()
        phone = str(data.get("phone") or "").strip()
        password = data.get("password")
        if not phone or not isinstance(password, str) or not password:
            return api_error("Mobile number and password are required.")
        user = connection().execute(
            "SELECT id, name, phone, password, role FROM users WHERE phone = ? AND role = 'customer'",
            (phone,),
        ).fetchone()
        if not user or not check_password_hash(user["password"], password):
            return api_error("Invalid mobile number or password.", 401)
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = "customer"
        session["csrf_token"] = secrets.token_urlsafe(32)
        return jsonify({"message": "Login successful."})

    @application.post("/api/admin/login")
    @application.post("/api/owner/login")
    def login_admin():
        data = payload()
        username = str(data.get("username") or "").strip()
        password = data.get("password")
        if not username or not isinstance(password, str) or not password:
            return api_error("Username and password are required.")
        user = connection().execute(
            "SELECT id, name, username, password FROM users WHERE username = ? AND role = 'admin'",
            (username,),
        ).fetchone()
        if not user or not check_password_hash(user["password"], password):
            return api_error("Invalid administrator username or password.", 401)
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = "admin"
        session["csrf_token"] = secrets.token_urlsafe(32)
        return jsonify({"message": "Login successful."})

    @application.post("/api/customer/logout")
    @application.post("/api/admin/logout")
    def logout():
        session.clear()
        return jsonify({"message": "Logged out successfully."})

    @application.get("/api/customer/profile")
    @customer_required
    def customer_profile():
        user = connection().execute(
            "SELECT id, name, phone, address FROM users WHERE id = ? AND role = 'customer'",
            (current_user_id(),),
        ).fetchone()
        if not user:
            session.clear()
            return api_error("Customer account not found.", 404)
        return jsonify(dict(user))

    @application.put("/api/customer/profile")
    @customer_required
    def update_customer_profile():
        data = payload()
        try:
            name = normalize_text(data.get("name"), "Name", 100)
            phone = valid_phone(data.get("phone"))
            address = normalize_text(data.get("address"), "Address", 500)
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        try:
            with db:
                db.execute(
                    "UPDATE users SET name = ?, phone = ?, address = ? WHERE id = ? AND role = 'customer'",
                    (name, phone, address, current_user_id()),
                )
                db.execute(
                    "UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?",
                    (name, phone, address, current_user_id()),
                )
                db.execute(
                    """
                    UPDATE addresses SET recipient_name = ?, phone = ?, address = ?
                    WHERE user_id = ? AND is_default = 1
                    """,
                    (name, phone, address, current_user_id()),
                )
        except DB_INTEGRITY_ERRORS:
            return api_error("That mobile number is already registered.", 409)
        session["user_name"] = name
        return jsonify({"message": "Profile updated successfully."})

    # Server-backed shopping cart and checkout.
    @application.get("/api/cart")
    @customer_required
    def get_cart():
        rows = connection().execute(
            """
            SELECT ci.id AS item_id, ci.product_id, ci.quantity,
                   p.brand, p.name, p.description, p.price, p.image,
                   p.stock, p.is_active
            FROM cart c
            JOIN cart_items ci ON ci.cart_id = c.id
            JOIN products p ON p.id = ci.product_id
            WHERE c.user_id = ? ORDER BY ci.id
            """,
            (current_user_id(),),
        ).fetchall()
        items = []
        total = 0.0
        for row in rows:
            item = dict(row)
            item["subtotal"] = round((item["price"] or 0) * item["quantity"], 2)
            total += item["subtotal"]
            items.append(item)
        return jsonify({"items": items, "count": sum(item["quantity"] for item in items), "total": round(total, 2)})

    @application.get("/api/cart/count")
    def get_cart_count():
        if session.get("role") != "customer" or not session.get("user_id"):
            return jsonify({"count": 0})
        result = connection().execute(
            """
            SELECT COALESCE(SUM(ci.quantity), 0)
            FROM cart c LEFT JOIN cart_items ci ON ci.cart_id = c.id
            WHERE c.user_id = ?
            """,
            (current_user_id(),),
        ).fetchone()
        return jsonify({"count": result[0]})

    @application.post("/api/cart/items")
    @customer_required
    def add_cart_item():
        data = payload()
        try:
            product_id = valid_id(data.get("product_id"), "product")
            quantity = valid_quantity(data.get("quantity", 1))
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        try:
            with db:
                product = db.execute(
                    "SELECT id, stock, price, is_active FROM products WHERE id = ?",
                    (product_id,),
                ).fetchone()
                if not product or not product["is_active"]:
                    return api_error("Product is no longer available.", 404)
                if product["price"] is None:
                    return api_error("Please contact us for this product's price.")
                if product["stock"] < quantity:
                    return api_error("There is not enough stock for that quantity.", 409)
                cart = db.execute("SELECT id FROM cart WHERE user_id = ?", (current_user_id(),)).fetchone()
                if not cart:
                    cart_id = db.execute("INSERT INTO cart (user_id) VALUES (?)", (current_user_id(),)).lastrowid
                else:
                    cart_id = cart["id"]
                existing = db.execute(
                    "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                    (cart_id, product_id),
                ).fetchone()
                new_quantity = quantity + (existing["quantity"] if existing else 0)
                if new_quantity > product["stock"] or new_quantity > 999:
                    return api_error("There is not enough stock for that quantity.", 409)
                if existing:
                    db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_quantity, existing["id"]))
                else:
                    db.execute(
                        "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)",
                        (cart_id, product_id, quantity),
                    )
                db.execute("UPDATE cart SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (cart_id,))
        except DB_INTEGRITY_ERRORS:
            return api_error("Unable to add this product to the cart.", 409)
        return jsonify({"message": "Added to cart."}), 201

    @application.patch("/api/cart/items/<int:item_id>")
    @customer_required
    def update_cart_item(item_id: int):
        try:
            quantity = valid_quantity(payload().get("quantity"))
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        item = db.execute(
            """
            SELECT ci.id, ci.product_id, p.stock, p.is_active
            FROM cart_items ci JOIN cart c ON c.id = ci.cart_id
            JOIN products p ON p.id = ci.product_id
            WHERE ci.id = ? AND c.user_id = ?
            """,
            (item_id, current_user_id()),
        ).fetchone()
        if not item:
            return api_error("Cart item not found.", 404)
        if not item["is_active"] or quantity > item["stock"]:
            return api_error("There is not enough stock for that quantity.", 409)
        with db:
            db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, item_id))
        return jsonify({"message": "Cart updated."})

    @application.delete("/api/cart/items/<int:item_id>")
    @customer_required
    def remove_cart_item(item_id: int):
        db = connection()
        with db:
            cursor = db.execute(
                """
                DELETE FROM cart_items
                WHERE id = ? AND cart_id IN (SELECT id FROM cart WHERE user_id = ?)
                """,
                (item_id, current_user_id()),
            )
        if not cursor.rowcount:
            return api_error("Cart item not found.", 404)
        return jsonify({"message": "Item removed from cart."})

    @application.post("/api/checkout")
    @customer_required
    def checkout():
        data = payload()
        try:
            address = normalize_text(data.get("delivery_address"), "Delivery address", 500)
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        try:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute(
                "SELECT id, name, phone FROM users WHERE id = ? AND role = 'customer'",
                (current_user_id(),),
            ).fetchone()
            if not user:
                db.rollback()
                return api_error("Customer account not found.", 404)
            items = db.execute(
                """
                SELECT ci.product_id, ci.quantity, p.name, p.price, p.stock, p.is_active
                FROM cart c JOIN cart_items ci ON ci.cart_id = c.id
                JOIN products p ON p.id = ci.product_id
                WHERE c.user_id = ? ORDER BY ci.id
                """,
                (current_user_id(),),
            ).fetchall()
            if not items:
                db.rollback()
                return api_error("Your cart is empty.")
            total = 0.0
            for item in items:
                if not item["is_active"] or item["price"] is None:
                    db.rollback()
                    return api_error(f"{item['name']} is not available for checkout.", 409)
                if item["quantity"] > item["stock"]:
                    db.rollback()
                    return api_error(f"Insufficient stock for {item['name']}.", 409)
                total += item["price"] * item["quantity"]
            total = round(total, 2)
            order_id = db.execute(
                """
                INSERT INTO orders (customer_id, user_id, total, status, delivery_address)
                VALUES (?, ?, ?, 'Pending', ?)
                """,
                (current_user_id(), current_user_id(), total, address),
            ).lastrowid
            for item in items:
                db.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, item["product_id"], item["name"], item["quantity"], item["price"]),
                )
                db.execute(
                    "UPDATE products SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )
            db.execute(
                "DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM cart WHERE user_id = ?)",
                (current_user_id(),),
            )
            db.commit()
        except DB_ERRORS:
            db.rollback()
            application.logger.exception("Checkout transaction failed for customer %s.", current_user_id())
            return api_error("Unable to place the order. Please try again.", 500)
        return jsonify({"message": "Order placed successfully.", "order_id": order_id, "total": total}), 201

    # Customer order history, order detail, and seven-day returns.
    @application.get("/api/customer/orders")
    @customer_required
    def get_customer_orders():
        orders = connection().execute(
            """
            SELECT o.id, o.total, o.status, o.order_date, o.delivered_at,
                   o.delivery_address, r.id AS return_id, r.status AS return_status
            FROM orders o LEFT JOIN returns r ON r.order_id = o.id AND r.user_id = ?
            WHERE o.user_id = ? ORDER BY o.id DESC
            """,
            (current_user_id(), current_user_id()),
        ).fetchall()
        return jsonify([order_data(order) for order in orders])

    @application.get("/api/customer/orders/<int:order_id>")
    @customer_required
    def get_customer_order(order_id: int):
        order = connection().execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?",
            (order_id, current_user_id()),
        ).fetchone()
        if not order:
            return api_error("Order not found.", 404)
        return jsonify(order_data(order))

    @application.get("/api/customer/returns")
    @customer_required
    def get_customer_returns():
        rows = connection().execute(
            """
            SELECT r.id, r.order_id, r.reason, r.status, r.return_date, r.updated_at,
                   o.total, o.status AS order_status, o.delivered_at
            FROM returns r JOIN orders o ON o.id = r.order_id
            WHERE r.user_id = ? ORDER BY r.id DESC
            """,
            (current_user_id(),),
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    @application.post("/api/customer/returns")
    @customer_required
    def request_return():
        data = payload()
        try:
            order_id = valid_id(data.get("order_id"), "order")
            reason = normalize_text(data.get("reason"), "Return reason", 1000)
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        order = db.execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?",
            (order_id, current_user_id()),
        ).fetchone()
        if not order:
            return api_error("Order not found.", 404)
        eligibility = order_data(order)
        if not eligibility["return_eligible"]:
            return api_error("Returns are available only within 7 days after delivery.", 409)
        try:
            db.execute("BEGIN IMMEDIATE")
            existing_return = db.execute(
                "SELECT id FROM returns WHERE order_id = ? AND user_id = ?",
                (order_id, current_user_id()),
            ).fetchone()
            if existing_return:
                db.rollback()
                return api_error("A return request already exists for this order.", 409)
            cursor = db.execute(
                """
                INSERT INTO returns (order_id, customer_id, user_id, reason)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, current_user_id(), current_user_id(), reason),
            )
            db.commit()
        except DB_INTEGRITY_ERRORS:
            db.rollback()
            return api_error("A return request already exists for this order.", 409)
        except DB_ERRORS:
            db.rollback()
            application.logger.exception("Return request creation failed for order %s.", order_id)
            return api_error("Unable to submit the return request.", 500)
        return jsonify({"message": "Return request submitted.", "return_id": cursor.lastrowid}), 201

    # Administrator dashboard and management APIs.
    @application.get("/api/admin/dashboard")
    @admin_required
    def admin_stats():
        db = connection()
        stats = {
            "customers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0],
            "products": db.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0],
            "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "pending_orders": db.execute("SELECT COUNT(*) FROM orders WHERE lower(status) = 'pending'").fetchone()[0],
            "returns": db.execute("SELECT COUNT(*) FROM returns WHERE lower(status) IN ('requested', 'pending')").fetchone()[0],
            "sales": db.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE lower(status) != 'cancelled'").fetchone()[0],
        }
        return jsonify(stats)

    @application.get("/api/admin/products")
    @admin_required
    def admin_products():
        rows = connection().execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])

    def product_values(data: dict[str, Any]) -> tuple[str, str, str | None, float | None, str | None, int]:
        brand = normalize_text(data.get("brand"), "Brand", 80)
        name = normalize_text(data.get("name"), "Product name", 160)
        description = normalize_text(data.get("description", ""), "Description", 2000, required=False)
        image = normalize_text(data.get("image", ""), "Image filename", 255, required=False)
        price = valid_price(data.get("price"))
        stock = valid_stock(data.get("stock", 0))
        if image and ("/" in image or "\\" in image or image in {".", ".."}):
            raise ValueError("Image must be a filename from the existing product image folder.")
        return brand or "", name or "", description, price, image, stock

    @application.post("/api/admin/products")
    @admin_required
    def create_product():
        try:
            values = product_values(payload())
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        try:
            with db:
                product_id = db.execute(
                    """
                    INSERT INTO products (brand, name, description, price, image, stock)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    values,
                ).lastrowid
        except DB_INTEGRITY_ERRORS:
            return api_error("Unable to create product. Check that its details are unique and valid.", 409)
        return jsonify({"message": "Product created.", "id": product_id}), 201

    @application.put("/api/admin/products/<int:product_id>")
    @admin_required
    def update_product(product_id: int):
        try:
            values = product_values(payload())
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        with db:
            cursor = db.execute(
                """
                UPDATE products
                SET brand = ?, name = ?, description = ?, price = ?, image = ?,
                    stock = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (*values, product_id),
            )
        if not cursor.rowcount:
            return api_error("Product not found.", 404)
        return jsonify({"message": "Product updated."})

    @application.patch("/api/admin/products/<int:product_id>/stock")
    @admin_required
    def update_stock(product_id: int):
        try:
            stock = valid_stock(payload().get("stock"))
        except ValueError as error:
            return api_error(str(error))
        db = connection()
        with db:
            cursor = db.execute(
                "UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (stock, product_id),
            )
        if not cursor.rowcount:
            return api_error("Product not found.", 404)
        return jsonify({"message": "Stock updated."})

    @application.delete("/api/admin/products/<int:product_id>")
    @admin_required
    def deactivate_product(product_id: int):
        db = connection()
        with db:
            cursor = db.execute(
                "UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_active = 1",
                (product_id,),
            )
        if not cursor.rowcount:
            return api_error("Active product not found.", 404)
        return jsonify({"message": "Product deactivated. Historical orders are unchanged."})

    @application.get("/api/admin/customers")
    @admin_required
    def admin_customers():
        rows = connection().execute(
            """
            SELECT u.id, u.name, u.phone, u.address, u.created_at,
                   COUNT(DISTINCT o.id) AS order_count,
                   COALESCE(SUM(o.total), 0) AS order_total
            FROM users u LEFT JOIN orders o ON o.user_id = u.id
            WHERE u.role = 'customer'
            GROUP BY u.id ORDER BY u.id DESC
            """
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    @application.get("/api/admin/orders")
    @admin_required
    def admin_orders():
        orders = connection().execute(
            """
            SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
            FROM orders o LEFT JOIN users u ON u.id = o.user_id
            ORDER BY o.id DESC
            """
        ).fetchall()
        return jsonify([order_data(order) | {
            "customer_name": order["customer_name"],
            "customer_phone": order["customer_phone"],
        } for order in orders])

    @application.get("/api/admin/orders/<int:order_id>")
    @admin_required
    def admin_order_detail(order_id: int):
        order = connection().execute(
            """
            SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
            FROM orders o LEFT JOIN users u ON u.id = o.user_id
            WHERE o.id = ?
            """,
            (order_id,),
        ).fetchone()
        if not order:
            return api_error("Order not found.", 404)
        result = order_data(order)
        result["customer_name"] = order["customer_name"]
        result["customer_phone"] = order["customer_phone"]
        return jsonify(result)

    @application.patch("/api/admin/orders/<int:order_id>/status")
    @admin_required
    def update_order_status(order_id: int):
        status = str(payload().get("status") or "").strip()
        allowed = {"Pending", "Processing", "Shipped", "Delivered", "Cancelled"}
        if status not in allowed:
            return api_error("Choose a valid order status.")
        db = connection()
        delivered_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if status == "Delivered" else None
        try:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order:
                db.rollback()
                return api_error("Order not found.", 404)
            previous_status = order["status"]
            if previous_status == "Cancelled" and status != "Cancelled":
                db.rollback()
                return api_error("A cancelled order cannot be reactivated.", 409)
            if previous_status == "Delivered" and status != "Delivered":
                db.rollback()
                return api_error("A delivered order cannot be changed; use the return process.", 409)
            if status == "Cancelled" and previous_status != "Cancelled":
                order_items = db.execute(
                    "SELECT product_id, quantity FROM order_items WHERE order_id = ? AND product_id IS NOT NULL",
                    (order_id,),
                ).fetchall()
                for item in order_items:
                    db.execute(
                        "UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (item["quantity"], item["product_id"]),
                    )
            db.execute(
                """
                UPDATE orders SET status = ?,
                    delivered_at = CASE
                        WHEN ? = 'Delivered' THEN COALESCE(delivered_at, ?)
                        ELSE delivered_at
                    END
                WHERE id = ?
                """,
                (status, status, delivered_at, order_id),
            )
            db.commit()
        except DB_ERRORS:
            db.rollback()
            application.logger.exception("Unable to update status for order %s.", order_id)
            return api_error("Unable to update order status.", 500)
        return jsonify({"message": "Order status updated."})

    @application.get("/api/admin/returns")
    @admin_required
    def admin_returns():
        rows = connection().execute(
            """
            SELECT r.*, u.name AS customer_name, u.phone AS customer_phone,
                   o.total, o.status AS order_status, o.delivered_at
            FROM returns r
            LEFT JOIN users u ON u.id = r.user_id
            JOIN orders o ON o.id = r.order_id
            ORDER BY r.id DESC
            """
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    @application.patch("/api/admin/returns/<int:return_id>/status")
    @admin_required
    def update_return_status(return_id: int):
        status = str(payload().get("status") or "").strip()
        if status not in {"Approved", "Rejected", "Received", "Refunded"}:
            return api_error("Choose Approved, Rejected, Received, or Refunded.")
        db = connection()
        with db:
            cursor = db.execute(
                "UPDATE returns SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, return_id),
            )
        if not cursor.rowcount:
            return api_error("Return request not found.", 404)
        return jsonify({"message": "Return request updated."})

    @application.errorhandler(400)
    @application.errorhandler(404)
    def expected_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"message": getattr(error, "description", "Not found.")}), error.code
        return render_template("error.html", status=error.code, message=getattr(error, "description", "Not found.")), error.code

    @application.errorhandler(500)
    def internal_error(error):
        application.logger.exception("Unhandled application error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"message": "An unexpected server error occurred."}), 500
        return render_template("error.html", status=500, message="An unexpected server error occurred."), 500

    @application.cli.command("create-admin")
    @click.option("--username", prompt=True, help="Administrator login name.")
    def create_admin_command(username: str) -> None:
        """Create an administrator account without storing a plaintext password."""
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
            raise click.ClickException("Username must be 3-40 letters, digits, dots, dashes, or underscores.")
        password = click.prompt("Password (minimum 12 characters)", hide_input=True, confirmation_prompt=True)
        if len(password) < 12 or len(password) > 128:
            raise click.ClickException("Password must be between 12 and 128 characters.")
        db = connection()
        try:
            with db:
                db.execute(
                    """
                    INSERT INTO users (name, phone, username, password, address, role)
                    VALUES (?, ?, ?, ?, '', 'admin')
                    """,
                    (username, f"admin:{username}", username, generate_password_hash(password)),
                )
        except DB_INTEGRITY_ERRORS:
            raise click.ClickException("That administrator username already exists.") from None
        click.echo(f"Administrator '{username}' created.")

    @application.cli.command("reset-admin")
    @click.option("--username", prompt=True, help="Administrator login name.")
    def reset_admin_command(username: str) -> None:
        """Set an existing administrator password using a hidden prompt."""
        username = username.strip()
        password = click.prompt("New password (minimum 12 characters)", hide_input=True, confirmation_prompt=True)
        if len(password) < 12 or len(password) > 128:
            raise click.ClickException("Password must be between 12 and 128 characters.")
        db = connection()
        with db:
            cursor = db.execute(
                "UPDATE users SET password = ? WHERE username = ? AND role = 'admin'",
                (generate_password_hash(password), username),
            )
        if not cursor.rowcount:
            raise click.ClickException("Administrator username not found.")
        click.echo(f"Password reset for administrator '{username}'.")

    return application


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true")
