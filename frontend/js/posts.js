/**
 * MANA — Posts Module
 * Fetches, filters, sorts, and renders post cards and the watchlist/pin system.
 *
 * API endpoints (backend must implement):
 *   GET   /api/posts                         Query: date_range, source, cluster_id, priority
 *                                            Returns: Post[]
 *   PATCH /api/posts/:id/status              Body: { status } → { id, status }
 *   GET   /api/watchlist                     Returns: { pinned: string[] }
 *   POST  /api/watchlist/:postId             Returns: { pinned: string[] }
 *   DELETE /api/watchlist/:postId            Returns: { pinned: string[] }
 *   GET   /api/dashboard/keywords            Returns: { keywords: [{keyword,note,count}] }
 *
 * Post shape expected from backend:
 *   { id, source, pageSource, author, caption,
 *     reactions?, shares?, likes?, reposts?, comments,
 *     topComments?: [{author, text}],
 *     priority, sentimentScore, recommendation,
 *     status, clusterId, date, keywords, location, severityRank }
 */

// ─── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_POSTS = [
  { id:"p1",  source:"Facebook", pageSource:"Tumana Community Updates",  author:"Tumana Community Updates",  caption:"Wala pa ring relief goods sa covered court. Mahigit 180 pamilya ang naghihintay ng pagkain, drinking water, at hygiene kits ngayong gabi.", reactions:1840, shares:612, comments:294, topComments:[{author:"R. Domingo",text:"Need din po ng gatas at diaper sa kabilang wing."},{author:"M. Santos",text:"Confirmed po, wala pa ring distribution list na umikot."}], priority:"Critical", sentimentScore:92, recommendation:"Dispatch rapid food and NFI validation to the covered court within the next response cycle.", status:"Ongoing",    clusterId:"cluster-a", date:"2026-04-25T08:20:00", keywords:["relief goods","drinking water","hygiene kits"], location:"Marikina City",     severityRank:4 },
  { id:"p2",  source:"X",        pageSource:"@healthwatch_mnl",          author:"@healthwatch_mnl",          caption:"May mga evacuees na may lagnat at ubo sa Brgy. Bagong Silangan. Kailangan ng medical team at clean drinking water agad.", likes:972, reposts:308, comments:140,                                                                                                                                                                                                                                                                              priority:"High",     sentimentScore:84, recommendation:"Coordinate a barangay health sweep and water safety check before the next crowding peak.",          status:"Monitoring", clusterId:"cluster-b", date:"2026-04-24T19:40:00", keywords:["medical team","clean drinking water","fever"],     location:"Quezon City",       severityRank:3 },
  { id:"p3",  source:"Facebook", pageSource:"Cainta Rescue Net",         author:"Cainta Rescue Net",         caption:"May apat na pamilya sa rooftop sa Brookside. Tumataas pa ang tubig at may kasamang senior citizen at bata.", reactions:2650, shares:1131, comments:416, topComments:[{author:"L. Rivera",text:"Nakita pa sila sa Block 3 kanina, tubig hanggang bubong na."},{author:"P. Flores",text:"Naipasa na raw sa MDRRMO pero wala pang boat."}],                    priority:"Critical", sentimentScore:97, recommendation:"Push SRR dispatch coordinates to the nearest rescue team and validate rooftop extraction access immediately.", status:"Unresolved", clusterId:"cluster-g", date:"2026-04-25T06:10:00", keywords:["rooftop","senior citizen","boat"],               location:"Cainta, Rizal",     severityRank:4 },
  { id:"p4",  source:"X",        pageSource:"@supplydesk_ph",            author:"@supplydesk_ph",            caption:"Main relief truck route to San Mateo is blocked again. Need reroute guidance for food convoy and fuel access before noon.", likes:524, reposts:211, comments:68,                                                                                                                                                                                                                                                                            priority:"High",     sentimentScore:76, recommendation:"Activate alternate convoy routing and issue a field logistics advisory before dispatch resumes.",          status:"Ongoing",    clusterId:"cluster-d", date:"2026-04-24T11:25:00", keywords:["relief truck","reroute","fuel access"],          location:"San Mateo, Rizal",  severityRank:3 },
  { id:"p5",  source:"Facebook", pageSource:"Evacuation Center Watch PH",author:"Evacuation Center Watch PH",caption:"Overcapacity na sa gym evacuation site. Isang CR lang gumagana at mahaba ang pila ng bagong dating na evacuees.", reactions:890, shares:205, comments:116, topComments:[{author:"J. Cruz",text:"May buntis din po na nakapila nang matagal."},{author:"A. Mendoza",text:"Need separation area for families and women."}],                                  priority:"High",     sentimentScore:79, recommendation:"Open overflow shelter support and protection checks for sanitation and vulnerable groups.",               status:"Monitoring", clusterId:"cluster-c", date:"2026-04-23T17:00:00", keywords:["overcapacity","CR","new evacuees"],              location:"Navotas City",      severityRank:3 },
  { id:"p6",  source:"X",        pageSource:"@signalwatch",              author:"@signalwatch",              caption:"No mobile signal in parts of Rodriguez after midnight. Residents cannot send location updates to responders.", likes:742, reposts:290, comments:95,                                                                                                                                                                                                                                                                                          priority:"High",     sentimentScore:82, recommendation:"Escalate ETC support and deploy backup communications to high-isolation pockets.",                       status:"Ongoing",    clusterId:"cluster-e", date:"2026-04-24T00:50:00", keywords:["no mobile signal","location updates","backup communications"], location:"Rodriguez, Rizal",  severityRank:3 },
  { id:"p7",  source:"Facebook", pageSource:"Parents for Safe Schools",  author:"Parents for Safe Schools",  caption:"Ginawang evacuation center ang elementary school. Kailan ibabalik ang learning materials ng mga bata at saan sila mag-aaral pansamantala?", reactions:416, shares:92, comments:74, topComments:[{author:"Teacher Ana",text:"Kailangan po ng temporary learning corner kahit basic lang."},{author:"Parent Group 4",text:"Nabasa na ang ibang school kits."}], priority:"Moderate",  sentimentScore:68, recommendation:"Coordinate transitional learning support with school administrators and relief planners.",             status:"Monitoring", clusterId:"cluster-f", date:"2026-04-22T13:30:00", keywords:["evacuation center","learning materials","temporary learning"], location:"Pasig City",       severityRank:2 },
  { id:"p8",  source:"X",        pageSource:"@hanap_pamilya",            author:"@hanap_pamilya",            caption:"Missing pa rin si Tatay after evacuation from riverside area. Wala siya sa hospital list at hindi rin makita sa barangay registry.", likes:693, reposts:401, comments:144,                                                                                                                                                                                                                                                                  priority:"High",     sentimentScore:88, recommendation:"Cross-check family tracing with hospital intake and barangay evacuation registries immediately.",              status:"Unresolved", clusterId:"cluster-h", date:"2026-04-24T16:35:00", keywords:["missing","hospital list","barangay registry"],          location:"Manila City",       severityRank:3 },
  { id:"p9",  source:"Facebook", pageSource:"Medical Volunteers Network",author:"Medical Volunteers Network",caption:"Naubusan ng insulin at BP meds sa evacuation site. May senior patients na hindi pa natitingnan mula kagabi.", reactions:1512, shares:522, comments:208, topComments:[{author:"C. Villanueva",text:"May dalawang diabetic patients na nanghihina na."},{author:"A. Reyes",text:"Need din po ng BP apparatus at triage station."}],                             priority:"Critical", sentimentScore:95, recommendation:"Send urgent medicine replenishment and a mobile medical triage team to the site today.",                 status:"Ongoing",    clusterId:"cluster-b", date:"2026-04-25T05:15:00", keywords:["insulin","BP meds","triage station"],                  location:"Mandaluyong City",  severityRank:4 },
  { id:"p10", source:"X",        pageSource:"@bahaalert",                author:"@bahaalert",                caption:"Rice packs are arriving but no clean water and blankets yet in Barangay Nangka. Families are asking which drop-off point is active.", likes:602, reposts:189, comments:72,                                                                                                                                                                                                                                                                  priority:"High",     sentimentScore:74, recommendation:"Publish the active drop-off point and prioritize water plus blanket delivery for the next dispatch batch.",      status:"Monitoring", clusterId:"cluster-a", date:"2026-04-25T09:05:00", keywords:["clean water","blankets","drop-off point"],              location:"Marikina City",     severityRank:3 },
  { id:"p11", source:"Facebook", pageSource:"Shelter Protection Desk",   author:"Shelter Protection Desk",   caption:"Women and children are asking for a safer partitioned area in the temporary camp. Lighting is weak near the sleeping zone.", reactions:731, shares:144, comments:98, topComments:[{author:"Grace B.",text:"Madilim po talaga after 9 PM near the tents."},{author:"Field Volunteer",text:"Need women-friendly space and extra lamps."}],                           priority:"High",     sentimentScore:81, recommendation:"Coordinate immediate camp protection adjustments and lighting support for vulnerable groups.",              status:"Ongoing",    clusterId:"cluster-c", date:"2026-04-24T21:20:00", keywords:["safer area","lighting","sleeping zone"],                location:"Malabon City",      severityRank:3 },
  { id:"p12", source:"X",        pageSource:"@rescue_now_mnl",           author:"@rescue_now_mnl",           caption:"SOS from riverside homes near Ampid. Children waving from second floor and current is getting stronger.", likes:1290, reposts:801, comments:231,                                                                                                                                                                                                                                                                                           priority:"Critical", sentimentScore:96, recommendation:"Escalate river rescue deployment and mark the site as immediate extraction priority.",                  status:"Unresolved", clusterId:"cluster-g", date:"2026-04-25T07:45:00", keywords:["SOS","children","river rescue"],                    location:"San Mateo, Rizal",  severityRank:4 },
];

