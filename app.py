from flask import Flask, render_template, request, session
import sqlite3


app = Flask(__name__)

app.secret_key = "sun_auto_centre_secret"

DATABASE = "database/products.db"

print("DATABASE PATH:", DATABASE)


# =========================================================
# CUSTOMER PAGES
# =========================================================

@app.route("/")
@app.route("/home.html")
def home():

    customer_logged_in = session.get("customer_id") is not None

    return render_template(
        "home.html",
        customer_logged_in=customer_logged_in
    )


@app.route("/products")
@app.route("/products.html")
def products():

    return render_template("products.html")


@app.route("/cart")
@app.route("/cart.html")
def cart():

    return render_template("cart.html")


@app.route("/customer-login")
def customer_login():

    return render_template("customer-login.html")


@app.route("/customer-register")
def customer_register():

    return render_template("customer-register.html")


@app.route("/customer-account")
def customer_account():

    return render_template("customer-account.html")


@app.route("/customer-orders")
def customer_orders():

    return render_template("customer-orders.html")


@app.route("/customer-returns")
def customer_returns():

    return render_template("customer-returns.html")


# =========================================================
# PRODUCT API
# =========================================================

@app.route("/api/products")
def get_products():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    products = conn.execute("""
        SELECT *
        FROM products
    """).fetchall()

    conn.close()

    return [dict(product) for product in products]


# =========================================================
# CUSTOMER REGISTER
# =========================================================

