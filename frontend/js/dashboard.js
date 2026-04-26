/**
 * MANA — Dashboard Module
 * Owns: KPI cards, keyword grid, trending posts, source directory, cluster nav.
 * Also owns dashboard mock data and the DataService shim for dashboard endpoints.
 *
 * API endpoints (backend must implement):
 *   GET /api/dashboard/summary   ?date_range=7d → { kpis: [{label,value,meta,bar}] }
 *   GET /api/dashboard/keywords               → { keywords: [{keyword,note,count}] }
 *   GET /api/clusters                         → Cluster[]
 */

// ─── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_CLUSTERS = [
  { id:"cluster-a", short:"Cluster A", name:"Food and Non-food Items (NFIs)",                                                                  description:"Tracks posts about food packs, water, hygiene kits, blankets, and other basic relief needs.",                       keywords:["relief goods","rice","water refill","hygiene kit","blanket","food pack"],                   accent:"#f59e0b" },
  { id:"cluster-b", short:"Cluster B", name:"WASH, Medical and Public Health, Nutrition, Mental Health and Psychosocial Support (Health)",     description:"Tracks posts about health, medicine, clean water, nutrition, and mental health support.",                          keywords:["fever","insulin","washing area","dehydration","doctor","medical team"],                      accent:"#3b82f6" },
  { id:"cluster-c", short:"Cluster C", name:"Camp Coordination, Management and Protection (CCCM)",                                            description:"Tracks evacuation center crowding, camp services, registration, and protection issues.",                           keywords:["evacuation center","overcapacity","privacy","registration","safe space","toilet line"],       accent:"#8b5cf6" },
  { id:"cluster-d", short:"Cluster D", name:"Logistics",                                                                                       description:"Tracks blocked routes, delivery delays, convoy movement, and supply transport issues.",                           keywords:["blocked road","convoy","truck","warehouse","delivery","reroute"],                             accent:"#f97316" },
  { id:"cluster-e", short:"Cluster E", name:"Emergency Telecommunications (ETC)",                                                             description:"Tracks signal loss, network problems, and urgent communication needs.",                                            keywords:["signal down","no network","power bank","cell site","radio","connectivity"],                  accent:"#06b6d4" },
  { id:"cluster-f", short:"Cluster F", name:"Education",                                                                                       description:"Tracks school closures, displaced learners, and temporary learning needs.",                                        keywords:["school closure","class suspension","learning materials","temporary classroom","DepEd","students"], accent:"#10b981" },
  { id:"cluster-g", short:"Cluster G", name:"Search, Rescue and Retrieval (SRR)",                                                             description:"Tracks stranded people, rescue calls, rooftop signals, and retrieval updates.",                                    keywords:["stranded","roof","rescue boat","trapped family","SOS","retrieval"],                          accent:"#ef4444" },
  { id:"cluster-h", short:"Cluster H", name:"Management of Dead and Mission (MDM)",                                                           description:"Tracks missing persons, identification concerns, and related coordination updates.",                                keywords:["missing","identified","hospital list","family tracing","coordination desk","verification"],   accent:"#64748b" },
];

const MOCK_DASHBOARD_SUMMARY = {
  "24h": [
    { label:"Critical Posts %",      value:"21%",    meta:"Today",         bar:21  },
    { label:"High Priority %",        value:"37%",    meta:"Today",         bar:37  },
    { label:"Total Posts Analyzed",   value:"2,148",  meta:"Today",         bar:32  },
    { label:"Total Facebook Posts",   value:"1,245",  meta:"Today",         bar:25  },
    { label:"Total X/Twitter Posts",  value:"903",    meta:"Today",         bar:18  },
    { label:"Active Clusters %",      value:"100%",   meta:"All active",    bar:100 },
  ],
  "7d": [
    { label:"Critical Posts %",      value:"18%",    meta:"Last 7 days",   bar:18  },
    { label:"High Priority %",        value:"34%",    meta:"Last 7 days",   bar:34  },
    { label:"Total Posts Analyzed",   value:"18,492", meta:"Last 7 days",   bar:76  },
    { label:"Total Facebook Posts",   value:"10,428", meta:"Last 7 days",   bar:56  },
    { label:"Total X/Twitter Posts",  value:"8,064",  meta:"Last 7 days",   bar:44  },
    { label:"Active Clusters %",      value:"100%",   meta:"All active",    bar:100 },
  ],
  "14d": [
    { label:"Critical Posts %",      value:"19%",    meta:"Last 14 days",  bar:19  },
    { label:"High Priority %",        value:"36%",    meta:"Last 14 days",  bar:36  },
    { label:"Total Posts Analyzed",   value:"31,864", meta:"Last 14 days",  bar:86  },
    { label:"Total Facebook Posts",   value:"18,065", meta:"Last 14 days",  bar:62  },
    { label:"Total X/Twitter Posts",  value:"13,799", meta:"Last 14 days",  bar:52  },
    { label:"Active Clusters %",      value:"100%",   meta:"All active",    bar:100 },
  ],
  "30d": [
    { label:"Critical Posts %",      value:"17%",    meta:"Last 30 days",  bar:17  },
    { label:"High Priority %",        value:"33%",    meta:"Last 30 days",  bar:33  },
    { label:"Total Posts Analyzed",   value:"63,208", meta:"Last 30 days",  bar:96  },
    { label:"Total Facebook Posts",   value:"35,890", meta:"Last 30 days",  bar:70  },
    { label:"Total X/Twitter Posts",  value:"27,318", meta:"Last 30 days",  bar:61  },
    { label:"Active Clusters %",      value:"100%",   meta:"All active",    bar:100 },
  ],
};

