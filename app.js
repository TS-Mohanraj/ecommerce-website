const express = require("express");
const path = require("path");
const session = require("express-session");
const bcrypt = require("bcryptjs");
const db = require("./database");

const app = express();
const PORT = 3000;


// ===============================
// MIDDLEWARE
// ===============================
app.use(express.json());

app.use(
    session({
        secret: "sun-auto-centre-secret",
        resave: false,
        saveUninitialized: false,
        cookie: {
            httpOnly: true
        }
    })
);

app.use(
    "/static",
    express.static(path.join(__dirname, "static"))
);


// ===============================
// CUSTOMER PAGES
// ===============================

app.get("/", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "home.html")
    );
});


app.get("/home.html", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "home.html")
    );
});


app.get("/products", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "products.html")
    );
});


app.get("/products.html", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "products.html")
    );
});


app.get("/cart", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "cart.html")
    );
});


app.get("/cart.html", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "cart.html")
    );
});


// ===============================
// TEST PAGE
// ===============================

app.get("/test.html", (req, res) => {
    res.sendFile(
        path.join(__dirname, "templates", "test.html")
    );
});
app.get("/owner-login", (req, res) => {

    res.sendFile(
        path.join(
            __dirname,
            "templates",
            "owner-login.html"
        )
    );

});
function requireOwner(req, res, next) {
    if (!req.session.ownerId) {
        return res.status(401).json({
            error: "Owner login required"
        });
    }

    next();
}

function requireOwnerPage(req, res, next) {
    if (!req.session.ownerId) {
        return res.redirect("/owner-login");
    }

    next();
}
app.get(
    "/owner-dashboard",
    requireOwnerPage,
    (req, res) => {
        res.sendFile(
            path.join(
                __dirname,
                "templates",
                "owner-dashboard.html"
            )
        );
    }
);

// ===============================
// GET ALL PRODUCTS
// ===============================

app.get("/api/products", (req, res) => {

    try {

        const products = db
            .prepare("SELECT * FROM products")
            .all();

        res.json(products);

    } catch (error) {

        console.error(
            "Error loading products:",
            error
        );

        res.status(500).json({
            error: "Failed to load products"
        });

    }

});


// ===============================
// ADD PRODUCT
// ===============================

app.post("/api/products", (req, res) => {

    try {

        const {
            brand,
            name,
            description,
            price,
            image
        } = req.body;


        // Check required fields

        if (!brand || !name) {

            return res.status(400).json({
                error:
                    "Brand and product name are required"
            });

        }


        // Insert product into database

        const result = db.prepare(`
            INSERT INTO products
            (brand, name, description, price, image)
            VALUES (?, ?, ?, ?, ?)
        `).run(

            brand,

            name,

            description || "",

            price || null,

            image || ""

        );


        // Send response

        res.status(201).json({

            message:
                "Product added successfully",

            productId:
                result.lastInsertRowid

        });


    } catch (error) {

        console.error(
            "Error adding product:",
            error
        );

        res.status(500).json({

            error:
                "Failed to add product"

        });

    }

});


// ===============================
// UPDATE PRODUCT
// ===============================

app.put("/api/products/:id", (req, res) => {

    try {

        // Get ID from URL

        const id = req.params.id;


        // Get updated data

        const {
            brand,
            name,
            description,
            price,
            image
        } = req.body;


        // Check required fields

        if (!brand || !name) {

            return res.status(400).json({

                error:
                    "Brand and product name are required"

            });

        }


        // Check whether product exists

        const existingProduct = db
            .prepare(
                "SELECT * FROM products WHERE id = ?"
            )
            .get(id);


        if (!existingProduct) {

            return res.status(404).json({

                error:
                    "Product not found"

            });

        }


        // Update product

        db.prepare(`
            UPDATE products
            SET
                brand = ?,
                name = ?,
                description = ?,
                price = ?,
                image = ?
            WHERE id = ?
        `).run(

            brand,

            name,

            description || "",

            price || null,

            image || "",

            id

        );


        // Send response

        res.json({

            message:
                "Product updated successfully"

        });


    } catch (error) {

        console.error(
            "Error updating product:",
            error
        );

        res.status(500).json({

            error:
                "Failed to update product"

        });

    }

});
// ===============================
// DELETE PRODUCT
// ===============================

app.delete("/api/products/:id", (req, res) => {

    try {

        // Get product ID from URL

        const id = req.params.id;


        // Check whether product exists

        const existingProduct = db
            .prepare(
                "SELECT * FROM products WHERE id = ?"
            )
            .get(id);


        if (!existingProduct) {

            return res.status(404).json({

                error: "Product not found"

            });

        }


        // Delete product

        db.prepare(
            "DELETE FROM products WHERE id = ?"
        ).run(id);


        // Send response

        res.json({

            message:
                "Product deleted successfully",

            productId: id

        });


    } catch (error) {

        console.error(
            "Error deleting product:",
            error
        );

        res.status(500).json({

            error:
                "Failed to delete product"

        });

    }

});
// ===============================
// OWNER LOGIN
// ===============================

app.post("/api/owner/login", (req, res) => {

    try {

        const {
            username,
            password
        } = req.body;


        // Check input

        if (!username || !password) {

            return res.status(400).json({
                error: "Username and password are required"
            });

        }


        // Find owner

        const owner = db
            .prepare(
                "SELECT * FROM owners WHERE username = ?"
            )
            .get(username);


        if (!owner) {

            return res.status(401).json({
                error: "Invalid username or password"
            });

        }


        // Compare password

        const passwordMatch =
            bcrypt.compareSync(
                password,
                owner.password
            );


        if (!passwordMatch) {

            return res.status(401).json({
                error: "Invalid username or password"
            });

        }


        // Create login session

        req.session.ownerId = owner.id;
        req.session.ownerUsername = owner.username;


        res.json({
            message: "Login successful"
        });


    } catch (error) {

        console.error(
            "Owner login error:",
            error
        );

        res.status(500).json({
            error: "Login failed"
        });

    }

});

// ===============================
// START SERVER
// ===============================

app.listen(PORT, () => {

    console.log(
        `Sun Auto Centre running at http://localhost:${PORT}`
    );

});