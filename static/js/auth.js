const COMMON_PASSWORDS = new Set([
    "password",
    "password123",
    "12345678",
    "123456789",
    "qwerty123",
    "admin123",
    "letmein",
    "welcome",
    "iloveyou",
    "sunshine",
]);

function isPasswordValid(password, email) {
    if (!password || password.length < 8) {
        return { valid: false, message: "Use at least 8 characters." };
    }
    if (/^\d+$/.test(password)) {
        return { valid: false, message: "Password cannot be all numbers." };
    }
    if (COMMON_PASSWORDS.has(password.toLowerCase())) {
        return { valid: false, message: "Choose a less common password." };
    }
    const emailLocal = (email || "").split("@")[0].toLowerCase();
    if (emailLocal && password.toLowerCase() === emailLocal) {
        return { valid: false, message: "Password is too similar to your email." };
    }
    if (emailLocal.length >= 3 && password.toLowerCase().includes(emailLocal)) {
        return { valid: false, message: "Password is too similar to your email." };
    }
    return { valid: true, message: "" };
}

function setHint(element, message, isError) {
    if (!element) return;
    if (!message) {
        element.hidden = true;
        element.textContent = "";
        element.classList.remove("is-error");
        return;
    }
    element.hidden = false;
    element.textContent = message;
    element.classList.toggle("is-error", isError);
}

function showFormError(message) {
    const box = document.getElementById("signup-form-error");
    if (!box) return;
    if (!message) {
        box.hidden = true;
        box.textContent = "";
        return;
    }
    box.hidden = false;
    box.textContent = message;
}

function getCsrfFromCookie() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
}

function getCsrfToken(form) {
    const fromCookie = getCsrfFromCookie();
    if (fromCookie) return fromCookie;
    if (form) {
        const input = form.querySelector("[name=csrfmiddlewaretoken]");
        if (input) return input.value;
    }
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
}

function ajaxHeaders(form) {
    const csrf = getCsrfToken(form);
    return {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf,
    };
}

function extractResponseError(data, fallback) {
    if (data.errors) {
        const flat = Object.values(data.errors).flat().filter(Boolean);
        if (flat.length) return flat[0];
    }
    if (data.form) {
        if (data.form.errors && data.form.errors.length) return data.form.errors[0];
        for (const field of Object.values(data.form.fields || {})) {
            if (field.errors && field.errors.length) return field.errors[0];
        }
    }
    return fallback;
}

function initPasswordToggles() {
    document.querySelectorAll(".password-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);
            const icon = button.querySelector("i");
            if (!input) return;
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            icon.classList.toggle("fa-eye", !show);
            icon.classList.toggle("fa-eye-slash", show);
            button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        });
    });
}

function setButtonLabel(button, text) {
    if (!button) return;
    const label = button.querySelector(".btn-label");
    if (label) {
        label.textContent = text;
    } else {
        button.textContent = text;
    }
}

function initSignupFlow() {
    const form = document.getElementById("signup-form");
    if (!form) return;

    const emailInput = document.getElementById("id_email");
    const passwordInput = document.getElementById("id_password1");
    const confirmInput = document.getElementById("id_password2");
    const confirmStep = document.getElementById("confirm-step");
    const continueBtn = document.getElementById("signup-continue");
    const passwordHint = document.getElementById("password-hint");
    const confirmHint = document.getElementById("confirm-hint");

    let confirmUnlocked = false;

    function resetConfirmStep() {
        confirmUnlocked = false;
        if (confirmStep) confirmStep.hidden = true;
        if (confirmInput) {
            confirmInput.value = "";
            confirmInput.removeAttribute("required");
        }
        setButtonLabel(continueBtn, "Continue");
        if (continueBtn) continueBtn.disabled = false;
        setHint(confirmHint, "", false);
    }

    function unlockConfirmStep() {
        confirmUnlocked = true;
        if (confirmStep) confirmStep.hidden = false;
        if (confirmInput) {
            confirmInput.setAttribute("required", "required");
            confirmInput.focus();
        }
    }

    async function createAccount() {
        const csrf = getCsrfToken(form);
        const formData = new FormData();
        formData.append("csrfmiddlewaretoken", csrf);
        formData.append("email", emailInput.value.trim());
        formData.append("password1", passwordInput.value);
        formData.append("password2", confirmInput.value);

        const response = await fetch(form.action, {
            method: "POST",
            body: formData,
            headers: ajaxHeaders(form),
            credentials: "same-origin",
        });

        let data = {};
        const raw = await response.text();
        try {
            data = raw ? JSON.parse(raw) : {};
        } catch (error) {
            if (response.status === 403) {
                throw new Error("Security check failed. Refresh the page and try again.");
            }
            if (response.status >= 500) {
                throw new Error("Server error while creating your account. Please try again shortly.");
            }
            throw new Error("Could not create account. Please try again.");
        }

        if (response.ok && (data.success || data.location || data.status === 200)) {
            window.location.href = data.location || "/accounts/confirm-email/";
            return;
        }

        throw new Error(extractResponseError(data, "Could not create account. Please try again."));
    }

    if (!continueBtn) return;

    continueBtn.addEventListener("click", async () => {
        setHint(passwordHint, "", false);
        passwordInput.classList.remove("auth-input-error");
        setHint(confirmHint, "", false);
        confirmInput.classList.remove("auth-input-error");
        showFormError("");

        if (!confirmUnlocked) {
            if (!emailInput.value.trim()) {
                emailInput.focus();
                setHint(passwordHint, "Enter your email first.", true);
                return;
            }

            const result = isPasswordValid(passwordInput.value, emailInput.value.trim());
            if (!result.valid) {
                setHint(passwordHint, result.message, true);
                passwordInput.classList.add("auth-input-error");
                passwordInput.focus();
                return;
            }

            unlockConfirmStep();
            return;
        }

        if (passwordInput.value !== confirmInput.value) {
            setHint(confirmHint, "Passwords do not match.", true);
            confirmInput.classList.add("auth-input-error");
            confirmInput.focus();
            return;
        }

        continueBtn.disabled = true;
        setButtonLabel(continueBtn, "Creating account...");

        try {
            await createAccount();
        } catch (error) {
            showFormError(error.message);
            continueBtn.disabled = false;
            setButtonLabel(continueBtn, "Continue");
        }
    });

    passwordInput.addEventListener("input", () => {
        if (confirmUnlocked) {
            resetConfirmStep();
        } else {
            setHint(passwordHint, "", false);
            passwordInput.classList.remove("auth-input-error");
        }
    });

    emailInput.addEventListener("input", () => {
        if (confirmUnlocked) {
            resetConfirmStep();
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initPasswordToggles();
    initSignupFlow();
});
