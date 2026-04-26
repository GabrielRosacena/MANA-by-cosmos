/**
 * MANA — Configuration & API Core
 * Single source of truth for backend URL, mock toggle, JWT helpers, and apiFetch().
 *
 * Backend: Python Flask or Django (see /backend/)
 * Auth: JWT Bearer token stored in localStorage after login.
 *
 * USE_MOCK = true  → hardcoded demo data, no backend needed
 * USE_MOCK = false → all calls go to Flask/Django at API_BASE
 */

const SUPABASE_URL = "https://gizuoookwwkximbqvcpx.supabase.co";
const SUPABASE_KEY = "sb_publishable_cj0YjBeAVubMaZVOyYXNyQ_D0en0BF_";

const API_BASE = "http://localhost:5000/api";
const USE_MOCK = true;

// ─── JWT Helpers ──────────────────────────────────────────────────────────────
function getToken()        { return localStorage.getItem("mana-token"); }
function setToken(token)   { localStorage.setItem("mana-token", token); }
function clearToken()      { localStorage.removeItem("mana-token"); }

// ─── Core Fetch Wrapper ───────────────────────────────────────────────────────
/**
 * apiFetch(endpoint, options)
 * Attaches auth headers, handles 401 auto-logout, and throws readable errors.
 *
 * @param {string}      endpoint  e.g. "/posts?date_range=7d"
 * @param {RequestInit} options   standard fetch options
 * @returns {Promise<any>}        parsed JSON response
 */
async function apiFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    showAuthView();
    throw new Error("Session expired. Please sign in again.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `API error ${res.status}`);
  }
  return res.json();
}
