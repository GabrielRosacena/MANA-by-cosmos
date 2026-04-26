/**
 * MANA — Auth Module
 * Handles login, logout, session memory, captcha, and password-toggle UI.
 *
 * API endpoints (backend must implement):
 *   POST /api/auth/login           { username, password, remember } → { token, user }
 *   POST /api/auth/logout          → { success }
 *   GET  /api/auth/me              → { username, role, email }
 *   PATCH /api/auth/me             { username?, role? } → updated user
 *   POST /api/auth/change-password { current_password, new_password } → { success }
 *   POST /api/auth/request-email-change  { new_email } → { success }
 *   POST /api/auth/verify-email-change   { new_email, code } → { success, email }
 */

// ─── API Calls ────────────────────────────────────────────────────────────────
async function apiLogin(username, password, remember) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password, remember }),
  });
  if (data.token) setToken(data.token);
  return data;
}

async function apiLogout() {
  await apiFetch("/auth/logout", { method: "POST" }).catch(() => {});
  clearToken();
}

async function apiGetProfile()      { return apiFetch("/auth/me"); }
async function apiUpdateProfile(u)  { return apiFetch("/auth/me", { method: "PATCH", body: JSON.stringify(u) }); }
async function apiChangePassword(current, next) {
  return apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: current, new_password: next }),
  });
}
async function apiRequestEmailChange(newEmail) {
  return apiFetch("/auth/request-email-change", { method: "POST", body: JSON.stringify({ new_email: newEmail }) });
}
async function apiVerifyEmailChange(newEmail, code) {
  return apiFetch("/auth/verify-email-change", { method: "POST", body: JSON.stringify({ new_email: newEmail, code }) });
}

// ─── DataService shim (used by main.js) ──────────────────────────────────────
const AuthService = {
  async login(username, password, remember) {
    if (USE_MOCK) {
      if (!username || !password) throw new Error("Username and password required.");
      if (username === "admin" && password === "admin2026") {
        return { user: { username, role: "Admin", email: "ana.reyes@mana.ph" } };
      }
      return { user: { username, role: "LGU Analyst", email: `${username}@mana.ph` } };
    }
    return apiLogin(username, password, remember);
  },

  async logout() {
    if (USE_MOCK) { clearToken(); return; }
    return apiLogout();
  },

  async getProfile() {
    if (USE_MOCK) return state.profile;
    return apiGetProfile();
  },

  async updateProfile(updates) {
    if (USE_MOCK) return { ...state.profile, ...updates };
    return apiUpdateProfile(updates);
  },

  async changePassword(current, next) {
    if (USE_MOCK) return { success: true };
    return apiChangePassword(current, next);
  },

  async requestEmailChange(newEmail) {
    if (USE_MOCK) return { success: true };
    return apiRequestEmailChange(newEmail);
  },

  async verifyEmailChange(newEmail, code) {
    if (USE_MOCK) {
      if (code !== "246810") throw new Error("Wrong code");
      return { success: true, email: newEmail };
    }
    return apiVerifyEmailChange(newEmail, code);
  },
};

// ─── Login Handler ────────────────────────────────────────────────────────────
async function handleLogin(event) {
  event.preventDefault();
  const identity = document.getElementById("loginIdentity").value.trim();
  const password = document.getElementById("loginPassword").value.trim();
  const captchaInput = document.getElementById("captchaInput").value.trim().toUpperCase();
  const remember = document.getElementById("rememberSession").checked;

  if (!identity || !password) {
    showToast("Sign-in incomplete", "Enter both username/email and password to continue.");
    return;
  }
  if (captchaInput !== state.currentCaptcha) {
    showToast("CAPTCHA mismatch", "The verification code does not match. Please try again.");
    generateCaptcha();
    document.getElementById("captchaInput").value = "";
    return;
  }

  try {
    const result = await AuthService.login(identity, password, remember);
    state.profile = result.user || state.profile;

    if (state.profile.role === "Admin") {
      window.location.href = "admin/index.html";
      return;
    }

    if (remember) {
      localStorage.setItem("mana-session", JSON.stringify({ expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000 }));
    } else {
      localStorage.removeItem("mana-session");
    }

    renderProfileSettings();
    showApp();
    showToast("Authenticated", "MANA is now ready for dashboard monitoring.");
  } catch (err) {
    showToast("Sign-in failed", err.message || "Invalid credentials. Please try again.");
    generateCaptcha();
  }
}

