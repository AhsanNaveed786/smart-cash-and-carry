(function () {
    "use strict";

    const STORAGE_KEY = "smart_language";
    const URDU = "ur";
    const ENGLISH = "en";

    const translations = {
        "Pay less. Expect more.": "کم قیمت، زیادہ توقع",
        "Shopping from": "خریداری کی برانچ",
        "Select branch": "برانچ منتخب کریں",
        "Search milk, rice, skincare...": "دودھ، چاول، سکن کیئر تلاش کریں...",
        "Search products": "مصنوعات تلاش کریں",
        "Search": "تلاش کریں",
        "Track": "ٹریک",
        "Admin": "عملہ",
        "Cart": "ٹوکری",
        "Home": "ہوم",
        "Shop": "خریداری",
        "Product": "مصنوعہ",
        "All categories": "تمام کیٹیگریز",
        "All products": "تمام مصنوعات",
        "Your cart": "آپ کی ٹوکری",
        "Track an order": "آرڈر ٹریک کریں",
        "Track order": "آرڈر ٹریک کریں",
        "Track your order": "اپنا آرڈر ٹریک کریں",
        "Order number": "آرڈر نمبر",
        "Phone number": "فون نمبر",
        "Phone number *": "فون نمبر *",
        "Stay informed": "باخبر رہیں",
        "Enter your order number and the same phone number used at checkout.": "اپنا آرڈر نمبر اور وہی فون نمبر درج کریں جو آرڈر دیتے وقت استعمال کیا تھا۔",
        "Shop now": "ابھی خریداری کریں",
        "Shop groceries": "گروسری خریدیں",
        "Everything your home needs": "آپ کے گھر کی ہر ضرورت",
        "Fresh products and prices for your selected branch.": "آپ کی منتخب برانچ کے لیے تازہ مصنوعات اور قیمتیں۔",
        "Filters": "فلٹرز",
        "Clear": "صاف کریں",
        "Clear filters": "فلٹرز صاف کریں",
        "Categories": "کیٹیگریز",
        "In-stock products": "دستیاب مصنوعات",
        "Loading products…": "مصنوعات لوڈ ہو رہی ہیں…",
        "Load more products": "مزید مصنوعات دکھائیں",
        "Name A–Z": "نام الف سے ی تک",
        "Price: low to high": "قیمت: کم سے زیادہ",
        "Price: high to low": "قیمت: زیادہ سے کم",
        "No matching products": "کوئی ملتی جلتی مصنوعہ نہیں ملی",
        "Try a different search, category or branch.": "کوئی دوسری تلاش، کیٹیگری یا برانچ آزمائیں۔",
        "We could not load the products": "مصنوعات لوڈ نہیں ہو سکیں",
        "Try again": "دوبارہ کوشش کریں",
        "View details": "تفصیل دیکھیں",
        "View all": "سب دیکھیں",
        "See all": "سب دیکھیں",
        "Add to cart": "ٹوکری میں ڈالیں",
        "Out of stock": "دستیاب نہیں",
        "Currently out of stock": "فی الحال دستیاب نہیں",
        "In stock at your selected branch": "آپ کی منتخب برانچ میں دستیاب ہے",
        "Everyday value": "روزمرہ کی بہترین قیمت",
        "SMART essentials": "ضروری اشیاء",
        "Choose an option": "ایک آپشن منتخب کریں",
        "Loading product…": "مصنوعہ لوڈ ہو رہی ہے…",
        "Checking availability…": "دستیابی چیک کی جا رہی ہے…",
        "Local pricing": "مقامی قیمت",
        "Selected branch": "منتخب برانچ",
        "Flexible fulfilment": "آسان وصولی",
        "Delivery or self pickup": "ڈیلیوری یا خود وصولی",
        "You may also like": "آپ کو یہ بھی پسند آ سکتا ہے",
        "More from this category": "اس کیٹیگری کی مزید مصنوعات",
        "Product unavailable": "مصنوعہ دستیاب نہیں",
        "Back to shop": "خریداری پر واپس جائیں",
        "A dependable everyday essential, available at your selected SMART branch.": "روزمرہ استعمال کی قابلِ اعتماد چیز، آپ کی منتخب اسمارٹ برانچ پر دستیاب ہے۔",
        "Your basket": "آپ کی ٹوکری",
        "Shopping cart": "خریداری کی ٹوکری",
        "Review quantities before checkout. Final prices are confirmed by the server.": "آرڈر مکمل کرنے سے پہلے مقدار چیک کریں۔ آخری قیمت کی تصدیق سسٹم کرے گا۔",
        "Cart items": "ٹوکری کی اشیاء",
        "Clear cart": "ٹوکری خالی کریں",
        "Order summary": "آرڈر کا خلاصہ",
        "Items subtotal": "اشیاء کی قیمت",
        "Delivery": "ڈیلیوری",
        "Calculated at checkout": "آرڈر کے وقت حساب ہوگا",
        "Estimated total": "تخمینی کل",
        "Prices and stock are validated for your selected branch before the order is placed.": "آرڈر دینے سے پہلے آپ کی منتخب برانچ کی قیمت اور اسٹاک کی تصدیق کی جاتی ہے۔",
        "Proceed to checkout": "آرڈر مکمل کریں",
        "Continue shopping": "خریداری جاری رکھیں",
        "Your basket is empty": "آپ کی ٹوکری خالی ہے",
        "Your cart is empty": "آپ کی ٹوکری خالی ہے",
        "Your cart is empty.": "آپ کی ٹوکری خالی ہے۔",
        "Browse branch-priced groceries and add your household favourites.": "اپنی برانچ کی قیمتوں کے مطابق گروسری دیکھیں اور پسندیدہ اشیاء شامل کریں۔",
        "Start shopping": "خریداری شروع کریں",
        "Standard item": "عام مصنوعہ",
        "Remove": "ہٹائیں",
        "Secure guest checkout": "محفوظ گیسٹ چیک آؤٹ",
        "Complete your order": "اپنا آرڈر مکمل کریں",
        "How would you like your order?": "آپ اپنا آرڈر کیسے حاصل کرنا چاہتے ہیں؟",
        "Choose delivery or collect it from your selected branch.": "ڈیلیوری منتخب کریں یا اپنی منتخب برانچ سے خود وصول کریں۔",
        "Home Delivery": "ہوم ڈیلیوری",
        "Self Pickup": "خود وصول کریں",
        "Minimum order Rs. 3,000": "کم از کم آرڈر 3,000 روپے",
        "No minimum order": "کم از کم آرڈر کی شرط نہیں",
        "Your details": "آپ کی معلومات",
        "We will use these details only to prepare your order.": "یہ معلومات صرف آپ کا آرڈر تیار کرنے کے لیے استعمال ہوں گی۔",
        "Full name *": "پورا نام *",
        "Email (optional)": "ای میل (اختیاری)",
        "Delivery address": "ڈیلیوری کا پتہ",
        "Give enough detail for a smooth delivery.": "آسان ڈیلیوری کے لیے مکمل تفصیل دیں۔",
        "Complete address *": "مکمل پتہ *",
        "House, street, landmark": "گھر، گلی، قریبی نشانی",
        "City *": "شہر *",
        "Order notes": "آرڈر کی ہدایات",
        "Any helpful instruction": "کوئی ضروری ہدایت",
        "Place website order": "ویب سائٹ پر آرڈر دیں",
        "Order on WhatsApp": "واٹس ایپ پر آرڈر دیں",
        "Your order": "آپ کا آرڈر",
        "Subtotal": "جزوی کل",
        "Delivery fee": "ڈیلیوری فیس",
        "Total": "کل",
        "Orders placed after store hours are queued for the next opening time.": "دکان بند ہونے کے بعد دیے گئے آرڈر اگلے کھلنے کے وقت کے لیے محفوظ ہو جاتے ہیں۔",
        "Order received": "آرڈر موصول ہو گیا",
        "Thank you for shopping with us.": "ہمارے ساتھ خریداری کرنے کا شکریہ۔",
        "Back to home": "ہوم پر واپس جائیں",
        "Add products before checking out.": "آرڈر مکمل کرنے سے پہلے مصنوعات شامل کریں۔",
        "Validating live branch prices and stock…": "برانچ کی موجودہ قیمت اور اسٹاک چیک کیا جا رہا ہے…",
        "✓ Your order qualifies for home delivery.": "✓ آپ کا آرڈر ہوم ڈیلیوری کے لیے موزوں ہے۔",
        "✓ Your order is ready for self pickup.": "✓ آپ کا آرڈر خود وصولی کے لیے تیار ہے۔",
        "Placing order…": "آرڈر دیا جا رہا ہے…",
        "Preparing WhatsApp…": "واٹس ایپ تیار کیا جا رہا ہے…",
        "Everyday essentials, beautifully simple": "روزمرہ ضروریات، نہایت آسانی سے",
        "Your neighborhood grocery store, now at your fingertips.": "آپ کی قریبی گروسری اب آپ کی دسترس میں۔",
        "Fresh prices for your selected branch, easy pickup and reliable home delivery.": "آپ کی منتخب برانچ کی تازہ قیمتیں، آسان پک اپ اور قابلِ اعتماد ہوم ڈیلیوری۔",
        "Free delivery": "مفت ڈیلیوری",
        "On orders above Rs. 3,000": "3,000 روپے سے زیادہ کے آرڈر پر",
        "Branch-perfect prices": "برانچ کے مطابق قیمتیں",
        "Matched to your selected store": "آپ کی منتخب برانچ کے مطابق",
        "Carefully prepared": "احتیاط سے تیار",
        "Reliable pickup and delivery": "قابلِ اعتماد پک اپ اور ڈیلیوری",
        "Browse quickly": "فوری تلاش",
        "Shop by category": "کیٹیگری کے مطابق خریدیں",
        "Limited-time value": "محدود مدت کی آفر",
        "Deals worth adding": "شاندار رعایتی آفرز",
        "Explore deals": "آفرز دیکھیں",
        "Loading fresh picks": "تازہ انتخاب لوڈ ہو رہا ہے",
        "Preparing your store": "آپ کا اسٹور تیار ہو رہا ہے",
        "Flexible ordering": "آسان آرڈر",
        "Delivery, pickup or WhatsApp—you choose.": "ڈیلیوری، پک اپ یا واٹس ایپ—انتخاب آپ کا۔",
        "Your cart stays ready while you choose the most convenient way to order.": "آرڈر کا آسان طریقہ منتخب کرنے تک آپ کی ٹوکری محفوظ رہتی ہے۔",
        "Build your basket": "اپنی ٹوکری بنائیں",
        "Featured at your branch": "آپ کی برانچ کی نمایاں آفر",
        "No active categories are available yet.": "ابھی کوئی فعال کیٹیگری دستیاب نہیں۔",
        "Your shelves are ready for products": "آپ کی شیلف مصنوعات کے لیے تیار ہیں",
        "Add products in the admin panel and they will appear here automatically.": "ایڈمن پینل میں مصنوعات شامل کریں، وہ یہاں خود ظاہر ہو جائیں گی۔",
        "Open admin": "ایڈمن کھولیں",
        "Freshly selected": "تازہ انتخاب",
        "Welcome to Smart Cash & Carry": "اسمارٹ کیش اینڈ کیری میں خوش آمدید",
        "Choose your nearest store": "اپنی قریبی برانچ منتخب کریں",
        "Prices and availability are matched to your selected branch. You can change it anytime.": "قیمتیں اور دستیابی آپ کی منتخب برانچ کے مطابق ہیں۔ آپ اسے کسی بھی وقت تبدیل کر سکتے ہیں۔",
        "No active branch is available yet.": "ابھی کوئی فعال برانچ دستیاب نہیں۔",
        "Everyday groceries, transparent branch prices and convenient ordering for families across our communities.": "روزمرہ گروسری، برانچ کے مطابق واضح قیمتیں اور خاندانوں کے لیے آسان آرڈر۔",
        "Order your way": "اپنی مرضی سے آرڈر کریں",
        "WhatsApp Order": "واٹس ایپ آرڈر",
        "Need help?": "مدد چاہیے؟",
        "Select your nearest branch and our team will prepare your order with care.": "اپنی قریبی برانچ منتخب کریں، ہماری ٹیم آپ کا آرڈر احتیاط سے تیار کرے گی۔",
        "Staff sign in": "عملے کا لاگ اِن",
        "Fresh prices • Reliable delivery": "تازہ قیمتیں • قابلِ اعتماد ڈیلیوری",
        "Grocery": "گروسری",
        "Fruits": "پھل",
        "Skin Care": "جلد کی دیکھ بھال",
        "Giftings": "تحائف",
        "Deals": "آفرز",
        "Pending": "زیرِ انتظار",
        "Confirmed": "تصدیق شدہ",
        "Processing": "تیاری جاری ہے",
        "Ready For Pickup": "وصولی کے لیے تیار",
        "Out For Delivery": "ڈیلیوری کے لیے روانہ",
        "Completed": "مکمل",
        "Cancelled": "منسوخ",
        "Order total": "آرڈر کی کل رقم",
        "Order method": "آرڈر کا طریقہ",
        "Items": "اشیاء",
        "Order contents": "آرڈر کی اشیاء",
        "This order was cancelled. Please contact your selected branch if you need help.": "یہ آرڈر منسوخ کر دیا گیا ہے۔ مدد کے لیے اپنی منتخب برانچ سے رابطہ کریں۔",
        "Checking…": "چیک کیا جا رہا ہے…",
        "Order not found": "آرڈر نہیں ملا",
        "Check the order number and phone number exactly as entered at checkout.": "آرڈر نمبر اور فون نمبر بالکل ویسے ہی درج کریں جیسے آرڈر کے وقت لکھے تھے۔",
        "Decrease": "کم کریں",
        "Increase": "بڑھائیں",
        "Quantity": "مقدار",
        "Sort products": "مصنوعات ترتیب دیں",
        "Featured promotions": "نمایاں آفرز",
        "Shopping benefits": "خریداری کے فوائد",
        "Quick links": "فوری روابط",
        "Mobile navigation": "موبائل نیویگیشن",
        "Search products": "مصنوعات تلاش کریں",
        "Product or barcode": "مصنوعہ یا بارکوڈ"
    };

    const lowerTranslations = Object.fromEntries(
        Object.entries(translations).map(([key, value]) => [key.toLowerCase(), value])
    );

    const originalText = new WeakMap();
    const renderedText = new WeakMap();
    const originalAttributes = new WeakMap();
    const renderedAttributes = new WeakMap();

    let language = localStorage.getItem(STORAGE_KEY) === URDU ? URDU : ENGLISH;
    let observer = null;

    function translateDynamic(value) {
        let match = value.match(/^Save (\d+)%$/i);
        if (match) return `${match[1]}% بچت`;

        match = value.match(/^(\d[\d,]*) products? found$/i);
        if (match) return `${match[1]} مصنوعات ملیں`;

        match = value.match(/^Fresh products and live prices at (.+)\.$/i);
        if (match) return `${match[1]} برانچ کی تازہ مصنوعات اور موجودہ قیمتیں۔`;

        match = value.match(/^(.+) added to your cart\.$/i);
        if (match) return `${match[1]} آپ کی ٹوکری میں شامل کر دیا گیا۔`;

        match = value.match(/^Add (Rs\.\s*[\d,.]+) more to reach the home-delivery minimum\.$/i);
        if (match) return `ہوم ڈیلیوری کی کم از کم حد پوری کرنے کے لیے مزید ${match[1]} شامل کریں۔`;

        match = value.match(/^(Rs\.\s*[\d,.]+) each$/i);
        if (match) return `فی عدد ${match[1]}`;

        match = value.match(/^Show banner (\d+)$/i);
        if (match) return `بینر ${match[1]} دکھائیں`;

        match = value.match(/^Add (.+) to cart$/i);
        if (match) return `${match[1]} ٹوکری میں ڈالیں`;

        match = value.match(/^Order (.+)$/i);
        if (match) return `آرڈر ${match[1]}`;

        match = value.match(/^Placed (.+)$/i);
        if (match) return `${match[1]} کو دیا گیا`;

        match = value.match(/^(\d+) item\(s\)$/i);
        if (match) return `${match[1]} اشیاء`;

        match = value.match(/^We will prepare your (delivery|pickup) at (.+)\.$/i);
        if (match) {
            const method = match[1].toLowerCase() === "delivery" ? "ڈیلیوری" : "پک اپ";
            return `ہم آپ کی ${method} ${match[2]} برانچ پر تیار کریں گے۔`;
        }

        return value;
    }

    function translateValue(value) {
        if (typeof value !== "string" || !value.trim()) return value;
        const leading = value.match(/^\s*/)?.[0] || "";
        const trailing = value.match(/\s*$/)?.[0] || "";
        const clean = value.trim();
        const translated = translations[clean]
            || lowerTranslations[clean.toLowerCase()]
            || translateDynamic(clean);
        return `${leading}${translated}${trailing}`;
    }

    function shouldSkip(element) {
        if (!element) return true;
        return Boolean(element.closest("script, style, noscript, svg, [data-no-translate]"));
    }

    function translateTextNode(node) {
        const parent = node.parentElement;
        if (!parent || shouldSkip(parent) || !node.nodeValue?.trim()) return;

        const lastRendered = renderedText.get(node);
        let source = originalText.get(node);

        if (source === undefined || (lastRendered !== undefined && node.nodeValue !== lastRendered)) {
            source = node.nodeValue;
            originalText.set(node, source);
        }

        const target = language === URDU ? translateValue(source) : source;
        renderedText.set(node, target);
        if (node.nodeValue !== target) node.nodeValue = target;
    }

    function translateElementAttributes(element) {
        if (!(element instanceof Element) || shouldSkip(element)) return;

        const attributes = ["placeholder", "aria-label", "title"];
        const originals = originalAttributes.get(element) || {};
        const rendered = renderedAttributes.get(element) || {};

        attributes.forEach((attribute) => {
            if (!element.hasAttribute(attribute)) return;
            const current = element.getAttribute(attribute) || "";

            if (!(attribute in originals) || (attribute in rendered && current !== rendered[attribute])) {
                originals[attribute] = current;
            }

            const target = language === URDU
                ? translateValue(originals[attribute])
                : originals[attribute];

            rendered[attribute] = target;
            if (current !== target) element.setAttribute(attribute, target);
        });

        originalAttributes.set(element, originals);
        renderedAttributes.set(element, rendered);
    }

    function applyTo(root) {
        if (!root) return;

        if (root.nodeType === Node.TEXT_NODE) {
            translateTextNode(root);
            return;
        }

        if (!(root instanceof Element) && root !== document) return;

        if (root instanceof Element) translateElementAttributes(root);

        const walker = document.createTreeWalker(
            root,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode(node) {
                    return node.nodeValue?.trim() && !shouldSkip(node.parentElement)
                        ? NodeFilter.FILTER_ACCEPT
                        : NodeFilter.FILTER_REJECT;
                },
            }
        );

        while (walker.nextNode()) translateTextNode(walker.currentNode);

        const elementRoot = root === document ? document.documentElement : root;
        elementRoot.querySelectorAll?.("[placeholder], [aria-label], [title]").forEach(
            translateElementAttributes
        );
    }

    function updateToggle() {
        const button = document.getElementById("language-toggle");
        const label = document.getElementById("language-toggle-label");
        if (!button || !label) return;

        const isUrdu = language === URDU;
        label.textContent = isUrdu ? "English" : "اردو";
        button.setAttribute("aria-pressed", String(isUrdu));
        button.setAttribute(
            "aria-label",
            isUrdu ? "Switch website to English" : "ویب سائٹ اردو میں دیکھیں"
        );
        button.title = isUrdu ? "Switch to English" : "اردو میں دیکھیں";
    }

    function setLanguage(nextLanguage) {
        language = nextLanguage === URDU ? URDU : ENGLISH;
        localStorage.setItem(STORAGE_KEY, language);
        document.documentElement.lang = language;
        document.documentElement.dir = language === URDU ? "rtl" : "ltr";
        updateToggle();
        applyTo(document.body);
        document.dispatchEvent(
            new CustomEvent("smart:language-change", { detail: { language } })
        );
    }

    function init() {
        document.documentElement.lang = language;
        document.documentElement.dir = language === URDU ? "rtl" : "ltr";
        updateToggle();
        applyTo(document.body);

        document.getElementById("language-toggle")?.addEventListener("click", () => {
            setLanguage(language === URDU ? ENGLISH : URDU);
        });

        observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === "characterData") {
                    translateTextNode(mutation.target);
                    return;
                }

                mutation.addedNodes.forEach((node) => applyTo(node));
            });
        });

        observer.observe(document.body, {
            childList: true,
            characterData: true,
            subtree: true,
        });
    }

    window.SmartI18n = {
        get language() {
            return language;
        },
        setLanguage,
        t(value) {
            return language === URDU ? translateValue(value) : value;
        },
        apply: applyTo,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
}());
