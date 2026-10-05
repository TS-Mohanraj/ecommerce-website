"use strict";

const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content || "";
const money = value => `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
};

async function api(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) headers["X-CSRF-Token"] = csrfToken();
    const response = await fetch(path, {
        ...options,
        method,
        headers,
        credentials: "same-origin",
        body: options.body === undefined ? undefined : JSON.stringify(options.body)
    });
    let result = {};
    try {
        result = await response.json();
    } catch {
        if (!response.ok) throw new Error("The server returned an unexpected response.");
    }
    if (!response.ok) throw new Error(result.message || "The request could not be completed.");
    return result;
}

function showMessage(element, message, success = false) {
    if (!element) return;
    element.textContent = message;
    element.className = `alert ${success ? "alert-success" : "alert-danger"}`;
}

function imageUrl(filename) {
    return `/static/img/${String(filename || "").split("/").map(encodeURIComponent).join("/")}`;
}

async function refreshCartCount() {
    const target = document.getElementById("cart-count");
    if (!target) return;
    try {
        const cart = await api("/api/cart/count");
        target.textContent = cart.count;
    } catch (error) {
        target.textContent = "0";
        console.error(error);
    }
}

async function loadHomeInventory() {
    const cards = document.querySelectorAll(".home-product-card[data-product-id]");
    if (!cards.length) return;
    try {
        const products = await api("/api/products");
        const byId = new Map(products.map(product => [String(product.id), product]));
        for (const card of cards) {
            const product = byId.get(card.dataset.productId);
            const button = card.querySelector(".add-cart");
            if (!product || !button) continue;
            button.dataset.productId = product.id;
            button.disabled = product.stock < 1 || product.price === null;
            button.title = product.stock < 1 ? "Currently out of stock" : "";
        }
    } catch (error) {
        console.error("Unable to load product availability:", error);
    }
}

function buildProductCard(product) {
    const column = node("div", "col-md-4 col-sm-6 mb-4");
    const card = node("article", "product-card");
    card.dataset.id = product.id;

    const image = node("img", "product-image");
    image.src = imageUrl(product.image);
    image.alt = product.name;
    image.loading = "lazy";
    card.append(image);
    card.append(node("span", "product-brand", product.brand));
    card.append(node("h4", "", product.name));
    card.append(node("p", "", product.description || ""));
    card.append(node("h5", "", product.price === null ? "Contact for Price" : money(product.price)));
    card.append(node("p", "text-muted small", product.stock > 0 ? `${product.stock} in stock` : "Currently out of stock"));

    const actions = node("div", "d-flex gap-2 flex-wrap");
    const details = node("a", "btn btn-outline-dark", "Details");
    details.href = `/products/${product.id}`;
    actions.append(details);
    const add = node("button", "btn btn-warning add-cart", "Add to Cart");
    add.type = "button";
    add.dataset.productId = product.id;
    add.disabled = product.stock < 1 || product.price === null;
    if (product.price === null) add.title = "Contact us for pricing";
    actions.append(add);
    card.append(actions);
    column.append(card);
    return column;
}

async function loadProducts() {
    const container = document.getElementById("products-container");
    if (!container) return;
    try {
        const products = await api("/api/products");
        container.replaceChildren();
        const brandOrder = ["CASTROL", "MOTUL", "HERO", "TVS", "ACCESSORIES"];
        const brandIds = {
            CASTROL: "castrol-products",
            MOTUL: "motul-products",
            HERO: "hero-products",
            TVS: "tvs-products",
            ACCESSORIES: "accessories-products"
        };
        for (const brand of brandOrder) {
            const group = products.filter(product => product.brand.toUpperCase() === brand);
            if (!group.length) continue;
            const section = node("section", "brand-product-section");
            section.id = brandIds[brand];
            section.append(node("h2", "text-center mb-4", brand));
            const row = node("div", "row");
            group.forEach(product => row.append(buildProductCard(product)));
            section.append(row);
            container.append(section);
        }
        const otherProducts = products.filter(product => !brandOrder.includes(product.brand.toUpperCase()));
        if (otherProducts.length) {
            const section = node("section", "brand-product-section");
            section.append(node("h2", "text-center mb-4", "OTHER PRODUCTS"));
            const row = node("div", "row");
            otherProducts.forEach(product => row.append(buildProductCard(product)));
            section.append(row);
            container.append(section);
        }
        if (!products.length) container.append(node("p", "text-center", "No products are available right now."));
    } catch (error) {
        console.error("Unable to load products:", error);
        container.replaceChildren(node("p", "alert alert-danger", error.message));
    }
}

async function renderCart() {
    const container = document.getElementById("cart-items");
    if (!container) return;
    const summary = document.getElementById("cart-summary");
    const empty = document.getElementById("empty-cart");
    try {
        const cart = await api("/api/cart");
        container.replaceChildren();
        const count = document.getElementById("cart-items-count");
        const subtotal = document.getElementById("cart-subtotal");
        const total = document.getElementById("cart-total");
        if (count) count.textContent = cart.count;
        if (subtotal) subtotal.textContent = money(cart.total);
        if (total) total.textContent = money(cart.total);
        if (!cart.items.length) {
            if (summary) summary.classList.add("d-none");
            if (empty) empty.classList.remove("d-none");
            return;
        }
        if (summary) summary.classList.remove("d-none");
        if (empty) empty.classList.add("d-none");
        for (const item of cart.items) {
            const row = node("div", "cart-item");
            const product = node("div", "cart-product");
            const imageWrap = node("div", "cart-image-wrapper");
            const image = node("img", "cart-product-image");
            image.src = imageUrl(item.image);
            image.alt = item.name;
            imageWrap.append(image);
            product.append(imageWrap);
            const details = node("div", "cart-product-details");
            details.append(node("h4", "", item.name));
            details.append(node("p", "cart-product-price", money(item.price)));
            details.append(node("p", "text-muted small", `${item.stock} in stock`));
            const controls = node("div", "quantity-box");
            const minus = node("button", "quantity-btn", "−");
            minus.type = "button";
            minus.dataset.cartAction = "decrease";
            minus.dataset.itemId = item.item_id;
            minus.disabled = item.quantity <= 1;
            const quantity = node("span", "px-3", item.quantity);
            const plus = node("button", "quantity-btn", "+");
            plus.type = "button";
            plus.dataset.cartAction = "increase";
            plus.dataset.itemId = item.item_id;
            plus.disabled = item.quantity >= item.stock || item.quantity >= 999;
            const remove = node("button", "btn btn-outline-danger btn-sm ms-2", "Remove");
            remove.type = "button";
            remove.dataset.cartAction = "remove";
            remove.dataset.itemId = item.item_id;
            controls.append(minus, quantity, plus, remove);
            details.append(controls);
            details.append(node("p", "mt-2 mb-0", `Subtotal: ${money(item.subtotal)}`));
            product.append(details);
            row.append(product);
            container.append(row);
        }
        const address = document.getElementById("delivery-address");
        if (address && !address.value) {
            const profile = await api("/api/customer/profile");
            address.value = profile.address || "";
        }
    } catch (error) {
        if (error.message === "Please log in to continue.") {
            window.location.assign(`/customer-login?next=${encodeURIComponent("/cart")}`);
            return;
        }
        showMessage(document.getElementById("cart-message"), error.message);
    }
}

async function submitReturn(orderId) {
    const reason = window.prompt("Please tell us why you are returning this order:");
    if (reason === null) return;
    try {
        await api("/api/customer/returns", { method: "POST", body: { order_id: orderId, reason } });
        await loadOrders();
        showMessage(document.getElementById("orders-message"), "Return request submitted.", true);
    } catch (error) {
        showMessage(document.getElementById("orders-message"), error.message);
    }
}

async function loadOrders() {
    const container = document.getElementById("orders-container");
    if (!container) return;
    try {
        const orders = await api("/api/customer/orders");
        container.replaceChildren();
        if (!orders.length) {
            const empty = node("div", "col-12 text-center");
            empty.append(node("div", "customer-profile-card"));
            const card = empty.firstChild;
            card.append(node("h4", "", "No orders yet"));
            card.append(node("p", "", "Your completed purchases will appear here."));
            const browse = node("a", "btn btn-dark", "Browse Products");
            browse.href = "/products";
            card.append(browse);
            container.append(empty);
            return;
        }
        for (const order of orders) {
            const column = node("div", "col-lg-6 col-md-12");
            const card = node("article", "customer-profile-card");
            card.append(node("span", "customer-profile-label", `ORDER #${order.id}`));
            card.append(node("h4", "", money(order.total)));
            card.append(node("p", "", `Status: ${order.status}`));
            card.append(node("p", "", `Placed: ${order.order_date}`));
            if (order.delivered_at) card.append(node("p", "", `Delivered: ${order.delivered_at}`));
            const items = node("div", "mt-3");
            items.append(node("h5", "", "Ordered products"));
            for (const item of order.items) {
                items.append(node("p", "border-bottom pb-2", `${item.product_name} — Qty ${item.quantity} — ${money(item.price)} each`));
            }
            card.append(items);
            if (order.return_status) {
                card.append(node("p", "alert alert-info", `Return request: ${order.return_status}`));
            } else if (order.return_eligible) {
                const button = node("button", "btn btn-outline-dark", "Request a return");
                button.type = "button";
                button.addEventListener("click", () => submitReturn(order.id));
                card.append(button);
                card.append(node("small", "d-block mt-2 text-muted", `Request by ${new Date(order.return_deadline).toLocaleString()}`));
            } else if (order.status.toLowerCase() === "delivered") {
                card.append(node("p", "text-muted small", "The 7-day return period has ended."));
            }
            column.append(card);
            container.append(column);
        }
    } catch (error) {
        if (error.message === "Please log in to continue.") {
            window.location.assign("/customer-login");
            return;
        }
        showMessage(document.getElementById("orders-message"), error.message);
    }
}