async function doLogout() {
  await AuthService.logout().catch(() => {});
  localStorage.removeItem("mana-session");
  showAuthView();
  document.body.classList.remove("sidebar-open", "sidebar-collapsed");
  showToast("Logged out", "You have been signed out of MANA.");
}

function checkRememberedSession() {
  if (!USE_MOCK) return; // real backend handles session via token
  const stored = localStorage.getItem("mana-session");
  if (!stored) return;
  try {
    const parsed = JSON.parse(stored);
    if (!parsed.expiresAt || parsed.expiresAt <= Date.now()) {
      localStorage.removeItem("mana-session");
    }
  } catch {
    localStorage.removeItem("mana-session");
  }
}

// ─── Profile & Password UI ────────────────────────────────────────────────────
async function saveProfile() {
  const username = document.getElementById("profileUsername").value.trim() || state.profile.username;
  const role = document.getElementById("profileRole").value.trim() || state.profile.role;
  try {
    state.profile = await AuthService.updateProfile({ username, role });
    persistLocalPreferences();
    renderProfileSettings();
    showToast("Profile saved", "Profile details were updated.");
  } catch (err) {
    showToast("Save failed", err.message || "Could not save profile.");
  }
}

async function savePassword() {
  const current = document.getElementById("currentPassword").value.trim();
  const next    = document.getElementById("newPassword").value.trim();
  const confirm = document.getElementById("confirmPassword").value.trim();
  if (!current || !next || !confirm) { showToast("Incomplete", "Fill in all password fields before saving."); return; }
  if (next !== confirm) { showToast("Password mismatch", "New password and confirmation do not match."); return; }
  try {
    await AuthService.changePassword(current, next);
    showToast("Password saved", "Your password has been updated.");
    clearPasswordFields();
  } catch (err) {
    showToast("Password update failed", err.message || "Incorrect current password or server error.");
  }
}

function toggleEmailPopover() {
  const popover = document.getElementById("emailPopover");
  popover.classList.toggle("hidden");
  if (!popover.classList.contains("hidden")) {
    AuthService.requestEmailChange(document.getElementById("newEmailInput").value).catch(() => {});
    if (USE_MOCK) showToast("Verification code sent", "Use code 246810 to verify the new email in this prototype.");
  }
}

function closeEmailPopover() { document.getElementById("emailPopover").classList.add("hidden"); }

async function verifyEmailChange() {
  const newEmail = document.getElementById("newEmailInput").value.trim();
  const code     = document.getElementById("emailCodeInput").value.trim();
  if (!newEmail) { showToast("New email required", "Enter the new email address first."); return; }
  try {
    await AuthService.verifyEmailChange(newEmail, code);
    state.profile.email = newEmail;
    document.getElementById("profileEmail").value = newEmail;
    document.getElementById("emailPopover").classList.add("hidden");
    document.getElementById("newEmailInput").value = "";
    document.getElementById("emailCodeInput").value = "";
    persistLocalPreferences();
    showToast("Email verified", "The new email address was saved.");
  } catch (err) {
    showToast("Wrong code", err.message || "The verification code is not correct.");
  }
}

// ─── Captcha ──────────────────────────────────────────────────────────────────
function generateCaptcha() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 5; i++) code += chars[Math.floor(Math.random() * chars.length)];
  state.currentCaptcha = code;
  document.getElementById("captchaCode").textContent = code;
}

// ─── Misc UI ──────────────────────────────────────────────────────────────────
function showApp()      { document.getElementById("authView").classList.add("hidden"); document.getElementById("appView").classList.remove("hidden"); }
function showAuthView() { document.getElementById("appView").classList.add("hidden"); document.getElementById("authView").classList.remove("hidden"); }

function togglePasswordField(inputId) {
  const field = document.getElementById(inputId);
  if (field) field.type = field.type === "password" ? "text" : "password";
}

function clearPasswordFields() {
  ["currentPassword", "newPassword", "confirmPassword"].forEach(id => {
    const f = document.getElementById(id);
    f.value = ""; f.type = "password";
  });
}
