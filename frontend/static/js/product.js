(function () {
    "use strict";
    const API = window.SmartAPI;
    const Store = window.SmartStore;
    const productId = Number(window.SMART_PRODUCT_ID);
    let product;
    let basePrice;
    let availability;
    let variants = [];
    let selectedVariant = null;
    let loadToken = 0;

    function renderGallery(gallery) {
        const images = [];
        const add = (url, alt) => {
            if (url && !images.some((item) => item.url === url)) images.push({ url, alt });
        };
        add(product.image_url, product.name);
        gallery.forEach((item) => add(item.image_url, item.alt_text || product.name));
        variants.forEach((variant) => (variant.image_urls || []).forEach((url) => add(url, `${product.name} ${variant.name}`)));
        const main = document.getElementById("product-main-image");
        const thumbs = document.getElementById("product-thumbnails");
        main.classList.remove("skeleton");
        if (!images.length) {
            main.innerHTML = Store.placeholder(product.name);
            thumbs.innerHTML = "";
            return;
        }
        main.innerHTML = Store.mediaMarkup(images[0].url, images[0].alt);
        thumbs.innerHTML = images.map((item, index) => `<button class="product-thumbnail ${index === 0 ? "active" : ""}" type="button" data-gallery-image="${index}">${Store.mediaMarkup(item.url, item.alt)}</button>`).join("");
        thumbs._gallery = images;
    }

    function renderPrice() {
        const price = selectedVariant?.effective_price ?? basePrice.effective_price;
        const normal = selectedVariant ? null : basePrice.special_price !== null ? basePrice.normal_price : null;
        const target = document.getElementById("product-price-large");
        target.innerHTML = `<strong>${API.formatMoney(price)}</strong>${normal !== null ? `<del>${API.formatMoney(normal)}</del><span class="save-label">Save ${Math.round(Number(basePrice.savings_percentage))}%</span>` : ""}`;
    }

    function renderStock() {
        const stock = selectedVariant ? selectedVariant.is_in_stock : availability.is_in_stock;
        const message = selectedVariant?.stock_message || availability.stock_message || (stock ? "In stock at your selected branch" : "Currently out of stock");
        const target = document.getElementById("product-stock-line");
        target.textContent = message;
        target.classList.toggle("out", !stock);
        document.getElementById("add-product-to-cart").disabled = !stock;
    }

    function selectVariant(variantId) {
        selectedVariant = variants.find((variant) => variant.variant_id === Number(variantId)) || null;
        document.querySelectorAll("[data-variant-id]").forEach((button) => button.classList.toggle("active", Number(button.dataset.variantId) === selectedVariant?.variant_id));
        renderPrice();
        renderStock();
        if (selectedVariant?.image_urls?.length) {
            const main = document.getElementById("product-main-image");
            main.innerHTML = Store.mediaMarkup(selectedVariant.image_urls[0], `${product.name} ${selectedVariant.name}`);
        }
    }

    function renderVariants() {
        const picker = document.getElementById("variant-picker");
        const options = document.getElementById("variant-options");
        if (!variants.length) {
            picker.hidden = true;
            selectedVariant = null;
            return;
        }
        picker.hidden = false;
        options.innerHTML = variants.map((variant) => `<button class="variant-option" data-variant-id="${variant.variant_id}" type="button" ${variant.is_in_stock ? "" : "disabled"}>${API.escapeHtml(variant.name)} · ${API.formatMoney(variant.effective_price)}</button>`).join("");
        const defaultVariant = variants.find((variant) => variant.is_default && variant.is_in_stock) || variants.find((variant) => variant.is_in_stock) || variants[0];
        selectVariant(defaultVariant.variant_id);
    }

    async function renderRelated() {
        try {
            const result = await API.get(`/api/products${API.query({ category_id: product.category_id, active_only: true, skip: 0, limit: 12 })}`);
            const items = (result.items || []).filter((item) => item.id !== product.id).slice(0, 10);
            const target = document.getElementById("related-products");
            target.innerHTML = items.map((item) => Store.productCard(item, { categoryName: Store.categoryName(item.category_id) })).join("");
            Store.hydrateCards(target);
        } catch (_) { /* Related products are optional. */ }
    }

    async function loadProduct() {
        await Store.ready;
        const token = ++loadToken;
        try {
            const results = await Promise.all([
                API.get(`/api/products/${productId}`),
                API.get(`/api/storefront/prices/${productId}/${Store.state.branch.id}`),
                API.get(`/api/availability/${productId}/${Store.state.branch.id}`),
                API.get(`/api/storefront/products/${productId}/variants/${Store.state.branch.id}`),
                API.get(`/api/product-gallery/product/${productId}`),
            ]);
            if (token !== loadToken) return;
            [product, basePrice, availability] = results;
            variants = results[3].items || [];
            const gallery = results[4] || [];
            document.title = `${product.name} | SMART CASH & CARRY`;
            document.getElementById("product-breadcrumb").textContent = product.name;
            document.getElementById("product-category-label").textContent = Store.categoryName(product.category_id);
            document.getElementById("product-title").textContent = product.name;
            document.getElementById("product-unit").textContent = product.unit_size || `Barcode: ${product.barcode}`;
            document.getElementById("product-description").textContent = product.description || "A dependable everyday essential, available at your selected SMART branch.";
            document.getElementById("product-branch-copy").textContent = Store.state.branch.name;
            renderVariants();
            renderPrice();
            renderStock();
            renderGallery(gallery);
            renderRelated();
        } catch (error) {
            document.getElementById("product-detail").innerHTML = `<div class="empty-state"><h3>Product unavailable</h3><p>${API.escapeHtml(error.message)}</p><a class="button button-primary" href="/shop">Back to shop</a></div>`;
        }
    }

    function addToCart() {
        if (!product || (variants.length && !selectedVariant)) return;
        const quantity = Math.max(1, Math.min(99, Number(document.getElementById("product-quantity").value || 1)));
        Store.addCartItem({
            product_id: product.id,
            variant_id: selectedVariant?.variant_id || null,
            name: product.name,
            variant_name: selectedVariant?.name || null,
            unit_size: product.unit_size,
            image_url: selectedVariant?.image_urls?.[0] || product.image_url,
            unit_price: selectedVariant?.effective_price ?? basePrice.effective_price,
        }, quantity);
    }

    document.addEventListener("click", (event) => {
        const variant = event.target.closest("[data-variant-id]");
        if (variant) selectVariant(variant.dataset.variantId);
        const thumb = event.target.closest("[data-gallery-image]");
        if (thumb) {
            const images = document.getElementById("product-thumbnails")._gallery || [];
            const item = images[Number(thumb.dataset.galleryImage)];
            if (item) document.getElementById("product-main-image").innerHTML = Store.mediaMarkup(item.url, item.alt);
            document.querySelectorAll("[data-gallery-image]").forEach((button) => button.classList.toggle("active", button === thumb));
        }
        if (event.target.closest("[data-qty-minus]")) {
            const input = document.getElementById("product-quantity");
            input.value = String(Math.max(1, Number(input.value || 1) - 1));
        }
        if (event.target.closest("[data-qty-plus]")) {
            const input = document.getElementById("product-quantity");
            input.value = String(Math.min(99, Number(input.value || 1) + 1));
        }
        if (event.target.closest("#add-product-to-cart")) addToCart();
    });
    document.addEventListener("smart:branch-change", loadProduct);
    document.addEventListener("DOMContentLoaded", loadProduct);
})();
