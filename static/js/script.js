// =====================================================
// SUN AUTO CENTRE - MAIN SCRIPT
// =====================================================


// =====================================================
// LOAD PRODUCTS FROM FLASK API
// =====================================================

async function loadProducts() {

    const container =
        document.getElementById("products-container");

    // Products page only
    if (!container) {
        return;
    }

    try {

        const response =
            await fetch("/api/products");

        if (!response.ok) {
            throw new Error("Failed to load products");
        }

        const products =
            await response.json();

        container.innerHTML = "";


        // =============================================
        // GROUP PRODUCTS BY BRAND
        // =============================================

        const brands = {

            CASTROL: "castrol-products",

            MOTUL: "motul-products",

            HERO: "hero-products",

            TVS: "tvs-products",

            ACCESSORIES: "accessories-products"

        };


        Object.keys(brands).forEach(function (brand) {

            const brandProducts =
                products.filter(function (product) {

                    return product.brand === brand;

                });


            if (brandProducts.length === 0) {
                return;
            }


            // =========================================
            // BRAND SECTION
            // =========================================

            const section =
                document.createElement("div");

            section.id =
                brands[brand];

            section.className =
                "brand-product-section";


            section.innerHTML = `

                <h2 class="text-center mb-4">
                    ${brand}
                </h2>

            `;


            // =========================================
            // PRODUCT ROW
            // =========================================

            const row =
                document.createElement("div");

            row.className =
                "row";


            brandProducts.forEach(function (product) {


                // =====================================
                // PRODUCT CARD
                // =====================================

                const productHTML = `

                    <div class="col-md-4 mb-4">

                        <div
                            class="product-card"
                            data-id="${product.id}"
                        >

                            <img
                                src="../static/img/${product.image}"
                                alt="${product.name}"
                                class="product-image"
                            >

                            <span class="product-brand">
                                ${product.brand}
                            </span>

                            <h4>
                                ${product.name}
                            </h4>

                            <p>
                                ${product.description || ""}
                            </p>

                            <h5>
                                ${
                                    product.price !== null &&
                                    product.price !== undefined
                                        ? "₹" +
                                          Number(product.price)
                                          .toLocaleString("en-IN")
                                        : "Contact for Price"
                                }
                            </h5>

                            <button
                                type="button"
                                class="btn btn-warning add-cart"
                            >
                                Add to Cart
                            </button>

                        </div>

                    </div>

                `;


                row.innerHTML +=
                    productHTML;

            });


            section.appendChild(row);

            container.appendChild(section);

        });


    } catch (error) {

        console.error(
            "Error loading products:",
            error
        );

    }

}


// =====================================================
// SHOPPING CART
// =====================================================

let cart =
    JSON.parse(localStorage.getItem("cart")) || [];


// =====================================================
// UPDATE CART COUNT
// =====================================================

function updateCartCount() {

    const cartCount =
        document.getElementById("cart-count");


    if (!cartCount) {
        return;
    }


    const count =
        cart.reduce(
            function (total, product) {

                return total +
                    (product.quantity || 1);

            },
            0
        );


    cartCount.textContent =
        count;

}


// =====================================================
// ADD PRODUCT TO CART
// =====================================================

function addToCart(button) {

    const productCard =
        button.closest(".product-card");


    if (!productCard) {

        console.error(
            "Product card not found"
        );

        return;
    }


    // Product ID from database
    const productId =
        productCard.dataset.id;


    const nameElement =
        productCard.querySelector("h4");


    const priceElement =
        productCard.querySelector("h5");


    const imageElement =
        productCard.querySelector(
            ".product-image"
        );


    if (
        !nameElement ||
        !priceElement ||
        !imageElement
    ) {

        console.error(
            "Product information missing"
        );

        return;
    }


    const productName =
        nameElement.textContent.trim();


    const productPrice =
        priceElement.textContent.trim();


    const productImage =
        imageElement.src;


    // =============================================
    // CHECK EXISTING PRODUCT
    // =============================================

    const existingProduct =
        cart.find(function (product) {

            return (
                String(product.id) ===
                String(productId)
                ||
                product.name ===
                productName
            );

        });


    if (existingProduct) {

        existingProduct.quantity =
            (existingProduct.quantity || 1) + 1;


        // Make sure old cart products get ID
        if (
            !existingProduct.id &&
            productId
        ) {

            existingProduct.id =
                productId;

        }

    } else {

        const product = {

            id: productId,

            name: productName,

            price: productPrice,

            image: productImage,

            quantity: 1

        };


        cart.push(product);

    }


    // =============================================
    // SAVE CART
    // =============================================

    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();


    showCartMessage(
        productName
    );

}


