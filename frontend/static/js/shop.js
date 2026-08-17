(function () {
    "use strict";
    const API = window.SmartAPI;
    const Store = window.SmartStore;
    const pageSize = 24;
    const params = new URLSearchParams(location.search);
    const filters = {
        search: params.get("q") || "",
        categoryId: params.get("category") ? Number(params.get("category")) : null,
        inStock: true,
        sort: "name",
        skip: 0,
        deals: params.get("deals") === "true",
    };
    let loaded = [];
    let total = 0;
    let requestNumber = 0;

    function renderFilters() {
        const target = document.getElementById("category-filters");
        const search = document.getElementById("shop-search");
        if (search) search.value = filters.search;
        if (!target) return;
        target.innerHTML = `
            <label class="filter-option"><input type="radio" name="category" value="" ${filters.categoryId ? "" : "checked"}><span>All categories</span></label>
            ${Store.state.categories.map((category) => `<label class="filter-option"><input type="radio" name="category" value="${category.id}" ${filters.categoryId === category.id ? "checked" : ""}><span>${API.escapeHtml(category.name)}</span></label>`).join("")}`;
    }

    async function enrichProduct(product) {
        try {
            const [price, availability] = await Promise.all([
                API.get(`/api/storefront/prices/${product.id || product.product_id}/${Store.state.branch.id}`),
                API.get(`/api/availability/${product.id || product.product_id}/${Store.state.branch.id}`),
            ]);
            return { ...product, ...price, availability };
        } catch (_) {
            return { ...product, effective_price: product.master_price || product.special_price || 0, availability: { is_in_stock: true } };
        }
    }

    function sortedProducts(products) {
        const visible = filters.inStock ? products.filter((product) => product.availability?.is_in_stock !== false) : products;
        return [...visible].sort((left, right) => {
            if (filters.sort === "price-low") return Number(left.effective_price) - Number(right.effective_price);
            if (filters.sort === "price-high") return Number(right.effective_price) - Number(left.effective_price);
            return String(left.name).localeCompare(String(right.name));
        });
    }

    function renderProducts() {
        const target = document.getElementById("shop-product-grid");
        const count = document.getElementById("results-count");
        const button = document.getElementById("load-more-products");
        const visible = sortedProducts(loaded);
        count.textContent = `${total.toLocaleString()} product${total === 1 ? "" : "s"} found`;
        if (!visible.length) {
            target.innerHTML = `<div class="empty-state shop-empty"><div class="empty-state-icon"><svg class="icon"><use href="#i-search"></use></svg></div><h3>No matching products</h3><p>Try a different search, category or branch.</p><button class="button button-outline" type="button" data-reset-shop>Clear filters</button></div>`;
        } else {
            target.innerHTML = visible.map((product) => Store.productCard(product, {
                categoryName: Store.categoryName(product.category_id),
                price: product.effective_price,
                normalPrice: product.normal_price,
            })).join("");
            visible.forEach((product) => {
                if (product.availability?.is_in_stock === false) {
                    const card = target.querySelector(`[data-product-id="${product.id || product.product_id}"]`);
                    card?.classList.add("is-out-of-stock");
                }
            });
        }
        button.hidden = loaded.length >= total;
        Store.hydrateCards(target);
    }

    async function loadProducts(reset = true) {
        const currentRequest = ++requestNumber;
        const target = document.getElementById("shop-product-grid");
        if (reset) {
            filters.skip = 0;
            loaded = [];
            target.innerHTML = `<div class="skeleton product-skeleton"></div><div class="skeleton product-skeleton"></div><div class="skeleton product-skeleton"></div><div class="skeleton product-skeleton"></div>`;
        }
        try {
            let result;
            if (filters.deals && !filters.search && !filters.categoryId) {
                result = await API.get(`/api/storefront/discount-products/${Store.state.branch.id}${API.query({ skip: filters.skip, limit: pageSize })}`);
            } else {
                result = await API.get(`/api/products${API.query({ search: filters.search || null, category_id: filters.categoryId, active_only: true, skip: filters.skip, limit: pageSize })}`);
            }
            const enriched = await Promise.all((result.items || []).map(enrichProduct));
            if (currentRequest !== requestNumber) return;
            total = Number(result.total || 0);
            loaded = reset ? enriched : [...loaded, ...enriched];
            filters.skip = loaded.length;
            renderProducts();
        } catch (error) {
            if (currentRequest !== requestNumber) return;
            target.innerHTML = `<div class="empty-state shop-empty"><h3>We could not load the products</h3><p>${API.escapeHtml(error.message)}</p><button class="button button-outline" type="button" data-retry-shop>Try again</button></div>`;
        }
    }

    function resetFilters() {
        filters.search = "";
        filters.categoryId = null;
        filters.inStock = true;
        filters.sort = "name";
        filters.deals = false;
        document.getElementById("shop-search").value = "";
        document.getElementById("in-stock-filter").checked = true;
        document.getElementById("shop-sort").value = "name";
        history.replaceState({}, "", "/shop");
        renderFilters();
        loadProducts(true);
    }

    async function init() {
        await Store.ready;
        document.getElementById("shop-context").textContent = `Fresh products and live prices at ${Store.state.branch.name}.`;
        renderFilters();
        await loadProducts(true);
    }

    document.addEventListener("input", API.debounce((event) => {
        if (event.target.id !== "shop-search") return;
        filters.search = event.target.value.trim();
        filters.deals = false;
        loadProducts(true);
    }, 350));
    document.addEventListener("change", (event) => {
        if (event.target.matches('input[name="category"]')) {
            filters.categoryId = event.target.value ? Number(event.target.value) : null;
            filters.deals = false;
            loadProducts(true);
        }
        if (event.target.id === "in-stock-filter") {
            filters.inStock = event.target.checked;
            renderProducts();
        }
        if (event.target.id === "shop-sort") {
            filters.sort = event.target.value;
            renderProducts();
        }
    });
    document.addEventListener("click", (event) => {
        if (event.target.closest("#load-more-products")) loadProducts(false);
        if (event.target.closest("#clear-filters") || event.target.closest("[data-reset-shop]")) resetFilters();
        if (event.target.closest("[data-retry-shop]")) loadProducts(true);
        if (event.target.closest("#mobile-filter-button")) document.getElementById("shop-sidebar").classList.toggle("is-open");
    });
    document.addEventListener("smart:branch-change", () => loadProducts(true));
    document.addEventListener("DOMContentLoaded", init);
})();
