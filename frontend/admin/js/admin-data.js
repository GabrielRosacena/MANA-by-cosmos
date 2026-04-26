/**
 * MANA Admin — Mock Data & DataService Layer
 *
 * When USE_MOCK = true  → all functions return data from MOCK_* constants below.
 * When USE_MOCK = false → all functions call the real Flask/Django admin API.
 *
 * Backend endpoints are documented on each function.
 */

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK DATA
// ═══════════════════════════════════════════════════════════════════════════════

const AVATAR_COLORS = ["#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b","#f43f5e","#0ea5e9","#a78bfa"];

function profileToUser(u, idx) {
  const initials = (u.name || u.email).split(" ").map(w => w[0]).join("").slice(0,2).toUpperCase();
  return {
    id:         u.id,
    name:       u.name || u.email,
    email:      u.email,
    role:       u.role || "LGU Analyst",
    status:     u.status || "Active",
    lastLogin:  "—",
    created:    (u.created_at || "").slice(0, 10),
    loginCount: 0,
    avatar:     initials,
    color:      AVATAR_COLORS[idx % AVATAR_COLORS.length],
  };
}


const MOCK_DASHBOARD_STATS = {
  "7d": {
    totalPosts:    18492, fbPosts: 10428, xPosts: 7064,
    critical:      3328,  high: 6287,     moderate: 5542, low: 3335,
    topKeywords: [
      { word:"relief goods",      count:428, pct:100 },
      { word:"rescue",            count:392, pct:92  },
      { word:"evacuation center", count:366, pct:85  },
      { word:"flood",             count:344, pct:80  },
      { word:"medical team",      count:290, pct:68  },
      { word:"signal down",       count:198, pct:46  },
    ],
    sentiment: { negative:42, neutral:31, positive:27 },
    trendLabels: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
    trendFb:     [1180,1540,1320,1750,1620,1880,1136],
    trendX:      [780, 920, 840, 1010,960, 1090,464 ],
    priorityTrend: {
      critical: [380,520,440,610,580,660,138],
      high:     [720,890,810,970,880,1040,977],
    },
  },
  "14d": {
    totalPosts:    31864, fbPosts: 18065, xPosts: 13799,
    critical:      6054,  high: 11470,    moderate: 9559, low: 4781,
    topKeywords: [
      { word:"relief goods",      count:822, pct:100 },
      { word:"rescue",            count:761, pct:93  },
      { word:"evacuation center", count:708, pct:86  },
      { word:"flood",             count:622, pct:76  },
      { word:"medical team",      count:540, pct:66  },
      { word:"signal down",       count:388, pct:47  },
    ],
    sentiment: { negative:44, neutral:30, positive:26 },
    trendLabels: ["W1","W2","W3","W4","W5","W6","W7"],
    trendFb:     [2180,2540,2320,2750,2620,2880,2775],
    trendX:      [1580,1820,1640,2010,1860,2090,1799],
    priorityTrend: {
      critical: [680,820,740,910,880,960,1064],
      high:     [1320,1590,1410,1770,1680,1840,1860],
    },
  },
  "30d": {
    totalPosts:    63208, fbPosts: 35890, xPosts: 27318,
    critical:      10745, high: 20858,    moderate: 18962, low: 12643,
    topKeywords: [
      { word:"relief goods",      count:1544, pct:100 },
      { word:"rescue",            count:1420, pct:92  },
      { word:"evacuation center", count:1348, pct:87  },
      { word:"flood",             count:1190, pct:77  },
      { word:"medical team",      count:1040, pct:67  },
      { word:"signal down",       count:730,  pct:47  },
    ],
    sentiment: { negative:45, neutral:29, positive:26 },
    trendLabels: ["P1","P2","P3","P4","P5","P6","P7"],
    trendFb:     [4280,4940,4520,5350,5020,5680,6098],
    trendX:      [3080,3620,3240,3910,3660,4090,4718],
    priorityTrend: {
      critical: [1280,1620,1440,1810,1680,1960,1953],
      high:     [2520,2990,2710,3270,3080,3440,3848],
    },
  },
};