// =====================================================
// DISPLAY CART PRODUCTS
// =====================================================

function displayCart() {

    const cartItems =
        document.getElementById(
            "cart-items"
        );


    const cartSummary =
        document.getElementById(
            "cart-summary"
        );


    const emptyCart =
        document.getElementById(
            "empty-cart"
        );


    // Not cart page
    if (!cartItems) {
        return;
    }


    // =============================================
    // EMPTY CART
    // =============================================

    if (cart.length === 0) {

        cartItems.innerHTML = "";


        if (cartSummary) {

            cartSummary.style.display =
                "none";

        }


        if (emptyCart) {

            emptyCart.style.display =
                "block";

        }


        calculateTotal();

        return;

    }


    // =============================================
    // CART HAS PRODUCTS
    // =============================================

    if (cartSummary) {

        cartSummary.style.display =
            "block";

    }


    if (emptyCart) {

        emptyCart.style.display =
            "none";

    }


    cartItems.innerHTML = "";


    cart.forEach(function (
        product,
        index
    ) {

        const quantity =
            product.quantity || 1;


        // Convert price safely
        const price =
            parseInt(
                String(product.price)
                    .replace(/[^\d]/g, "")
            );


        const subtotal =
            !isNaN(price)
                ? price * quantity
                : 0;


        const cartItem =
            document.createElement("div");


        cartItem.className =
            "cart-item";


        cartItem.innerHTML = `

            <div class="cart-product">

                <div class="cart-image-wrapper">

                    <img
                        src="${product.image}"
                        alt="${product.name}"
                        class="cart-product-image"
                    >

                </div>


                <div class="cart-product-details">

                    <h4>
                        ${product.name}
                    </h4>


                    <p class="cart-product-price">
                        ${product.price}
                    </p>


                    <div class="quantity-box">

                        <button
                            class="quantity-btn"
                            onclick="decreaseQuantity(${index})"
                        >
                            −
                        </button>


                        <span class="quantity-number">
                            ${quantity}
                        </span>


                        <button
                            class="quantity-btn"
                            onclick="increaseQuantity(${index})"
                        >
                            +
                        </button>

                    </div>


                    <p class="cart-subtotal">

                        Subtotal:

                        <strong>
                            ₹${subtotal.toLocaleString("en-IN")}
                        </strong>

                    </p>


                    <button
                        class="btn btn-danger btn-sm"
                        onclick="removeFromCart(${index})"
                    >
                        Remove
                    </button>

                </div>

            </div>

        `;


        cartItems.appendChild(
            cartItem
        );

    });


    calculateTotal();

}


// =====================================================
// INCREASE QUANTITY
// =====================================================

function increaseQuantity(index) {

    if (!cart[index]) {
        return;
    }


    cart[index].quantity =
        (cart[index].quantity || 1) + 1;


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();

    displayCart();

}


// =====================================================
// DECREASE QUANTITY
// =====================================================

function decreaseQuantity(index) {

    if (!cart[index]) {
        return;
    }


    if (
        (cart[index].quantity || 1) > 1
    ) {

        cart[index].quantity -= 1;

    } else {

        cart.splice(index, 1);

    }


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();

    displayCart();

}


// =====================================================
// CALCULATE TOTAL
// =====================================================

function calculateTotal() {

    const cartItemsCount =
        document.getElementById(
            "cart-items-count"
        );


    const cartSubtotal =
        document.getElementById(
            "cart-subtotal"
        );


    const cartTotal =
        document.getElementById(
            "cart-total"
        );


    let total = 0;

    let itemsCount = 0;


    cart.forEach(function (product) {

        const price =
            parseInt(
                String(product.price)
                    .replace(/[^\d]/g, "")
            );


        const quantity =
            product.quantity || 1;


        if (!isNaN(price)) {

            total +=
                price * quantity;


            itemsCount +=
                quantity;

        }

    });


    // Items count
    if (cartItemsCount) {

        cartItemsCount.textContent =
            itemsCount;

    }


    // Subtotal
    if (cartSubtotal) {

        cartSubtotal.textContent =
            "₹" +
            total.toLocaleString("en-IN");

    }


    // Total
    if (cartTotal) {

        cartTotal.textContent =
            "₹" +
            total.toLocaleString("en-IN");

    }

}


// =====================================================
// REMOVE PRODUCT
// =====================================================

