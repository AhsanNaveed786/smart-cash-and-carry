(function () {
    "use strict";
    const API = window.SmartAPI;
    const state = {
        access: null,
        branches: [],
        permissions: [],
        section: "overview",
        loaded: new Set(),
        orderSkip: 0,
        orderLimit: 50,
        orderResult: null,
        priceResult: null,
        categories: [],
        products: [],
        catalogResult: null,
        catalogSkip: 0,
        catalogLimit: 100,
        selectedProductIds: new Set(),
        lastExportId: null,
        importProductSkip: 0,
        importPageSize: 100,
        activeImport: null,
    };

    const titles = {
        overview: "Overview", orders: "Orders", prices: "Products & prices", catalog: "Catalog & branches", inventory: "Branch inventory",
        imports: "Excel imports", content: "Store content", discounts: "Deals & discounts",
        team: "Admins & sessions", reports: "Revenue & exports",
    };

    function isSuper() { return state.access?.role === "super_admin"; }
    function can(code) { return isSuper() || state.access?.permission_codes?.includes(code); }
    function esc(value) { return API.escapeHtml(value); }
    function statusLabel(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
    function statusPill(value) { return `<span class="status-pill ${esc(value)}">${esc(statusLabel(value))}</span>`; }
    function empty(message) { return `<div class="empty-panel">${esc(message)}</div>`; }

    function toast(message, type = "success") {
        const item = document.createElement("div");
        item.className = `admin-toast ${type}`;
        item.textContent = message;
        document.getElementById("admin-toast-stack").appendChild(item);
        setTimeout(() => item.remove(), 3500);
    }

    function modal(markup) {
        document.getElementById("admin-modal-content").innerHTML = markup;
        const container = document.getElementById("admin-modal");
        container.classList.add("is-open");
        container.setAttribute("aria-hidden", "false");
    }

    function closeModal() {
        const container = document.getElementById("admin-modal");
        container.classList.remove("is-open");
        container.setAttribute("aria-hidden", "true");
    }

    function formObject(form) {
        return Object.fromEntries(new FormData(form).entries());
    }

    function toIso(value) {
        return value ? new Date(value).toISOString() : null;
    }

    function branchName(id) {
        return state.branches.find((branch) => branch.id === Number(id))?.name || `Branch ${id}`;
    }

    function accessibleBranches() {
        if (isSuper()) return state.branches;
        return state.branches.filter((branch) => state.access.branch_ids.includes(branch.id));
    }

    function branchOptions(selected = null, includeAll = false) {
        return `${includeAll ? `<option value="">All permitted branches</option>` : ""}${accessibleBranches().map((branch) => `<option value="${branch.id}" ${Number(selected) === branch.id ? "selected" : ""}>${esc(branch.name)}</option>`).join("")}`;
    }

    function populateBranchSelects() {
        document.querySelectorAll("[data-branch-select]").forEach((select) => {
            const hasAll = select.querySelector('option[value=""]');
            const current = select.value;
            select.innerHTML = branchOptions(current, Boolean(hasAll));
        });
    }

    function applyAccess() {
        document.querySelectorAll("[data-super-only]").forEach((element) => { element.hidden = !isSuper(); });
        document.querySelectorAll("[data-permission]").forEach((element) => { element.hidden = !can(element.dataset.permission); });
        document.getElementById("admin-name").textContent = state.access.full_name;
        document.getElementById("welcome-name").textContent = state.access.full_name.split(" ")[0];
        document.getElementById("admin-avatar").textContent = state.access.full_name.charAt(0).toUpperCase();
        document.getElementById("admin-role").textContent = isSuper() ? "Super Admin" : `Mini Admin · ${state.access.branch_ids.length} branch(es)`;
    }

    let sessionMonitor = null;
    let sessionRedirectStarted = false;

    function redirectToAdminLogin() {
        if (sessionRedirectStarted) return;

        sessionRedirectStarted = true;

        if (sessionMonitor) {
            window.clearInterval(sessionMonitor);
            sessionMonitor = null;
        }

        sessionStorage.removeItem("smart_admin_csrf");
        location.replace("/admin/login?reason=session-ended");
    }

    async function checkAdminSession() {
        try {
            await API.get(`/api/admin/auth/me?check=${Date.now()}`);
        } catch (error) {
            if (error.status === 401) {
                redirectToAdminLogin();
            }
        }
    }

    function startSessionMonitor() {
        if (sessionMonitor) return;

        sessionMonitor = window.setInterval(
            checkAdminSession,
            5000,
        );

        window.addEventListener(
            "focus",
            checkAdminSession,
        );
    }

    async function logout() {
        if (sessionMonitor) {
            window.clearInterval(sessionMonitor);
            sessionMonitor = null;
        }

        try {
            await API.post("/api/admin/auth/logout", {});
        } catch (_) {
            // Clear browser state even if the session was already revoked.
        }

        redirectToAdminLogin();
    }

    async function bootstrap() {
        try {
            [state.access, state.branches] = await Promise.all([
                API.get("/api/admin/access/me"),
                API.get("/api/branches?active_only=false"),
            ]);
            applyAccess();
            populateBranchSelects();
            document.getElementById("admin-date").textContent = new Intl.DateTimeFormat("en-PK", { dateStyle: "full" }).format(new Date());
            document.getElementById("admin-loading").hidden = true;
            document.getElementById("admin-app").hidden = false;
            await showSection("overview", true);
            startSessionMonitor();
        } catch (error) {
            if (error.status === 401 || error.status === 403) location.replace("/admin/login");
            else {
                document.getElementById("admin-loading").innerHTML = `<strong>Dashboard could not open</strong><span>${esc(error.message)}</span><button class="admin-button secondary" onclick="location.reload()">Try again</button>`;
            }
        }
    }

    async function showSection(name, force = false) {
        const navButton = document.querySelector(`[data-section="${name}"]`);
        if (!navButton || navButton.hidden) return;
        state.section = name;
        document.querySelectorAll(".admin-section").forEach((section) => section.classList.toggle("active", section.id === `section-${name}`));
        document.querySelectorAll("[data-section]").forEach((button) => button.classList.toggle("active", button.dataset.section === name));
        document.getElementById("admin-page-title").textContent = titles[name];
        document.getElementById("admin-sidebar").classList.remove("is-open");
        if (!force && state.loaded.has(name)) return;
        try {
            const loaders = { overview: loadOverview, orders: loadOrders, prices: loadPrices, catalog: loadCatalog, inventory: loadInventory, imports: async () => {}, content: loadContent, discounts: loadDiscounts, team: loadTeam, reports: loadReports };
            await loaders[name]?.();
            state.loaded.add(name);
        } catch (error) {
            toast(error.message, "error");
        }
    }

    function orderTable(items, compact = false) {
        if (!items.length) return empty("No orders match these filters.");
        return `<table class="admin-table"><thead><tr><th>Order</th><th>Customer</th><th>Branch</th><th>Status</th><th>Total</th><th>Placed</th>${compact ? "" : "<th>Actions</th>"}</tr></thead><tbody>${items.map((order) => `<tr><td><strong>${esc(order.order_number)}</strong><small>${esc(statusLabel(order.fulfillment_method))}</small></td><td><strong>${esc(order.customer_name)}</strong><small>${esc(order.phone_number)}</small></td><td>${esc(branchName(order.branch_id))}</td><td>${statusPill(order.status)}</td><td><strong>${API.formatMoney(order.total_amount)}</strong></td><td>${API.formatDate(order.created_at)}</td>${compact ? "" : `<td><div class="table-actions"><button data-view-order="${order.id}">Details</button>${can("orders.update_status") ? `<button data-update-order="${order.id}">Update status</button>` : ""}</div></td>`}</tr>`).join("")}</tbody></table>`;
    }

    async function loadOverview() {
        const branchCount = accessibleBranches().length;
        const recent = can("orders.read") ? await API.get("/api/orders?skip=0&limit=8") : { total: 0, items: [] };
        const today = new Date().toISOString().slice(0, 10);
        const [pending, confirmed, processing, ready, delivery, completed] = can("orders.read") ? await Promise.all([
            "pending", "confirmed", "processing", "ready_for_pickup", "out_for_delivery", "completed",
        ].map((status) => API.get(`/api/orders${API.query({ order_status: status, created_from: status === "completed" ? today : null, created_to: status === "completed" ? today : null, skip: 0, limit: 1 })}`))) : Array(6).fill({ total: 0 });
        const openTotal = pending.total + confirmed.total + processing.total + ready.total + delivery.total;
        const stats = document.querySelectorAll("#overview-stats article strong");
        stats[0].textContent = openTotal.toLocaleString();
        stats[1].textContent = completed.total.toLocaleString();
        if (isSuper()) {
            const revenue = await API.get(`/api/admin/business/revenue?date_from=${today}&date_to=${today}`);
            stats[2].textContent = API.formatMoney(revenue.total_revenue);
            stats[3].textContent = branchCount.toLocaleString();
        } else {
            stats[3].textContent = branchCount.toLocaleString();
        }
        document.getElementById("overview-orders").innerHTML = orderTable(recent.items || [], true);
    }

    function currentOrderFilters() {
        const form = document.getElementById("order-filters");
        const values = formObject(form);
        return { ...values, skip: state.orderSkip, limit: state.orderLimit };
    }

    async function loadOrders() {
        const filters = currentOrderFilters();
        state.orderResult = await API.get(`/api/orders${API.query(filters)}`);
        document.getElementById("orders-count").textContent = `${state.orderResult.total.toLocaleString()} order(s)`;
        document.getElementById("orders-table").innerHTML = orderTable(state.orderResult.items || []);
        const page = Math.floor(state.orderSkip / state.orderLimit) + 1;
        const pages = Math.max(1, Math.ceil(state.orderResult.total / state.orderLimit));
        document.getElementById("orders-pagination").innerHTML = `<button data-order-page="prev" ${page <= 1 ? "disabled" : ""}>Previous</button><span>Page ${page} of ${pages}</span><button data-order-page="next" ${page >= pages ? "disabled" : ""}>Next</button>`;
    }

    async function viewOrder(orderId) {
        const [order, history] = await Promise.all([API.get(`/api/orders/${orderId}`), API.get(`/api/orders/${orderId}/history`)]);
        modal(`<div class="modal-form"><span class="admin-eyebrow">Order detail</span><h2>${esc(order.order_number)}</h2><p>${esc(order.customer_name)} · ${esc(order.phone_number)} · ${esc(branchName(order.branch_id))}</p><div class="preview-summary"><span>${statusPill(order.status)}</span><span>${API.formatMoney(order.total_amount)}</span><span>${esc(statusLabel(order.fulfillment_method))}</span></div><table class="admin-table"><thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${order.items.map((item) => `<tr><td>${esc(item.product_name)}<small>${esc(item.variant_name || "")}</small></td><td>${item.quantity}</td><td>${API.formatMoney(item.unit_price)}</td><td>${API.formatMoney(item.line_total)}</td></tr>`).join("")}</tbody></table><h3>Status history</h3><div class="session-list">${history.map((item) => `<div class="session-row"><div><strong>${esc(statusLabel(item.new_status))}</strong><small>${esc(item.change_note || "No note")} · ${esc(item.changed_by_name || "System")}</small></div><small>${API.formatDate(item.created_at)}</small></div>`).join("") || empty("No history yet.")}</div></div>`);
    }

    async function updateOrder(orderId) {
        const order = await API.get(`/api/orders/${orderId}`);
        modal(`<form class="modal-form" id="order-status-form" data-order-id="${orderId}"><span class="admin-eyebrow">Permanent history update</span><h2>Update ${esc(order.order_number)}</h2><p>Every change is saved with your admin identity and timestamp.</p><label>New status<select name="status" required>${["pending", "confirmed", "processing", "ready_for_pickup", "out_for_delivery", "completed", "cancelled"].map((value) => `<option value="${value}" ${value === order.status ? "selected" : ""}>${esc(statusLabel(value))}</option>`).join("")}</select></label><label>Internal note<textarea name="note" rows="3" maxlength="500" placeholder="Why is this status changing?"></textarea></label><button class="admin-button primary" type="submit">Save status update</button></form>`);
    }

    async function loadPrices() {
        const values = formObject(document.getElementById("price-filters"));
        values.active_only = document.querySelector('#price-filters [name="active_only"]').checked;
        values.different_only = document.querySelector('#price-filters [name="different_only"]').checked;
        state.priceResult = await API.get(`/api/admin/business/products/prices${API.query({ ...values, skip: 0, limit: 500 })}`);
        document.getElementById("prices-count").textContent = `${state.priceResult.total.toLocaleString()} product(s)`;
        const items = state.priceResult.items || [];
        if (!items.length) { document.getElementById("prices-table").innerHTML = empty("No matching products."); return; }
        const branches = accessibleBranches();
        document.getElementById("prices-table").innerHTML = `<table class="admin-table"><thead><tr><th>Product</th><th>Master price</th><th>Price rule</th>${branches.map((branch) => `<th>${esc(branch.name)}</th>`).join("")}</tr></thead><tbody>${items.map((product) => `<tr><td><strong>${esc(product.product_name)}</strong><small>${esc(product.barcode)} · ${esc(product.category_name)}</small></td><td>${isSuper() ? `<div class="table-actions"><input class="mini-price-input" data-master-price="${product.product_id}" type="number" min="0" step="0.01" value="${product.master_price}"><button data-save-master="${product.product_id}">Save</button></div>` : API.formatMoney(product.master_price)}</td><td><span class="price-pill ${product.same_price_on_all_branches ? "" : "different"}">${product.same_price_on_all_branches ? "Same on all branches" : `Different: ${esc(product.different_branch_names.join(", "))}`}</span></td>${branches.map((branch) => { const value = product.branch_prices.find((price) => price.branch_id === branch.id); return `<td><div class="price-cell"><strong>${API.formatMoney(value?.effective_price)}</strong><small>${value?.price_source === "branch_override" ? "Branch price" : "Master price"}</small>${can("prices.update") ? `<div class="table-actions"><input class="mini-price-input" data-branch-price="${branch.id}:${product.product_id}" type="number" min="0" step="0.01" value="${value?.effective_price ?? product.master_price}"><button data-save-branch-price="${branch.id}:${product.product_id}">Save</button>${value?.price_source === "branch_override" ? `<button data-reset-branch-price="${branch.id}:${product.product_id}">Reset</button>` : ""}</div>` : ""}</div></td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
    }

    async function saveBranchPrice(key) {
        const [branchId, productId] = key.split(":").map(Number);
        const input = document.querySelector(`[data-branch-price="${key}"]`);
        await API.put(`/api/admin/business/branches/${branchId}/products/${productId}/price`, { override_price: Number(input.value) });
        toast("Branch price updated.");
        await loadPrices();
    }

    function updateBulkProductControls() {
        const button = document.getElementById("bulk-disable-products");
        const selectAll = document.getElementById("catalog-select-all");
        const checkboxes = [
            ...document.querySelectorAll(
                "[data-product-select]:not(:disabled)",
            ),
        ];
        const checkedCount = checkboxes.filter(
            (checkbox) => checkbox.checked,
        ).length;

        if (button) {
            button.disabled = state.selectedProductIds.size === 0;
            button.textContent = (
                `Disable selected (${state.selectedProductIds.size})`
            );
        }

        if (selectAll) {
            selectAll.checked = (
                checkboxes.length > 0
                && checkedCount === checkboxes.length
            );
            selectAll.indeterminate = (
                checkedCount > 0
                && checkedCount < checkboxes.length
            );
        }
    }

    async function loadCatalog() {
        const filterForm = document.getElementById(
            "catalog-product-filters",
        );
        const search = filterForm
            ? new FormData(filterForm).get("search")?.trim()
            : "";

        const [categories, productResult, branches] = await Promise.all([
            API.get("/api/categories?active_only=false"),
            API.get(
                `/api/products${API.query({
                    active_only: false,
                    search,
                    skip: state.catalogSkip,
                    limit: state.catalogLimit,
                })}`,
            ),
            API.get("/api/branches?active_only=false"),
        ]);

        state.categories = categories;
        state.products = productResult.items || [];
        state.catalogResult = productResult;
        state.branches = branches;
        populateBranchSelects();

        document.getElementById("catalog-categories").innerHTML = categories.length ? categories.map((category) => `<article class="content-list-item"><div class="content-thumb">${category.image_url ? `<img src="${esc(category.image_url)}" alt="">` : esc(category.name.charAt(0))}</div><div><h3>${esc(category.name)}</h3><p>${esc(statusLabel(category.display_mode))} · Order ${category.display_order} · ${category.is_active ? "Active" : "Inactive"}</p><div class="catalog-media-actions"><label>Icon<input type="file" hidden accept="image/jpeg,image/png,image/webp" data-category-icon="${category.id}"></label><label>Banner<input type="file" hidden accept="image/jpeg,image/png,image/webp" data-category-banner="${category.id}"></label></div></div><div class="table-actions"><button data-edit-category="${category.id}">Edit</button><button class="danger" data-deactivate-category="${category.id}">${category.is_active ? "Disable" : "Keep disabled"}</button></div></article>`).join("") : empty("No categories yet.");
        document.getElementById("catalog-branches").innerHTML = branches.length ? branches.map((branch) => `<article class="content-list-item"><div class="content-thumb">⌖</div><div><h3>${esc(branch.name)}</h3><p>${esc(branch.code)} · ${branch.is_active ? "Customer-visible" : "Inactive"}</p></div><div class="table-actions"><button data-edit-branch="${branch.id}">Edit</button><button class="danger" data-deactivate-branch="${branch.id}">${branch.is_active ? "Disable" : "Keep disabled"}</button></div></article>`).join("") : empty("No branches yet.");

        document.getElementById("catalog-products-count").textContent = (
            `Showing ${state.products.length} of ${productResult.total} product(s)`
        );

        document.getElementById("catalog-products").innerHTML = state.products.length
            ? `<table class="admin-table"><thead><tr><th><input class="product-select-checkbox" id="catalog-select-all" type="checkbox" aria-label="Select every active product on this page"></th><th>Product</th><th>Category</th><th>Master price</th><th>Status</th><th>Media & options</th><th>Actions</th></tr></thead><tbody>${state.products.map((product) => `<tr><td><input class="product-select-checkbox" data-product-select="${product.id}" type="checkbox" ${state.selectedProductIds.has(product.id) ? "checked" : ""} ${product.is_active ? "" : "disabled"} aria-label="Select ${esc(product.name)}"></td><td><strong>${esc(product.name)}</strong><small>${esc(product.barcode)} · ${esc(product.unit_size || "No unit size")}</small></td><td>${esc(state.categories.find((category) => category.id === product.category_id)?.name || `Category ${product.category_id}`)}</td><td>${API.formatMoney(product.master_price)}</td><td>${statusPill(product.is_active ? "active" : "inactive")}</td><td><div class="catalog-media-actions"><label>Main image<input type="file" hidden accept="image/jpeg,image/png,image/webp" data-product-image="${product.id}"></label><label>Gallery<input type="file" hidden accept="image/jpeg,image/png,image/webp" data-product-gallery="${product.id}"></label><button data-product-variants="${product.id}">Variants</button></div></td><td><div class="table-actions"><button data-edit-product="${product.id}">Edit</button>${product.is_active ? `<button class="danger" data-deactivate-product="${product.id}">Disable</button>` : "Disabled"}</div></td></tr>`).join("")}</tbody></table>`
            : empty("No products match this search.");

        const currentPage = Math.floor(
            state.catalogSkip / state.catalogLimit,
        ) + 1;
        const pageCount = Math.max(
            1,
            Math.ceil(productResult.total / state.catalogLimit),
        );

        document.getElementById("catalog-products-pagination").innerHTML = (
            `<button data-catalog-page="prev" ${currentPage <= 1 ? "disabled" : ""}>Previous</button>`
            + `<span>Page ${currentPage} of ${pageCount}</span>`
            + `<button data-catalog-page="next" ${currentPage >= pageCount ? "disabled" : ""}>Next</button>`
        );

        updateBulkProductControls();
    }

    async function openBranchForm(branchId = null) {
        const branch = branchId ? await API.get(`/api/branches/${branchId}`) : null;
        modal(`<form class="modal-form" id="catalog-branch-form" data-branch-id="${branchId || ""}"><span class="admin-eyebrow">Store location</span><h2>${branch ? "Edit branch" : "Add branch"}</h2><label>Branch name<input name="name" minlength="2" maxlength="100" required value="${esc(branch?.name || "")}"></label><label>Branch code<input name="code" minlength="2" maxlength="50" pattern="[A-Za-z0-9_-]+" required value="${esc(branch?.code || "")}"></label><label class="check-label"><input type="checkbox" name="is_active" ${branch?.is_active === false ? "" : "checked"}> Active for customers</label><button class="admin-button primary" type="submit">${branch ? "Save branch" : "Create branch"}</button></form>`);
    }

    async function openCategoryForm(categoryId = null) {
        const category = categoryId ? await API.get(`/api/categories/${categoryId}`) : null;
        modal(`<form class="modal-form" id="catalog-category-form" data-category-id="${categoryId || ""}"><span class="admin-eyebrow">Store navigation</span><h2>${category ? "Edit category" : "Add category"}</h2><label>Name<input name="name" minlength="2" maxlength="120" required value="${esc(category?.name || "")}"></label><label>Description<textarea name="description" rows="3" maxlength="1000">${esc(category?.description || "")}</textarea></label><div class="form-row"><label>Display order<input type="number" name="display_order" min="0" value="${category?.display_order || 0}"></label><label>Homepage display<select name="display_mode"><option value="default_heading" ${category?.display_mode === "custom_image_banner" ? "" : "selected"}>Default heading</option><option value="custom_image_banner" ${category?.display_mode === "custom_image_banner" ? "selected" : ""}>Custom image banner</option></select></label></div><label class="check-label"><input type="checkbox" name="is_active" ${category?.is_active === false ? "" : "checked"}> Active on storefront</label><button class="admin-button primary" type="submit">${category ? "Save category" : "Create category"}</button></form>`);
    }

    async function openProductForm(productId = null) {
        if (!state.categories.length) state.categories = await API.get("/api/categories?active_only=false");
        const product = productId ? await API.get(`/api/products/${productId}`) : null;
        modal(`<form class="modal-form" id="catalog-product-form" data-product-id="${productId || ""}"><span class="admin-eyebrow">Product master record</span><h2>${product ? "Edit product" : "Add product"}</h2><div class="form-row"><label>Barcode<input name="barcode" maxlength="64" required value="${esc(product?.barcode || "")}"></label><label>Product name<input name="name" minlength="2" maxlength="255" required value="${esc(product?.name || "")}"></label></div><label>Description<textarea name="description" rows="3" maxlength="2000">${esc(product?.description || "")}</textarea></label><div class="form-row"><label>Unit size<input name="unit_size" maxlength="100" placeholder="1 kg / 500 ml" value="${esc(product?.unit_size || "")}"></label><label>Master price<input type="number" name="master_price" min="0" step="0.01" required value="${product?.master_price ?? ""}"></label></div><label>Category<select name="category_id" required>${state.categories.map((category) => `<option value="${category.id}" ${product?.category_id === category.id ? "selected" : ""}>${esc(category.name)}</option>`).join("")}</select></label><label class="check-label"><input type="checkbox" name="is_active" ${product?.is_active === false ? "" : "checked"}> Active on storefront</label><button class="admin-button primary" type="submit">${product ? "Save product" : "Create product"}</button></form>`);
    }

    async function openVariants(productId) {
        const [product, variants] = await Promise.all([API.get(`/api/products/${productId}`), API.get(`/api/variants/product/${productId}?include_inactive=true`)]);
        modal(`<div class="modal-form"><span class="admin-eyebrow">Product options</span><h2>${esc(product.name)} variants</h2><div class="session-list">${variants.map((variant) => `<div class="session-row"><div><strong>${esc(variant.name)}</strong><small>${esc(variant.sku)} · Adjustment ${API.formatMoney(variant.price_adjustment)} · ${variant.is_active ? "Active" : "Inactive"}</small></div>${variant.is_active ? `<button class="admin-button danger" data-deactivate-variant="${variant.id}:${productId}">Disable</button>` : ""}</div>`).join("") || empty("No variants. Customers will buy the standard product.")}</div><form class="modal-form nested-form" id="variant-create-form" data-product-id="${productId}"><h3>Add a variant</h3><div class="form-row"><label>Option name<input name="name" required placeholder="Large / 1 litre"></label><label>SKU<input name="sku" required pattern="[A-Za-z0-9._-]+"></label></div><label>Price adjustment<input type="number" name="price_adjustment" step="0.01" value="0"></label><label class="check-label"><input type="checkbox" name="is_default"> Default option</label><button class="admin-button primary" type="submit">Add variant</button></form></div>`);
    }

    async function loadInventory() {
        const form = document.getElementById("inventory-filters");
        const values = formObject(form);
        if (!values.branch_id) {
            const first = accessibleBranches()[0];
            if (!first) { document.getElementById("inventory-table").innerHTML = empty("No assigned branch."); return; }
            form.branch_id.value = String(first.id);
            values.branch_id = String(first.id);
        }
        const result = await API.get(`/api/availability/branch/${values.branch_id}${API.query({ in_stock: values.in_stock, skip: 0, limit: 200 })}`);
        document.getElementById("inventory-count").textContent = `${result.total.toLocaleString()} product(s) at ${branchName(values.branch_id)}`;
        document.getElementById("inventory-table").innerHTML = result.items.length ? `<table class="admin-table"><thead><tr><th>Product</th><th>Current status</th><th>Message</th><th>Action</th></tr></thead><tbody>${result.items.map((item) => `<tr><td><strong>${esc(item.product_name)}</strong><small>${esc(item.barcode)}</small></td><td>${statusPill(item.is_in_stock ? "in stock" : "inactive")}</td><td>${esc(item.stock_message || "Default availability")}</td><td><div class="table-actions"><button data-stock-toggle="${item.product_id}:${values.branch_id}:${item.is_in_stock ? "false" : "true"}">Mark ${item.is_in_stock ? "out of stock" : "in stock"}</button><button data-stock-reset="${item.product_id}:${values.branch_id}">Use default</button></div></td></tr>`).join("")}</tbody></table>` : empty("No products match this filter.");
    }

    async function uploadImport(form) {
        const type = form.dataset.importForm;
        state.importProductSkip = 0;
        const data = new FormData();
        const file = form.querySelector('[name="excel_file"]').files[0];
        if (!file) return;
        data.append("excel_file", file);
        const button = form.querySelector("button");
        button.disabled = true;
        button.textContent = "Uploading…";
        try {
            let result;
            if (type === "master") result = await API.upload("/api/price-imports/master/preview", data);
            if (type === "branch") result = await API.upload(`/api/price-imports/branch/${form.branch_id.value}/preview`, data);
            if (type === "products") result = await API.upload("/api/product-imports/preview", data);
            await renderImportPreview(type, result);
        } finally {
            button.disabled = false;
            button.textContent = "Upload & preview";
        }
    }

    async function renderImportPreview(type, result) {
        const target = document.getElementById("import-preview");
        if (type === "products") {
            state.activeImport = { type, productBatchId: result.id, priceBatchId: null };
            target.innerHTML = await productImportMarkup(result.id, false);
        } else {
            state.activeImport = { type, priceBatchId: result.id, productBatchId: result.product_import_batch_id || null };
            const priceIsEditable = result.status === "preview";
            const priceButton = priceIsEditable
                ? type === "master"
                    ? `<button class="admin-button primary" data-master-price-apply="${result.id}">Confirm master price changes only</button>`
                    : `<button class="admin-button primary" data-price-apply="branch:${result.id}">Confirm selected branch prices</button>`
                : `<span class="import-complete-note">✓ Price changes have been applied.</span>`;
            const priceDescription = type === "master"
                ? "Only matched products are handled here. New products shown below are not created by this button."
                : "Only matched products for the selected branch are handled here. Unchanged prices remain untouched.";
            const priceMarkup = `<section class="import-workflow-section"><div class="card-head"><div><span class="admin-eyebrow">Step 1 · Prices only</span><h2>${type === "master" ? "Master" : "Branch"} price preview #${result.id}</h2><p>${priceDescription}</p></div>${statusPill(result.status)}</div><div class="preview-summary"><span>${result.total_rows.toLocaleString()} checked</span><span>${result.changed_rows.toLocaleString()} changed</span><span>${result.unchanged_rows.toLocaleString()} unchanged</span>${type === "master" ? `<span>${Number(result.new_product_rows || 0).toLocaleString()} new products</span>` : ""}<span>${result.invalid_rows.toLocaleString()} invalid</span></div>${priceImportRowsTable(result.rows || [], result.id)}<div class="import-action-bar"><div><strong>Apply price updates</strong><small>This action does not create any new product.</small></div><div class="table-actions">${priceButton}</div></div></section>`;
            let productMarkup = "";
            if (type === "master" && result.product_import_batch_id) {
                productMarkup = await productImportMarkup(result.product_import_batch_id, true);
            }
            target.innerHTML = `${priceMarkup}${productMarkup}`;
        }
    }

    function priceImportRowsTable(rows, batchId) {
        if (!rows?.length) return empty("No changed or invalid preview rows.");
        return `<div class="table-wrap"><table class="admin-table"><thead><tr><th>Use</th><th>Row</th><th>Item code</th><th>Item</th><th>Old price</th><th>New price</th><th>Status</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${row.status === "changed" ? `<input class="import-row-check" type="checkbox" data-price-import-select="${batchId}:${row.id}" ${row.apply_selected ? "checked" : ""}>` : "—"}</td><td>${row.excel_row_number}</td><td>${esc(row.barcode || "—")}</td><td>${esc(row.item_name || "—")}</td><td>${row.current_price === null ? "—" : API.formatMoney(row.current_price)}</td><td>${row.uploaded_price === null ? "—" : API.formatMoney(row.uploaded_price)}</td><td>${statusPill(row.status)}</td></tr>`).join("")}</tbody></table></div>`;
    }

    function categoryReviewControl(batchId, row) {
        const selectedId = row.confirmed_category_id || row.suggested_category_id || "";
        const newName = row.confirmed_category_name || row.suggested_category_name || "";
        const existingOptions = state.categories
            .filter((category) => category.is_active && category.slug !== "deals")
            .map((category) => `<option value="id:${category.id}" ${Number(selectedId) === category.id ? "selected" : ""}>${esc(category.name)}</option>`)
            .join("");
        const newOption = newName ? `<option value="new:${esc(newName)}" selected>New category: ${esc(newName)}</option>` : "";
        return `<div class="table-actions"><select data-import-category="${batchId}:${row.id}"><option value="">Choose category</option>${newOption}${existingOptions}</select><button data-use-import-category="${batchId}:${row.id}">Use</button></div>`;
    }

    async function productImportMarkup(batchId, embedded) {
        if (!state.categories.length) state.categories = await API.get("/api/categories?active_only=false");
        const [batch, summary, rows] = await Promise.all([
            API.get(`/api/product-imports/${batchId}`),
            API.get(`/api/product-imports/${batchId}/summary`),
            API.get(`/api/product-imports/${batchId}/rows?skip=${state.importProductSkip}&limit=${state.importPageSize}`),
        ]);
        const isEditable = !["applied", "cancelled", "failed"].includes(batch.status);
        const table = rows.items.length ? `<div class="table-wrap"><table class="admin-table"><thead><tr><th>Upload</th><th>Row</th><th>Item code</th><th>Product</th><th>Price</th><th>AI / reviewed category</th><th>Status</th></tr></thead><tbody>${rows.items.map((row) => `<tr><td>${isEditable && ["pending_category", "ready"].includes(row.status) ? `<input class="import-row-check" type="checkbox" data-product-import-select="${batchId}:${row.id}" ${row.apply_selected ? "checked" : ""}>` : "—"}</td><td>${row.excel_row_number}</td><td>${esc(row.barcode || "—")}</td><td><strong>${esc(row.item_name || "—")}</strong>${row.ai_reason ? `<small>${esc(row.ai_reason)}</small>` : ""}</td><td>${row.uploaded_price === null ? "—" : API.formatMoney(row.uploaded_price)}</td><td>${isEditable && ["pending_category", "ready"].includes(row.status) ? categoryReviewControl(batchId, row) : "—"}</td><td>${row.suggested_category_name ? `<span class="new-category-pill">New: ${esc(row.suggested_category_name)}</span>` : statusPill(row.status)}</td></tr>`).join("")}</tbody></table></div>` : empty("No rows on this page.");
        const from = rows.total ? rows.skip + 1 : 0;
        const to = Math.min(rows.skip + rows.limit, rows.total);
        const pager = `<div class="pagination"><button data-import-page="previous" ${rows.skip === 0 ? "disabled" : ""}>Previous</button><span>${from.toLocaleString()}–${to.toLocaleString()} of ${rows.total.toLocaleString()}</span><button data-import-page="next" ${to >= rows.total ? "disabled" : ""}>Next</button></div>`;
        const bulkSelection = isEditable ? `<div class="import-bulk-controls"><div><strong>Choose products from the complete file</strong><small>These buttons affect all ${summary.total_rows.toLocaleString()} reviewable rows, not only the current page.</small></div><div class="table-actions"><button data-product-bulk-selection="${batchId}:true">Check all</button><button data-product-bulk-selection="${batchId}:false">Uncheck all</button></div></div>` : "";
        const productActions = isEditable
            ? `<div class="import-action-bar"><div><strong>Create selected new products</strong><small>${embedded ? "This is separate from the master-price confirmation above." : "Only checked and reviewed products will be created."}</small></div><div class="table-actions"><button data-product-ai="${batchId}">Categorize next selected rows</button><button data-product-confirm="${batchId}">Accept reviewed AI suggestions</button><button class="admin-button primary" data-product-apply="${batchId}">Confirm selected new products only</button></div></div>`
            : `<div class="import-action-bar"><span class="import-complete-note">✓ This product list has been processed.</span></div>`;
        return `<section class="import-workflow-section"><div class="card-head"><div><span class="admin-eyebrow">${embedded ? "Step 2 · New products only" : "Product review"}</span><h2>${embedded ? "New products found in master file" : `Product import #${batch.id}`}</h2><p>Choose products, run AI, review existing or proposed new categories, then confirm this list separately.</p></div>${statusPill(batch.status)}</div><div class="preview-summary"><span>${summary.total_rows.toLocaleString()} total</span><span>${summary.selected_rows.toLocaleString()} selected</span><span>${summary.categorized_rows.toLocaleString()} checked</span><span>${summary.pending_rows.toLocaleString()} remaining</span><span>${summary.existing_category_rows.toLocaleString()} existing category</span><span>${summary.new_category_rows.toLocaleString()} new category</span><span>${summary.invalid_rows.toLocaleString()} invalid</span></div><div class="import-progress"><span style="width:${Math.max(0, Math.min(100, summary.progress_percentage))}%"></span></div>${bulkSelection}${summary.new_category_rows ? `<p class="import-review-note">Groq proposed ${summary.new_category_rows} new category assignment(s). Review them below; categories are created only after final confirmation.</p>` : ""}${table}${pager}${productActions}</section>`;
    }

    async function refreshActiveImport() {
        if (!state.activeImport) return;
        if (state.activeImport.type === "products") {
            const batch = await API.get(`/api/product-imports/${state.activeImport.productBatchId}`);
            await renderImportPreview("products", batch);
        } else {
            const batch = await API.get(`/api/price-imports/${state.activeImport.priceBatchId}`);
            await renderImportPreview(state.activeImport.type, batch);
        }
    }

    async function loadContent() {
        const [settings, banners] = await Promise.all([API.get("/api/content/settings"), API.get("/api/content/banners")]);
        const form = document.getElementById("settings-form");
        form.store_name.value = settings.store_name;
        form.announcement_primary.value = settings.announcement_primary || "";
        form.announcement_secondary.value = settings.announcement_secondary || "";
        form.announcement_is_active.checked = settings.announcement_is_active;
        const logoPreview = document.getElementById("website-logo-preview");
        const logoImage = document.getElementById("website-logo-preview-image");

        if (logoPreview && logoImage) {
            logoPreview.hidden = !settings.logo_url;

            if (settings.logo_url) {
                logoImage.src = settings.logo_url;
            } else {
                logoImage.removeAttribute("src");
            }
        }

        document.getElementById("banner-list").innerHTML = banners.length ? banners.map((banner) => `<article class="content-list-item"><div class="content-thumb">${banner.image_url ? `<img src="${esc(banner.image_url)}" alt="">` : "✦"}</div><div><h3>${esc(banner.title)}</h3><p>${esc(banner.subtitle || "No subtitle")} · ${banner.is_active ? "Active" : "Inactive"}</p></div><div class="table-actions"><label class="upload-action">Upload image<input type="file" accept="image/jpeg,image/png,image/webp" data-banner-image="${banner.id}" hidden></label><button data-toggle-banner="${banner.id}:${banner.is_active ? "false" : "true"}">${banner.is_active ? "Disable" : "Enable"}</button><button class="danger" data-delete-banner="${banner.id}">Remove</button></div></article>`).join("") : empty("No homepage banners yet.");
    }

    async function loadDiscounts() {
        const campaigns = await API.get("/api/discounts");
        document.getElementById("discount-list").innerHTML = campaigns.length ? campaigns.map((campaign) => `<article class="content-list-item"><div class="content-thumb">%</div><div><h3>${esc(campaign.title)}</h3><p>${esc(statusLabel(campaign.campaign_type))} · ${API.formatDate(campaign.start_at)} to ${API.formatDate(campaign.end_at)} · ${campaign.prices.length} branch price(s)</p></div><span>${statusPill(campaign.is_active ? "active" : "inactive")}</span><div class="table-actions"><button data-discount-prices="${campaign.id}">Assign prices</button><button data-toggle-discount="${campaign.id}:${campaign.is_active ? "false" : "true"}">${campaign.is_active ? "Disable" : "Enable"}</button></div></article>`).join("") : empty("No campaigns yet. Create your first timed deal.");
    }

    async function openDiscountForm() {
        modal(`<form class="modal-form" id="discount-form"><span class="admin-eyebrow">New storefront offer</span><h2>Create discount campaign</h2><label>Campaign title<input name="title" required minlength="2"></label><label>Description<textarea name="description" rows="2"></textarea></label><label>Type<select name="campaign_type"><option value="deal">Deal</option><option value="special_discount">Special discount</option></select></label><div class="form-row"><label>Starts<input type="datetime-local" name="start_at" required></label><label>Ends<input type="datetime-local" name="end_at" required></label></div><button class="admin-button primary" type="submit">Create campaign</button></form>`);
    }

    async function openDiscountPrices(campaignId) {
        const products = await API.get("/api/products?active_only=true&skip=0&limit=100");
        modal(`<form class="modal-form" id="discount-price-form" data-campaign-id="${campaignId}"><span class="admin-eyebrow">Branch special price</span><h2>Assign campaign pricing</h2><label>Product<select name="product_id" required>${products.items.map((product) => `<option value="${product.id}">${esc(product.name)} · ${esc(product.barcode)}</option>`).join("")}</select></label><label>Special price<input type="number" name="special_price" min="0" step="0.01" required></label><span class="admin-eyebrow">Branches</span><div class="checkbox-grid">${state.branches.map((branch) => `<label><input type="checkbox" name="branch_ids" value="${branch.id}">${esc(branch.name)}</label>`).join("")}</div><button class="admin-button primary" type="submit">Save special prices</button></form>`);
    }

    async function loadTeam() {
        [state.permissions] = await Promise.all([API.get("/api/admin/access/permissions")]);
        const [admins, logs] = await Promise.all([API.get("/api/admin/access/admins"), API.get("/api/admin/access/audit-logs?skip=0&limit=50")]);
        document.getElementById("admin-list").innerHTML = `<table class="admin-table"><thead><tr><th>Admin</th><th>Role</th><th>Branches</th><th>Login</th><th>Last login</th><th>Actions</th></tr></thead><tbody>${admins.map((admin) => `<tr><td><strong>${esc(admin.full_name)}</strong><small>${esc(admin.email)}</small></td><td><span class="role-pill ${admin.role}">${esc(statusLabel(admin.role))}</span></td><td>${admin.role === "super_admin" ? "All branches" : admin.branch_ids.map(branchName).map(esc).join(", ")}</td><td>${statusPill(admin.is_active && admin.login_allowed ? "active" : "inactive")}</td><td>${API.formatDate(admin.last_login_at)}</td><td><div class="table-actions">${admin.role === "mini_admin" ? `<button data-edit-admin="${admin.id}">Access</button><button data-admin-sessions="${admin.id}">Sessions</button><button class="danger" data-revoke-all="${admin.id}">Log out all</button>` : "Protected super admin"}</div></td></tr>`).join("")}</tbody></table>`;
        document.getElementById("audit-list").innerHTML = logs.length ? `<table class="admin-table"><thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Target</th><th>IP</th></tr></thead><tbody>${logs.map((log) => `<tr><td>${API.formatDate(log.created_at)}</td><td>${esc(statusLabel(log.action))}</td><td>${log.actor_admin_id || "System"}</td><td>${log.target_admin_id || "—"}</td><td>${esc(log.ip_address || "—")}</td></tr>`).join("")}</tbody></table>` : empty("No audit activity yet.");
    }

    async function openAdminForm(adminId = null) {
        const admin = adminId ? await API.get(`/api/admin/access/admins/${adminId}`) : null;
        const assignable = state.permissions.filter((permission) => permission.is_assignable_to_mini_admin);
        modal(`<form class="modal-form" id="mini-admin-form" data-admin-id="${adminId || ""}"><span class="admin-eyebrow">${admin ? "Edit access" : "New team member"}</span><h2>${admin ? esc(admin.full_name) : "Add mini admin"}</h2><label>Full name<input name="full_name" minlength="2" required value="${esc(admin?.full_name || "")}"></label>${admin ? "" : `<label>Email address<input type="email" name="email" required></label><label>Temporary password<input type="password" name="password" minlength="8" required><small>Minimum 8 characters.</small></label>`}<span class="admin-eyebrow">Assigned branches</span><div class="checkbox-grid">${state.branches.map((branch) => `<label><input type="checkbox" name="branch_ids" value="${branch.id}" ${admin?.branch_ids.includes(branch.id) ? "checked" : ""}>${esc(branch.name)}</label>`).join("")}</div><span class="admin-eyebrow">Permissions</span><div class="checkbox-grid">${assignable.map((permission) => `<label><input type="checkbox" name="permission_codes" value="${esc(permission.code)}" ${admin?.permission_codes.includes(permission.code) || (!admin && ["products.read", "prices.read", "prices.update", "orders.read", "orders.update_status", "imports.manage"].includes(permission.code)) ? "checked" : ""}>${esc(permission.description)}</label>`).join("")}</div><label class="check-label"><input type="checkbox" name="is_active" ${admin?.is_active === false ? "" : "checked"}> Account active</label><label class="check-label"><input type="checkbox" name="login_allowed" ${admin?.login_allowed === false ? "" : "checked"}> Login allowed</label><div class="form-row"><label>Allow login from<input type="datetime-local" name="login_allowed_from"></label><label>Allow login until<input type="datetime-local" name="login_allowed_until"></label></div><button class="admin-button primary" type="submit">${admin ? "Save access" : "Create mini admin"}</button></form>`);
    }

    async function openSessions(adminId) {
        const sessions = await API.get(`/api/admin/access/admins/${adminId}/sessions?active_only=false`);
        modal(`<div class="modal-form"><span class="admin-eyebrow">Session control</span><h2>Admin login sessions</h2><p>Revoking a session signs that device out immediately.</p><div class="session-list">${sessions.map((session) => `<div class="session-row"><div><strong>${session.revoked_at ? "Revoked" : "Active until " + API.formatDate(session.expires_at)}</strong><small>${esc(session.ip_address || "Unknown IP")} · ${esc(session.user_agent || "Unknown device")}</small></div>${session.revoked_at ? `<small>${API.formatDate(session.revoked_at)}</small>` : `<button class="admin-button danger" data-revoke-session="${session.id}">Revoke</button>`}</div>`).join("") || empty("No sessions found.")}</div></div>`);
    }

    function reportValues() { return formObject(document.getElementById("report-filters")); }
    async function loadReports() {
        const values = reportValues();
        const [revenue, exports] = await Promise.all([
            API.get(`/api/admin/business/revenue${API.query(values)}`),
            API.get("/api/admin/business/exports?skip=0&limit=50"),
        ]);
        document.getElementById("report-revenue").textContent = API.formatMoney(revenue.total_revenue);
        document.getElementById("report-orders").textContent = revenue.total_orders.toLocaleString();
        document.getElementById("report-average").textContent = API.formatMoney(revenue.total_orders ? Number(revenue.total_revenue) / revenue.total_orders : 0);
        const max = Math.max(1, ...revenue.daily.map((item) => Number(item.revenue)));
        document.getElementById("revenue-chart").innerHTML = revenue.daily.length ? revenue.daily.map((item) => `<div class="revenue-bar" title="${esc(item.sale_date)} · ${API.formatMoney(item.revenue)}"><div style="height:${Math.max(3, Number(item.revenue) / max * 220)}px"></div><small>${esc(item.sale_date.slice(5))}</small></div>`).join("") : empty("No completed sales in this period.");
        document.getElementById("export-history").innerHTML = exports.length ? exports.map((item) => `<div class="export-row"><div><strong>${esc(item.file_name)}</strong><span>${item.record_count} records · ${API.formatDate(item.created_at)}</span></div>${item.export_type === "orders" && item.allows_order_deletion && !item.orders_deleted_at ? `<button class="admin-button danger" data-delete-exported="${item.id}">Delete exported orders</button>` : `<small>${item.orders_deleted_at ? `${item.deleted_order_count} orders archived` : item.export_type}</small>`}</div>`).join("") : empty("No exports created yet.");
    }

    async function handleSubmit(event) {
        const form = event.target;
        if (form.id === "order-filters") { event.preventDefault(); state.orderSkip = 0; await loadOrders(); }
        if (form.id === "price-filters") { event.preventDefault(); await loadPrices(); }
        if (form.id === "catalog-product-filters") { event.preventDefault(); state.catalogSkip = 0; await loadCatalog(); }
        if (form.id === "inventory-filters") { event.preventDefault(); await loadInventory(); }
        if (form.id === "report-filters") { event.preventDefault(); await loadReports(); }
        if (form.id === "catalog-branch-form") {
            event.preventDefault(); const data = formObject(form); const branchId = form.dataset.branchId; data.is_active = form.is_active.checked;
            try { branchId ? await API.patch(`/api/branches/${branchId}`, data) : await API.post("/api/branches", data); closeModal(); toast(branchId ? "Branch updated." : "Branch created."); await loadCatalog(); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "catalog-category-form") {
            event.preventDefault(); const data = formObject(form); const categoryId = form.dataset.categoryId; const displayMode = data.display_mode; delete data.display_mode; data.display_order = Number(data.display_order); data.description = data.description || null; data.is_active = form.is_active.checked; if (!categoryId) data.image_url = null;
            try { const saved = categoryId ? await API.patch(`/api/categories/${categoryId}`, data) : await API.post("/api/categories", data); await API.patch(`/api/categories/${saved.id}/display-mode`, { display_mode: displayMode }); closeModal(); toast(categoryId ? "Category updated." : "Category created."); await loadCatalog(); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "catalog-product-form") {
            event.preventDefault(); const data = formObject(form); const productId = form.dataset.productId; data.master_price = Number(data.master_price); data.category_id = Number(data.category_id); data.description = data.description || null; data.unit_size = data.unit_size || null; data.image_url = productId ? undefined : null; data.is_active = form.is_active.checked; if (productId) delete data.image_url;
            try { productId ? await API.patch(`/api/products/${productId}`, data) : await API.post("/api/products", data); closeModal(); toast(productId ? "Product updated." : "Product created."); await loadCatalog(); state.loaded.delete("prices"); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "variant-create-form") {
            event.preventDefault(); const data = formObject(form);
            try { await API.post(`/api/variants/product/${form.dataset.productId}`, { name: data.name, sku: data.sku, barcode: null, attributes: {}, price_adjustment: Number(data.price_adjustment || 0), display_order: 0, is_default: form.is_default.checked, is_active: true }); toast("Product variant added."); await openVariants(form.dataset.productId); } catch (error) { toast(error.message, "error"); }
        }
        if (form.matches("[data-import-form]")) { event.preventDefault(); try { await uploadImport(form); } catch (error) { toast(error.message, "error"); } }
        if (form.id === "order-status-form") {
            event.preventDefault(); const data = formObject(form);
            try { await API.patch(`/api/orders/${form.dataset.orderId}/status`, { status: data.status, note: data.note || null }); closeModal(); toast("Order status and history updated."); await loadOrders(); state.loaded.delete("overview"); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "settings-form") {
            event.preventDefault();
            const data = formObject(form);
            data.store_name = data.store_name.trim();
            data.announcement_primary = data.announcement_primary.trim() || null;
            data.announcement_secondary = data.announcement_secondary.trim() || null;
            data.announcement_is_active = form.announcement_is_active.checked;
            try {
                await API.patch("/api/content/settings", data);
                await loadContent();
                toast("Storefront settings saved.");
            } catch (error) {
                toast(error.message, "error");
            }
        }
        if (form.id === "banner-form") {
            event.preventDefault(); const data = formObject(form);
            try { await API.post("/api/content/banners", { ...data, subtitle: data.subtitle || null, button_text: data.button_text || null, button_url: data.button_url || null, display_order: 0, start_at: null, end_at: null, is_active: true }); form.reset(); toast("Banner created. You can upload its image now."); await loadContent(); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "discount-form") {
            event.preventDefault(); const data = formObject(form);
            try { await API.post("/api/discounts", { ...data, description: data.description || null, start_at: toIso(data.start_at), end_at: toIso(data.end_at), display_order: 0, is_active: true }); closeModal(); toast("Discount campaign created."); await loadDiscounts(); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "discount-price-form") {
            event.preventDefault(); const data = new FormData(form); const branchIds = data.getAll("branch_ids").map(Number);
            try { await API.put(`/api/discounts/${form.dataset.campaignId}/prices`, { product_id: Number(data.get("product_id")), branch_ids: branchIds, special_price: Number(data.get("special_price")) }); closeModal(); toast("Special branch prices assigned."); await loadDiscounts(); } catch (error) { toast(error.message, "error"); }
        }
        if (form.id === "mini-admin-form") {
            event.preventDefault(); const data = new FormData(form); const adminId = form.dataset.adminId;
            const payload = { full_name: data.get("full_name"), branch_ids: data.getAll("branch_ids").map(Number), permission_codes: data.getAll("permission_codes"), login_allowed: form.login_allowed.checked, login_allowed_from: toIso(data.get("login_allowed_from")), login_allowed_until: toIso(data.get("login_allowed_until")) };
            if (adminId) payload.is_active = form.is_active.checked; else { payload.email = data.get("email"); payload.password = data.get("password"); }
            try { adminId ? await API.patch(`/api/admin/access/admins/${adminId}`, payload) : await API.post("/api/admin/access/admins", payload); closeModal(); toast(adminId ? "Admin access updated." : "Mini admin created."); await loadTeam(); } catch (error) { toast(error.message, "error"); }
        }
    }

    async function handleClick(event) {
        const section = event.target.closest("[data-section]"); if (section) return showSection(section.dataset.section);
        const go = event.target.closest("[data-go-section]"); if (go) return showSection(go.dataset.goSection);
        const refresh = event.target.closest("[data-refresh-section]"); if (refresh) return showSection(refresh.dataset.refreshSection, true);
        if (event.target.closest("[data-close-modal]")) return closeModal();
        if (event.target.closest("#admin-menu-toggle")) return document.getElementById("admin-sidebar").classList.toggle("is-open");
        if (event.target.closest("#admin-logout")) return logout();
        if (event.target.closest("#new-branch")) return openBranchForm();
        if (event.target.closest("#new-category")) return openCategoryForm();
        if (event.target.closest("#new-product")) return openProductForm();
        if (event.target.closest("#bulk-disable-products")) {
            const productIds = [...state.selectedProductIds];
            if (!productIds.length) return;
            if (!confirm(`Disable ${productIds.length} selected product(s) on the storefront?`)) return;
            try {
                const result = await API.post(
                    "/api/products/bulk-deactivate",
                    { product_ids: productIds },
                );
                state.selectedProductIds.clear();
                state.loaded.delete("prices");
                await loadCatalog();
                toast(`${result.deactivated_count} product(s) disabled.`);
            } catch (error) {
                toast(error.message, "error");
            }
            return;
        }
        const editBranch = event.target.closest("[data-edit-branch]"); if (editBranch) return openBranchForm(editBranch.dataset.editBranch).catch((error) => toast(error.message, "error"));
        const editCategory = event.target.closest("[data-edit-category]"); if (editCategory) return openCategoryForm(editCategory.dataset.editCategory).catch((error) => toast(error.message, "error"));
        const editProduct = event.target.closest("[data-edit-product]"); if (editProduct) return openProductForm(editProduct.dataset.editProduct).catch((error) => toast(error.message, "error"));
        const productVariants = event.target.closest("[data-product-variants]"); if (productVariants) return openVariants(productVariants.dataset.productVariants).catch((error) => toast(error.message, "error"));
        const deactivateBranch = event.target.closest("[data-deactivate-branch]"); if (deactivateBranch && confirm("Disable this branch for customers?")) { try { await API.delete(`/api/branches/${deactivateBranch.dataset.deactivateBranch}`); toast("Branch disabled."); await loadCatalog(); } catch (error) { toast(error.message, "error"); } return; }
        const deactivateCategory = event.target.closest("[data-deactivate-category]"); if (deactivateCategory && confirm("Disable this category and hide it from the storefront?")) { try { await API.delete(`/api/categories/${deactivateCategory.dataset.deactivateCategory}`); toast("Category disabled."); await loadCatalog(); } catch (error) { toast(error.message, "error"); } return; }
        const deactivateProduct = event.target.closest("[data-deactivate-product]"); if (deactivateProduct && confirm("Disable this product on the storefront?")) { try { await API.delete(`/api/products/${deactivateProduct.dataset.deactivateProduct}`); toast("Product disabled."); await loadCatalog(); } catch (error) { toast(error.message, "error"); } return; }
        const deactivateVariant = event.target.closest("[data-deactivate-variant]"); if (deactivateVariant && confirm("Disable this product option?")) { const [variantId, productId] = deactivateVariant.dataset.deactivateVariant.split(":"); try { await API.delete(`/api/variants/${variantId}`); toast("Variant disabled."); await openVariants(productId); } catch (error) { toast(error.message, "error"); } return; }
        const orderView = event.target.closest("[data-view-order]"); if (orderView) return viewOrder(orderView.dataset.viewOrder).catch((error) => toast(error.message, "error"));
        const orderUpdate = event.target.closest("[data-update-order]"); if (orderUpdate) return updateOrder(orderUpdate.dataset.updateOrder).catch((error) => toast(error.message, "error"));
        const page = event.target.closest("[data-order-page]"); if (page) { state.orderSkip = Math.max(0, state.orderSkip + (page.dataset.orderPage === "next" ? state.orderLimit : -state.orderLimit)); return loadOrders(); }
        const catalogPage = event.target.closest("[data-catalog-page]");
        if (catalogPage) {
            state.catalogSkip = Math.max(
                0,
                state.catalogSkip + (
                    catalogPage.dataset.catalogPage === "next"
                        ? state.catalogLimit
                        : -state.catalogLimit
                ),
            );
            return loadCatalog();
        }
        const branchSave = event.target.closest("[data-save-branch-price]"); if (branchSave) return saveBranchPrice(branchSave.dataset.saveBranchPrice).catch((error) => toast(error.message, "error"));
        const branchReset = event.target.closest("[data-reset-branch-price]"); if (branchReset) { const [branchId, productId] = branchReset.dataset.resetBranchPrice.split(":"); try { await API.delete(`/api/admin/business/branches/${branchId}/products/${productId}/price`); toast("Branch price reset to master."); await loadPrices(); } catch (error) { toast(error.message, "error"); } return; }
        const masterSave = event.target.closest("[data-save-master]"); if (masterSave) { const input = document.querySelector(`[data-master-price="${masterSave.dataset.saveMaster}"]`); try { await API.patch(`/api/admin/business/products/${masterSave.dataset.saveMaster}/master-price`, { master_price: Number(input.value) }); toast("Master price updated."); await loadPrices(); } catch (error) { toast(error.message, "error"); } return; }
        const stock = event.target.closest("[data-stock-toggle]"); if (stock) { const [productId, branchId, value] = stock.dataset.stockToggle.split(":"); try { await API.put(`/api/availability/${productId}/${branchId}`, { is_in_stock: value === "true", stock_message: value === "true" ? null : "Temporarily out of stock" }); toast("Availability updated."); await loadInventory(); } catch (error) { toast(error.message, "error"); } return; }
        const stockReset = event.target.closest("[data-stock-reset]"); if (stockReset) { const [productId, branchId] = stockReset.dataset.stockReset.split(":"); try { await API.delete(`/api/availability/${productId}/${branchId}`); toast("Default availability restored."); await loadInventory(); } catch (error) { toast(error.message, "error"); } return; }
        const priceApply = event.target.closest("[data-price-apply]"); if (priceApply) { const [type, batchId] = priceApply.dataset.priceApply.split(":"); try { const result = await API.post(`/api/price-imports/branch/${batchId}/apply`, { confirm: true }); await renderImportPreview(type, result); toast("Selected prices applied."); } catch (error) { toast(error.message, "error"); } return; }
        const masterPriceApply = event.target.closest("[data-master-price-apply]");
        if (masterPriceApply) {
            if (!confirm("Apply only the selected master-price changes? New products will not be created.")) return;
            try {
                const result = await API.post(
                    `/api/price-imports/master/${masterPriceApply.dataset.masterPriceApply}/apply`,
                    { confirm: true },
                );
                await renderImportPreview("master", result);
                toast("Master-price changes applied. New products were not created.");
            } catch (error) {
                toast(error.message, "error");
            }
            return;
        }
        const productBulkSelection = event.target.closest("[data-product-bulk-selection]");
        if (productBulkSelection) {
            const [batchId, rawSelection] = productBulkSelection.dataset.productBulkSelection.split(":");
            const applySelected = rawSelection === "true";
            productBulkSelection.disabled = true;
            try {
                const summary = await API.patch(
                    `/api/product-imports/${batchId}/rows/selection-all`,
                    { apply_selected: applySelected },
                );
                await refreshActiveImport();
                toast(
                    applySelected
                        ? `All reviewable products checked (${summary.selected_rows.toLocaleString()} selected).`
                        : "All new products unchecked. No new product will be created unless selected again.",
                );
            } catch (error) {
                toast(error.message, "error");
            } finally {
                productBulkSelection.disabled = false;
            }
            return;
        }
        const productAi = event.target.closest("[data-product-ai]"); if (productAi) { try { await API.post(`/api/product-imports/${productAi.dataset.productAi}/categorize-ai?limit=100`, {}); await refreshActiveImport(); toast("Next selected products categorized."); } catch (error) { toast(error.message, "error"); } return; }
        const productConfirm = event.target.closest("[data-product-confirm]"); if (productConfirm) { try { await API.post(`/api/product-imports/${productConfirm.dataset.productConfirm}/confirm-ai`, { confirm: true }); await refreshActiveImport(); toast("AI suggestions accepted for selected rows."); } catch (error) { toast(error.message, "error"); } return; }
        const productApply = event.target.closest("[data-product-apply]");
        if (productApply) {
            if (!confirm("Create only the selected and reviewed new products? Master prices are handled separately.")) return;
            try {
                const result = await API.post(
                    `/api/product-imports/${productApply.dataset.productApply}/apply`,
                    { confirm: true },
                );
                if (state.activeImport?.type === "master") {
                    await refreshActiveImport();
                } else {
                    document.getElementById("import-preview").innerHTML = `<div class="empty-panel"><strong>${result.created_products.toLocaleString()} products created.</strong><br>${result.created_categories.length.toLocaleString()} categories created and ${result.skipped_rows.toLocaleString()} row(s) skipped.</div>`;
                }
                toast(`${result.created_products.toLocaleString()} selected new product(s) created.`);
            } catch (error) {
                toast(error.message, "error");
            }
            return;
        }
        const useCategory = event.target.closest("[data-use-import-category]"); if (useCategory) { const [batchId, rowId] = useCategory.dataset.useImportCategory.split(":"); const selectElement = document.querySelector(`[data-import-category="${batchId}:${rowId}"]`); const value = selectElement?.value || ""; if (!value) { toast("Choose a category first.", "error"); return; } const isNew = value.startsWith("new:"); try { await API.patch(`/api/product-imports/${batchId}/rows/${rowId}/category`, { confirmed_category_id: isNew ? null : Number(value.split(":")[1]), confirmed_category_name: isNew ? value.slice(4) : null, apply_selected: true }); await refreshActiveImport(); toast("Category reviewed."); } catch (error) { toast(error.message, "error"); } return; }
        const importPage = event.target.closest("[data-import-page]"); if (importPage && !importPage.disabled) { state.importProductSkip = Math.max(0, state.importProductSkip + (importPage.dataset.importPage === "next" ? state.importPageSize : -state.importPageSize)); await refreshActiveImport(); return; }
        if (event.target.closest("#new-discount")) return openDiscountForm();
        const discountPrice = event.target.closest("[data-discount-prices]"); if (discountPrice) return openDiscountPrices(discountPrice.dataset.discountPrices).catch((error) => toast(error.message, "error"));
        const toggleDiscount = event.target.closest("[data-toggle-discount]"); if (toggleDiscount) { const [id, active] = toggleDiscount.dataset.toggleDiscount.split(":"); try { await API.patch(`/api/discounts/${id}`, { is_active: active === "true" }); await loadDiscounts(); } catch (error) { toast(error.message, "error"); } return; }
        const toggleBanner = event.target.closest("[data-toggle-banner]"); if (toggleBanner) { const [id, active] = toggleBanner.dataset.toggleBanner.split(":"); try { await API.patch(`/api/content/banners/${id}`, { is_active: active === "true" }); await loadContent(); } catch (error) { toast(error.message, "error"); } return; }
        const deleteBanner = event.target.closest("[data-delete-banner]"); if (deleteBanner && confirm("Remove this banner permanently?")) { try { await API.delete(`/api/content/banners/${deleteBanner.dataset.deleteBanner}`); await loadContent(); toast("Banner removed."); } catch (error) { toast(error.message, "error"); } return; }
        if (event.target.closest("#remove-website-logo") && confirm("Remove the current store logo?")) {
            try {
                await API.delete("/api/content/settings/logo");
                await loadContent();
                toast("Store logo removed.");
            } catch (error) {
                toast(error.message, "error");
            }
            return;
        }
        if (event.target.closest("#new-admin")) return openAdminForm();
        const editAdmin = event.target.closest("[data-edit-admin]"); if (editAdmin) return openAdminForm(editAdmin.dataset.editAdmin).catch((error) => toast(error.message, "error"));
        const sessions = event.target.closest("[data-admin-sessions]"); if (sessions) return openSessions(sessions.dataset.adminSessions).catch((error) => toast(error.message, "error"));
        const revokeSession = event.target.closest("[data-revoke-session]"); if (revokeSession && confirm("Sign this device out now?")) { try { await API.post(`/api/admin/access/sessions/${revokeSession.dataset.revokeSession}/revoke`, { reason: "Revoked from super admin dashboard" }); closeModal(); toast("Session revoked."); } catch (error) { toast(error.message, "error"); } return; }
        const revokeAll = event.target.closest("[data-revoke-all]"); if (revokeAll && confirm("Log this admin out from every device?")) { try { await API.post(`/api/admin/access/admins/${revokeAll.dataset.revokeAll}/sessions/revoke-all`, { reason: "All sessions revoked from super admin dashboard" }); toast("All sessions revoked."); } catch (error) { toast(error.message, "error"); } return; }
        if (event.target.closest("#export-orders")) { try { const values = reportValues(); const result = await API.download(`/api/admin/business/exports/orders${API.query({ branch_id: values.branch_id, created_from: values.date_from, created_to: values.date_to })}`, "smart-orders.xlsx"); state.lastExportId = result.exportId; toast(`Downloaded ${result.filename}.`); await loadReports(); } catch (error) { toast(error.message, "error"); } return; }
        if (event.target.closest("#export-products")) { try { const values = reportValues(); const result = await API.download(`/api/admin/business/exports/products${API.query({ branch_id: values.branch_id, active_only: true })}`, "smart-products.xlsx"); toast(`Downloaded ${result.filename}.`); await loadReports(); } catch (error) { toast(error.message, "error"); } return; }
        const deleteExported = event.target.closest("[data-delete-exported]"); if (deleteExported && confirm("Permanent action: delete the completed orders captured by this verified export? Revenue and status history will be preserved.")) { try { const result = await API.post("/api/admin/business/orders/delete-exported", { export_id: Number(deleteExported.dataset.deleteExported), confirm: true }); toast(`${result.deleted_orders} exported orders deleted. Permanent history preserved.`); await loadReports(); } catch (error) { toast(error.message, "error"); } }
    }

    async function handleChange(event) {
        const priceImportSelect = event.target.closest(
            "[data-price-import-select]",
        );
        if (priceImportSelect) {
            const [batchId, rowId] = (
                priceImportSelect.dataset.priceImportSelect
            ).split(":");
            try {
                await API.patch(
                    `/api/price-imports/${batchId}/rows/selection`,
                    {
                        row_ids: [Number(rowId)],
                        apply_selected: priceImportSelect.checked,
                    },
                );
                toast("Price row selection updated.");
            } catch (error) {
                priceImportSelect.checked = !priceImportSelect.checked;
                toast(error.message, "error");
            }
            return;
        }

        const productImportSelect = event.target.closest(
            "[data-product-import-select]",
        );
        if (productImportSelect) {
            const [batchId, rowId] = (
                productImportSelect.dataset.productImportSelect
            ).split(":");
            try {
                await API.patch(
                    `/api/product-imports/${batchId}/rows/selection`,
                    {
                        row_ids: [Number(rowId)],
                        apply_selected: productImportSelect.checked,
                    },
                );
                await refreshActiveImport();
                toast("Product selection updated.");
            } catch (error) {
                productImportSelect.checked = !productImportSelect.checked;
                toast(error.message, "error");
            }
            return;
        }

        if (event.target.id === "catalog-select-all") {
            document.querySelectorAll(
                "[data-product-select]:not(:disabled)",
            ).forEach((checkbox) => {
                checkbox.checked = event.target.checked;
                const productId = Number(
                    checkbox.dataset.productSelect,
                );
                if (event.target.checked) {
                    state.selectedProductIds.add(productId);
                } else {
                    state.selectedProductIds.delete(productId);
                }
            });
            updateBulkProductControls();
            return;
        }

        const productSelect = event.target.closest(
            "[data-product-select]",
        );
        if (productSelect) {
            const productId = Number(
                productSelect.dataset.productSelect,
            );
            if (productSelect.checked) {
                state.selectedProductIds.add(productId);
            } else {
                state.selectedProductIds.delete(productId);
            }
            updateBulkProductControls();
            return;
        }

        if (event.target.id === "website-logo-file" && event.target.files?.[0]) {
            const data = new FormData(); data.append("file", event.target.files[0]);
            try {
                await API.upload("/api/content/settings/logo", data);
                event.target.value = "";
                await loadContent();
                toast("Store logo uploaded.");
            } catch (error) {
                toast(error.message, "error");
            }
            return;
        }
        const categoryIcon = event.target.closest("[data-category-icon]");
        if (categoryIcon?.files?.[0]) {
            const data = new FormData(); data.append("file", categoryIcon.files[0]);
            try { await API.upload(`/api/categories/${categoryIcon.dataset.categoryIcon}/icon`, data); toast("Category icon uploaded."); await loadCatalog(); } catch (error) { toast(error.message, "error"); }
            return;
        }
        const categoryBanner = event.target.closest("[data-category-banner]");
        if (categoryBanner?.files?.[0]) {
            const data = new FormData(); data.append("file", categoryBanner.files[0]);
            try { await API.upload(`/api/categories/${categoryBanner.dataset.categoryBanner}/banner`, data); toast("Category banner uploaded."); await loadCatalog(); } catch (error) { toast(error.message, "error"); }
            return;
        }
        const productImage = event.target.closest("[data-product-image]");
        if (productImage?.files?.[0]) {
            const data = new FormData(); data.append("image_file", productImage.files[0]);
            try { await API.upload(`/api/products/${productImage.dataset.productImage}/image`, data); toast("Main product image uploaded."); await loadCatalog(); } catch (error) { toast(error.message, "error"); }
            return;
        }
        const productGallery = event.target.closest("[data-product-gallery]");
        if (productGallery?.files?.[0]) {
            const data = new FormData(); data.append("file", productGallery.files[0]); data.append("display_order", "0"); data.append("is_primary", "false");
            try { await API.upload(`/api/product-gallery/product/${productGallery.dataset.productGallery}`, data); toast("Gallery image uploaded."); } catch (error) { toast(error.message, "error"); }
            return;
        }
        const bannerImage = event.target.closest("[data-banner-image]");
        if (!bannerImage?.files?.[0]) return;
        const data = new FormData(); data.append("file", bannerImage.files[0]);
        try { await API.upload(`/api/content/banners/${bannerImage.dataset.bannerImage}/image`, data); toast("Banner image uploaded."); await loadContent(); } catch (error) { toast(error.message, "error"); }
    }

    document.addEventListener("submit", handleSubmit);
    document.addEventListener("click", handleClick);
    document.addEventListener("change", handleChange);
    document.addEventListener("DOMContentLoaded", bootstrap);
})();
