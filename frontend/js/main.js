/**
 * MANA — Main Entry Point
 * Bootstraps the app: loads data, wires events, owns app-level state and routing.
 *
 * Load order in index.html (scripts must appear in this order):
 *   config.js → utils.js → auth.js → posts.js → charts.js → dashboard.js → main.js
 */

// ─── App State ────────────────────────────────────────────────────────────────
const state = {
  // Data (populated from backend or mock on init)
  clusters:         [],
  posts:            [],
  keywords:         [],
  dashboardSummary: [],
  analytics:        {},

  // UI state
  currentPage:      "dashboard",
  currentCluster:   "cluster-a",
  currentTheme:     "dark",
  currentCaptcha:   "",

  // Filter state
  dashboardRange:   "7d",
  alerts:           { dateRange: "3d", source: "All" },
  clusterFilters:   { source: "All", severity: "Trending", dateRange: "7d" },
  analyticsRange:   "14d",

  // User state
  pinned:      new Set(),
  statuses:    {},
  profile:     { username: "admin_mana", role: "LGU Analyst", email: "lgu.analyst@mana.ph" },
  emailAlerts: true,
};

const pageTitles = {
  dashboard:       { eyebrow:"Dashboard",        title:"MANA command overview" },
  analytics:       { eyebrow:"Analytics",        title:"Trend and sentiment analysis" },
  alerts:          { eyebrow:"Live Alerts",      title:"Priority cluster and severity watch" },
  watchlist:       { eyebrow:"Saved Intelligence",title:"Pinned incident review queue" },
  settings:        { eyebrow:"Settings",         title:"Profile, alerts, and security" },
  "cluster-detail":{ eyebrow:"Cluster Detail",   title:"Operational cluster profile" },
};

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  hydrateLocalPreferences();
  applyTheme(state.currentTheme);
  generateCaptcha();
  bindStaticControls();
  updateClock();
  await loadAppData();
  renderClusterNav();
  renderAll();
  await checkRememberedSession();
}

async function loadAppData() {
  try {
    const [clusters, posts, watchlist, keywords] = await Promise.all([
      DashboardService.getClusters(),
      PostsService.getPosts(),
      PostsService.getWatchlist(),
      PostsService.getKeywords(),
    ]);

    state.clusters = clusters;
    state.posts    = posts;
    state.pinned   = new Set(watchlist.pinned || []);
    state.keywords = keywords;
    state.statuses = Object.fromEntries(posts.map(p => [p.id, p.status]));

    // In mock mode, restore any locally-saved status overrides
    if (USE_MOCK) {
      const saved = localStorage.getItem("mana-statuses");
      if (saved) state.statuses = { ...state.statuses, ...JSON.parse(saved) };
    }

    state.analytics        = await ChartsService.getAnalytics(state.analyticsRange);
    state.dashboardSummary = await DashboardService.getDashboardSummary(state.dashboardRange);
  } catch (err) {
    console.error("Data load failed:", err);
    showToast("Data load error", err.message || "Could not load data. Check backend connection.");
  }
}

// ─── Preferences (localStorage only — no API) ─────────────────────────────────
function hydrateLocalPreferences() {
  const theme = localStorage.getItem("mana-theme");
  if (theme === "light" || theme === "dark") state.currentTheme = theme;

  if (USE_MOCK) {
    const savedPinned = localStorage.getItem("mana-pinned");
    if (savedPinned) state.pinned = new Set(JSON.parse(savedPinned));

    const savedProfile = localStorage.getItem("mana-profile");
    if (savedProfile) state.profile = { ...state.profile, ...JSON.parse(savedProfile) };
  }

  const savedAlerts = localStorage.getItem("mana-email-alerts");
  if (savedAlerts !== null) state.emailAlerts = savedAlerts === "true";
}

function persistLocalPreferences() {
  if (USE_MOCK) {
    localStorage.setItem("mana-pinned",   JSON.stringify([...state.pinned]));
    localStorage.setItem("mana-statuses", JSON.stringify(state.statuses));
    localStorage.setItem("mana-profile",  JSON.stringify(state.profile));
  }
  localStorage.setItem("mana-email-alerts", String(state.emailAlerts));
}

