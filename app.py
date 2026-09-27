from flask import Flask, render_template, request, session
import sqlite3

app = Flask(__name__)

app.secret_key = "sun_auto_centre_secret"

DATABASE = "database/products.db"

print("DATABASE PATH:", DATABASE)


# ===============================
# CUSTOMER PAGES
# ===============================

@app.route("/")
@app.route("/home.html")
def home():
    return render_template("home.html")


@app.route("/products")
@app.route("/products.html")
def products():
    return render_template("products.html")

@app.route("/api/products")
def get_products():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()

    conn.close()

    return [dict(product) for product in products]


@app.route("/cart")
@app.route("/cart.html")
def cart():
    return render_template("cart.html")


# ===============================
# OWNER PAGES
# ===============================

@app.route("/owner-login")
def owner_login():
    return render_template("owner-login.html")


@app.route("/owner-dashboard")
def owner_dashboard():
    return render_template("owner-dashboard.html")

@app.route("/customer-login")
def customer_login():
    return render_template("customer-login.html")

@app.route("/api/customer/login", methods=["POST"])
def login_customer():

    data = request.get_json()

    phone = data["phone"]
    password = data["password"]

    conn = sqlite3.connect("database/products.db")
    conn.row_factory = sqlite3.Row

    customer = conn.execute("""
        SELECT * FROM customers
        WHERE phone = ? AND password = ?
    """, (phone, password)).fetchone()

    conn.close()

    if customer:

         session["customer_id"] = customer["id"]
         session["customer_name"] = customer["name"]
         session["customer_phone"] = customer["phone"]

         print("SESSION SAVED:", dict(session))

         return {
              "message": "Login successful",
              "customer": dict(customer)
    }

    return {"message": "Invalid mobile number or password"}, 401

@app.route("/api/customer/profile")
def customer_profile():

    customer_id = session.get("customer_id")

    if not customer_id:
        return {"message": "Please login first"}, 401

    conn = sqlite3.connect("database/products.db")
    conn.row_factory = sqlite3.Row

    customer = conn.execute("""
        SELECT id, name, phone, address
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    conn.close()

    if not customer:
        return {"message": "Customer not found"}, 404

    return dict(customer)


@app.route("/customer-register")
def customer_register():
    return render_template("customer-register.html")

@app.route("/api/customer/register", methods=["POST"])
def register_customer():

    data = request.get_json()

    name = data["name"]
    phone = data["phone"]
    password = data["password"]
    address = data["address"]

    conn = sqlite3.connect("database/products.db")

    try:
        conn.execute("""
            INSERT INTO customers (name, phone, password, address)
            VALUES (?, ?, ?, ?)
        """, (name, phone, password, address))

        conn.commit()

        return {"message": "Registration successful"}

    except sqlite3.IntegrityError:
        return {"message": "Mobile number already registered"}, 400

    finally:
        conn.close()


@app.route("/api/orders", methods=["POST"])
def create_order():

    customer_id = session.get("customer_id")

    if not customer_id:
        return {"message": "Please login first"}, 401

    data = request.get_json()

    total = data["total"]
    items = data["items"]

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    # Create order
    cursor.execute("""
        INSERT INTO orders (customer_id, total)
        VALUES (?, ?)
    """, (customer_id, total))

    order_id = cursor.lastrowid

    # Add order items
    for item in items:
        cursor.execute("""
            INSERT INTO order_items
            (order_id, product_id, product_name, quantity, price)
            VALUES (?, ?, ?, ?, ?)
        """, (
            order_id,
            item["id"],
            item["name"],
            item["quantity"],
            item["price"]
        ))

    conn.commit()
    conn.close()

    return {
        "message": "Order placed successfully",
        "order_id": order_id
    }
    


# ===============================
# START FLASK
# ===============================

if __name__ == "__main__":
    app.run(debug=True)