const db = require("./database");

const products = [
    // CASTROL
    {
        brand: "CASTROL",
        name: "Castrol Engine Oil",
        description: "High-quality engine oil for smooth and reliable engine performance.",
        price: 650,
        image: "castrol engine oil.jpg"
    },
    {
        brand: "CASTROL",
        name: "Castrol Premium Engine Oil",
        description: "Premium protection designed for better performance and engine durability.",
        price: 850,
        image: "primiem engine oil.jpg.png"
    },
    {
        brand: "CASTROL",
        name: "Castrol Chain Cleaner",
        description: "Helps remove dirt, grease and road grime from motorcycle chains.",
        price: 399,
        image: "Castrol Chain Cleaner.jpg.png"
    },
    {
        brand: "CASTROL",
        name: "Castrol Chain Lubricant",
        description: "Provides smooth chain performance and helps reduce wear.",
        price: 449,
        image: "Castrol Chain lubricant.png"
    },

    // MOTUL
    {
        brand: "MOTUL",
        name: "Motul Engine Oil",
        description: "High-performance engine oil for smooth and reliable motorcycle performance.",
        price: 750,
        image: "motul engine oil.png"
    },
    {
        brand: "MOTUL",
        name: "Motul C1 Chain Clean",
        description: "Powerful cleaner that removes dirt and grease from motorcycle chains.",
        price: 399,
        image: "moto chain cleanser.jpg"
    },
    {
        brand: "MOTUL",
        name: "Motul C2 Chain Lube",
        description: "Long-lasting lubricant for smooth and reliable chain performance.",
        price: 449,
        image: "chain lubricant.jpg"
    },
    {
        brand: "MOTUL",
        name: "Motul Bike Care",
        description: "Premium bike care product to help keep your motorcycle clean and protected.",
        price: 499,
        image: "motul bike product.webp"
    },

    // HERO
    {
        brand: "HERO",
        name: "Hero Engine Guard",
        description: "Strong protection for your motorcycle engine during everyday rides.",
        price: 2499,
        image: "engine-guard.jpg"
    },
    {
        brand: "HERO",
        name: "Hero Side Stand",
        description: "Strong and reliable side stand designed for daily motorcycle use.",
        price: 899,
        image: "hero side stand.jpg"
    },
    {
        brand: "HERO",
        name: "Hero Body Graphics & Stickers",
        description: "Stylish graphics and stickers to customize your motorcycle.",
        price: 599,
        image: "Hero Body Graphics & Stickers.jpg"
    },
    {
        brand: "HERO",
        name: "Hero Tank Pad",
        description: "Helps protect the fuel tank from scratches and everyday wear.",
        price: 399,
        image: "Hero tank pad.jpg"
    },
    {
        brand: "HERO",
        name: "Hero Motorcycle Visor",
        description: "Stylish visor designed to improve wind protection.",
        price: 1099,
        image: "visor.jpg"
    },
    {
        brand: "HERO",
        name: "Hero Genuine Spare Parts",
        description: "Genuine replacement parts for reliable motorcycle maintenance.",
        price: null,
        image: "hero genuine parts.jpg"
    },

    // TVS
    {
        brand: "TVS",
        name: "TVS Engine Guard",
        description: "Strong protection designed to help protect your motorcycle engine.",
        price: 2499,
        image: "TVS Engine Guard.jpg"
    },
    {
        brand: "TVS",
        name: "TVS Side Stand",
        description: "Strong and durable side stand suitable for daily motorcycle use.",
        price: 899,
        image: "tvs-side-stand.jpg"
    },
    {
        brand: "TVS",
        name: "TVS Tank Pad",
        description: "Helps protect the motorcycle fuel tank from scratches and wear.",
        price: 399,
        image: "tvs-tank-pad.jpg"
    },
    {
        brand: "TVS",
        name: "TVS Motorcycle Visor",
        description: "Stylish visor designed to provide better wind protection.",
        price: 1099,
        image: "TVS Motorcycle Visor.jpg"
    },
    {
        brand: "TVS",
        name: "TVS Genuine Spare Parts",
        description: "Genuine replacement spare parts for reliable motorcycle maintenance.",
        price: null,
        image: "tvs-spare-parts.jpg"
    },

    // ACCESSORIES
    {
        brand: "ACCESSORIES",
        name: "Motorcycle Mobile Holder",
        description: "Strong and secure mobile holder suitable for multiple motorcycle brands.",
        price: 799,
        image: "mobile holder.jpg"
    },
    {
        brand: "ACCESSORIES",
        name: "Motorcycle Foot Mat",
        description: "Durable foot mat designed for improved comfort and protection.",
        price: 499,
        image: "footmat.jpg"
    },
    {
        brand: "ACCESSORIES",
        name: "Motorcycle Luggage Accessories",
        description: "Useful luggage accessories designed for carrying items safely.",
        price: 1499,
        image: "lugguage accessaaries.jpg"
    }
];

const insert = db.prepare(`
    INSERT INTO products
    (brand, name, description, price, image)
    VALUES (?, ?, ?, ?, ?)
`);

const insertMany = db.transaction((products) => {

    for (const product of products) {

        insert.run(
            product.brand,
            product.name,
            product.description,
            product.price,
            product.image
        );

    }

});

insertMany(products);

console.log(`${products.length} products inserted successfully!`);