const MOCK_KEYWORDS = [
  { keyword:"relief goods",     note:"Cluster A surge",         count:428 },
  { keyword:"medical team",     note:"Cluster B escalation",    count:392 },
  { keyword:"rooftop rescue",   note:"Cluster G spike",         count:366 },
  { keyword:"evacuation center",note:"Cross-cluster signal",    count:344 },
  { keyword:"signal down",      note:"Cluster E issue",         count:198 },
  { keyword:"missing",          note:"Cluster H tracing",       count:174 },
];

// ─── API Calls ────────────────────────────────────────────────────────────────
async function apiGetPosts(filters = {}) {
  const params = new URLSearchParams();
  if (filters.dateRange) params.set("date_range", filters.dateRange);
  if (filters.source && filters.source !== "All") params.set("source", filters.source);
  if (filters.clusterId) params.set("cluster_id", filters.clusterId);
  if (filters.priority)  params.set("priority",   filters.priority);
  const qs = params.toString();
  return apiFetch(`/posts${qs ? "?" + qs : ""}`);
}

async function apiUpdatePostStatus(postId, status) {
  return apiFetch(`/posts/${postId}/status`, {
    method:"PATCH",
    body: JSON.stringify({ status }),
    skipAuthRedirect: true,
  });
}

async function apiGetWatchlist()       { return apiFetch("/watchlist"); }
async function apiPinPost(postId)      {
  return apiFetch(`/watchlist/${postId}`, { method:"POST", skipAuthRedirect: true });
}
async function apiUnpinPost(postId)    {
  return apiFetch(`/watchlist/${postId}`, { method:"DELETE", skipAuthRedirect: true });
}
async function apiGetKeywords()        { const d = await apiFetch("/dashboard/keywords"); return d.keywords; }