async function loadReturns() {
    const container = document.getElementById("returns-container");
    if (!container) return;
    try {
        const returns = await api("/api/customer/returns");
        container.replaceChildren();
        if (!returns.length) {
            const empty = node("div", "col-12 text-center");
            empty.append(node("div", "customer-profile-card"));
            empty.firstChild.append(node("h4", "", "No return requests"));
            empty.firstChild.append(node("p", "", "Return requests for eligible delivered orders will appear here."));
            container.append(empty);
            return;
        }
        for (const item of returns) {
            const column = node("div", "col-lg-6 col-md-12");
            const card = node("article", "customer-profile-card");
            card.append(node("span", "customer-profile-label", `RETURN #${item.id}`));
            card.append(node("h4", "", `Order #${item.order_id}`));
            card.append(node("p", "", `Order total: ${money(item.total)}`));
            card.append(node("p", "", `Reason: ${item.reason}`));
            card.append(node("p", "", `Status: ${item.status}`));
            card.append(node("p", "", `Requested: ${item.return_date}`));
            column.append(card);
            container.append(column);
        }
    } catch (error) {
        if (error.message === "Please log in to continue.") window.location.assign("/customer-login");
        else showMessage(document.getElementById("returns-message"), error.message);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    refreshCartCount();
    loadHomeInventory();
    loadProducts();
    renderCart();
    loadOrders();
    loadReturns();

    document.addEventListener("click", async event => {
        const button = event.target.closest("button.add-cart[data-product-id]");
        if (!button) return;
        try {
            await api("/api/cart/items", { method: "POST", body: { product_id: Number(button.dataset.productId), quantity: 1 } });
            await refreshCartCount();
            const oldText = button.textContent;
            button.textContent = "Added";
            window.setTimeout(() => { button.textContent = oldText; }, 1200);
        } catch (error) {
            if (error.message === "Please log in to continue.") {
                window.location.assign(`/customer-login?next=${encodeURIComponent("/products")}`);
            } else {
                window.alert(error.message);
            }
        }
    });

    document.getElementById("add-product-detail")?.addEventListener("click", async event => {
        const button = event.currentTarget;
        try {
            await api("/api/cart/items", {
                method: "POST",
                body: { product_id: Number(button.dataset.productId), quantity: 1 }
            });
            await refreshCartCount();
            showMessage(document.getElementById("product-message"), "Added to your cart.", true);
        } catch (error) {
            if (error.message === "Please log in to continue.") {
                window.location.assign(`/customer-login?next=${encodeURIComponent(window.location.pathname)}`);
            } else {
                showMessage(document.getElementById("product-message"), error.message);
            }
        }
    });

    document.getElementById("cart-items")?.addEventListener("click", async event => {
        const button = event.target.closest("[data-cart-action]");
        if (!button) return;
        const itemId = Number(button.dataset.itemId);
        try {
            if (button.dataset.cartAction === "remove") {
                await api(`/api/cart/items/${itemId}`, { method: "DELETE" });
            } else {
                const row = button.closest(".cart-item");
                const current = Number(row.querySelector(".quantity-box span").textContent);
                const quantity = current + (button.dataset.cartAction === "increase" ? 1 : -1);
                await api(`/api/cart/items/${itemId}`, { method: "PATCH", body: { quantity } });
            }
            await renderCart();
            await refreshCartCount();
        } catch (error) {
            showMessage(document.getElementById("cart-message"), error.message);
        }
    });

    document.getElementById("place-order-btn")?.addEventListener("click", async event => {
        const button = event.currentTarget;
        const address = document.getElementById("delivery-address").value.trim();
        if (!address) {
            showMessage(document.getElementById("cart-message"), "Delivery address is required.");
            return;
        }
        button.disabled = true;
        try {
            const order = await api("/api/checkout", { method: "POST", body: { delivery_address: address } });
            window.location.assign(`/customer-orders?placed=${order.order_id}`);
        } catch (error) {
            showMessage(document.getElementById("cart-message"), error.message);
            button.disabled = false;
        }
    });

    document.getElementById("customerLoginForm")?.addEventListener("submit", async event => {
        event.preventDefault();
        const message = document.getElementById("login-message");
        try {
            await api("/api/customer/login", {
                method: "POST",
                body: {
                    phone: document.getElementById("phone").value.trim(),
                    password: document.getElementById("password").value
                }
            });
            const next = new URLSearchParams(window.location.search).get("next");
            window.location.assign(next && next.startsWith("/") && !next.startsWith("//") ? next : "/customer-account");
        } catch (error) {
            showMessage(message, error.message);
        }
    });

    document.getElementById("customerRegisterForm")?.addEventListener("submit", async event => {
        event.preventDefault();
        const message = document.getElementById("register-message");
        try {
            await api("/api/customer/register", {
                method: "POST",
                body: {
                    name: document.getElementById("name").value.trim(),
                    phone: document.getElementById("phone").value.trim(),
                    password: document.getElementById("password").value,
                    address: document.getElementById("address").value.trim()
                }
            });
            showMessage(message, "Registration successful. You can now log in.", true);
            window.setTimeout(() => window.location.assign("/customer-login"), 900);
        } catch (error) {
            showMessage(message, error.message);
        }
    });

    document.getElementById("profile-form")?.addEventListener("submit", async event => {
        event.preventDefault();
        try {
            const data = await api("/api/customer/profile", { method: "PUT", body: {
                name: document.getElementById("profile-name").value.trim(),
                phone: document.getElementById("profile-phone").value.trim(),
                address: document.getElementById("profile-address").value.trim()
            }});
            showMessage(document.getElementById("account-message"), data.message, true);
        } catch (error) {
            showMessage(document.getElementById("account-message"), error.message);
        }
    });

    document.getElementById("logout-button")?.addEventListener("click", async () => {
        try {
            await api("/api/customer/logout", { method: "POST" });
            window.location.assign("/");
        } catch (error) {
            showMessage(document.getElementById("account-message"), error.message);
        }
    });

    if (document.getElementById("profile-form")) {
        api("/api/customer/profile").then(profile => {
            document.getElementById("profile-name").value = profile.name;
            document.getElementById("profile-phone").value = profile.phone;
            document.getElementById("profile-address").value = profile.address || "";
        }).catch(error => {
            if (error.message === "Please log in to continue.") window.location.assign("/customer-login");
            else showMessage(document.getElementById("account-message"), error.message);
        });
    }
});
