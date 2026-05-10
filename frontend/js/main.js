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
  dashboardComments: [],
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
  pinned:        new Set(),
  statuses:      {},
  verifications: {},
  profile:       { username: "admin_mana", role: "LGU Analyst", email: "lgu.analyst@mana.ph" },
  emailAlerts:   true,
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
    const [clusters, posts, watchlist, keywords, dashboardComments] = await Promise.all([
      DashboardService.getClusters(),
      PostsService.getPosts(),
      PostsService.getWatchlist(),
      PostsService.getKeywords(),
      DashboardService.getDashboardComments(state.dashboardRange).catch(() => []),
    ]);

    state.clusters = clusters;
    state.posts    = posts.map(post => ({
      ...post,
      reactions: toCount(post.reactions),
      shares: toCount(post.shares),
      likes: toCount(post.likes),
      reposts: toCount(post.reposts),
      comments: toCount(post.comments),
      views: toCount(post.views),
    }));
    state.pinned   = new Set(watchlist.pinned || []);
    state.keywords = keywords;
    state.dashboardComments = dashboardComments;
    state.statuses = Object.fromEntries(state.posts.map(p => [p.id, p.status]));

    // In mock mode, restore any locally-saved status overrides
    if (USE_MOCK) {
      const saved = localStorage.getItem("mana-statuses");
      if (saved) state.statuses = { ...state.statuses, ...JSON.parse(saved) };
    }

    state.analytics        = await ChartsService.getAnalytics(state.analyticsRange);
    state.dashboardSummary = buildDashboardSummary(state.posts, state.dashboardRange, state.clusters);
    initVerifications(state.posts);
  } catch (err) {
    console.error("Data load failed:", err);
    showToast("Data load error", err.message || "Could not load data. Check backend connection.");
  }
}

// ─── Verification helpers ─────────────────────────────────────────────────────
function initVerifications(posts) {
  state.verifications = {};
  for (const post of posts) {
    const ref = MOCK_CROSS_REFS[post.id];
    state.verifications[post.id] = ref
      ? { status:"auto-verified",   crossRefs:ref.crossRefs, matchCount:ref.matchCount, note:"", markedBy:null }
      : { status:"auto-unverified", crossRefs:[],             matchCount:0,              note:"", markedBy:null };
  }
  const saved = localStorage.getItem("mana-verifications");
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      for (const [id, v] of Object.entries(parsed)) {
        if (state.verifications[id]) state.verifications[id] = { ...state.verifications[id], ...v };
      }
    } catch (_) {}
  }
}

function persistVerifications() {
  localStorage.setItem("mana-verifications", JSON.stringify(state.verifications));
}

