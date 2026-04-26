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

const MOCK_USERS = [
  { id:"u1",  name:"Ana Reyes",       email:"ana.reyes@mana.ph",      role:"Admin",       status:"Active",    lastLogin:"2026-04-26 09:14", created:"2025-11-03", loginCount:248, avatar:"AR", color:"#3b82f6" },
  { id:"u2",  name:"Carlos Mendoza",  email:"c.mendoza@mana.ph",      role:"LGU Analyst", status:"Active",    lastLogin:"2026-04-26 07:52", created:"2025-11-10", loginCount:182, avatar:"CM", color:"#8b5cf6" },
  { id:"u3",  name:"Maria Santos",    email:"m.santos@mana.ph",       role:"Viewer",      status:"Active",    lastLogin:"2026-04-25 18:30", created:"2025-12-01", loginCount:94,  avatar:"MS", color:"#06b6d4" },
  { id:"u4",  name:"Jose dela Cruz",  email:"jose.dc@mana.ph",        role:"LGU Analyst", status:"Suspended", lastLogin:"2026-04-20 11:05", created:"2025-12-15", loginCount:67,  avatar:"JC", color:"#f59e0b" },
  { id:"u5",  name:"Liza Bautista",   email:"l.bautista@mana.ph",     role:"Viewer",      status:"Active",    lastLogin:"2026-04-24 14:20", created:"2026-01-08", loginCount:43,  avatar:"LB", color:"#10b981" },
  { id:"u6",  name:"Ramon Villanueva",email:"r.villanueva@mana.ph",   role:"LGU Analyst", status:"Active",    lastLogin:"2026-04-26 08:41", created:"2026-01-20", loginCount:129, avatar:"RV", color:"#f43f5e" },
  { id:"u7",  name:"Grace Aquino",    email:"g.aquino@mana.ph",       role:"Viewer",      status:"Inactive",  lastLogin:"2026-03-10 09:00", created:"2026-02-01", loginCount:12,  avatar:"GA", color:"#64748b" },
  { id:"u8",  name:"Miguel Torres",   email:"m.torres@mana.ph",       role:"LGU Analyst", status:"Active",    lastLogin:"2026-04-25 22:15", created:"2026-02-14", loginCount:88,  avatar:"MT", color:"#0ea5e9" },
];