// ─── API Calls ────────────────────────────────────────────────────────────────
async function apiGetClusters()            { return apiFetch("/clusters"); }
async function apiGetDashboardSummary(r)   { const d = await apiFetch(`/dashboard/summary?date_range=${r}`); return d.kpis; }
async function apiUpdateEmailAlerts(en)    { return apiFetch("/settings/email-alerts", { method:"PATCH", body: JSON.stringify({ enabled: en }) }); }

// ─── DataService shim ─────────────────────────────────────────────────────────
const DashboardService = {
  async getClusters()           { return USE_MOCK ? MOCK_CLUSTERS : apiGetClusters(); },
  async getDashboardSummary(r)  { return USE_MOCK ? (MOCK_DASHBOARD_SUMMARY[r] || MOCK_DASHBOARD_SUMMARY["7d"]) : apiGetDashboardSummary(r); },
  async updateEmailAlerts(en)   { if (!USE_MOCK) return apiUpdateEmailAlerts(en); },
};

// ─── Render: Cluster Nav ──────────────────────────────────────────────────────
function renderClusterNav() {
  document.getElementById("clusterNav").innerHTML = state.clusters.map(cluster => `
    <button class="cluster-btn ${cluster.id === state.currentCluster ? "active" : ""}"
            type="button" data-cluster-nav="${cluster.id}"
            style="--cluster-accent:${cluster.accent};">
      <span class="cluster-btn-title">${cluster.short}: ${cluster.name}</span>
    </button>
  `).join("");
}

// ─── Render: Dashboard ────────────────────────────────────────────────────────
function renderDashboard() {
  const summaryCards = Array.isArray(state.dashboardSummary)
    ? state.dashboardSummary
    : (MOCK_DASHBOARD_SUMMARY[state.dashboardRange] || []);

  document.getElementById("kpiGrid").innerHTML = summaryCards.map(card => `
    <div class="mini-card ${kpiToneClass(card.label)}">
      <div class="mini-card-label">${card.label}</div>
      <div class="mini-card-value">${card.value}</div>
      <div class="mini-card-meta">${card.meta}</div>
      <div class="mini-bar"><span style="width:${card.bar}%;"></span></div>
    </div>
  `).join("");

  document.getElementById("keywordGrid").innerHTML = state.keywords.map(item => `
    <div class="keyword-chip">
      <div><strong>${item.keyword}</strong><span>${item.note}</span></div>
      <strong>${formatNumber(item.count)}</strong>
    </div>
  `).join("");

  const trendingPosts = filterPosts(state.posts, state.dashboardRange, "All")
    .sort((a, b) => (b.severityRank * 1000 + getEngagement(b)) - (a.severityRank * 1000 + getEngagement(a)))
    .slice(0, 4);
  document.getElementById("dashboardPosts").innerHTML = renderPostCards(trendingPosts);

  const commentCards = filterPosts(state.posts, state.dashboardRange, "All")
    .filter(p => p.topComments)
    .flatMap(p => p.topComments.map(c => ({ ...c, post: p })))
    .slice(0, 6);

  document.getElementById("dashboardComments").innerHTML = commentCards.map(c => `
    <article class="comment-card">
      <div class="comment-tag">${c.post.source} comment</div>
      <small>${c.author} on ${c.post.pageSource} · ${(state.clusters.find(cl => cl.id === c.post.clusterId) || {}).short || ""}</small>
      <p>${c.text}</p>
      <small>From post in ${c.post.location}</small>
    </article>
  `).join("");
}

// ─── Render: Source Directory ─────────────────────────────────────────────────
function renderSourceDirectory() {
  const sources = [...new Map(
    filterPosts(state.posts, state.dashboardRange, "All").map(p => [p.pageSource, p])
  ).values()].slice(0, 8);

  document.getElementById("sourceDirectory").innerHTML = sources.map(post => `
    <div class="source-item">
      <div class="source-item-main">
        <div class="source-badge ${post.source === "Facebook" ? "facebook" : "x"}">${post.source === "Facebook" ? "F" : "X"}</div>
        <div class="source-item-meta"><strong>${post.pageSource}</strong><span>${post.source}</span></div>
      </div>
      <div class="source-count">${formatCompact(getEngagement(post))} interactions</div>
    </div>
  `).join("");
}

// ─── Render: Profile Settings ─────────────────────────────────────────────────
function renderProfileSettings() {
  document.getElementById("profileUsername").value    = state.profile.username;
  document.getElementById("profileRole").value        = state.profile.role;
  document.getElementById("profileEmail").value       = state.profile.email;
  document.getElementById("topbarRole").textContent   = state.profile.role;
  document.getElementById("settingsRoleBadge").textContent = state.profile.role;
  document.getElementById("emailAlertsToggle").checked = state.emailAlerts;
}