function refreshVerifyBox(postId) {
  const post = state.posts.find(p => p.id === postId);
  if (!post) return;

  // Capture which wrappers had an open popup before replacing
  const openWrappers = new Set();
  document.querySelectorAll(`[data-verify-for="${postId}"]`).forEach(existing => {
    if (!existing.classList.contains("hidden")) openWrappers.add(existing.closest(".verify-wrapper"));
    existing.outerHTML = renderVerifyBox(post);
  });

  // Re-open popups in the wrappers that were open
  openWrappers.forEach(wrapper => {
    if (!wrapper) return;
    const fresh = wrapper.querySelector(`[data-verify-for="${postId}"]`);
    if (fresh) fresh.classList.remove("hidden");
  });

  const v = state.verifications[postId];
  const isVerified = v.status === "auto-verified" || v.status === "manually-verified";
  document.querySelectorAll(`[data-verify-toggle="${postId}"]`).forEach(btn => {
    btn.textContent = isVerified ? "✓ Verified" : "⊕ Unverified";
    btn.className   = `verify-btn verify-${v.status}`;
  });
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
    state.dashboardSummary = buildDashboardSummary(state.posts, state.dashboardRange, state.clusters);
    state.dashboardComments = await DashboardService.getDashboardComments(state.dashboardRange).catch(() => state.dashboardComments);
    renderDashboard();
    renderSourceDirectory();
  });

  document.getElementById("priorityFilter").addEventListener("change", e => {
    renderPriorityPosts(e.target.value);
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

  const openPost = event.target.closest("[data-open-post]");
  if (openPost) {
    showToast("Post link unavailable", "Direct post URLs are not stored in the current dataset.");
  }

  if (commentToggle) {
    const postCard = commentToggle.closest("[data-post-card]");
    const box = postCard?.querySelector(`[data-comments-box="${commentToggle.dataset.toggleComments}"]`);
    if (box) {
      box.classList.toggle("open");
      const isOpen = box.classList.contains("open");
      commentToggle.setAttribute("aria-expanded", String(isOpen));
      const label = commentToggle.querySelector(".comment-toggle-label");
      if (label) label.textContent = isOpen ? "Hide Comments" : "View Comments";
    }
  }

  const verifyToggle = event.target.closest("[data-verify-toggle]");
  if (!event.target.closest(".verify-wrapper")) {
    document.querySelectorAll(".verify-popup:not(.hidden)").forEach(p => p.classList.add("hidden"));
  }
  if (verifyToggle) {
    const popup = verifyToggle.closest(".verify-wrapper")?.querySelector(".verify-popup");
    document.querySelectorAll(".verify-popup:not(.hidden)").forEach(p => {
      if (p !== popup) p.classList.add("hidden");
    });
    if (popup) popup.classList.toggle("hidden");
  }

  const recToggle = event.target.closest("[data-rec-toggle]");
  if (!event.target.closest(".rec-wrapper")) {
    document.querySelectorAll(".rec-popup:not(.hidden)").forEach(p => p.classList.add("hidden"));
  }
  if (recToggle) {
    const popup = recToggle.closest(".rec-wrapper")?.querySelector(".rec-popup");
    document.querySelectorAll(".rec-popup:not(.hidden)").forEach(p => {
      if (p !== popup) p.classList.add("hidden");
    });
    if (popup) popup.classList.toggle("hidden");
  }

  const markUnverified = event.target.closest("[data-mark-unverified]");
  if (markUnverified) {
    const pid = markUnverified.dataset.markUnverified;
    if (state.verifications[pid]) {
      state.verifications[pid].status   = "marked-unverified";
      state.verifications[pid].markedBy = state.profile.username || state.profile.name || "Unknown";
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  const manualVerify = event.target.closest("[data-manually-verify]");
  if (manualVerify) {
    const pid = manualVerify.dataset.manuallyVerify;
    if (state.verifications[pid]) {
      state.verifications[pid].status   = "manually-verified";
      state.verifications[pid].markedBy = state.profile.username || state.profile.name || "Unknown";
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  const reverify = event.target.closest("[data-reverify]");
  if (reverify) {
    const pid = reverify.dataset.reverify;
    if (state.verifications[pid]) {
      state.verifications[pid].status   = "auto-verified";
      state.verifications[pid].markedBy = null;
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  const unverifyManual = event.target.closest("[data-unverify-manual]");
  if (unverifyManual) {
    const pid = unverifyManual.dataset.unverifyManual;
    if (state.verifications[pid]) {
      state.verifications[pid].status   = "auto-unverified";
      state.verifications[pid].markedBy = null;
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  const addNote = event.target.closest("[data-add-note]");
  if (addNote) {
    const editor = addNote.closest(".verify-wrapper")?.querySelector(`[data-note-editor="${addNote.dataset.addNote}"]`);
    if (editor) editor.classList.remove("hidden");
  }

  const cancelNote = event.target.closest("[data-cancel-note]");
  if (cancelNote) {
    const editor = cancelNote.closest(".verify-wrapper")?.querySelector(`[data-note-editor="${cancelNote.dataset.cancelNote}"]`);
    if (editor) editor.classList.add("hidden");
  }

  const saveNote = event.target.closest("[data-save-note]");
  if (saveNote) {
    const pid   = saveNote.dataset.saveNote;
    const input = saveNote.closest(".verify-wrapper")?.querySelector(`[data-note-input="${pid}"]`);
    if (input && state.verifications[pid]) {
      state.verifications[pid].note = input.value.trim();
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  const editNote = event.target.closest("[data-edit-note]");
  if (editNote && editNote.dataset.editNote) {
    const pid    = editNote.dataset.editNote;
    const wrapper = editNote.closest(".verify-wrapper");
    const editor = wrapper?.querySelector(`[data-note-editor="${pid}"]`);
    if (editor) {
      editor.classList.remove("hidden");
      const ta = wrapper?.querySelector(`[data-note-input="${pid}"]`);
      if (ta) ta.value = state.verifications[pid]?.note || "";
    }
  }

  const deleteNote = event.target.closest("[data-delete-note]");
  if (deleteNote) {
    const pid = deleteNote.dataset.deleteNote;
    if (state.verifications[pid]) {
      state.verifications[pid].note = "";
      persistVerifications();
      refreshVerifyBox(pid);
    }
  }

  if (!event.target.closest(".email-inline")) {
    document.getElementById("emailPopover").classList.add("hidden");
  }
}

async function handleDocumentChange(event) {
  if (event.target.matches("[data-status-select]")) {
    const postId = event.target.dataset.statusSelect;
    const status = event.target.value;
    state.statuses[postId] = status;
    applyStatusStyle(event.target, status);
    persistLocalPreferences();
    try {
      const result = await PostsService.updatePostStatus(postId, status);
      showToast(
        result?.localOnly ? "Status updated locally" : "Post status updated",
        result?.localOnly
          ? "The operational status was saved in this browser for now."
          : "The operational status has been updated."
      );
    } catch (err) {
      showToast("Status saved locally", "The card updated in the dashboard, but the backend request failed.");
      console.warn("Status update failed:", err);
    }
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
