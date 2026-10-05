"use strict";

const adminToken = () => document.querySelector('meta[name="csrf-token"]')?.content || "";
const adminMoney = value => `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const adminNode = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
};

async function adminApi(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) headers["X-CSRF-Token"] = adminToken();
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
        if (!response.ok) throw new Error("Unexpected server response.");
    }
    if (!response.ok) throw new Error(result.message || "Request failed.");
    return result;
}

function adminMessage(message, success = false) {
    const target = document.getElementById("admin-message");
    if (!target) return;
    target.textContent = message;
    target.className = `alert ${success ? "alert-success" : "alert-danger"}`;
}

function staticImage(filename) {
    return `/static/img/${String(filename || "").split("/").map(encodeURIComponent).join("/")}`;
}

async function loadAdminDashboard() {
    try {
        const [stats, products, orders, customers, returns] = await Promise.all([
            adminApi("/api/admin/dashboard"),
            adminApi("/api/admin/products"),
            adminApi("/api/admin/orders"),
            adminApi("/api/admin/customers"),
            adminApi("/api/admin/returns")
        ]);
        renderStats(stats);
        renderProducts(products);
        renderOrders(orders);
        renderCustomers(customers);
        renderReturns(returns);
    } catch (error) {
        if (error.message === "Administrator login required.") window.location.assign("/admin/login");
        else adminMessage(error.message);
    }
}

function renderStats(stats) {
    const container = document.getElementById("admin-stats");
    if (!container) return;
    container.replaceChildren();
    const entries = [
        ["Customers", stats.customers],
        ["Active products", stats.products],
        ["Orders", stats.orders],
        ["Pending orders", stats.pending_orders],
        ["Open returns", stats.returns],
        ["Sales (excluding cancelled)", adminMoney(stats.sales)]
    ];
    for (const [label, value] of entries) {
        const column = adminNode("div", "col-6 col-lg-2");
        const card = adminNode("div", "card h-100 shadow-sm");
        const body = adminNode("div", "card-body");
        body.append(adminNode("div", "text-muted small", label), adminNode("div", "h4 mt-2 mb-0", value));
        card.append(body);
        column.append(card);
        container.append(column);
    }
}

function renderProducts(products) {
    const table = document.getElementById("products-table");
    if (!table) return;
    table.replaceChildren();
    if (!products.length) {
        const row = adminNode("tr");
        row.append(adminNode("td", "text-center", "No products."));
        row.firstChild.colSpan = 6;
        table.append(row);
        return;
    }
    for (const product of products) {
        const row = adminNode("tr");
        const imageCell = adminNode("td");
        if (product.image) {
            const image = adminNode("img", "rounded");
            image.src = staticImage(product.image);
            image.alt = product.name;
            image.width = 56;
            image.height = 56;
            image.style.objectFit = "cover";
            imageCell.append(image);
        }
        const nameCell = adminNode("td");
        nameCell.append(adminNode("strong", "", product.name), adminNode("div", "text-muted small", product.brand));
        row.append(imageCell, nameCell, adminNode("td", "", product.price === null ? "Contact for price" : adminMoney(product.price)));

        const stockCell = adminNode("td");
        const stockControl = adminNode("div", "input-group input-group-sm");
        const stockInput = adminNode("input", "form-control");
        stockInput.type = "number";
        stockInput.min = "0";
        stockInput.max = "1000000";
        stockInput.step = "1";
        stockInput.value = product.stock;
        stockInput.setAttribute("aria-label", `Stock for ${product.name}`);
        const saveStock = adminNode("button", "btn btn-outline-primary", "Save");
        saveStock.type = "button";
        saveStock.dataset.action = "stock";
        saveStock.dataset.id = product.id;
        stockControl.append(stockInput, saveStock);
        stockCell.append(stockControl);
        row.append(stockCell, adminNode("td", "", product.is_active ? "Active" : "Inactive"));

        const actions = adminNode("td", "text-nowrap");
        const edit = adminNode("button", "btn btn-sm btn-outline-dark me-1", "Edit");
        edit.type = "button";
        edit.dataset.action = "edit";
        edit.dataset.id = product.id;
        const deactivate = adminNode("button", "btn btn-sm btn-outline-danger", product.is_active ? "Deactivate" : "Inactive");
        deactivate.type = "button";
        deactivate.dataset.action = "deactivate";
        deactivate.dataset.id = product.id;
        deactivate.disabled = !product.is_active;
        actions.append(edit, deactivate);
        row.append(actions);
        table.append(row);
    }
}

function renderOrders(orders) {
    const table = document.getElementById("orders-table");
    if (!table) return;
    table.replaceChildren();
    if (!orders.length) {
        const row = adminNode("tr");
        const cell = adminNode("td", "text-center", "No orders.");
        cell.colSpan = 6;
        row.append(cell);
        table.append(row);
        return;
    }
    const statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"];
    for (const order of orders) {
        const row = adminNode("tr");
        row.append(adminNode("td", "", `#${order.id}\n${order.order_date}`));
        row.append(adminNode("td", "", `${order.customer_name || "Customer"}\n${order.customer_phone || ""}`));
        const itemCell = adminNode("td");
        for (const item of order.items) itemCell.append(adminNode("div", "small", `${item.product_name} × ${item.quantity}`));
        row.append(itemCell, adminNode("td", "", adminMoney(order.total)));
        const statusCell = adminNode("td");
        const select = adminNode("select", "form-select form-select-sm");
        select.dataset.statusSelect = "";
        for (const status of statuses) {
            const option = adminNode("option", "", status);
            option.value = status;
            option.selected = order.status === status;
            select.append(option);
        }
        statusCell.append(select);
        row.append(statusCell);
        const actionCell = adminNode("td");
        const save = adminNode("button", "btn btn-sm btn-primary", "Update");
        save.type = "button";
        save.dataset.action = "order-status";
        save.dataset.id = order.id;
        actionCell.append(save);
        row.append(actionCell);
        table.append(row);
    }
}