function removeFromCart(index) {

    if (!cart[index]) {
        return;
    }


    cart.splice(index, 1);


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();

    displayCart();

}


// =====================================================
// CART TOAST MESSAGE
// =====================================================

function showCartMessage(productName) {

    const message =
        document.createElement("div");


    message.className =
        "cart-toast";


    message.innerHTML = `

        <span class="cart-toast-icon">
            ✓
        </span>

        <div>

            <strong>
                Added to Cart
            </strong>

            <p>
                ${productName}
            </p>

        </div>

    `;


    document.body.appendChild(
        message
    );


    setTimeout(function () {

        message.classList.add(
            "show"
        );

    }, 10);


    setTimeout(function () {

        message.classList.remove(
            "show"
        );


        setTimeout(function () {

            message.remove();

        }, 300);

    }, 2500);

}


// =====================================================
// PLACE ORDER
// =====================================================

async function placeOrder() {

    // =============================================
    // CHECK CART
    // =============================================

    if (cart.length === 0) {

        alert(
            "Your cart is empty."
        );

        return;
    }


    // =============================================
    // CUSTOMER DETAILS
    // =============================================

    let name = "";
    let phone = "";
    let address = "";


    try {

        // =========================================
        // CHECK LOGIN STATUS
        // =========================================

        const profileResponse =
            await fetch(
                "/api/customer/profile"
            );


        if (profileResponse.ok) {

            // =====================================
            // LOGGED-IN CUSTOMER
            // =====================================

            const customer =
                await profileResponse.json();


            name =
                customer.name || "";


            phone =
                customer.phone || "";


            address =
                customer.address || "";


            console.log(
                "Logged-in customer:",
                customer
            );


            // Hide customer details
            const customerDetails =
                document.querySelector(
                    ".customer-details"
                );


            if (customerDetails) {

                customerDetails.style.display =
                    "none";

            }


        } else {

            // =====================================
            // NOT LOGGED IN
            // =====================================

            const nameInput =
                document.getElementById(
                    "customer-name"
                );


            const phoneInput =
                document.getElementById(
                    "customer-phone"
                );


            const addressInput =
                document.getElementById(
                    "customer-address"
                );


            name =
                nameInput
                    ? nameInput.value.trim()
                    : "";


            phone =
                phoneInput
                    ? phoneInput.value.trim()
                    : "";


            address =
                addressInput
                    ? addressInput.value.trim()
                    : "";


            // =====================================
            // VALIDATE DETAILS
            // =====================================

            if (name === "") {

                alert(
                    "Please enter your name."
                );

                return;
            }


            if (
                !/^[0-9]{10}$/.test(phone)
            ) {

                alert(
                    "Please enter a valid 10-digit mobile number."
                );

                return;
            }


            if (address === "") {

                alert(
                    "Please enter your delivery address."
                );

                return;
            }

        }


        // =============================================
        // CALCULATE TOTAL
        // =============================================

        let total = 0;


        cart.forEach(function (product) {

            const price =
                parseInt(
                    String(product.price)
                        .replace(/[^\d]/g, "")
                );


            const quantity =
                product.quantity || 1;


            if (!isNaN(price)) {

                total +=
                    price * quantity;

            }

        });


        // =============================================
        // CHECK PRODUCT IDs
        // =============================================

        const invalidProduct =
            cart.find(function (product) {

                return !product.id;

            });


        if (invalidProduct) {

            alert(
                "Please remove the old cart item and add the product again."
            );

            return;
        }


        // =============================================
        // SAVE ORDER TO DATABASE
        // =============================================

        const orderResponse =
            await fetch(
                "/api/orders",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        total: total,

                        items: cart

                    })

                }
            );


        const orderResult =
            await orderResponse.json();


        if (!orderResponse.ok) {

            alert(
                orderResult.message ||
                "Failed to save order."
            );

            return;
        }


        alert(
            "Order saved successfully. Order ID: " +
            orderResult.order_id
        );


        // =============================================
        // WHATSAPP MESSAGE
        // =============================================

        let message =
            "🛒 *SUN AUTO CENTRE - NEW ORDER*%0A%0A";


        message +=
            "👤 *Customer Details*%0A";


        message +=
            "Name: " +
            name +
            "%0A";


        message +=
            "Mobile: " +
            phone +
            "%0A";


        message +=
            "Address: " +
            address +
            "%0A%0A";


        message +=
            "📦 *Order Details*%0A";


        cart.forEach(function (
            product,
            index
        ) {

            const price =
                parseInt(
                    String(product.price)
                        .replace(/[^\d]/g, "")
                );


            const quantity =
                product.quantity || 1;


            const subtotal =
                !isNaN(price)
                    ? price * quantity
                    : 0;


            message +=
                (index + 1) +
                ". " +
                product.name +
                " × " +
                quantity +
                " - ₹" +
                subtotal.toLocaleString("en-IN") +
                "%0A";

        });


        message +=
            "%0A💰 *Total: ₹" +
            total.toLocaleString("en-IN") +
            "*";


        // =============================================
        // SUN AUTO CENTRE WHATSAPP
        // =============================================

        const whatsappNumber =
            "918072289426";


        const whatsappURL =
            "https://wa.me/" +
            whatsappNumber +
            "?text=" +
            message;


        window.open(
            whatsappURL,
            "_blank"
        );


        // =============================================
        // CLEAR CART
        // =============================================

        localStorage.removeItem(
            "cart"
        );


        cart = [];


        updateCartCount();

        displayCart();


    } catch (error) {

        console.error(
            "Order error:",
            error
        );


        alert(
            "Something went wrong while placing the order."
        );

    }

}


