// ===============================
// Shopping Cart
// ===============================

let cart = JSON.parse(localStorage.getItem("cart")) || [];


// ===============================
// Update Cart Count
// ===============================

function updateCartCount() {

    const cartCount = document.getElementById("cart-count");

    if (cartCount) {

        cartCount.textContent = cart.reduce(function(total, product) {

            return total + (product.quantity || 1);

        }, 0);

    }
}


// ===============================
// Add Product to Cart
// ===============================

function addToCart(button) {

    const productCard = button.closest(".product-card");

    if (!productCard) {
        return;
    }

    const productName =
        productCard.querySelector("h4").textContent.trim();

    const productPrice =
        productCard.querySelector("h5").textContent.trim();

    const productImage =
        productCard.querySelector(".product-image").src;


    const existingProduct = cart.find(function(product) {

        return product.name === productName;

    });


    if (existingProduct) {

        existingProduct.quantity =
            (existingProduct.quantity || 1) + 1;

    } else {

        const product = {

            name: productName,

            price: productPrice,

            image: productImage,

            quantity: 1

        };

        cart.push(product);

    }


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();

    showCartMessage(productName);

}


// ===============================
// Display Cart Products
// ===============================

function displayCart() {

    const cartItems =
        document.getElementById("cart-items");

    const cartSummary =
        document.getElementById("cart-summary");

    const emptyCart =
        document.getElementById("empty-cart");


    if (!cartItems) {
        return;
    }


    // Empty Cart
    if (cart.length === 0) {

        cartItems.innerHTML = "";


        if (cartSummary) {
            cartSummary.style.display = "none";
        }


        if (emptyCart) {
            emptyCart.style.display = "block";
        }


        calculateTotal();

        return;
    }


    // Cart has products
    if (cartSummary) {
        cartSummary.style.display = "block";
    }


    if (emptyCart) {
        emptyCart.style.display = "none";
    }


    cartItems.innerHTML = "";


    cart.forEach(function(product, index) {

        const quantity = product.quantity || 1;


        const price = parseInt(
            product.price.replace(/[^\d]/g, "")
        );


        const subtotal =
            !isNaN(price)
                ? price * quantity
                : 0;


        const cartItem =
            document.createElement("div");


        cartItem.className = "cart-item";


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

                    <h4>${product.name}</h4>


                    <p class="cart-product-price">
                        ${product.price}
                    </p>


                    <div class="quantity-box">

                        <button
                            class="quantity-btn"
                            onclick="decreaseQuantity(${index})">
                            −
                        </button>


                        <span class="quantity-number">
                            ${quantity}
                        </span>


                        <button
                            class="quantity-btn"
                            onclick="increaseQuantity(${index})">
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
                        onclick="removeFromCart(${index})">

                        Remove

                    </button>

                </div>

            </div>

        `;


        cartItems.appendChild(cartItem);

    });


    calculateTotal();

}


// ===============================
// Increase Quantity
// ===============================

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


// ===============================
// Decrease Quantity
// ===============================

function decreaseQuantity(index) {

    if (!cart[index]) {
        return;
    }


    if ((cart[index].quantity || 1) > 1) {

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


// ===============================
// Calculate Total
// ===============================

function calculateTotal() {

    const cartItemsCount =
        document.getElementById("cart-items-count");

    const cartSubtotal =
        document.getElementById("cart-subtotal");

    const cartTotal =
        document.getElementById("cart-total");


    let total = 0;

    let itemsCount = 0;


    cart.forEach(function(product) {

        const price = parseInt(
            product.price.replace(/[^\d]/g, "")
        );


        const quantity =
            product.quantity || 1;


        if (!isNaN(price)) {

            total += price * quantity;

            itemsCount += quantity;

        }

    });


    // Items
    if (cartItemsCount) {

        cartItemsCount.textContent =
            itemsCount;

    }


    // Subtotal
    if (cartSubtotal) {

        cartSubtotal.textContent =
            "₹" + total.toLocaleString("en-IN");

    }


    // Total
    if (cartTotal) {

        cartTotal.textContent =
            "₹" + total.toLocaleString("en-IN");

    }

}


// ===============================
// Remove Product
// ===============================

function removeFromCart(index) {

    cart.splice(index, 1);


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();

    displayCart();

}


// ===============================
// Cart Toast Message
// ===============================

function showCartMessage(productName) {

    const message =
        document.createElement("div");


    message.className =
        "cart-toast";


    message.innerHTML = `

        <span class="cart-toast-icon">✓</span>

        <div>

            <strong>Added to Cart</strong>

            <p>${productName}</p>

        </div>

    `;


    document.body.appendChild(message);


    setTimeout(function() {

        message.classList.add("show");

    }, 10);


    setTimeout(function() {

        message.classList.remove("show");


        setTimeout(function() {

            message.remove();

        }, 300);

    }, 2500);

}


// ===============================
// Page Loaded
// ===============================

document.addEventListener(
    "DOMContentLoaded",
    function() {


        // Old Cart Products Compatibility

        cart.forEach(function(product) {

            if (!product.quantity) {

                product.quantity = 1;

            }

        });


        localStorage.setItem(
            "cart",
            JSON.stringify(cart)
        );


        // Add to Cart Buttons

        const addCartButtons =
            document.querySelectorAll(".add-cart");


        addCartButtons.forEach(function(button) {

            button.addEventListener(
                "click",
                function() {

                    addToCart(this);

                }
            );

        });


        // Update Cart

        updateCartCount();

        displayCart();


        // Place Order Button

        const placeOrderButton =
            document.getElementById("place-order-btn");


        if (placeOrderButton) {

            placeOrderButton.addEventListener(
                "click",
                function() {

                    placeOrder();

                }
            );

        }

    }
);


// ===============================
// Place Order - WhatsApp
// ===============================

function placeOrder() {

    if (cart.length === 0) {

        alert("Your cart is empty.");

        return;

    }


    const name =
        document.getElementById("customer-name")
            .value.trim();


    const phone =
        document.getElementById("customer-phone")
            .value.trim();


    const address =
        document.getElementById("customer-address")
            .value.trim();


    if (name === "") {

        alert("Please enter your name.");

        return;

    }


    if (!/^[0-9]{10}$/.test(phone)) {

        alert(
            "Please enter a valid 10-digit mobile number."
        );

        return;

    }


    if (address === "") {

        alert("Please enter your delivery address.");

        return;

    }


    let message =
        "🛒 *SUN AUTO CENTRE - NEW ORDER*%0A%0A";


    message +=
        "👤 *Customer Details*%0A";


    message +=
        "Name: " + name + "%0A";


    message +=
        "Mobile: " + phone + "%0A";


    message +=
        "Address: " + address + "%0A%0A";


    message +=
        "📦 *Order Details*%0A";


    let total = 0;


    cart.forEach(function(product, index) {

        const price = parseInt(
            product.price.replace(/[^\d]/g, "")
        );


        const quantity =
            product.quantity || 1;


        const subtotal =
            price * quantity;


        total += subtotal;


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


    // Sun Auto Centre WhatsApp Number

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


    localStorage.removeItem("cart");

    cart = [];


    updateCartCount();

    displayCart();

}