const MOCK_SETTINGS = {
  general: {
    systemName:  "MANA — Manila Advisory Network Alert",
    systemDesc:  "Disaster Response Recommendation and Decision Support System for Philippine LGUs.",
    timezone:    "Asia/Manila",
    dateFormat:  "MMM D, YYYY",
    defaultRange:"7d",
    maintenanceMode: false,
  },
  security: {
    sessionTimeout: 30,
    maxLoginAttempts: 5,
    require2FA: false,
    passwordMinLength: 8,
    logRetentionDays: 90,
    allowedIPs: "",
  },
  notifications: {
    emailAlerts: true,
    criticalAlerts: true,
    dailyDigest: false,
    alertEmail: "admin@mana.ph",
    slackWebhook: "",
    smsEnabled: false,
  },
  system: {
    scrapeInterval: 60,
    maxPostsPerRun: 500,
    retryOnFail: true,
    debugMode: false,
    backupEnabled: true,
    backupFreq: "daily",
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// DATA SERVICE
// Replace every USE_MOCK branch with a real adminFetch() call when backend ready.
// ═══════════════════════════════════════════════════════════════════════════════

const AdminData = {

  // ── Auth ────────────────────────────────────────────────────────────────────
  /**
   * POST /api/admin/auth/login
   * Body: { username, password }
   * Returns: { token, admin: { id, name, email, role } }
   */
  async login(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
    const role = data.user.user_metadata?.role || (data.user.email === "admin@mana.ph" ? "Admin" : null);
    if (role !== "Admin") throw new Error("Access denied. Admin role required.");
    const name = data.user.user_metadata?.name || data.user.email;
    return { admin: { id: data.user.id, name, email: data.user.email, role: "Admin" } };
  },

  // ── Users ────────────────────────────────────────────────────────────────────
  async getUsers(filters = {}) {
    const { data, error } = await supabase.from("profiles").select("*").order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    let list = (data || []).map(profileToUser);
    if (filters.search) {
      const q = filters.search.toLowerCase();
      list = list.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    }
    if (filters.role   && filters.role   !== "all") list = list.filter(u => u.role   === filters.role);
    if (filters.status && filters.status !== "all") list = list.filter(u => u.status === filters.status);
    return list;
  },

  async createUser({ name, email, role, password }) {
    const tmp = window._supabaseLib.createClient(SUPABASE_URL, SUPABASE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false, storageKey: "mana-admin-tmp" }
    });
    const { data: authData, error: authError } = await tmp.auth.signUp({
      email, password, options: { data: { role, name } }
    });
    if (authError) throw new Error(authError.message);
    if (!authData.user) throw new Error("Signup failed — no user returned.");
    if (authData.user.identities?.length === 0) throw new Error("An account with that email already exists.");

    const { error: profileError } = await supabase.from("profiles").insert({
      id: authData.user.id, name, email, role, status: "Active"
    });
    if (profileError) throw new Error(profileError.message);

    return profileToUser({ id: authData.user.id, name, email, role, status: "Active", created_at: new Date().toISOString() }, 0);
  },

  async updateUser(id, { name, email, role }) {
    const updates = {};
    if (name)  updates.name  = name;
    if (email) updates.email = email;
    if (role)  updates.role  = role;
    const { data, error } = await supabase.from("profiles").update(updates).eq("id", id).select().single();
    if (error) throw new Error(error.message);
    if (role) await supabase.rpc("update_user_metadata", { user_id: id, metadata: { role, name } }).catch(() => {});
    return profileToUser(data, 0);
  },

  async resetPassword(id, newPassword) {
    const { error } = await supabase.rpc("reset_user_password", { user_id: id, new_password: newPassword });
    if (error) throw new Error("Password reset requires the SQL function to be installed. See setup instructions.");
    return { success: true };
  },

  async setUserStatus(id, status) {
    const { error } = await supabase.from("profiles").update({ status }).eq("id", id);
    if (error) throw new Error(error.message);
    return { id, status };
  },

  async deleteUser(id) {
    const { error } = await supabase.from("profiles").delete().eq("id", id);
    if (error) throw new Error(error.message);
    return { success: true };
  },

  // ── Activity Logs ─────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/logs?user_id=&type=&limit=50
   * Returns: ActivityLog[]
   */
  async getLogs(filters = {}) {
    let query = supabase
      .from("activity_logs")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(filters.limit || 50);
    if (filters.type && filters.type !== "all") query = query.eq("type", filters.type);
    const { data, error } = await query;
    if (error) throw new Error(error.message);
    return (data || []).map(l => ({
      id:     l.id,
      userId: l.user_id,
      user:   l.user_name,
      action: l.action,
      detail: l.detail || "",
      time:   new Date(l.created_at).toLocaleString("en-PH", { dateStyle: "short", timeStyle: "short" }),
      type:   l.type,
    }));
  },

  async insertLog(action, detail, type = "admin") {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;
    const name = user.user_metadata?.name || user.email;
    await supabase.from("activity_logs").insert({
      user_id:   user.id,
      user_name: name,
      action,
      detail,
      type,
    });
  },

  // ── Dashboard Stats ───────────────────────────────────────────────────────────
  /**
   * GET /api/admin/stats?date_range=7d
   * Returns: DashboardStats
   */
  async getStats(dateRange = "7d") {
    if (USE_MOCK) return MOCK_DASHBOARD_STATS[dateRange] || MOCK_DASHBOARD_STATS["7d"];
    return adminFetch(`/stats?date_range=${dateRange}`);
  },

  // ── Settings ──────────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/settings
   * Returns: Settings object
   */
  async getSettings() {
    if (USE_MOCK) return { ...MOCK_SETTINGS };
    return adminFetch("/settings");
  },

  /**
   * PATCH /api/admin/settings/:section
   * Body: partial settings for that section
   * Returns: { success, section, data }
   */
  async saveSettings(section, data) {
    if (USE_MOCK) {
      MOCK_SETTINGS[section] = { ...MOCK_SETTINGS[section], ...data };
      return { success: true, section, data: MOCK_SETTINGS[section] };
    }
    return adminFetch(`/settings/${section}`, { method: "PATCH", body: JSON.stringify(data) });
  },
};
