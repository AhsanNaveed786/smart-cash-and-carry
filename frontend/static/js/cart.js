(function () {
    "use strict";
    const API = window.SmartAPI;
    const Store = window.SmartStore;
    let quoteTimer;

    function itemKey(item) {
        return `${item.product_id}:${item.variant_id || 0}`;
    }

    function render() {
        const target = document.getElementById("cart-items");
        const cart = Store.state.cart;
        document.getElementById("clear-cart").hidden = cart.length === 0;
        document.getElementById("checkout-link").classList.toggle("disabled", cart.length === 0);
        if (!cart.length) {
            target.innerHTML = `<div class="empty-state"><div class="empty-state-icon"><svg class="icon"><use href="#i-cart"></use></svg></div><h3>Your basket is empty</h3><p>Browse branch-priced groceries and add your household favourites.</p><a class="button button-primary" href="/shop">Start shopping</a></div>`;
            updateTotals(0);
            return;
        }
        target.innerHTML = cart.map((item) => `
            <article class="cart-item" data-cart-key="${itemKey(item)}">
                <a class="cart-item-image" href="/product/${item.product_id}">${Store.mediaMarkup(item.image_url, item.name)}</a>
                <div><h3><a href="/product/${item.product_id}">${API.escapeHtml(item.name)}</a></h3><p>${API.escapeHtml(item.variant_name || item.unit_size || "Standard item")}</p><strong class="cart-item-price">${API.formatMoney(item.unit_price)}</strong></div>
                <div class="cart-item-controls">
                    <button class="cart-remove" type="button" data-cart-remove aria-label="Remove"><svg class="icon"><use href="#i-trash"></use></svg> Remove</button>
                    <div class="quantity-stepper"><button type="button" data-cart-minus aria-label="Decrease"><svg class="icon"><use href="#i-minus"></use></svg></button><input value="${item.quantity}" min="1" max="99" type="number" data-cart-quantity aria-label="Quantity"><button type="button" data-cart-plus aria-label="Increase"><svg class="icon"><use href="#i-plus"></use></svg></button></div>
                </div>
            </article>`).join("");
        updateTotals(cart.reduce((sum, item) => sum + Number(item.unit_price || 0) * Number(item.quantity), 0));
        refreshQuote();
    }

    function updateTotals(subtotal) {
        document.getElementById("cart-subtotal").textContent = API.formatMoney(subtotal);
        document.getElementById("cart-total").textContent = API.formatMoney(subtotal);
    }

    async function refreshQuote() {
        clearTimeout(quoteTimer);
        if (!Store.state.cart.length || !Store.state.branch) return;
        quoteTimer = setTimeout(async () => {
            try {
                const quote = await API.post("/api/orders/quote", {
                    branch_id: Store.state.branch.id,
                    fulfillment_method: "self_pickup",
                    items: Store.checkoutItems(),
                });
                updateTotals(quote.subtotal);
                quote.items.forEach((quoted) => {
                    const local = Store.state.cart.find((item) => item.product_id === quoted.product_id && (item.variant_id || null) === (quoted.variant_id || null));
                    if (local) local.unit_price = quoted.unit_price;
                    const row = document.querySelector(`[data-cart-key="${quoted.product_id}:${quoted.variant_id || 0}"]`);
                    const price = row?.querySelector(".cart-item-price");
                    if (price) price.textContent = `${API.formatMoney(quoted.unit_price)} each`;
                });
                localStorage.setItem("smart_cart", JSON.stringify(Store.state.cart));
            } catch (error) {
                Store.toast(error.message, "error");
            }
        }, 180);
    }

    function rowItem(element) {
        const [productId, variantId] = element.closest("[data-cart-key]").dataset.cartKey.split(":").map(Number);
        return Store.state.cart.find((item) => item.product_id === productId && (item.variant_id || 0) === variantId);
    }

    document.addEventListener("click", (event) => {
        const row = event.target.closest("[data-cart-key]");
        if (!row) {
            if (event.target.closest("#clear-cart")) {
                Store.clearCart();
                render();
            }
            if (event.target.closest("#checkout-link")?.classList.contains("disabled")) event.preventDefault();
            return;
        }
        const item = rowItem(row);
        if (!item) return;
        if (event.target.closest("[data-cart-remove]")) Store.removeCartItem(item.product_id, item.variant_id);
        if (event.target.closest("[data-cart-minus]")) Store.updateCartItem(item.product_id, item.variant_id, item.quantity - 1);
        if (event.target.closest("[data-cart-plus]")) Store.updateCartItem(item.product_id, item.variant_id, item.quantity + 1);
        render();
    });
    document.addEventListener("change", (event) => {
        if (!event.target.matches("[data-cart-quantity]")) return;
        const item = rowItem(event.target);
        if (item) Store.updateCartItem(item.product_id, item.variant_id, Math.max(1, Math.min(99, Number(event.target.value || 1))));
        render();
    });
    document.addEventListener("smart:branch-change", render);
    document.addEventListener("DOMContentLoaded", async () => { await Store.ready; render(); });
})();
