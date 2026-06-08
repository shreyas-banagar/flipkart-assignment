/**
 * api.js — Shared API utility
 * All fetch calls go through here so we have one place to change the base URL.
 * When served via Nginx the proxy rewrites /api/* → http://backend:8000/api/*
 */

const API_BASE = window.API_BASE ?? '/api';

/**
 * Generic fetch wrapper. Returns parsed JSON or throws an Error with
 * a human-readable message (extracted from FastAPI's {detail:...} shape).
 *
 * @param {string} path       - Path relative to API_BASE, e.g. '/ingest'
 * @param {RequestInit} opts  - Standard fetch options
 * @returns {Promise<any>}
 */
async function apiFetch(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, opts);
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const msg = data?.detail ?? `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

/**
 * POST /api/ingest
 * @param {FormData} formData
 */
async function apiIngest(formData) {
  return apiFetch('/ingest', { method: 'POST', body: formData });
}

/**
 * GET /api/ingest/status/:taskId
 * @param {string} taskId
 * @param {string} username
 */
async function apiIngestStatus(taskId, username) {
  return apiFetch(`/ingest/status/${taskId}?username=${encodeURIComponent(username)}`);
}

/**
 * POST /api/products/validate
 * @param {FormData} formData   - wid, username, file
 */
async function apiValidateProduct(formData) {
  return apiFetch('/products/validate', { method: 'POST', body: formData });
}

/**
 * GET /api/reports/verification
 * @param {string} startDate  - YYYY-MM-DD
 * @param {string} endDate    - YYYY-MM-DD
 * @param {string} username
 */
async function apiGetReport(startDate, endDate, username) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate, username });
  return apiFetch(`/reports/verification?${params}`);
}

/**
 * DELETE /api/reset
 * Truncates the products table (CASCADE). Must pass confirm=true.
 * @param {string} username
 */
async function apiReset(username) {
  const params = new URLSearchParams({ username, confirm: 'true' });
  return apiFetch(`/reset?${params}`, { method: 'DELETE' });
}

/* ---- Shared helper: format date string nicely ---- */
function fmtDate(val) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleDateString('en-IN', {
      year: 'numeric', month: 'short', day: '2-digit',
    });
  } catch { return val; }
}

/* ---- Shared helper: format datetime ---- */
function fmtDateTime(val) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleString('en-IN', {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return val; }
}

/* ---- Shared helper: days until expiry ---- */
function daysUntilExpiry(expiryDate) {
  if (!expiryDate) return null;
  const exp = new Date(expiryDate);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.ceil((exp - now) / (1000 * 60 * 60 * 24));
}
