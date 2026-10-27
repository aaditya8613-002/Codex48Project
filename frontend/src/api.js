/**
 * Central API client for BrandGuard backend service
 */
const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, options);
  if (!res.ok) {
    let errorDetail = 'API request failed';
    try {
      const err = await res.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Health
  getHealth: () => request('/health'),

  // Organisation
  getOrg: (orgId = 1) => request(`/orgs/${orgId}`),
  createOrg: (data) => request('/orgs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // Knowledge Base: Facts & Terms
  getFacts: (orgId = 1) => request(`/orgs/${orgId}/kb/facts`),
  addFact: (orgId = 1, fact) => request(`/orgs/${orgId}/kb/facts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fact),
  }),
  deleteFact: (orgId = 1, factId) => request(`/orgs/${orgId}/kb/facts/${factId}`, {
    method: 'DELETE',
  }),

  getTerms: (orgId = 1) => request(`/orgs/${orgId}/kb/terms`),
  addTerm: (orgId = 1, term) => request(`/orgs/${orgId}/kb/terms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(term),
  }),
  deleteTerm: (orgId = 1, termId) => request(`/orgs/${orgId}/kb/terms/${termId}`, {
    method: 'DELETE',
  }),

  // Documents
  getDocuments: (orgId = 1) => request(`/orgs/${orgId}/kb/documents`),
  uploadDocument: (orgId = 1, formData) => request(`/orgs/${orgId}/kb/documents`, {
    method: 'POST',
    body: formData,
  }),

  // Review
  reviewText: (orgId = 1, data) => request(`/orgs/${orgId}/review/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  reviewFile: (orgId = 1, formData) => request(`/orgs/${orgId}/review/file`, {
    method: 'POST',
    body: formData,
  }),
  reviewImage: (orgId = 1, formData) => request(`/orgs/${orgId}/review/image`, {
    method: 'POST',
    body: formData,
  }),
  checkContrast: (orgId = 1, data) => request(`/orgs/${orgId}/review/contrast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // Finding decisions
  decideFinding: (findingId, data) => request(`/findings/${findingId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // Workflow & Reviews
  listReviews: (orgId = 1) => request(`/orgs/${orgId}/reviews`),
  getReview: (reviewId) => request(`/reviews/${reviewId}`),
  updateWorkflow: (reviewId, data) => request(`/reviews/${reviewId}/workflow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  saveRevision: (reviewId, data) => request(`/reviews/${reviewId}/revisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  addComment: (reviewId, data) => request(`/reviews/${reviewId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // Insights
  getRuleInsights: (orgId = 1) => request(`/orgs/${orgId}/insights/rules`),
  getGovernanceSummary: (orgId = 1) => request(`/orgs/${orgId}/insights/summary`),

  // Demo Presets
  getDemoPresets: (orgId = 1) => request(`/orgs/${orgId}/demo-presets`),
};
