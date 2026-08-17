(function () {
    "use strict";

    function getCookie(name) {
        const prefix = `${encodeURIComponent(name)}=`;
        return document.cookie
            .split(";")
            .map((value) => value.trim())
            .find((value) => value.startsWith(prefix))
            ?.slice(prefix.length) || null;
    }

    function errorMessage(detail, fallback) {
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) {
            return detail
                .map((item) => item.msg || item.message || String(item))
                .join(" ");
        }
        if (detail && typeof detail === "object") {
            return detail.message || detail.msg || JSON.stringify(detail);
        }
        return fallback || "Something went wrong. Please try again.";
    }

    async function request(path, options = {}) {
        const headers = new Headers(options.headers || {});
        const method = (options.method || "GET").toUpperCase();
        let body = options.body;

        if (body && !(body instanceof FormData) && typeof body !== "string") {
            headers.set("Content-Type", "application/json");
            body = JSON.stringify(body);
        }

        if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
            const csrfToken = getCookie("smart_admin_csrf") || sessionStorage.getItem("smart_admin_csrf");
            if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
        }

        const response = await fetch(path, {
            ...options,
            method,
            body,
            headers,
            credentials: "same-origin",
        });

        const contentType = response.headers.get("content-type") || "";
        let payload = null;
        if (response.status !== 204) {
            payload = contentType.includes("application/json")
                ? await response.json().catch(() => null)
                : await response.text().catch(() => null);
        }

        if (!response.ok) {
            const isAdminDashboard =
                window.location.pathname === "/admin"
                || window.location.pathname.startsWith("/admin/");

            if (
                response.status === 401
                && isAdminDashboard
                && window.location.pathname !== "/admin/login"
            ) {
                sessionStorage.removeItem(
                    "smart_admin_csrf"
                );

                window.location.replace(
                    "/admin/login?reason=session-ended"
                );
            }

            const error = new Error(
                errorMessage(
                    payload?.detail || payload,
                    `Request failed (${response.status}).`
                )
            );

            error.status = response.status;
            error.payload = payload;

            throw error;
        }
        return payload;
    }

    async function download(path, fallbackName) {
        const response = await fetch(path, { credentials: "same-origin" });
        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const error = new Error(errorMessage(payload?.detail || payload, "Download failed."));
            error.status = response.status;
            throw error;
        }
        const disposition = response.headers.get("content-disposition") || "";
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
        const filename = filenameMatch?.[1] || fallbackName || "download.xlsx";
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        return {
            filename,
            exportId: response.headers.get("x-export-id"),
            sha256: response.headers.get("x-file-sha256"),
        };
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatMoney(value) {
        const number = Number(value || 0);
        return `Rs. ${number.toLocaleString("en-PK", {
            minimumFractionDigits: Number.isInteger(number) ? 0 : 2,
            maximumFractionDigits: 2,
        })}`;
    }

    function formatDate(value, withTime = true) {
        if (!value) return "—";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return new Intl.DateTimeFormat("en-PK", {
            dateStyle: "medium",
            ...(withTime ? { timeStyle: "short" } : {}),
        }).format(date);
    }

    function debounce(fn, wait = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), wait);
        };
    }

    function query(params) {
        const search = new URLSearchParams();
        Object.entries(params || {}).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                search.set(key, String(value));
            }
        });
        const value = search.toString();
        return value ? `?${value}` : "";
    }

    window.SmartAPI = {
        request,
        get: (path) => request(path),
        post: (path, body) => request(path, { method: "POST", body }),
        put: (path, body) => request(path, { method: "PUT", body }),
        patch: (path, body) => request(path, { method: "PATCH", body }),
        delete: (path, body) => request(path, { method: "DELETE", ...(body === undefined ? {} : { body }) }),
        upload: (path, formData, method = "POST") => request(path, { method, body: formData }),
        download,
        getCookie,
        escapeHtml,
        formatMoney,
        formatDate,
        debounce,
        query,
    };
})();