const MOCK_ACTIVITY_LOGS = [
  { id:"a1",  userId:"u1", user:"Ana Reyes",       action:"Logged in",                  detail:"Via admin panel",            time:"2026-04-26 09:14", type:"auth"   },
  { id:"a2",  userId:"u2", user:"Carlos Mendoza",  action:"Post status updated",        detail:"p3 → Resolved",              time:"2026-04-26 08:55", type:"edit"   },
  { id:"a3",  userId:"u6", user:"Ramon Villanueva",action:"Logged in",                  detail:"Via main dashboard",         time:"2026-04-26 08:41", type:"auth"   },
  { id:"a4",  userId:"u1", user:"Ana Reyes",       action:"User suspended",             detail:"Jose dela Cruz (u4)",        time:"2026-04-25 17:30", type:"admin"  },
  { id:"a5",  userId:"u2", user:"Carlos Mendoza",  action:"Collection triggered",       detail:"Facebook + X, last 24h",     time:"2026-04-25 16:00", type:"system" },
  { id:"a6",  userId:"u3", user:"Maria Santos",    action:"Logged in",                  detail:"Via main dashboard",         time:"2026-04-25 18:30", type:"auth"   },
  { id:"a7",  userId:"u8", user:"Miguel Torres",   action:"Post pinned to watchlist",   detail:"Post p9 pinned",             time:"2026-04-25 22:15", type:"edit"   },
  { id:"a8",  userId:"u1", user:"Ana Reyes",       action:"New user created",           detail:"Grace Aquino — Viewer",      time:"2026-04-24 10:00", type:"admin"  },
  { id:"a9",  userId:"u2", user:"Carlos Mendoza",  action:"Logged in",                  detail:"Via admin panel",            time:"2026-04-24 09:00", type:"auth"   },
  { id:"a10", userId:"u5", user:"Liza Bautista",   action:"Logged in",                  detail:"Via main dashboard",         time:"2026-04-24 14:20", type:"edit"   },
];

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
  async login(username, password) {
    if (USE_MOCK) {
      if (username === "admin" && password === "admin2026") {
        return { admin: { id:"u1", name:"Ana Reyes", email:"ana.reyes@mana.ph", role:"Admin" } };
      }
      throw new Error("Invalid admin credentials.");
    }
    const data = await adminFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (data.token) setAdminToken(data.token);
    return data;
  },

  // ── Users ────────────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/users?search=&role=&status=
   * Returns: User[]
   */
  async getUsers(filters = {}) {
    if (USE_MOCK) {
      let list = [...MOCK_USERS];
      if (filters.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
      }
      if (filters.role   && filters.role   !== "all") list = list.filter(u => u.role   === filters.role);
      if (filters.status && filters.status !== "all") list = list.filter(u => u.status === filters.status);
      return list;
    }
    const params = new URLSearchParams(filters).toString();
    return adminFetch(`/users${params ? "?" + params : ""}`);
  },

  /**
   * POST /api/admin/users
   * Body: { name, email, role, password }
   * Returns: User
   */
  async createUser(data) {
    if (USE_MOCK) {
      const newUser = {
        id: "u" + (MOCK_USERS.length + 1),
        ...data,
        status: "Active",
        lastLogin: "—",
        created: new Date().toISOString().slice(0,10),
        loginCount: 0,
        avatar: data.name.split(" ").map(w => w[0]).join("").slice(0,2).toUpperCase(),
        color: ["#3b82f6","#8b5cf6","#10b981","#f59e0b","#06b6d4","#f43f5e"][MOCK_USERS.length % 6],
      };
      MOCK_USERS.push(newUser);
      return newUser;
    }
    return adminFetch("/users", { method: "POST", body: JSON.stringify(data) });
  },

  /**
   * PATCH /api/admin/users/:id
   * Body: { name?, email?, role?, status? }
   * Returns: User
   */
  async updateUser(id, data) {
    if (USE_MOCK) {
      const idx = MOCK_USERS.findIndex(u => u.id === id);
      if (idx === -1) throw new Error("User not found.");
      MOCK_USERS[idx] = { ...MOCK_USERS[idx], ...data };
      return MOCK_USERS[idx];
    }
    return adminFetch(`/users/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  },

  /**
   * POST /api/admin/users/:id/reset-password
   * Body: { new_password }
   * Returns: { success }
   */
  async resetPassword(id, newPassword) {
    if (USE_MOCK) return { success: true };
    return adminFetch(`/users/${id}/reset-password`, { method: "POST", body: JSON.stringify({ new_password: newPassword }) });
  },

  /**
   * PATCH /api/admin/users/:id/status
   * Body: { status: "Active" | "Suspended" | "Inactive" }
   * Returns: { id, status }
   */
  async setUserStatus(id, status) {
    if (USE_MOCK) {
      const user = MOCK_USERS.find(u => u.id === id);
      if (user) user.status = status;
      return { id, status };
    }
    return adminFetch(`/users/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  },

  /**
   * DELETE /api/admin/users/:id
   * Returns: { success }
   */
  async deleteUser(id) {
    if (USE_MOCK) {
      const idx = MOCK_USERS.findIndex(u => u.id === id);
      if (idx > -1) MOCK_USERS.splice(idx, 1);
      return { success: true };
    }
    return adminFetch(`/users/${id}`, { method: "DELETE" });
  },

  // ── Activity Logs ─────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/logs?user_id=&type=&limit=50
   * Returns: ActivityLog[]
   */
  async getLogs(filters = {}) {
    if (USE_MOCK) {
      let list = [...MOCK_ACTIVITY_LOGS];
      if (filters.userId) list = list.filter(l => l.userId === filters.userId);
      if (filters.type && filters.type !== "all") list = list.filter(l => l.type === filters.type);
      return list.slice(0, filters.limit || 50);
    }
    const params = new URLSearchParams(filters).toString();
    return adminFetch(`/logs${params ? "?" + params : ""}`);
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
