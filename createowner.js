const bcrypt = require("bcryptjs");
const db = require("./database");


// Owner login details

const username = "owner";
const password = "1234";


// Convert password into a secure hash

const hashedPassword = bcrypt.hashSync(password, 10);


// Insert owner

try {
    db.prepare(`
        INSERT INTO owners
        (username, password)
        VALUES (?, ?)
    `).run(
        username,
        hashedPassword
    );

    console.log("Owner account created successfully");

} catch (error) {

    console.log("Owner account may already exist");

}