@app.route("/api/customer/register", methods=["POST"])
def register_customer():

    data = request.get_json()

    name = data["name"]
    phone = data["phone"]
    password = data["password"]
    address = data["address"]

    conn = sqlite3.connect(DATABASE)

    try:

        conn.execute("""
            INSERT INTO customers
            (name, phone, password, address)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            phone,
            password,
            address
        ))

        conn.commit()

        return {
            "message": "Registration successful"
        }

    except sqlite3.IntegrityError:

        return {
            "message": "Mobile number already registered"
        }, 400

    finally:

        conn.close()


# =========================================================
# CUSTOMER LOGIN
# =========================================================

@app.route("/api/customer/login", methods=["POST"])
def login_customer():

    data = request.get_json()

    phone = data["phone"]
    password = data["password"]

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    customer = conn.execute("""
        SELECT *
        FROM customers
        WHERE phone = ?
        AND password = ?
    """, (
        phone,
        password
    )).fetchone()

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

    return {
        "message": "Invalid mobile number or password"
    }, 401


# =========================================================
# CUSTOMER PROFILE
# =========================================================

@app.route("/api/customer/profile")
def customer_profile():

    customer_id = session.get("customer_id")

    if not customer_id:

        return {
            "message": "Please login first"
        }, 401

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    customer = conn.execute("""
        SELECT
            id,
            name,
            phone,
            address
        FROM customers
        WHERE id = ?
    """, (
        customer_id,
    )).fetchone()

    conn.close()

    if not customer:

        return {
            "message": "Customer not found"
        }, 404

    return dict(customer)


# =========================================================
# CUSTOMER LOGOUT
# =========================================================

@app.route("/api/customer/logout", methods=["POST"])
def logout_customer():

    session.pop("customer_id", None)
    session.pop("customer_name", None)
    session.pop("customer_phone", None)

    return {
        "message": "Logout successful"
    }


# =========================================================
# CREATE ORDER
# =========================================================

@app.route("/api/orders", methods=["POST"])
def create_order():

    customer_id = session.get("customer_id")

    if not customer_id:

        return {
            "message": "Please login first"
        }, 401

    data = request.get_json()

    total = data["total"]
    items = data["items"]

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    # Create order

    cursor.execute("""
        INSERT INTO orders
        (customer_id, total)
        VALUES (?, ?)
    """, (
        customer_id,
        total
    ))

    order_id = cursor.lastrowid


    # Add order items

    for item in items:

        cursor.execute("""
            INSERT INTO order_items
            (
                order_id,
                product_id,
                product_name,
                quantity,
                price
            )
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


# =========================================================
# CUSTOMER ORDERS
# =========================================================

@app.route("/api/customer/orders")
def customer_orders_api():

    customer_id = session.get("customer_id")

    if not customer_id:

        return {
            "message": "Please login first"
        }, 401

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row


    # Get customer orders

    orders = conn.execute("""
        SELECT
            o.id,
            o.total,
            o.status,
            o.order_date,
            r.id AS return_id,
            r.status AS return_status
        FROM orders o

        LEFT JOIN returns r
            ON o.id = r.order_id
            AND r.customer_id = ?

        WHERE o.customer_id = ?

        ORDER BY o.id DESC
    """, (
        customer_id,
        customer_id
    )).fetchall()


    result = []


    # Get products inside every order

    for order in orders:

        items = conn.execute("""
            SELECT
                product_id,
                product_name,
                quantity,
                price
            FROM order_items
            WHERE order_id = ?
        """, (
            order["id"],
        )).fetchall()


        result.append({

            "id": order["id"],

            "total": order["total"],

            "status": order["status"],

            "order_date": order["order_date"],

            "return_id": order["return_id"],

            "return_status": order["return_status"],

            "items": [
                dict(item)
                for item in items
            ]

        })


    conn.close()

    return result


# =========================================================
# CREATE RETURN REQUEST
# =========================================================

@app.route("/api/customer/returns", methods=["POST"])
def create_return():

    customer_id = session.get("customer_id")

    if not customer_id:

        return {
            "message": "Please login first"
        }, 401


    data = request.get_json()

    order_id = data.get("order_id")

    reason = data.get("reason")


    if not order_id or not reason:

        return {
            "message": "Order ID and return reason are required"
        }, 400


    conn = sqlite3.connect(DATABASE)


    # -----------------------------------------------------
    # Check whether order belongs to logged-in customer
    # -----------------------------------------------------

    order = conn.execute("""
        SELECT id
        FROM orders
        WHERE id = ?
        AND customer_id = ?
    """, (
        order_id,
        customer_id
    )).fetchone()


    if not order:

        conn.close()

        return {
            "message": "Order not found"
        }, 404


    # -----------------------------------------------------
    # Check duplicate return request
    # -----------------------------------------------------

    existing_return = conn.execute("""
        SELECT id
        FROM returns
        WHERE order_id = ?
        AND customer_id = ?
    """, (
        order_id,
        customer_id
    )).fetchone()


    if existing_return:

        conn.close()

        return {
            "message": "A return request already exists for this order"
        }, 400


    # -----------------------------------------------------
    # Create return request
    # -----------------------------------------------------

    conn.execute("""
        INSERT INTO returns
        (
            order_id,
            customer_id,
            reason
        )
        VALUES (?, ?, ?)
    """, (
        order_id,
        customer_id,
        reason
    ))


    conn.commit()
    conn.close()


    return {
        "message": "Return request submitted successfully"
    }


# =========================================================
# GET CUSTOMER RETURNS
# =========================================================

@app.route("/api/customer/returns")
def get_customer_returns():

    customer_id = session.get("customer_id")

    if not customer_id:

        return {
            "message": "Please login first"
        }, 401


    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row


    returns = conn.execute("""
        SELECT
            r.id,
            r.order_id,
            r.reason,
            r.status,
            r.return_date,
            o.total
        FROM returns r

        JOIN orders o
            ON r.order_id = o.id

        WHERE r.customer_id = ?

        ORDER BY r.id DESC
    """, (
        customer_id,
    )).fetchall()


    conn.close()


    return [
        dict(item)
        for item in returns
    ]


# =========================================================
# OWNER PAGES
# =========================================================

@app.route("/owner-login")
def owner_login():

    return render_template("owner-login.html")


@app.route("/owner-dashboard")
def owner_dashboard():

    return render_template("owner-dashboard.html")


# =========================================================
# START FLASK
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)