function renderCustomers(customers) {
    const table = document.getElementById("customers-table");
    if (!table) return;
    table.replaceChildren();
    if (!customers.length) {
        const row = adminNode("tr");
        const cell = adminNode("td", "text-center", "No customers.");
        cell.colSpan = 6;
        row.append(cell);
        table.append(row);
        return;
    }
    for (const customer of customers) {
        const row = adminNode("tr");
        row.append(
            adminNode("td", "", customer.name),
            adminNode("td", "", customer.phone),
            adminNode("td", "", customer.address),
            adminNode("td", "", customer.order_count),
            adminNode("td", "", adminMoney(customer.order_total)),
            adminNode("td", "", customer.created_at)
        );
        table.append(row);
    }
}

function renderReturns(returns) {
    const table = document.getElementById("returns-table");
    if (!table) return;
    table.replaceChildren();
    if (!returns.length) {
        const row = adminNode("tr");
        const cell = adminNode("td", "text-center", "No return requests.");
        cell.colSpan = 6;
        row.append(cell);
        table.append(row);
        return;
    }
    const statuses = ["Approved", "Rejected", "Received", "Refunded"];
    for (const item of returns) {
        const row = adminNode("tr");
        row.append(adminNode("td", "", `#${item.id} / Order #${item.order_id}`));
        row.append(adminNode("td", "", `${item.customer_name || "Customer"}\n${item.customer_phone || ""}`));
        row.append(adminNode("td", "", item.reason));
        row.append(adminNode("td", "", item.return_date));
        const statusCell = adminNode("td");
        const select = adminNode("select", "form-select form-select-sm");
        select.dataset.returnStatus = "";
        for (const status of statuses) {
            const option = adminNode("option", "", status);
            option.value = status;
            option.selected = item.status === status;
            select.append(option);
        }
        statusCell.append(select);
        row.append(statusCell);
        const actionCell = adminNode("td");
        const save = adminNode("button", "btn btn-sm btn-primary", "Update");
        save.type = "button";
        save.dataset.action = "return-status";
        save.dataset.id = item.id;
        actionCell.append(save);
        row.append(actionCell);
        table.append(row);
    }
}