// ─── DataService shim ─────────────────────────────────────────────────────────
const PostsService = {
  async getPosts()      { return USE_MOCK ? MOCK_POSTS    : apiGetPosts(); },
  async getWatchlist()  { return USE_MOCK ? { pinned:["p1","p3","p9"] } : { pinned: [] }; },
  async getKeywords()   { return USE_MOCK ? MOCK_KEYWORDS : apiGetKeywords(); },

  async pinPost(postId) {
    return { postId, pinned: true, localOnly: true };
  },
  async unpinPost(postId) {
    return { postId, pinned: false, localOnly: true };
  },
  async updatePostStatus(postId, status) {
    return { postId, status, localOnly: true };
  },
};

// ─── Toggle Pin ───────────────────────────────────────────────────────────────
async function togglePin(postId) {
  if (state.pinned.has(postId)) {
    state.pinned.delete(postId);
    const result = await PostsService.unpinPost(postId).catch(() => null);
    showToast(
      result?.localOnly ? "Removed locally" : "Removed from Saved Intelligence",
      result?.localOnly
        ? "The post was removed from the local watchlist in this browser."
        : "The post has been removed from the pinned watchlist."
    );
  } else {
    state.pinned.add(postId);
    const result = await PostsService.pinPost(postId).catch(() => null);
    showToast(
      result?.localOnly ? "Pinned locally" : "Pinned to Saved Intelligence",
      result?.localOnly
        ? "The post was added to the local watchlist in this browser."
        : "The post has been added to the watchlist for later review."
    );
  }
  persistLocalPreferences();
  renderDashboard();
  renderAlerts();
  renderWatchlist();
  renderClusterDetail();
}

