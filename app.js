const express = require("express");
const path = require("path");

const app = express();
const PORT = 3000;

app.use("/static", express.static(path.join(__dirname, "static")));

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "home.html"));
});

app.get("/home.html", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "home.html"));
});

app.get("/products", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "products.html"));
});

app.get("/products.html", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "products.html"));
});

app.get("/cart", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "cart.html"));
});

app.get("/cart.html", (req, res) => {
    res.sendFile(path.join(__dirname, "templates", "cart.html"));
});
// Products API
app.get("/api/products", (req, res) => {
    const products = [
    // ==================== CASTROL ====================
    {
        id: 1,
        brand: "CASTROL",
        name: "Castrol Engine Oil",
        description: "High-quality engine oil for smooth and reliable engine performance.",
        price: 650,
        image: "castrol engine oil.jpg"
    },
    {
        id: 2,
        brand: "CASTROL",
        name: "Castrol Premium Engine Oil",
        description: "Premium protection designed for better performance and engine durability.",
        price: 850,
        image: "primiem engine oil.jpg.png"
    },
    {
        id: 3,
        brand: "CASTROL",
        name: "Castrol Chain Cleaner",
        description: "Helps remove dirt, grease and road grime from motorcycle chains.",
        price: 399,
        image: "Castrol Chain Cleaner.jpg.png"
    },
    {
        id: 4,
        brand: "CASTROL",
        name: "Castrol Chain Lubricant",
        description: "Provides smooth chain performance and helps reduce wear.",
        price: 449,
        image: "Castrol Chain lubricant.png"
    },

    // ==================== MOTUL ====================
    {
        id: 5,
        brand: "MOTUL",
        name: "Motul Engine Oil",
        description: "High-performance engine oil for smooth and reliable motorcycle performance.",
        price: 750,
        image: "motul engine oil.png"
    },
    {
        id: 6,
        brand: "MOTUL",
        name: "Motul C1 Chain Clean",
        description: "Powerful cleaner that removes dirt and grease from motorcycle chains.",
        price: 399,
        image: "moto chain cleanser.jpg"
    },
    {
        id: 7,
        brand: "MOTUL",
        name: "Motul C2 Chain Lube",
        description: "Long-lasting lubricant for smooth and reliable chain performance.",
        price: 449,
        image: "chain lubricant.jpg"
    },
    {
        id: 8,
        brand: "MOTUL",
        name: "Motul Bike Care",
        description: "Premium bike care product to help keep your motorcycle clean and protected.",
        price: 499,
        image: "motul bike product.webp"
    },

    // ==================== HERO ====================
    {
        id: 9,
        brand: "HERO",
        name: "Hero Engine Guard",
        description: "Strong protection for your motorcycle engine during everyday rides.",
        price: 2499,
        image: "engine-guard.jpg"
    },
    {
        id: 10,
        brand: "HERO",
        name: "Hero Side Stand",
        description: "Strong and reliable side stand designed for daily motorcycle use.",
        price: 899,
        image: "hero side stand.jpg"
    },
    {
        id: 11,
        brand: "HERO",
        name: "Hero Body Graphics & Stickers",
        description: "Stylish graphics and stickers to customize your motorcycle.",
        price: 599,
        image: "Hero Body Graphics & Stickers.jpg"
    },
    {
        id: 12,
        brand: "HERO",
        name: "Hero Tank Pad",
        description: "Helps protect the fuel tank from scratches and everyday wear.",
        price: 399,
        image: "Hero tank pad.jpg"
    },
    {
        id: 13,
        brand: "HERO",
        name: "Hero Motorcycle Visor",
        description: "Stylish visor designed to improve wind protection.",
        price: 1099,
        image: "visor.jpg"
    },
    {
        id: 14,
        brand: "HERO",
        name: "Hero Genuine Spare Parts",
        description: "Genuine replacement parts for reliable motorcycle maintenance.",
        price: null,
        image: "hero genuine parts.jpg"
    },

    // ==================== TVS ====================
    {
        id: 15,
        brand: "TVS",
        name: "TVS Engine Guard",
        description: "Strong protection designed to help protect your motorcycle engine.",
        price: 2499,
        image: "TVS Engine Guard.jpg"
    },
    {
        id: 16,
        brand: "TVS",
        name: "TVS Side Stand",
        description: "Strong and durable side stand suitable for daily motorcycle use.",
        price: 899,
        image: "tvs-side-stand.jpg"
    },
    {
        id: 17,
        brand: "TVS",
        name: "TVS Tank Pad",
        description: "Helps protect the motorcycle fuel tank from scratches and wear.",
        price: 399,
        image: "tvs-tank-pad.jpg"
    },
    {
        id: 18,
        brand: "TVS",
        name: "TVS Motorcycle Visor",
        description: "Stylish visor designed to provide better wind protection.",
        price: 1099,
        image: "TVS Motorcycle Visor.jpg"
    },
    {
        id: 19,
        brand: "TVS",
        name: "TVS Genuine Spare Parts",
        description: "Genuine replacement spare parts for reliable motorcycle maintenance.",
        price: null,
        image: "tvs-spare-parts.jpg"
    },

    // ==================== COMMON ACCESSORIES ====================
    {
        id: 20,
        brand: "ACCESSORIES",
        name: "Motorcycle Mobile Holder",
        description: "Strong and secure mobile holder suitable for multiple motorcycle brands.",
        price: 799,
        image: "mobile holder.jpg"
    },
    {
        id: 21,
        brand: "ACCESSORIES",
        name: "Motorcycle Foot Mat",
        description: "Durable foot mat designed for improved comfort and protection.",
        price: 499,
        image: "footmat.jpg"
    },
    {
        id: 22,
        brand: "ACCESSORIES",
        name: "Motorcycle Luggage Accessories",
        description: "Useful luggage accessories designed for carrying items safely.",
        price: 1499,
        image: "lugguage accessaaries.jpg"
    }
];

    res.json(products);
});


app.listen(PORT, () => {
    console.log(`Sun Auto Centre running at http://localhost:${PORT}`);
});