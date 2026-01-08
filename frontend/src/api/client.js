/**
 * API Client for Enterprise Insider Threat Detection Platform
 */
import axios from 'axios';

const API_BASE_URL = '/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Could implement token refresh here
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await apiClient.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    
    // Store tokens
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
  
  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
  
  getStoredUser: () => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },
  
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};

// Events API
export const eventsAPI = {
  ingest: async (eventData) => {
    const response = await apiClient.post('/events/ingest', eventData);
    return response.data;
  },
  
  getHistory: async (limit = 50, offset = 0) => {
    const response = await apiClient.get('/events/history', {
      params: { limit, offset },
    });
    return response.data;
  },

  // Alias for getHistory with object params
  history: async (params = {}) => {
    const { limit = 50, offset = 0 } = params;
    const response = await apiClient.get('/events/history', {
      params: { limit, offset },
    });
    return response.data;
  },

  // Get all events (for analysts)
  getAll: async (params = {}) => {
    const response = await apiClient.get('/events/all', { params });
    return response.data;
  },
  
  getEvent: async (eventId) => {
    const response = await apiClient.get(`/events/${eventId}`);
    return response.data;
  },
};

// Documents API
export const documentsAPI = {
  list: async (params = {}) => {
    const response = await apiClient.get('/documents/', { params });
    return response.data;
  },
  
  getAll: async () => {
    const response = await apiClient.get('/documents/all');
    return response.data;
  },
  
  getByDepartment: async (department) => {
    const response = await apiClient.get(`/documents/by-department/${department}`);
    return response.data;
  },
  
  view: async (documentId) => {
    const response = await apiClient.get(`/documents/${documentId}/view`);
    return response.data;
  },
  
  download: async (documentId) => {
    const response = await apiClient.post(`/documents/${documentId}/download`);
    return response.data;
  },
  
  getStatistics: async () => {
    const response = await apiClient.get('/documents/statistics');
    return response.data;
  },

  upload: async (filename, content, department, sensitivity = 'INTERNAL') => {
    const response = await apiClient.post('/documents/upload', {
      filename,
      content,
      department,
      sensitivity,
    });
    return response.data;
  },
};

// Alerts API
export const alertsAPI = {
  list: async (params = {}) => {
    const response = await apiClient.get('/alerts/', { params });
    return response.data;
  },
  
  getRecent: async (limit = 10) => {
    const response = await apiClient.get('/alerts/recent', { params: { limit } });
    return response.data;
  },
  
  getCritical: async () => {
    const response = await apiClient.get('/alerts/critical');
    return response.data;
  },
  
  get: async (alertId) => {
    const response = await apiClient.get(`/alerts/${alertId}`);
    return response.data;
  },
  
  update: async (alertId, data) => {
    const response = await apiClient.put(`/alerts/${alertId}`, data);
    return response.data;
  },
  
  assign: async (alertId, assignee) => {
    const response = await apiClient.post(`/alerts/${alertId}/assign`, null, {
      params: { assignee },
    });
    return response.data;
  },
  
  resolve: async (alertId, notes) => {
    const response = await apiClient.post(`/alerts/${alertId}/resolve`, null, {
      params: { notes },
    });
    return response.data;
  },
  
  getByUser: async (userId) => {
    const response = await apiClient.get(`/alerts/user/${userId}`);
    return response.data;
  },
};

// Reports API
export const reportsAPI = {
  generate: async (data) => {
    const response = await apiClient.post('/reports/generate', data);
    return response.data;
  },
  
  list: async (params = {}) => {
    const response = await apiClient.get('/reports/', { params });
    return response.data;
  },
  
  get: async (reportId) => {
    const response = await apiClient.get(`/reports/${reportId}`);
    return response.data;
  },
  
  generateDaily: async () => {
    const response = await apiClient.post('/reports/daily');
    return response.data;
  },
  
  generateWeekly: async () => {
    const response = await apiClient.post('/reports/weekly');
    return response.data;
  },

  daily: async () => {
    const response = await apiClient.post('/reports/daily');
    return response.data;
  },

  weekly: async () => {
    const response = await apiClient.post('/reports/weekly');
    return response.data;
  },
};

// ML Status API
export const mlAPI = {
  status: async () => {
    const response = await apiClient.get('/ml/status');
    return response.data;
  },
  
  getStatus: async () => {
    const response = await apiClient.get('/ml/status');
    return response.data;
  },

  getAnomalyTimeline: async (hours = 24) => {
    const response = await apiClient.get('/ml/anomaly-timeline', { params: { hours } });
    return response.data;
  },

  getTopRiskUsers: async (limit = 10) => {
    const response = await apiClient.get('/ml/top-risk-users', { params: { limit } });
    return response.data;
  },

  getDocumentModifications: async (limit = 10) => {
    const response = await apiClient.get('/ml/document-modifications', { params: { limit } });
    return response.data;
  },

  getFeatureImportance: async () => {
    const response = await apiClient.get('/ml/feature-importance');
    return response.data;
  },

  getExplanations: async (limit = 10) => {
    const response = await apiClient.get('/ml/explanations', { params: { limit } });
    return response.data;
  },

  getAlertsByDay: async (days = 7) => {
    const response = await apiClient.get('/ml/alerts-by-day', { params: { days } });
    return response.data;
  },

  getReportSummary: async () => {
    const response = await apiClient.get('/ml/report-summary');
    return response.data;
  },
};

export default apiClient;
