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

function syncCsrfInput(form) {
    const token = getCsrfFromCookie();
    if (!token || !form) return;
    const input = form.querySelector("[name=csrfmiddlewaretoken]");
    if (input) input.value = token;
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

    const profileUrl = form.dataset.profileUrl;
    const credentialsPhase = document.getElementById("phase-credentials");
    const onboardingPhase = document.getElementById("phase-onboarding");
    const emailInput = document.getElementById("id_email");
    const passwordInput = document.getElementById("id_password1");
    const confirmInput = document.getElementById("id_password2");
    const confirmStep = document.getElementById("confirm-step");
    const continueBtn = document.getElementById("signup-continue");
    const finishBtn = document.getElementById("signup-finish");
    const passwordHint = document.getElementById("password-hint");
    const confirmHint = document.getElementById("confirm-hint");
    const successModal = document.getElementById("signup-success-modal");

    if (successModal) {
        successModal.hidden = true;
    }

    const fileInput = document.getElementById("id_profile_picture");
    const avatarPicker = document.getElementById("avatar-picker");
    const avatarPreview = document.getElementById("avatar-preview");
    const avatarPlus = document.getElementById("avatar-plus");
    const usernameInput = document.getElementById("onboard-username");
    const nameInput = document.getElementById("onboard-name");
    const birthdayInput = document.getElementById("onboard-birthday");

    const steps = Array.from(document.querySelectorAll("[data-onboard-step]"));
    const dots = Array.from(document.querySelectorAll("[data-step-dot]"));
    let currentStep = 1;
    let confirmUnlocked = false;
    let accountCreated = false;

    function showStep(step) {
        currentStep = step;
        steps.forEach((panel) => {
            const active = Number(panel.dataset.onboardStep) === step;
            panel.hidden = !active;
            panel.classList.toggle("active", active);
        });
        dots.forEach((dot) => {
            dot.classList.toggle("active", Number(dot.dataset.stepDot) === step);
        });
    }

    function resetConfirmStep() {
        confirmUnlocked = false;
        accountCreated = false;
        confirmStep.hidden = true;
        confirmInput.value = "";
        confirmInput.removeAttribute("required");
        setButtonLabel(continueBtn, "Continue");
        continueBtn.disabled = false;
        setHint(confirmHint, "", false);
    }

    function unlockConfirmStep() {
        confirmUnlocked = true;
        confirmStep.hidden = false;
        confirmInput.setAttribute("required", "required");
        confirmInput.focus();
    }

    function startOnboarding() {
        credentialsPhase.hidden = true;
        onboardingPhase.hidden = false;
        showStep(1);
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

        const data = await response.json();

        if (response.ok && (data.success || data.location)) {
            accountCreated = true;
            syncCsrfInput(form);
            return;
        }

        throw new Error(extractResponseError(data, "Could not create account. Please try again."));
    }

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
            startOnboarding();
        } catch (error) {
            showFormError(error.message);
        } finally {
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

    avatarPicker.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            avatarPreview.src = event.target.result;
            avatarPreview.hidden = false;
            avatarPlus.hidden = true;
        };
        reader.readAsDataURL(file);
    });

    document.querySelectorAll("[data-onboard-next]").forEach((button) => {
        button.addEventListener("click", () => {
            if (currentStep < 3) {
                showStep(currentStep + 1);
            }
        });
    });

    async function submitProfile() {
        if (!accountCreated) {
            showFormError("Create your account first before finishing profile setup.");
            credentialsPhase.hidden = false;
            onboardingPhase.hidden = true;
            return;
        }

        const csrf = getCsrfToken(form);
        const formData = new FormData();
        formData.append("csrfmiddlewaretoken", csrf);
        if (fileInput.files && fileInput.files[0]) {
            formData.append("profile_picture", fileInput.files[0]);
        }
        formData.append("username", usernameInput.value.trim());
        formData.append("display_name", nameInput.value.trim());
        formData.append("birthday_date", birthdayInput.value);

        finishBtn.disabled = true;
        setButtonLabel(finishBtn, "Saving profile...");
        showFormError("");

        try {
            const response = await fetch(profileUrl, {
                method: "POST",
                body: formData,
                headers: ajaxHeaders(form),
                credentials: "same-origin",
            });

            if (response.status === 403) {
                showFormError("Session expired. Please refresh the page and try again.");
                finishBtn.disabled = false;
                setButtonLabel(finishBtn, "Finish");
                return;
            }

            const data = await response.json();

            if (!response.ok || !data.success) {
                const message = extractResponseError(data, "Could not save your profile. Please try again.");
                showFormError(message);
                finishBtn.disabled = false;
                setButtonLabel(finishBtn, "Finish");
                return;
            }

            successModal.hidden = false;
            window.setTimeout(() => {
                window.location.href = data.redirect || "/dashboard/";
            }, 1200);
        } catch (error) {
            showFormError("Could not save your profile. Please try again.");
            finishBtn.disabled = false;
            setButtonLabel(finishBtn, "Finish");
        }
    }

    finishBtn.addEventListener("click", submitProfile);
}

document.addEventListener("DOMContentLoaded", () => {
    initPasswordToggles();
    initSignupFlow();
});