// ─── Render: Post Cards ───────────────────────────────────────────────────────
function renderPostCards(postList) {
  if (!postList.length) return `<div class="watch-empty"><strong>No posts match the selected filters.</strong>Try a broader source selection or a wider date range.</div>`;

  return postList.map(post => {
    const cluster   = state.clusters.find(c => c.id === post.clusterId) || {};
    const isFB      = post.source === "Facebook";
    const pinned    = state.pinned.has(post.id);
    const status    = state.statuses[post.id] || post.status;
    const sentiment = getDominantSentiment(post.sentimentScore);
    // ── metrics: match original exactly (metric-pill spans, no sentiment row)
    const metrics = isFB
      ? [
          { label:"Reactions", value:formatNumber(post.reactions) },
          { label:"Likes", value:formatNumber(post.likes || post.reactions) },
          { label:"Shares", value:formatNumber(post.shares) },
          { label:"Comments", value:formatNumber(post.comments) },
        ]
      : [
          { label:"Likes", value:formatNumber(post.likes) },
          { label:"Reposts", value:formatNumber(post.reposts) },
          { label:"Comments", value:formatNumber(post.comments) },
        ];

    return `
      <article class="post-card">
        <div class="post-card-head">
          <div class="post-source">
            <div class="source-badge ${isFB ? "facebook" : "x"}">${isFB ? "F" : "X"}</div>
            <div class="post-meta">
              <strong>${post.pageSource}</strong>
              <span>${formatDate(post.date)} - ${post.location}</span>
              <small>${cluster.short || ""}: ${cluster.name || ""}</small>
            </div>
          </div>
          <button class="pin-btn ${pinned ? "pinned" : ""}" type="button" data-pin="${post.id}" aria-label="Pin post">
            <svg viewBox="0 0 24 24"><path d="M8 3h8l-1 5 3 3v1H6v-1l3-3-1-5z"></path><path d="M12 12v9"></path></svg>
          </button>
        </div>

        <div class="badge-row">
          <span class="badge ${priorityClass(post.priority)}">${post.priority} Priority</span>
          <span class="badge sentiment-badge sentiment-${sentiment.tone}">Single Dominant Sentiment Gauge: ${sentiment.label} ${sentiment.percent}%</span>
          <span class="cluster-pill">${post.source}</span>
          <span class="cluster-pill">${cluster.short || ""}</span>
        </div>

        <div class="post-text">${post.caption}</div>
        <div class="metric-row">
          ${metrics.map(m => `<span class="metric-pill">${m.label}: ${m.value}</span>`).join("")}
        </div>

        <div class="recommendation"><strong>Recommendation:</strong>${post.recommendation}</div>

        <div class="post-foot">
          <div class="status-wrap">
            <label for="status-${post.id}">Status</label>
            <select class="status-select ${statusClass(status)}" id="status-${post.id}" data-status-select="${post.id}">
              ${["Resolved","Ongoing","Monitoring","Unresolved"].map(s => `
                <option value="${s}" ${status === s ? "selected" : ""}>${s}</option>
              `).join("")}
            </select>
          </div>
          ${isFB && post.topComments ? `<button class="comments-toggle" type="button" data-toggle-comments="${post.id}">View top comments</button>` : ""}
        </div>

        ${isFB && post.topComments ? `
          <div class="comments-box" id="comments-${post.id}">
            ${post.topComments.map(c => `
              <div class="comment-entry">
                <strong>${c.author}</strong>
                <span>${c.text}</span>
              </div>
            `).join("")}
          </div>
        ` : ""}
      </article>`;
  }).join("");
}

// ─── Render: Watchlist ────────────────────────────────────────────────────────
function renderWatchlist() {
  const pinned = state.posts.filter(p => state.pinned.has(p.id)).sort(sortPostsByPriority);
  document.getElementById("watchlistGrid").innerHTML = pinned.length
    ? renderPostCards(pinned)
    : `<div class="watch-empty"><strong>No saved intelligence yet.</strong>Use the pin control on any post card to send it here for prioritized watchlist review.</div>`;
}

