function showToast(message, type) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.setAttribute("aria-live", "polite");
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    const tag = (type || "info").split(" ")[0];
    toast.className = `toast toast-${tag}`;
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("show"));
    window.setTimeout(() => {
        toast.classList.remove("show");
        window.setTimeout(() => toast.remove(), 300);
    }, 4200);
}

function initToasts() {
    document.querySelectorAll("[data-toast-message]").forEach((el) => {
        showToast(el.dataset.toastMessage, el.dataset.toastType || "info");
        el.remove();
    });
}

document.addEventListener("DOMContentLoaded", initToasts);