function resetProductForm() {
    const form = document.getElementById("product-form");
    if (!form) return;
    form.reset();
    document.getElementById("product-id").value = "";
    form.classList.add("d-none");
}

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("admin-login-form");
    loginForm?.addEventListener("submit", async event => {
        event.preventDefault();
        const message = document.getElementById("admin-login-message");
        try {
            await adminApi("/api/admin/login", {
                method: "POST",
                body: {
                    username: document.getElementById("username").value.trim(),
                    password: document.getElementById("password").value
                }
            });
            window.location.assign("/admin");
        } catch (error) {
            message.textContent = error.message;
            message.className = "alert alert-danger mt-3";
        }
    });
    if (!document.getElementById("products-table")) return;
    loadAdminDashboard();

    document.getElementById("admin-logout")?.addEventListener("click", async () => {
        try {
            await adminApi("/api/admin/logout", { method: "POST" });
            window.location.assign("/admin/login");
        } catch (error) {
            adminMessage(error.message);
        }
    });
    document.getElementById("new-product-button")?.addEventListener("click", () => {
        resetProductForm();
        document.getElementById("product-form").classList.remove("d-none");
    });
    document.getElementById("cancel-product")?.addEventListener("click", resetProductForm);

    document.getElementById("product-form")?.addEventListener("submit", async event => {
        event.preventDefault();
        const productId = document.getElementById("product-id").value;
        const data = {
            brand: document.getElementById("product-brand").value.trim(),
            name: document.getElementById("product-name").value.trim(),
            description: document.getElementById("product-description").value.trim(),
            price: document.getElementById("product-price").value || null,
            image: document.getElementById("product-image").value.trim(),
            stock: document.getElementById("product-stock").value
        };
        try {
            await adminApi(productId ? `/api/admin/products/${productId}` : "/api/admin/products", {
                method: productId ? "PUT" : "POST",
                body: data
            });
            resetProductForm();
            adminMessage(productId ? "Product updated." : "Product created.", true);
            await loadAdminDashboard();
        } catch (error) {
            adminMessage(error.message);
        }
    });

    document.getElementById("products-table")?.addEventListener("click", async event => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const id = button.dataset.id;
        try {
            if (button.dataset.action === "edit") {
                const products = await adminApi("/api/admin/products");
                const product = products.find(item => String(item.id) === id);
                if (!product) throw new Error("Product not found.");
                document.getElementById("product-id").value = product.id;
                document.getElementById("product-brand").value = product.brand;
                document.getElementById("product-name").value = product.name;
                document.getElementById("product-description").value = product.description || "";
                document.getElementById("product-price").value = product.price ?? "";
                document.getElementById("product-stock").value = product.stock;
                document.getElementById("product-image").value = product.image || "";
                document.getElementById("product-form").classList.remove("d-none");
                return;
            }
            if (button.dataset.action === "stock") {
                const value = button.parentElement.querySelector("input").value;
                await adminApi(`/api/admin/products/${id}/stock`, { method: "PATCH", body: { stock: value } });
                adminMessage("Stock updated.", true);
            } else if (button.dataset.action === "deactivate" && window.confirm("Deactivate this product? Order history will be retained.")) {
                await adminApi(`/api/admin/products/${id}`, { method: "DELETE" });
                adminMessage("Product deactivated.", true);
            } else {
                return;
            }
            await loadAdminDashboard();
        } catch (error) {
            adminMessage(error.message);
        }
    });

    document.getElementById("orders-table")?.addEventListener("click", async event => {
        const button = event.target.closest('[data-action="order-status"]');
        if (!button) return;
        const status = button.closest("tr").querySelector("[data-status-select]").value;
        try {
            await adminApi(`/api/admin/orders/${button.dataset.id}/status`, { method: "PATCH", body: { status } });
            adminMessage("Order status updated.", true);
            await loadAdminDashboard();
        } catch (error) {
            adminMessage(error.message);
        }
    });

    document.getElementById("returns-table")?.addEventListener("click", async event => {
        const button = event.target.closest('[data-action="return-status"]');
        if (!button) return;
        const status = button.closest("tr").querySelector("[data-return-status]").value;
        try {
            await adminApi(`/api/admin/returns/${button.dataset.id}/status`, { method: "PATCH", body: { status } });
            adminMessage("Return request updated.", true);
            await loadAdminDashboard();
        } catch (error) {
            adminMessage(error.message);
        }
    });
});