// ─── Render: Alerts ───────────────────────────────────────────────────────────
function renderAlerts() {
  const filtered = filterPosts(state.posts, state.alerts.dateRange, state.alerts.source)
    .filter(p => p.priority === "Critical" || p.priority === "High")
    .sort(sortPostsByPriority);

  const grouped = state.clusters.map(cluster => {
    const cp = filtered.filter(p => p.clusterId === cluster.id);
    if (!cp.length) return null;
    const highest   = cp[0];
    const locations = [...new Set(cp.map(p => p.location))].slice(0, 2).join(", ");
    const keywords  = [...new Set(cp.flatMap(p => p.keywords))].slice(0, 3).join(", ");
    return { cluster, highest, total: cp.length, locations, keywords };
  }).filter(Boolean).sort((a, b) => sortPostsByPriority(a.highest, b.highest));

  document.getElementById("alertClusterGrid").innerHTML = grouped.map(entry => `
    <article class="cluster-tile" style="border-left:3px solid ${entry.cluster.accent};">
      <div class="cluster-tile-top">
        <div>
          <div class="badge ${priorityClass(entry.highest.priority)}">${entry.highest.priority} Priority</div>
          <h4 style="margin-top:10px;">${entry.cluster.short}: ${entry.cluster.name}</h4>
        </div>
        <div class="page-chip">${formatNumber(entry.total)} posts</div>
      </div>
      <ul>
        <li><span>Top keywords</span><strong>${entry.keywords}</strong></li>
        <li><span>Mentioned locations</span><strong>${entry.locations}</strong></li>
        <li><span>Primary source</span><strong>${entry.highest.source}</strong></li>
      </ul>
    </article>
  `).join("") || `<div class="watch-empty"><strong>No priority clusters match the current filters.</strong></div>`;

  document.getElementById("alertPostGrid").innerHTML = renderPostCards(filtered);
}

// ─── Render: Cluster Detail ───────────────────────────────────────────────────
function renderClusterDetail() {
  const cluster = state.clusters.find(c => c.id === state.currentCluster);
  if (!cluster) return;

  document.getElementById("clusterPageTitle").textContent = `${cluster.short}: ${cluster.name}`;
  document.getElementById("clusterPageLead").textContent  = "Cluster page with filters, key metrics, and related posts.";

  const clusterPosts  = state.posts.filter(p => p.clusterId === cluster.id);
  const criticalCount = clusterPosts.filter(p => p.priority === "Critical").length;
  const highCount     = clusterPosts.filter(p => p.priority === "High").length;

  document.getElementById("clusterHero").innerHTML = `
    <div class="cluster-title-row">
      <div class="cluster-description">
        <small class="eyebrow">Cluster profile</small>
        <h3>${cluster.short}: ${cluster.name}</h3>
        <p>${cluster.description}</p>
        <small class="eyebrow" style="margin-top:12px;">Keywords used for scraping</small>
        <div class="keyword-strip">${cluster.keywords.map(k => `<span class="keyword-tag">${k}</span>`).join("")}</div>
      </div>
    </div>
    <div class="cluster-metrics">
      <div class="mini-card kpi-blue"><div class="mini-card-label">Total posts in cluster</div><div class="mini-card-value">${formatNumber(clusterPosts.length)}</div><div class="mini-card-meta">Posts shown in this demo</div></div>
      <div class="mini-card kpi-red"><div class="mini-card-label">Critical posts count</div><div class="mini-card-value">${formatNumber(criticalCount)}</div><div class="mini-card-meta">Posts that need fastest response</div></div>
      <div class="mini-card kpi-gold"><div class="mini-card-label">High priority posts count</div><div class="mini-card-value">${formatNumber(highCount)}</div><div class="mini-card-meta">Posts that need close attention</div></div>
    </div>`;

  const f = state.clusterFilters;
  const filteredPosts = filterPosts(clusterPosts, f.dateRange, f.source)
    .filter(p => {
      if (f.severity === "Critical") return p.priority === "Critical";
      if (f.severity === "High")     return p.priority === "High";
      if (f.severity === "Medium")   return p.priority === "Moderate";
      if (f.severity === "Low")      return p.priority === "Monitoring";
      return true;
    })
    .sort((a, b) => f.severity === "Trending" ? getEngagement(b) - getEngagement(a) : sortPostsByPriority(a, b));

  document.getElementById("clusterPostGrid").innerHTML = renderPostCards(filteredPosts);
  renderClusterNav();
  applySeverityStyle(document.getElementById("clusterSeverityFilter"), f.severity);
}