// =====================================================
// CUSTOMER REGISTRATION
// =====================================================

function setupCustomerRegister() {

    const registerForm =
        document.querySelector(
            "#customerRegisterForm"
        );


    if (!registerForm) {
        return;
    }


    registerForm.addEventListener(
        "submit",
        async function (e) {

            e.preventDefault();


            const name =
                document.querySelector(
                    "#name"
                ).value.trim();


            const phone =
                document.querySelector(
                    "#phone"
                ).value.trim();


            const password =
                document.querySelector(
                    "#password"
                ).value;


            const address =
                document.querySelector(
                    "#address"
                ).value.trim();


            try {

                const response =
                    await fetch(
                        "/api/customer/register",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                name: name,

                                phone: phone,

                                password: password,

                                address: address

                            })

                        }
                    );


                const result =
                    await response.json();


                alert(
                    result.message
                );


                if (response.ok) {

                    window.location.href =
                        "/customer-login";

                }


            } catch (error) {

                console.error(
                    "Registration error:",
                    error
                );


                alert(
                    "Registration failed."
                );

            }

        }
    );

}


// =====================================================
// CUSTOMER LOGIN
// =====================================================

function setupCustomerLogin() {

    const loginForm =
        document.querySelector(
            "#customerLoginForm"
        );


    if (!loginForm) {
        return;
    }


    loginForm.addEventListener(
        "submit",
        async function (e) {

            e.preventDefault();


            const phone =
                document.querySelector(
                    "#phone"
                ).value.trim();


            const password =
                document.querySelector(
                    "#password"
                ).value;


            try {

                const response =
                    await fetch(
                        "/api/customer/login",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                phone: phone,

                                password: password

                            })

                        }
                    );


                const result =
                    await response.json();


                alert(
                    result.message
                );


                if (response.ok) {

                    // Login successful
                    // Flask session is created
                    window.location.href =
                        "/";

                }


            } catch (error) {

                console.error(
                    "Login error:",
                    error
                );


                alert(
                    "Login failed."
                );

            }

        }
    );

}


// =====================================================
// PAGE LOADED
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {


        // =============================================
        // ADD TO CART
        // Works for Popular Products
        // and Products page
        // =============================================

        document.addEventListener(
            "click",
            function (event) {

                const button =
                    event.target.closest(
                        ".add-cart"
                    );


                if (!button) {
                    return;
                }


                addToCart(button);

            }
        );


        // =============================================
        // OLD CART COMPATIBILITY
        // =============================================

        cart.forEach(
            function (product) {

                if (!product.quantity) {

                    product.quantity = 1;

                }

            }
        );


        localStorage.setItem(
            "cart",
            JSON.stringify(cart)
        );


        // =============================================
        // LOAD PRODUCTS
        // =============================================

        loadProducts();


        // =============================================
        // UPDATE CART COUNT
        // =============================================

        updateCartCount();


        // =============================================
        // DISPLAY CART
        // =============================================

        displayCart();


        // =============================================
        // PLACE ORDER BUTTON
        // =============================================

        const placeOrderButton =
            document.getElementById(
                "place-order-btn"
            );


        if (placeOrderButton) {

            placeOrderButton.addEventListener(
                "click",
                function () {

                    placeOrder();

                }
            );

        }


        // =============================================
        // CUSTOMER REGISTER
        // =============================================

        setupCustomerRegister();


        // =============================================
        // CUSTOMER LOGIN
        // =============================================

        setupCustomerLogin();

    }
);