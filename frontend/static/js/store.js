(function () {
    "use strict";

    const API = window.SmartAPI;
    const BRANCH_KEY = "smart_branch";
    const CART_KEY = "smart_cart";
    const state = {
        branches: [],
        branch: null,
        content: null,
        categories: [],
        cart: readJson(CART_KEY, []),
    };
    if (!Array.isArray(state.cart)) state.cart = [];
    let branchReadyResolve;
    const branchReady = new Promise((resolve) => { branchReadyResolve = resolve; });
    let branchResolved = false;

    function readJson(key, fallback) {
        try {
            const value = JSON.parse(localStorage.getItem(key));
            return value ?? fallback;
        } catch (_) {
            return fallback;
        }
    }

    function saveCart() {
        localStorage.setItem(CART_KEY, JSON.stringify(state.cart));
        updateCartCount();
        document.dispatchEvent(new CustomEvent("smart:cart-change", { detail: state.cart }));
    }

    function updateCartCount() {
        const count = state.cart.reduce((total, item) => total + Number(item.quantity || 0), 0);
        document.querySelectorAll("[data-cart-count]").forEach((element) => {
            element.textContent = String(count);
            element.hidden = count === 0;
        });
    }

    function toast(message, type = "success") {
        const stack = document.getElementById("toast-stack");
        if (!stack) return;
        const item = document.createElement("div");
        item.className = `toast ${type}`;
        item.textContent = message;
        stack.appendChild(item);
        requestAnimationFrame(() => item.classList.add("show"));
        setTimeout(() => {
            item.classList.remove("show");
            setTimeout(() => item.remove(), 250);
        }, 3200);
    }

    function imageUrl(value) {
        if (!value) return null;
        if (/^(https?:|data:|blob:)/i.test(value)) return value;
        return value.startsWith("/") ? value : `/${value}`;
    }

    function placeholder(label = "SMART") {
        return `<div class="product-placeholder" aria-label="${API.escapeHtml(label)}"><span>🛒</span><small>${API.escapeHtml(label)}</small></div>`;
    }

    function mediaMarkup(url, alt, className = "") {
        const safeUrl = imageUrl(url);
        return safeUrl
            ? `<img class="${API.escapeHtml(className)}" src="${API.escapeHtml(safeUrl)}" alt="${API.escapeHtml(alt)}" loading="lazy" data-smart-image>`
            : placeholder(alt || "SMART");
    }

    function categoryName(categoryId) {
        return state.categories.find((category) => category.id === Number(categoryId))?.name || "SMART essentials";
    }

    function productCard(product, options = {}) {
        const id = product.id || product.product_id;
        const category = options.categoryName || categoryName(product.category_id);
        const discount = Number(product.savings_percentage || 0);
        const price = product.special_price ?? product.effective_price ?? options.price ?? product.master_price;
        const normal = product.normal_price ?? options.normalPrice;
        return `
            <article class="product-card" data-product-card data-product-id="${Number(id)}">
                <a class="product-card-image" href="/product/${Number(id)}">
                    ${discount > 0 ? `<span class="discount-badge">Save ${Math.round(discount)}%</span>` : ""}
                    ${mediaMarkup(product.image_url, product.name)}
                </a>
                <div class="product-card-body">
                    <span class="product-card-category">${API.escapeHtml(category)}</span>
                    <h3><a href="/product/${Number(id)}">${API.escapeHtml(product.name)}</a></h3>
                    <p class="product-card-unit">${API.escapeHtml(product.unit_size || product.barcode || "Everyday value")}</p>
                    <div class="product-card-price" data-card-price>
                        ${price !== undefined && price !== null ? `<strong>${API.formatMoney(price)}</strong>${normal && Number(normal) > Number(price) ? `<del>${API.formatMoney(normal)}</del>` : ""}` : `<span class="skeleton text-skeleton"></span>`}
                    </div>
                    <div class="product-card-actions">
                        <a href="/product/${Number(id)}">View details</a>
                        <button class="quick-add" type="button" data-quick-add="${Number(id)}" aria-label="Add ${API.escapeHtml(product.name)} to cart"><svg class="icon"><use href="#i-plus"></use></svg></button>
                    </div>
                </div>
            </article>`;
    }

    async function hydrateProductCard(card) {
        if (!card || card.dataset.hydrated === "true" || !state.branch) return;
        card.dataset.hydrated = "true";
        const productId = Number(card.dataset.productId);
        try {
            const [price, availability] = await Promise.all([
                API.get(`/api/storefront/prices/${productId}/${state.branch.id}`),
                API.get(`/api/availability/${productId}/${state.branch.id}`),
            ]);
            const priceBox = card.querySelector("[data-card-price]");
            if (priceBox) {
                priceBox.innerHTML = `<strong>${API.formatMoney(price.effective_price)}</strong>${price.special_price !== null ? `<del>${API.formatMoney(price.normal_price)}</del>` : ""}`;
            }
            const image = card.querySelector(".product-card-image");
            if (price.savings_percentage > 0 && image && !image.querySelector(".discount-badge")) {
                image.insertAdjacentHTML("afterbegin", `<span class="discount-badge">Save ${Math.round(Number(price.savings_percentage))}%</span>`);
            }
            if (!availability.is_in_stock) {
                card.classList.add("is-out-of-stock");
                image?.insertAdjacentHTML("afterbegin", `<span class="stock-badge">Out of stock</span>`);
                const button = card.querySelector("[data-quick-add]");
                if (button) button.disabled = true;
            }
        } catch (_) {
            card.dataset.hydrated = "false";
        }
    }

    function hydrateCards(root = document) {
        const cards = [...root.querySelectorAll("[data-product-card]:not([data-observed])")];
        if (!("IntersectionObserver" in window)) {
            cards.forEach(hydrateProductCard);
            return;
        }
        const observer = new IntersectionObserver((entries, instance) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                instance.unobserve(entry.target);
                hydrateProductCard(entry.target);
            });
        }, { rootMargin: "250px" });
        cards.forEach((card) => {
            card.dataset.observed = "true";
            observer.observe(card);
        });
    }

    function addCartItem(item, quantity = 1) {
        const productId = Number(item.product_id || item.id);
        const variantId = item.variant_id ? Number(item.variant_id) : null;
        const found = state.cart.find((entry) => entry.product_id === productId && (entry.variant_id || null) === variantId);
        if (found) {
            found.quantity = Math.min(99, Number(found.quantity) + Number(quantity));
            Object.assign(found, { ...item, product_id: productId, variant_id: variantId, quantity: found.quantity });
        } else {
            state.cart.push({ ...item, product_id: productId, variant_id: variantId, quantity: Math.min(99, Number(quantity)) });
        }
        saveCart();
        toast(`${item.name || item.product_name || "Product"} added to your cart.`);
    }

    function updateCartItem(productId, variantId, quantity) {
        const item = state.cart.find((entry) => entry.product_id === Number(productId) && (entry.variant_id || null) === (variantId ? Number(variantId) : null));
        if (!item) return;
        if (Number(quantity) <= 0) {
            removeCartItem(productId, variantId);
            return;
        }
        item.quantity = Math.min(99, Number(quantity));
        saveCart();
    }

    function removeCartItem(productId, variantId) {
        state.cart = state.cart.filter((entry) => !(entry.product_id === Number(productId) && (entry.variant_id || null) === (variantId ? Number(variantId) : null)));
        saveCart();
    }

    function clearCart() {
        state.cart = [];
        saveCart();
    }

    function checkoutItems() {
        return state.cart.map((item) => ({
            product_id: item.product_id,
            variant_id: item.variant_id || null,
            quantity: item.quantity,
        }));
    }

    async function quickAdd(productId) {
        if (!state.branch) {
            openBranchModal();
            return;
        }
        const card = document.querySelector(`[data-product-card][data-product-id="${productId}"]`);
        const button = card?.querySelector("[data-quick-add]");
        if (button) button.disabled = true;
        try {
            const [product, variants, price, availability] = await Promise.all([
                API.get(`/api/products/${productId}`),
                API.get(`/api/storefront/products/${productId}/variants/${state.branch.id}`),
                API.get(`/api/storefront/prices/${productId}/${state.branch.id}`),
                API.get(`/api/availability/${productId}/${state.branch.id}`),
            ]);
            if (!availability.is_in_stock) throw new Error(availability.stock_message || "This product is currently out of stock.");
            const availableVariants = (variants.items || []).filter((variant) => variant.is_in_stock);
            if ((variants.items || []).length && !availableVariants.length) throw new Error("All options for this product are currently out of stock.");
            const chosen = availableVariants.find((variant) => variant.is_default) || availableVariants[0] || null;
            addCartItem({
                product_id: product.id,
                variant_id: chosen?.variant_id || null,
                name: product.name,
                variant_name: chosen?.name || null,
                unit_size: product.unit_size,
                image_url: chosen?.image_urls?.[0] || product.image_url,
                unit_price: chosen?.effective_price ?? price.effective_price,
            });
        } catch (error) {
            toast(error.message, "error");
        } finally {
            if (button) button.disabled = false;
        }
    }

    function renderHeaderCategories() {
        const target = document.getElementById("header-category-links");
        if (!target) return;
        target.innerHTML = state.categories.slice(0, 8).map((category) =>
            `<a href="/shop?category=${category.id}">${API.escapeHtml(category.name)}</a>`
        ).join("");
    }

    function applyContent() {
        const settings = state.content?.settings;
        if (!settings) return;

        document.querySelectorAll("#store-name").forEach((node) => {
            node.textContent = settings.store_name;
        });

        const logo = document.getElementById("store-logo");
        const logoFallback = document.getElementById("store-logo-fallback");
        const brandMark = document.getElementById("brand-mark");
        const logoUrl = imageUrl(settings.logo_url);

        if (logo && logoFallback) {
            if (logoUrl) {
                brandMark?.classList.add("has-logo");
                logo.src = logoUrl;
                logo.hidden = false;
                logoFallback.hidden = true;
                logo.onload = () => {
                    brandMark?.classList.add("has-logo");
                    logo.hidden = false;
                    logoFallback.hidden = true;
                };
                logo.onerror = () => {
                    brandMark?.classList.remove("has-logo");
                    logo.hidden = true;
                    logoFallback.hidden = false;
                };
            } else {
                brandMark?.classList.remove("has-logo");
                logo.removeAttribute("src");
                logo.hidden = true;
                logoFallback.hidden = false;
            }
        }

        const announcement = document.getElementById("announcement-bar");
        const primary = document.getElementById("announcement-primary");
        const secondary = document.getElementById("announcement-secondary");
        const separator = document.getElementById("announcement-separator");
        const primaryText = settings.announcement_primary || "";
        const secondaryText = settings.announcement_secondary || "";

        if (primary) {
            primary.textContent = primaryText;
            primary.hidden = !primaryText;
        }

        if (secondary) {
            secondary.textContent = secondaryText;
            secondary.hidden = !secondaryText;
        }

        if (separator) {
            separator.hidden = !(primaryText && secondaryText);
        }

        if (announcement) {
            announcement.hidden = (
                !settings.announcement_is_active
                || (!primaryText && !secondaryText)
            );
        }
    }

    function openBranchModal(force = false) {
        const modal = document.getElementById("branch-modal");
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        modal.dataset.forced = String(force);
        document.body.classList.add("modal-open");
    }

    function closeBranchModal() {
        const modal = document.getElementById("branch-modal");
        if (!modal || !state.branch) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
    }

    function renderBranches() {
        const target = document.getElementById("branch-choice-list");
        if (!target) return;
        if (!state.branches.length) {
            target.innerHTML = `<p>No active branch is available yet.</p>`;
            return;
        }
        target.innerHTML = state.branches.map((branch) => `
            <button type="button" data-branch-id="${branch.id}" class="branch-choice ${state.branch?.id === branch.id ? "selected" : ""}">
                <span class="branch-choice-icon"><svg class="icon"><use href="#i-pin"></use></svg></span>
                <strong class="branch-choice-name">${API.escapeHtml(branch.name)}</strong>
                <svg class="icon choice-chevron"><use href="#i-chevron"></use></svg>
            </button>`).join("");
    }

    async function selectBranch(branchId, dispatch = true) {
        const branch = state.branches.find((item) => item.id === Number(branchId));
        if (!branch) return;
        const previousId = state.branch?.id;
        state.branch = branch;
        localStorage.setItem(BRANCH_KEY, JSON.stringify(branch));
        document.getElementById("current-branch-name")?.replaceChildren(document.createTextNode(branch.name));
        renderBranches();
        try {
            state.content = await API.get(`/api/storefront/content/${branch.id}`);
            state.categories = state.content.categories || [];
            applyContent();
            renderHeaderCategories();
        } catch (error) {
            toast(error.message, "error");
        }
        closeBranchModal();
        const wasResolved = branchResolved;
        if (!branchResolved) {
            branchResolved = true;
            branchReadyResolve(branch);
        }
        if (dispatch && wasResolved && previousId !== branch.id) {
            document.querySelectorAll("[data-product-card]").forEach((card) => {
                card.dataset.hydrated = "false";
                card.removeAttribute("data-observed");
            });
            document.dispatchEvent(new CustomEvent("smart:branch-change", { detail: branch }));
            hydrateCards();
        }
    }

    async function initBranch() {
        const errorTarget = document.getElementById("branch-modal-error");
        try {
            state.branches = await API.get("/api/branches?active_only=true");
            const stored = readJson(BRANCH_KEY, null);
            const valid = stored && state.branches.find((branch) => branch.id === Number(stored.id));
            state.branch = valid || null;
            renderBranches();
            if (valid) await selectBranch(valid.id, false);
            else openBranchModal(true);
        } catch (error) {
            if (errorTarget) {
                errorTarget.hidden = false;
                errorTarget.textContent = error.message;
            }
            openBranchModal(true);
        }
    }

    document.addEventListener("click", (event) => {
        const branchChoice = event.target.closest("[data-branch-id]");
        if (branchChoice) selectBranch(branchChoice.dataset.branchId);
        if (event.target.closest("#branch-trigger")) openBranchModal();
        const quickButton = event.target.closest("[data-quick-add]");
        if (quickButton) quickAdd(Number(quickButton.dataset.quickAdd));
    });

    document.addEventListener("error", (event) => {
        const image = event.target;
        if (!(image instanceof HTMLImageElement) || !image.matches("[data-smart-image]")) return;
        const wrapper = document.createElement("div");
        wrapper.className = "product-placeholder";
        wrapper.innerHTML = "<span>🛒</span><small>SMART</small>";
        image.replaceWith(wrapper);
    }, true);

    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("current-year")?.replaceChildren(document.createTextNode(String(new Date().getFullYear())));
        updateCartCount();
        initBranch();
    });

    window.SmartStore = {
        state,
        ready: branchReady,
        toast,
        imageUrl,
        mediaMarkup,
        placeholder,
        productCard,
        hydrateCards,
        addCartItem,
        updateCartItem,
        removeCartItem,
        clearCart,
        checkoutItems,
        saveCart,
        openBranchModal,
        selectBranch,
        categoryName,
    };
})();
