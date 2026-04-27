/**
 * MANA — Utilities Module
 * Pure helper functions shared across all other modules.
 * No DOM side-effects, no API calls, no state mutations.
 */

// ─── Number & Date Formatting ─────────────────────────────────────────────────
function formatNumber(n)  { return new Intl.NumberFormat("en-US").format(n); }
function formatCompact(n) { return new Intl.NumberFormat("en-US", { notation:"compact", maximumFractionDigits:1 }).format(n); }
function formatDate(d)    { return new Date(d).toLocaleString("en-US", { month:"short", day:"numeric", hour:"numeric", minute:"2-digit" }); }
function toCount(value)   { return Number.isFinite(Number(value)) ? Number(value) : 0; }

// ─── Post Engagement ──────────────────────────────────────────────────────────
function getEngagement(post) {
  return post.source === "Facebook"
    ? (post.reactions || 0) + (post.shares || 0)  + (post.comments || 0)
    : (post.likes     || 0) + (post.reposts  || 0) + (post.comments || 0);
}

// ─── Post Filtering & Sorting ─────────────────────────────────────────────────
function matchesDateRange(postDate, range) {
  const diffDays = (Date.now() - new Date(postDate).getTime()) / (1000 * 60 * 60 * 24);
  if (range === "24h") return diffDays <= 1;
  if (range === "3d")  return diffDays <= 3;
  if (range === "7d")  return diffDays <= 7;
  if (range === "14d") return diffDays <= 14;
  if (range === "30d") return diffDays <= 30;
  return true;
}

function filterPosts(sourcePosts, dateRange, source) {
  return sourcePosts
    .filter(p => matchesDateRange(p.date, dateRange))
    .filter(p => source === "All" ? true : p.source === source);
}

function sortPostsByPriority(a, b) {
  if (b.severityRank !== a.severityRank) return b.severityRank - a.severityRank;
  return getEngagement(b) - getEngagement(a);
}

// ─── Sentiment ────────────────────────────────────────────────────────────────
// Matches original exactly: 80+ = Negative, 60+ = Neutral, else Positive
function getDominantSentiment(score) {
  if (score >= 80) return { label: "Negative", percent: score, tone: "negative" };
  if (score >= 60) return { label: "Neutral",  percent: score, tone: "neutral"  };
  return               { label: "Positive", percent: score, tone: "positive" };
}

// ─── CSS Class Helpers ────────────────────────────────────────────────────────
function priorityClass(priority) {
  if (priority === "Critical") return "priority-critical";
  if (priority === "High")     return "priority-high";
  if (priority === "Moderate") return "priority-moderate";
  return "priority-monitoring";
}

function statusClass(status) { return `status-${status.toLowerCase()}`; }

function kpiToneClass(label) {
  if (label.includes("Critical"))            return "kpi-red";
  if (label.includes("High Priority"))       return "kpi-gold";
  if (label.includes("Total Posts Analyzed"))return "kpi-blue";
  if (label.includes("Facebook"))            return "kpi-cyan";
  if (label.includes("X/Twitter"))           return "kpi-slate";
  return "kpi-green";
}

function applyStatusStyle(select, status) {
  // ensure the element always has status-select base class (original CSS targets .status-select.status-*)
  select.classList.add("status-select");
  select.classList.remove("status-resolved","status-ongoing","status-monitoring","status-unresolved");
  select.classList.add(statusClass(status));
}

function applySeverityStyle(select, severity) {
  select.classList.remove("severity-critical","severity-high","severity-medium","severity-low");
  if (severity === "Critical") select.classList.add("severity-critical");
  if (severity === "High")     select.classList.add("severity-high");
  if (severity === "Medium")   select.classList.add("severity-medium");
  if (severity === "Low")      select.classList.add("severity-low");
}

// ─── Toast Notifications ──────────────────────────────────────────────────────
function showToast(title, message) {
  const wrap  = document.getElementById("toastWrap");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<strong>${title}</strong><p>${message}</p>`;
  wrap.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

// ─── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  document.getElementById("topbarClock").textContent = "Updated 26 Apr 2026";
}
