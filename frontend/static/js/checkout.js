(function () {
    "use strict";
    const API = window.SmartAPI;
    const Store = window.SmartStore;
    let currentQuote = null;
    let quoting = false;

    const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const PHONE_PATTERN = /^[0-9+()\- ]{7,30}$/;

    function digitsOnlyInput(event) {
        const input = event.target;
        // Keep digits and a leading "+" only; strip letters/symbols as the user types.
        const hasLeadingPlus = input.value.trim().startsWith("+");
        let cleaned = input.value.replace(/[^0-9]/g, "");
        if (hasLeadingPlus) cleaned = "+" + cleaned;
        if (cleaned !== input.value) input.value = cleaned;
        input.setCustomValidity("");
    }

    function validatePhone(input) {
        const value = input.value.trim();
        if (!value) {
            input.setCustomValidity("Phone number is required.");
        } else if (!PHONE_PATTERN.test(value) || !/\d{7,}/.test(value.replace(/[^0-9]/g, ""))) {
            input.setCustomValidity("Enter a valid phone number using digits only (e.g. 03xx xxxxxxx).");
        } else {
            input.setCustomValidity("");
        }
        return input.checkValidity();
    }

    function validateEmail(input) {
        const value = input.value.trim();
        if (!value) {
            input.setCustomValidity("");
            return true;
        }
        if (!EMAIL_PATTERN.test(value)) {
            input.setCustomValidity("Enter a valid email address (must contain @ and a domain, e.g. name@example.com).");
        } else {
            input.setCustomValidity("");
        }
        return input.checkValidity();
    }

    function fulfillment() {
        return document.querySelector('input[name="fulfillment_method"]:checked')?.value || "home_delivery";
    }

    function syncAddressRequirements() {
        const delivery = fulfillment() === "home_delivery";
        const card = document.getElementById("delivery-address-card");
        card.classList.toggle("is-optional", !delivery);
        card.querySelector('[name="delivery_address"]').required = delivery;
        card.querySelector('[name="city"]').required = delivery;
    }

    function renderItems() {
        const target = document.getElementById("checkout-items");
        if (!Store.state.cart.length) {
            target.innerHTML = `<div class="empty-state"><h3>Your cart is empty</h3><p>Add products before checking out.</p><a class="button button-primary" href="/shop">Shop now</a></div>`;
            document.querySelectorAll("#checkout-form button, .checkout-summary button").forEach((button) => { button.disabled = true; });
            return;
        }
        target.innerHTML = Store.state.cart.map((item) => `<div class="checkout-item-mini"><span>${item.quantity} × ${API.escapeHtml(item.name)}${item.variant_name ? ` (${API.escapeHtml(item.variant_name)})` : ""}</span><strong>${API.formatMoney(Number(item.unit_price || 0) * item.quantity)}</strong></div>`).join("");
    }

    async function refreshQuote() {
        if (!Store.state.cart.length || quoting) return;
        quoting = true;
        const minimum = document.getElementById("minimum-message");
        minimum.textContent = "Validating live branch prices and stock…";
        minimum.classList.remove("success");
        try {
            currentQuote = await API.post("/api/orders/quote", {
                branch_id: Store.state.branch.id,
                fulfillment_method: fulfillment(),
                items: Store.checkoutItems(),
            });
            document.getElementById("checkout-subtotal").textContent = API.formatMoney(currentQuote.subtotal);
            const deliveryFeeNum = Number(currentQuote.delivery_fee || 0);
            document.getElementById("checkout-delivery").textContent = (deliveryFeeNum === 0 && fulfillment() === "home_delivery") ? "FREE" : API.formatMoney(currentQuote.delivery_fee);
            document.getElementById("checkout-total").textContent = API.formatMoney(currentQuote.total_amount);

            const minDelivery = Number(currentQuote.minimum_order_amount || 0);
            const deliverySubtitle = document.getElementById("checkout-delivery-subtitle");
            if (deliverySubtitle) {
                deliverySubtitle.textContent = minDelivery > 0 ? `Minimum order ${API.formatMoney(minDelivery)}` : "Direct to your doorstep";
            }

            if (currentQuote.minimum_order_met) {
                minimum.textContent = fulfillment() === "home_delivery" ? "✓ Your order qualifies for home delivery." : "✓ Your order is ready for self pickup.";
                minimum.classList.add("success");
            } else {
                const remaining = minDelivery - Number(currentQuote.subtotal);
                minimum.textContent = `Add ${API.formatMoney(remaining)} more to reach the home-delivery minimum.`;
            }
            document.querySelectorAll('button[type="submit"], #whatsapp-order, #whatsapp-order-mobile').forEach((button) => { button.disabled = !currentQuote.minimum_order_met; });
            currentQuote.items.forEach((quoted) => {
                const item = Store.state.cart.find((entry) => entry.product_id === quoted.product_id && (entry.variant_id || null) === (quoted.variant_id || null));
                if (item) item.unit_price = quoted.unit_price;
            });
            localStorage.setItem("smart_cart", JSON.stringify(Store.state.cart));
            renderItems();
        } catch (error) {
            currentQuote = null;
            minimum.textContent = error.message;
            document.querySelectorAll('button[type="submit"], #whatsapp-order, #whatsapp-order-mobile').forEach((button) => { button.disabled = true; });
            Store.toast(error.message, "error");
        } finally {
            quoting = false;
        }
    }

    function orderPayload(channel) {
        const form = document.getElementById("checkout-form");
        const data = new FormData(form);
        return {
            branch_id: Store.state.branch.id,
            fulfillment_method: fulfillment(),
            items: Store.checkoutItems(),
            customer_name: String(data.get("customer_name") || "").trim(),
            phone_number: String(data.get("phone_number") || "").trim(),
            customer_email: String(data.get("customer_email") || "").trim() || null,
            order_channel: channel,
            delivery_address: String(data.get("delivery_address") || "").trim() || null,
            city: String(data.get("city") || "").trim() || null,
            notes: String(data.get("notes") || "").trim() || null,
        };
    }

    function setBusy(busy, label) {
        document.querySelectorAll('button[type="submit"], #whatsapp-order, #whatsapp-order-mobile').forEach((button) => {
            button.disabled = busy || (currentQuote && !currentQuote.minimum_order_met);
            if (busy && button.matches('button[type="submit"]')) {
                button.dataset.original = button.textContent;
                button.textContent = label;
            } else if (!busy && button.dataset.original) {
                button.textContent = button.dataset.original;
                delete button.dataset.original;
            }
        });
    }

    function validateDetails() {
        syncAddressRequirements();
        const form = document.getElementById("checkout-form");
        const phoneInput = form.querySelector('[name="phone_number"]');
        const emailInput = form.querySelector('[name="customer_email"]');

        const phoneOk = validatePhone(phoneInput);
        const emailOk = validateEmail(emailInput);

        if (!form.reportValidity() || !phoneOk || !emailOk) {
            if (!phoneOk) Store.toast("Phone number must contain only digits (7-30 characters).", "error");
            else if (!emailOk) Store.toast("Please enter a valid email address (it must contain @).", "error");
            return false;
        }
        if (!Store.state.cart.length) {
            Store.toast("Your cart is empty.", "error");
            return false;
        }
        return true;
    }

    async function placeWebsiteOrder(event) {
        event.preventDefault();
        if (!validateDetails()) return;
        setBusy(true, "Placing order…");
        try {
            const payload = orderPayload("website");
            const order = await API.post("/api/orders", payload);
            Store.clearCart();
            document.getElementById("success-order-number").textContent = order.order_number;
            document.getElementById("order-success-copy").textContent = `We will prepare your ${order.fulfillment_method === "home_delivery" ? "delivery" : "pickup"} at ${Store.state.branch.name}.`;
            const trackLink = document.querySelector("#order-success-modal a[href='/track-order']");
            trackLink.href = `/track-order?order=${encodeURIComponent(order.order_number)}&phone=${encodeURIComponent(order.phone_number)}`;
            document.getElementById("order-success-modal").classList.add("is-open");
            document.getElementById("order-success-modal").setAttribute("aria-hidden", "false");
        } catch (error) {
            Store.toast(error.message, "error");
        } finally {
            setBusy(false, "Place website order");
        }
    }

    async function placeWhatsAppOrder() {
        if (!validateDetails()) return;
        const popup = window.open("about:blank", "_blank");
        setBusy(true, "Preparing WhatsApp…");
        try {
            const result = await API.post("/api/whatsapp/order-link", orderPayload("whatsapp"));
            if (popup) popup.location.href = result.whatsapp_url;
            else location.href = result.whatsapp_url;
        } catch (error) {
            popup?.close();
            Store.toast(error.message, "error");
        } finally {
            setBusy(false, "Place website order");
        }
    }

    async function init() {
        await Store.ready;
        renderItems();
        syncAddressRequirements();
        await refreshQuote();
    }

    document.addEventListener("change", (event) => {
        if (event.target.name === "fulfillment_method") {
            syncAddressRequirements();
            refreshQuote();
        }
    });
    document.getElementById("checkout-form")?.addEventListener("submit", placeWebsiteOrder);
    document.addEventListener("click", (event) => {
        if (event.target.closest("#whatsapp-order, #whatsapp-order-mobile")) placeWhatsAppOrder();
    });
    document.addEventListener("smart:branch-change", refreshQuote);
    document.addEventListener("DOMContentLoaded", () => {
        init();
        const form = document.getElementById("checkout-form");
        const phoneInput = form?.querySelector('[name="phone_number"]');
        const emailInput = form?.querySelector('[name="customer_email"]');
        phoneInput?.addEventListener("input", digitsOnlyInput);
        phoneInput?.addEventListener("blur", () => validatePhone(phoneInput));
        emailInput?.addEventListener("input", () => emailInput.setCustomValidity(""));
        emailInput?.addEventListener("blur", () => validateEmail(emailInput));
    });
})();