import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app


class EcommerceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.database),
                "SECRET_KEY": "test-only-secret",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def token(self):
        with self.client.session_transaction() as current_session:
            token = current_session.get("csrf_token")
            if not token:
                token = "test-csrf-token"
                current_session["csrf_token"] = token
            return token

    def mutate(self, path, method="POST", json=None):
        return self.client.open(
            path,
            method=method,
            json=json,
            headers={"X-CSRF-Token": self.token()},
        )

    def register(self, phone="5551234567", name="Test Customer"):
        return self.mutate(
            "/api/customer/register",
            json={
                "name": name,
                "phone": phone,
                "password": "customer-password-1",
                "address": "10 Test Street",
            },
        )

    def login_customer(self, phone="5551234567"):
        return self.mutate(
            "/api/customer/login",
            json={"phone": phone, "password": "customer-password-1"},
        )

    def create_admin(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute(
                """
                INSERT INTO users (name, phone, username, password, address, role)
                VALUES (?, ?, ?, ?, '', 'admin')
                """,
                ("Test Admin", "admin:test-admin", "test-admin", generate_password_hash("admin-password-123")),
            )

    def login_admin(self):
        return self.mutate(
            "/api/admin/login",
            json={"username": "test-admin", "password": "admin-password-123"},
        )

    def set_stock(self, product_id, stock):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, product_id))

    def test_catalog_seed_is_idempotent_and_pages_render(self):
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 22)
        self.assertEqual(len({(p["brand"], p["name"]) for p in response.json}), 22)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/products").status_code, 200)
        self.assertEqual(self.client.get("/products/1").status_code, 200)
        self.assertEqual(self.client.get("/products/99999").status_code, 404)
        self.assertEqual(self.client.get("/products/14").status_code, 200)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT price FROM products WHERE id = 14").fetchone()[0], None)
        self.assertEqual(self.client.get("/customer-account").status_code, 302)
        with self.app.app_context():
            from store import initialize_database

            initialize_database(self.database)
        self.assertEqual(len(self.client.get("/api/products").json), 22)

    def test_authenticated_customer_and_admin_pages_render(self):
        self.register()
        self.login_customer()
        for path in ("/cart", "/customer-account", "/customer-orders", "/customer-returns"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.mutate("/api/customer/logout")
        self.create_admin()
        self.assertEqual(self.client.get("/admin/login").status_code, 200)
        self.login_admin()
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_register_login_profile_update_and_logout(self):
        self.assertEqual(self.register().status_code, 201)
        with closing(sqlite3.connect(self.database)) as db, db:
            hashed = db.execute("SELECT password FROM users WHERE phone = ?", ("5551234567",)).fetchone()[0]
        self.assertTrue(check_password_hash(hashed, "customer-password-1"))
        self.assertNotEqual(hashed, "customer-password-1")
        self.assertEqual(self.login_customer().status_code, 200)
        profile = self.client.get("/api/customer/profile")
        self.assertEqual(profile.json["name"], "Test Customer")
        updated = self.mutate(
            "/api/customer/profile",
            "PUT",
            {"name": "Updated Customer", "phone": "5551234567", "address": "New address"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.get("/api/customer/profile").json["address"], "New address")
        self.assertEqual(self.mutate("/api/customer/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/customer/profile").status_code, 401)

    def test_cart_checkout_order_snapshots_stock_and_order_ownership(self):
        self.register()
        self.login_customer()
        self.set_stock(1, 8)
        self.assertEqual(
            self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 2}).status_code,
            201,
        )
        cart = self.client.get("/api/cart").json
        self.assertEqual(cart["count"], 2)
        self.assertEqual(cart["total"], 1300)
        item_id = cart["items"][0]["item_id"]
        self.assertEqual(self.mutate(f"/api/cart/items/{item_id}", "PATCH", {"quantity": 3}).status_code, 200)
        self.assertEqual(self.client.get("/api/cart").json["total"], 1950)
        order_response = self.mutate(
            "/api/checkout",
            json={
                "delivery_address": "Delivery Address",
                "total": 1,
                "items": [{"id": 999999, "price": 0, "quantity": 999}],
            },
        )
        self.assertEqual(order_response.status_code, 201, order_response.json)
        order_id = order_response.json["order_id"]
        self.assertEqual(order_response.json["total"], 1950)
        self.assertEqual(self.client.get("/api/cart").json["count"], 0)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0], 5)
        self.assertEqual(self.client.get(f"/api/customer/orders/{order_id}").json["items"][0]["product_name"], "Castrol Engine Oil")
        self.set_stock(1, 4)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE products SET name = ?, price = ? WHERE id = 1", ("Renamed later", 777))
        self.assertEqual(self.client.get(f"/api/customer/orders/{order_id}").json["items"][0]["product_name"], "Castrol Engine Oil")
        self.assertEqual(self.client.get(f"/api/customer/orders/{order_id}").json["items"][0]["price"], 650)
        history = self.client.get("/api/customer/orders")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json[0]["id"], order_id)
        self.register("5557654321", "Other Customer")
        self.login_customer("5557654321")
        self.assertEqual(self.client.get(f"/api/customer/orders/{order_id}").status_code, 404)

    def test_cart_quantity_validation_and_stock_limits(self):
        self.register()
        self.login_customer()
        self.set_stock(1, 1)
        self.assertEqual(
            self.mutate("/api/cart/items", json={"product_id": 14, "quantity": 1}).status_code,
            400,
        )
        self.assertEqual(self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 2}).status_code, 409)
        self.assertEqual(self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 1}).status_code, 201)
        item_id = self.client.get("/api/cart").json["items"][0]["item_id"]
        self.assertEqual(self.mutate(f"/api/cart/items/{item_id}", "PATCH", {"quantity": 0}).status_code, 400)
        self.assertEqual(self.mutate(f"/api/cart/items/{item_id}", "PATCH", {"quantity": 2}).status_code, 409)
        self.assertEqual(self.mutate(f"/api/cart/items/{item_id}", "DELETE").status_code, 200)

    def test_admin_crud_stock_orders_returns_and_customer_denial(self):
        self.register()
        self.login_customer()
        self.assertEqual(self.client.get("/api/admin/dashboard").status_code, 401)
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.set_stock(1, 4)
        self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 1})
        order = self.mutate("/api/checkout", json={"delivery_address": "10 Test Street"}).json

        self.client.post("/api/customer/logout", headers={"X-CSRF-Token": self.token()})
        self.create_admin()
        self.assertEqual(self.login_admin().status_code, 200)
        self.assertEqual(self.client.get("/api/admin/dashboard").status_code, 200)
        self.assertEqual(len(self.client.get("/api/admin/products").json), 22)
        new_product = self.mutate(
            "/api/admin/products",
            json={
                "brand": "TEST",
                "name": "Test Accessory",
                "description": "Test item",
                "price": 120,
                "image": "",
                "stock": 3,
            },
        )
        self.assertEqual(new_product.status_code, 201)
        product_id = new_product.json["id"]
        self.assertEqual(
            self.mutate(f"/api/admin/products/{product_id}/stock", "PATCH", {"stock": 7}).status_code,
            200,
        )
        self.assertEqual(
            self.mutate(
                f"/api/admin/products/{product_id}",
                "PUT",
                {"brand": "TEST", "name": "Updated Accessory", "description": "", "price": 140, "image": "", "stock": 7},
            ).status_code,
            200,
        )
        self.assertEqual(self.mutate(f"/api/admin/orders/{order['order_id']}/status", "PATCH", {"status": "Delivered"}).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/orders").status_code, 200)
        self.assertEqual(self.client.get(f"/api/admin/orders/{order['order_id']}").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/customers").status_code, 200)

        # Return requests are customer-only and become eligible only after delivery.
        self.mutate("/api/admin/logout")
        self.login_customer()
        return_response = self.mutate(
            "/api/customer/returns",
            json={"order_id": order["order_id"], "reason": "Part does not fit"},
        )
        self.assertEqual(return_response.status_code, 201, return_response.json)
        customer_returns = self.client.get("/api/customer/returns")
        self.assertEqual(customer_returns.status_code, 200)
        self.assertEqual(customer_returns.json[0]["id"], return_response.json["return_id"])
        self.assertEqual(
            self.mutate("/api/customer/returns", json={"order_id": order["order_id"], "reason": "Duplicate"}).status_code,
            409,
        )
        self.mutate("/api/customer/logout")
        self.login_admin()
        self.assertEqual(
            self.mutate(
                f"/api/admin/returns/{return_response.json['return_id']}/status",
                "PATCH",
                {"status": "Approved"},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/admin/returns").json[0]["status"], "Approved")
        self.assertEqual(
            self.mutate(
                f"/api/admin/returns/{return_response.json['return_id']}/status",
                "PATCH",
                {"status": "Rejected"},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/admin/returns").json[0]["status"], "Rejected")
        self.assertEqual(self.mutate(f"/api/admin/products/{product_id}", "DELETE").status_code, 200)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ?", (order["order_id"],)).fetchone()[0], 1)

    def test_return_window_is_seven_days_from_delivery(self):
        self.register()
        self.login_customer()
        self.set_stock(1, 2)
        self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 1})
        order_id = self.mutate("/api/checkout", json={"delivery_address": "10 Test Street"}).json["order_id"]
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute(
                "UPDATE orders SET status = 'Delivered', delivered_at = ? WHERE id = ?",
                ((datetime.now(timezone.utc) - timedelta(days=8)).isoformat(), order_id),
            )
        response = self.mutate("/api/customer/returns", json={"order_id": order_id, "reason": "Too late"})
        self.assertEqual(response.status_code, 409)

    def test_cancelling_an_order_restocks_once(self):
        self.register()
        self.login_customer()
        self.set_stock(1, 2)
        self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 1})
        order_id = self.mutate("/api/checkout", json={"delivery_address": "10 Test Street"}).json["order_id"]
        self.mutate("/api/customer/logout")
        self.create_admin()
        self.login_admin()
        response = self.mutate(f"/api/admin/orders/{order_id}/status", "PATCH", {"status": "Cancelled"})
        self.assertEqual(response.status_code, 200)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0], 2)
        self.assertEqual(
            self.mutate(f"/api/admin/orders/{order_id}/status", "PATCH", {"status": "Cancelled"}).status_code,
            200,
        )
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0], 2)
        self.assertEqual(
            self.mutate(f"/api/admin/orders/{order_id}/status", "PATCH", {"status": "Processing"}).status_code,
            409,
        )

    def test_sessions_and_orders_persist_when_app_restarts(self):
        self.register()
        self.login_customer()
        self.set_stock(1, 3)
        self.mutate("/api/cart/items", json={"product_id": 1, "quantity": 1})
        order_id = self.mutate("/api/checkout", json={"delivery_address": "Persistent address"}).json["order_id"]
        restarted = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.database),
                "SECRET_KEY": "test-only-secret",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        restarted_client = restarted.test_client()
        with restarted_client.session_transaction() as restarted_session:
            restarted_session["csrf_token"] = "restart-test-csrf"
        login = restarted_client.post(
            "/api/customer/login",
            json={"phone": "5551234567", "password": "customer-password-1"},
            headers={"X-CSRF-Token": "restart-test-csrf"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(restarted_client.get(f"/api/customer/orders/{order_id}").status_code, 200)
        self.assertEqual(restarted_client.get(f"/api/customer/orders/{order_id}").json["delivery_address"], "Persistent address")
        self.assertEqual(len(restarted_client.get("/api/products").json), 22)

    def test_legacy_database_migration_preserves_records_and_hashes_passwords(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as db:
            db.executescript(
                """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT NOT NULL,
                    name TEXT NOT NULL, description TEXT, price REAL, image TEXT
                );
                CREATE TABLE owners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                    password TEXT NOT NULL
                );
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL, password TEXT NOT NULL, address TEXT
                );
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL,
                    total REAL NOT NULL, status TEXT DEFAULT 'Pending',
                    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );
                CREATE TABLE order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL, product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL, price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                );
                CREATE TABLE returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL, reason TEXT NOT NULL,
                    status TEXT DEFAULT 'Requested', return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );
                INSERT INTO products (id, brand, name, description, price, image)
                VALUES (1, 'CASTROL', 'Castrol Engine Oil', 'Legacy product', 650, 'castrol engine oil.jpg');
                INSERT INTO owners (id, username, password)
                VALUES (17, 'legacy-admin', 'legacy-owner-password');
                INSERT INTO customers (id, name, phone, password, address)
                VALUES (41, 'Legacy Customer', '5550000041', 'legacy-plain-password', 'Legacy address');
                INSERT INTO orders (id, customer_id, total, status)
                VALUES (71, 41, 650, 'Pending');
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (71, 1, 'Legacy order name', 1, 650);
                INSERT INTO returns (order_id, customer_id, reason, status)
                VALUES (71, 41, 'Legacy reason', 'Requested');
                """
            )
        migrated = create_app(
            {
                "TESTING": True,
                "DATABASE": str(legacy_path),
                "SECRET_KEY": "migration-test-secret",
            }
        )
        with closing(sqlite3.connect(legacy_path)) as db:
            admin_hash = db.execute(
                "SELECT password FROM users WHERE username = ?",
                ("legacy-admin",),
            ).fetchone()[0]
            self.assertTrue(check_password_hash(admin_hash, "legacy-owner-password"))
            self.assertNotIn(
                "owners",
                {
                    row[0]
                    for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
                },
            )
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0],
                1,
            )
            self.assertTrue(
                all(
                    check_password_hash(password, "legacy-plain-password")
                    for (password,) in db.execute("SELECT password FROM customers")
                )
            )
            self.assertTrue(
                all(
                    password.startswith(("scrypt:", "pbkdf2:"))
                    for (password,) in db.execute("SELECT password FROM users")
                )
            )
            customer_hash = db.execute("SELECT password FROM users WHERE id = 41").fetchone()[0]
            self.assertTrue(check_password_hash(customer_hash, "legacy-plain-password"))
            self.assertEqual(db.execute("SELECT user_id FROM orders WHERE id = 71").fetchone()[0], 41)
            self.assertEqual(db.execute("SELECT user_id FROM returns WHERE order_id = 71").fetchone()[0], 41)
            self.assertEqual(db.execute("SELECT product_name FROM order_items WHERE order_id = 71").fetchone()[0], "Legacy order name")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM products").fetchone()[0], 22)
        self.assertEqual(migrated.test_client().get("/api/products").status_code, 200)

    def test_csrf_protection_rejects_mutation_without_token(self):
        self.register()
        self.login_customer()
        response = self.client.post("/api/customer/logout")
        self.assertEqual(response.status_code, 400)

    def test_admin_setup_command_hashes_password_and_admin_login(self):
        result = self.app.test_cli_runner().invoke(
            args=["create-admin", "--username", "created-admin"],
            input="Administrator-password-123\nAdministrator-password-123\n",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("Administrator-password-123", result.output)
        with closing(sqlite3.connect(self.database)) as db:
            password = db.execute("SELECT password FROM users WHERE username = ?", ("created-admin",)).fetchone()[0]
        self.assertTrue(check_password_hash(password, "Administrator-password-123"))
        response = self.mutate(
            "/api/admin/login",
            json={"username": "created-admin", "password": "Administrator-password-123"},
        )
        self.assertEqual(response.status_code, 200)
        reset_result = self.app.test_cli_runner().invoke(
            args=["reset-admin", "--username", "created-admin"],
            input="Replacement-admin-password-456\nReplacement-admin-password-456\n",
        )
        self.assertEqual(reset_result.exit_code, 0, reset_result.output)
        self.assertNotIn("Replacement-admin-password-456", reset_result.output)
        with closing(sqlite3.connect(self.database)) as db:
            replacement_hash = db.execute(
                "SELECT password FROM users WHERE username = ?",
                ("created-admin",),
            ).fetchone()[0]
        self.assertTrue(check_password_hash(replacement_hash, "Replacement-admin-password-456"))
        self.assertEqual(
            self.mutate(
                "/api/admin/login",
                json={"username": "created-admin", "password": "Replacement-admin-password-456"},
            ).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
