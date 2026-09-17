const Database = require("better-sqlite3");

const db = new Database("./database/products.db");


// ===============================
// PRODUCTS TABLE
// ===============================

db.prepare(`
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price REAL,
        image TEXT
    )
`).run();


// ===============================
// OWNERS TABLE
// ===============================

db.prepare(`
    CREATE TABLE IF NOT EXISTS owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
`).run();


console.log("Database connected successfully");

module.exports = db;