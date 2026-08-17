(function () {
    "use strict";
    const API = window.SmartAPI;
    const Store = window.SmartStore;
    let slideTimer;

    function safeLink(value, fallback = "/shop") {
        if (!value) return fallback;
        return /^(\/|https?:\/\/)/i.test(value) ? value : fallback;
    }

    function renderHero() {
        const slider = document.getElementById("hero-slider");
        const dots = document.getElementById("hero-dots");
        const banners = Store.state.content?.banners || [];
        if (!slider || !banners.length) return;
        slider.innerHTML = banners.map((banner, index) => `
            <article class="hero-slide ${index === 0 ? "is-active" : ""}" data-slide="${index}" data-background="${API.escapeHtml(Store.imageUrl(banner.image_url) || "")}">
                <div class="hero-copy">
                    <span class="eyebrow light">Featured at your branch</span>
                    <h1>${API.escapeHtml(banner.title)}</h1>
                    ${banner.subtitle ? `<p>${API.escapeHtml(banner.subtitle)}</p>` : ""}
                    <a class="button button-accent" href="${API.escapeHtml(safeLink(banner.button_url))}">${API.escapeHtml(banner.button_text || "Shop now")} <svg class="icon"><use href="#i-arrow"></use></svg></a>
                </div>
                ${banner.image_url ? "" : `<div class="hero-visual" aria-hidden="true"><span>🥬</span><span>🍎</span><span>🥛</span><span>🧴</span></div>`}
            </article>`).join("");
        slider.querySelectorAll("[data-background]").forEach((slide) => {
            if (slide.dataset.background) slide.style.backgroundImage = `url("${slide.dataset.background.replaceAll('"', '\\"')}")`;
        });
        dots.innerHTML = banners.map((_, index) => `<button type="button" data-hero-dot="${index}" class="${index === 0 ? "active" : ""}" aria-label="Show banner ${index + 1}"></button>`).join("");
        startSlider();
    }

    function showSlide(index) {
        const slides = [...document.querySelectorAll("[data-slide]")];
        if (!slides.length) return;
        const selected = ((Number(index) % slides.length) + slides.length) % slides.length;
        slides.forEach((slide, position) => slide.classList.toggle("is-active", position === selected));
        document.querySelectorAll("[data-hero-dot]").forEach((dot, position) => dot.classList.toggle("active", position === selected));
    }

    function startSlider() {
        clearInterval(slideTimer);
        const slides = [...document.querySelectorAll("[data-slide]")];
        if (slides.length < 2) return;
        slideTimer = setInterval(() => {
            const active = slides.findIndex((slide) => slide.classList.contains("is-active"));
            showSlide(active + 1);
        }, 5500);
    }

    function renderCategories() {
        const target = document.getElementById("category-scroll");
        if (!target) return;
        target.innerHTML = Store.state.categories.map((category) => `
            <a class="category-chip" href="/shop?category=${category.id}">
                <span class="category-icon">${category.image_url ? Store.mediaMarkup(category.image_url, category.name) : API.escapeHtml(category.name.charAt(0).toUpperCase())}</span>
                <strong>${API.escapeHtml(category.name)}</strong>
            </a>`).join("") || `<p>No active categories are available yet.</p>`;
    }

    async function renderDeals() {
        const section = document.getElementById("deals-section");
        const target = document.getElementById("deals-carousel");
        try {
            const result = await API.get(`/api/storefront/discount-products/${Store.state.branch.id}?skip=0&limit=20`);
            if (!result.items?.length) return;
            target.innerHTML = result.items.map((product) => Store.productCard(product)).join("");
            section.hidden = false;
            Store.hydrateCards(target);
        } catch (_) {
            section.hidden = true;
        }
    }

    async function renderCategoryProducts() {
        const target = document.getElementById("category-product-sections");
        const categories = Store.state.categories.slice(0, 12);
        const results = await Promise.all(categories.map(async (category) => {
            try {
                const products = await API.get(`/api/products${API.query({ category_id: category.id, active_only: true, skip: 0, limit: 16 })}`);
                return { category, products: products.items || [] };
            } catch (_) {
                return { category, products: [] };
            }
        }));
        const visible = results.filter((entry) => entry.products.length);
        if (!visible.length) {
            target.innerHTML = `<section class="section container"><div class="empty-state"><div class="empty-state-icon"><svg class="icon"><use href="#i-grid"></use></svg></div><h3>Your shelves are ready for products</h3><p>Add products in the admin panel and they will appear here automatically.</p><a class="button button-primary" href="/admin/login">Open admin</a></div></section>`;
            return;
        }
        target.innerHTML = visible.map(({ category, products }) => `
            <section class="section">
                <div class="container">
                    ${category.display_mode === "custom_image_banner" && category.banner_image_url ? `<a class="category-banner" href="/shop?category=${category.id}">${Store.mediaMarkup(category.banner_image_url, category.name)}</a>` : `
                    <div class="category-heading-bar"><div><span class="eyebrow">Freshly selected</span><h2>${API.escapeHtml(category.name)}</h2></div><a href="/shop?category=${category.id}">View all <svg class="icon"><use href="#i-arrow"></use></svg></a></div>`}
                    <div class="product-carousel no-scrollbar">${products.map((product) => Store.productCard(product, { categoryName: category.name })).join("")}</div>
                </div>
            </section>`).join("");
        Store.hydrateCards(target);
    }

    async function loadHome() {
        await Store.ready;
        renderHero();
        renderCategories();
        await Promise.all([renderDeals(), renderCategoryProducts()]);
    }

    document.addEventListener("click", (event) => {
        const dot = event.target.closest("[data-hero-dot]");
        if (!dot) return;
        showSlide(Number(dot.dataset.heroDot));
        startSlider();
    });
    document.addEventListener("smart:branch-change", loadHome);
    document.addEventListener("DOMContentLoaded", loadHome);
})();