// ─── Event Bindings ───────────────────────────────────────────────────────────
function bindStaticControls() {
  document.getElementById("loginForm").addEventListener("submit", handleLogin);

  document.getElementById("dashboardRange").addEventListener("change", async e => {
    state.dashboardRange  = e.target.value;
    state.dashboardSummary = await DashboardService.getDashboardSummary(state.dashboardRange).catch(() => state.dashboardSummary);
    renderDashboard();
    renderSourceDirectory();
  });

  document.getElementById("analyticsRange").addEventListener("change", async e => {
    state.analyticsRange = e.target.value;
    state.analytics       = await ChartsService.getAnalytics(state.analyticsRange).catch(() => state.analytics);
    renderAnalytics();
  });

  document.getElementById("alertsDateRange").addEventListener("change", e => { state.alerts.dateRange = e.target.value; renderAlerts(); });
  document.getElementById("alertsSource").addEventListener("change",    e => { state.alerts.source    = e.target.value; renderAlerts(); });

  document.getElementById("clusterSourceFilter").addEventListener("change",   e => { state.clusterFilters.source   = e.target.value; renderClusterDetail(); });
  document.getElementById("clusterSeverityFilter").addEventListener("change", e => { state.clusterFilters.severity = e.target.value; renderClusterDetail(); });
  document.getElementById("clusterDateFilter").addEventListener("change",     e => { state.clusterFilters.dateRange= e.target.value; renderClusterDetail(); });

  document.getElementById("themeCheckbox").addEventListener("change", e => applyTheme(e.target.checked ? "dark" : "light"));

  document.getElementById("emailAlertsToggle").addEventListener("change", async e => {
    state.emailAlerts = e.target.checked;
    await DashboardService.updateEmailAlerts(state.emailAlerts).catch(() => {});
    persistLocalPreferences();
    showToast("Email alerts updated", state.emailAlerts ? "Email alerts are now on." : "Email alerts are now off.");
  });

  document.getElementById("savePasswordBtn").addEventListener("click",  savePassword);
  document.getElementById("clearPasswordBtn").addEventListener("click", clearPasswordFields);
  document.getElementById("saveProfileBtn").addEventListener("click",   saveProfile);
  document.getElementById("changeEmailBtn").addEventListener("click",   toggleEmailPopover);
  document.getElementById("verifyEmailBtn").addEventListener("click",   verifyEmailChange);
  document.getElementById("cancelEmailBtn").addEventListener("click",   closeEmailPopover);
  document.getElementById("testAlertBtn").addEventListener("click", () =>
    showToast("Test alert sent", `A sample email alert was sent to ${state.profile.email}.`));
  document.getElementById("logoutBtn").addEventListener("click", doLogout);

  document.addEventListener("click",  handleDocumentClick);
  document.addEventListener("change", handleDocumentChange);
}

function handleDocumentClick(event) {
  const nav           = event.target.closest("[data-nav]");
  const clusterNav    = event.target.closest("[data-cluster-nav]");
  const pwToggle      = event.target.closest("[data-toggle-password]");
  const action        = event.target.closest("[data-action]");
  const pin           = event.target.closest("[data-pin]");
  const commentToggle = event.target.closest("[data-toggle-comments]");

  if (nav)        setPage(nav.dataset.nav);
  if (clusterNav) { state.currentCluster = clusterNav.dataset.clusterNav; setPage("cluster-detail"); }
  if (pwToggle)   togglePasswordField(pwToggle.dataset.togglePassword);

  if (action) {
    const a = action.dataset.action;
    if (a === "refresh-captcha") { generateCaptcha(); showToast("CAPTCHA refreshed", "A new verification code has been generated."); }
    if (a === "forgot-password") showToast("Password recovery", "Route password reset requests to the system administrator.");
    if (a === "toggle-sidebar")  toggleSidebar();
    if (a === "close-sidebar")   document.body.classList.remove("sidebar-open");
  }

  if (pin) togglePin(pin.dataset.pin);

  if (commentToggle) {
    const box = document.getElementById("comments-" + commentToggle.dataset.toggleComments);
    if (box) {
      box.classList.toggle("open");
      commentToggle.textContent = box.classList.contains("open") ? "Hide top comments" : "View top comments";
    }
  }

  if (!event.target.closest(".email-inline")) {
    document.getElementById("emailPopover").classList.add("hidden");
  }
}

function handleDocumentChange(event) {
  if (event.target.matches("[data-status-select]")) {
    const postId = event.target.dataset.statusSelect;
    const status = event.target.value;
    state.statuses[postId] = status;
    applyStatusStyle(event.target, status);
    PostsService.updatePostStatus(postId, status).catch(() => {});
    persistLocalPreferences();
    showToast("Post status updated", "The operational status has been updated.");
  }
  if (event.target.matches("#clusterSeverityFilter")) {
    applySeverityStyle(event.target, event.target.value);
  }
}

// ─── Render (orchestrates all modules) ───────────────────────────────────────
function renderAll() {
  renderProfileSettings();
  renderDashboard();
  renderSourceDirectory();
  renderAnalytics();
  renderAlerts();
  renderWatchlist();
  renderClusterDetail();
  setPage(state.currentPage);
}

// ─── Page Routing ─────────────────────────────────────────────────────────────
function setPage(page) {
  state.currentPage = page;
  document.querySelectorAll(".page").forEach(s => s.classList.toggle("active", s.dataset.page === page));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.nav === page));
  document.querySelectorAll(".cluster-btn").forEach(b =>
    b.classList.toggle("active", page === "cluster-detail" && b.dataset.clusterNav === state.currentCluster));

  const title = pageTitles[page];
  document.getElementById("topbarEyebrow").textContent = title.eyebrow;
  document.getElementById("topbarTitle").textContent   = title.title;
  if (page === "cluster-detail") renderClusterDetail();
  document.body.classList.remove("sidebar-open");
}

// ─── Theme & Sidebar ─────────────────────────────────────────────────────────
function applyTheme(theme) {
  state.currentTheme = theme;
  document.body.classList.toggle("light-theme", theme === "light");
  document.getElementById("themeCheckbox").checked = theme === "dark";
  document.getElementById("themeModeText").textContent = theme === "dark" ? "Dark mode active" : "Light mode active";
  localStorage.setItem("mana-theme", theme);
}

function toggleSidebar() {
  if (window.innerWidth <= 1240) { document.body.classList.toggle("sidebar-open"); return; }
  document.body.classList.toggle("sidebar-collapsed");
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
init();
