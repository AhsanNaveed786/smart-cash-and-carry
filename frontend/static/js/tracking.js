(function () {
    "use strict";
    const API = window.SmartAPI;

    function label(value) {
        return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    function render(order) {
        const target = document.getElementById("tracking-result");
        const steps = order.fulfillment_method === "self_pickup"
            ? ["pending", "confirmed", "processing", "ready_for_pickup", "completed"]
            : ["pending", "confirmed", "processing", "out_for_delivery", "completed"];
        const currentIndex = steps.indexOf(order.status);
        const cancelled = order.status === "cancelled";
        target.innerHTML = `
            <div class="tracking-head"><div><span class="eyebrow">Order ${API.escapeHtml(order.order_number)}</span><h2>${API.escapeHtml(order.customer_name)}'s order</h2><small>Placed ${API.formatDate(order.created_at)}</small></div><span class="status-badge ${cancelled ? "cancelled" : ""}">${API.escapeHtml(label(order.status))}</span></div>
            ${cancelled ? `<div class="minimum-message">This order was cancelled. Please contact your selected branch if you need help.</div>` : `<div class="status-progress">${steps.map((step, index) => `<div class="status-step ${index <= currentIndex ? "done" : ""}"><span class="status-dot">${index <= currentIndex ? "✓" : index + 1}</span><span>${API.escapeHtml(label(step))}</span></div>`).join("")}</div>`}
            <div class="tracking-detail-grid">
                <div><small>Order total</small><strong>${API.formatMoney(order.total_amount)}</strong></div>
                <div><small>Order method</small><strong>${API.escapeHtml(label(order.fulfillment_method))}</strong></div>
                <div><small>Items</small><strong>${order.items.reduce((sum, item) => sum + item.quantity, 0)} item(s)</strong></div>
            </div>
            <div class="tracking-items"><h3>Order contents</h3>${order.items.map((item) => `<div class="checkout-item-mini"><span>${item.quantity} × ${API.escapeHtml(item.product_name)}${item.variant_name ? ` (${API.escapeHtml(item.variant_name)})` : ""}</span><strong>${API.formatMoney(item.line_total)}</strong></div>`).join("")}</div>`;
        target.hidden = false;
        target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    async function track(event) {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button");
        const orderNumber = document.getElementById("tracking-order-number").value.trim().toUpperCase();
        const phone = document.getElementById("tracking-phone").value.trim();
        button.disabled = true;
        button.textContent = "Checking…";
        try {
            const order = await API.get(`/api/orders/lookup/${encodeURIComponent(orderNumber)}?phone_number=${encodeURIComponent(phone)}`);
            render(order);
        } catch (error) {
            const target = document.getElementById("tracking-result");
            target.hidden = false;
            target.innerHTML = `<div class="empty-state"><div class="empty-state-icon"><svg class="icon"><use href="#i-search"></use></svg></div><h3>Order not found</h3><p>${API.escapeHtml(error.message)} Check the order number and phone number exactly as entered at checkout.</p></div>`;
        } finally {
            button.disabled = false;
            button.textContent = "Track order";
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const params = new URLSearchParams(location.search);
        const order = params.get("order");
        const phone = params.get("phone");
        if (order) document.getElementById("tracking-order-number").value = order;
        if (phone) document.getElementById("tracking-phone").value = phone;
        if (order && phone) document.getElementById("tracking-form").requestSubmit();
    });
    document.getElementById("tracking-form")?.addEventListener("submit", track);
})();
