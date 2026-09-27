from flask import Flask, render_template, request,session

app = Flask(__name__)
app.secret_key = "sun_auto_centre_secret"

import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

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
        return {
            "message": "Login successful",
            "customer": dict(customer)
        }

    return {"message": "Invalid mobile number or password"}, 401

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


# ===============================
# START FLASK
# ===============================

if __name__ == "__main__":
    app.run(debug=True)