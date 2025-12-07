import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

// Allow overriding the backend URL so we don't rely on a dev proxy pointing at the right port
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API Functions

// Auth
export const login = async (email: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Dashboard
export const getDashboardMetrics = async () => {
  const response = await api.get('/reports/dashboard');
  return response.data;
};

// Assets
export const getAssets = async (params?: Record<string, unknown>) => {
  const response = await api.get('/assets', { params });
  return response.data;
};

export const getAsset = async (id: number) => {
  const response = await api.get(`/assets/${id}`);
  return response.data;
};

export const createAsset = async (data: Record<string, unknown>) => {
  const response = await api.post('/assets', data);
  return response.data;
};

export const updateAsset = async (id: number, data: Record<string, unknown>) => {
  const response = await api.put(`/assets/${id}`, data);
  return response.data;
};

// Locations
export const getLocations = async (params?: Record<string, unknown>) => {
  const response = await api.get('/locations', { params });
  return response.data;
};

export const getLocationTree = async () => {
  const response = await api.get('/locations/tree');
  return response.data;
};

export const createLocation = async (data: Record<string, unknown>) => {
  const response = await api.post('/locations', data);
  return response.data;
};

// Work Orders
export const getWorkOrders = async (params?: Record<string, unknown>) => {
  const response = await api.get('/work-orders', { params });
  return response.data;
};

export const getWorkOrder = async (id: number) => {
  const response = await api.get(`/work-orders/${id}`);
  return response.data;
};

export interface CreateWorkOrderData {
  title: string;
  description?: string;
  work_type?: string;
  priority?: string;
  asset_id?: number; // Primary asset
  asset_ids?: number[]; // Additional assets for multi-asset work orders
  location_id?: number;
  assigned_to_id?: number;
  assigned_team?: string;
  scheduled_start?: string;
  scheduled_end?: string;
  due_date?: string;
  estimated_hours?: number;
  estimated_cost?: number;
  custom_fields?: Record<string, unknown>;
  tasks?: Array<{
    sequence: number;
    description: string;
    instructions?: string;
    task_type?: string;
    expected_value?: string;
    estimated_hours?: number;
  }>;
}

export const createWorkOrder = async (data: CreateWorkOrderData) => {
  const response = await api.post('/work-orders', data);
  return response.data;
};

export const updateWorkOrder = async (id: number, data: Record<string, unknown>) => {
  const response = await api.put(`/work-orders/${id}`, data);
  return response.data;
};

export interface StatusUpdateData {
  status: string;
  reason?: string;
  completion_notes?: string;
  failure_code?: string;
  failure_cause?: string;
  failure_remedy?: string;
  downtime_hours?: number;
  asset_was_down?: boolean;
}

export const updateWorkOrderStatus = async (id: number, data: StatusUpdateData) => {
  const response = await api.put(`/work-orders/${id}/status`, data);
  return response.data;
};

export const addLaborTransaction = async (woId: number, data: Record<string, unknown>) => {
  const response = await api.post(`/work-orders/${woId}/labor`, data);
  return response.data;
};

export const addMaterialTransaction = async (woId: number, data: Record<string, unknown>) => {
  const response = await api.post(`/work-orders/${woId}/materials`, data);
  return response.data;
};

export const addWorkOrderTask = async (woId: number, data: Record<string, unknown>) => {
  const response = await api.post(`/work-orders/${woId}/tasks`, data);
  return response.data;
};

export const updateWorkOrderTask = async (woId: number, taskId: number, data: Record<string, unknown>) => {
  const response = await api.put(`/work-orders/${woId}/tasks/${taskId}`, data);
  return response.data;
};

export const addComment = async (woId: number, comment: string) => {
  const response = await api.post(`/work-orders/${woId}/comments`, { comment });
  return response.data;
};

export const deleteWorkOrder = async (id: number) => {
  const response = await api.delete(`/work-orders/${id}`);
  return response.data;
};

// User Groups
export * from './userGroups';

// Notifications
export const getNotifications = async () => {
  const response = await api.get('/reports/notifications');
  return response.data;
};

// Dashboard Widgets
export const getDashboardWidget = async (widget: string, params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
  status?: string;
  priority?: string;
  work_type?: string;
  assigned_to?: number;
  asset_status?: string;
  criticality?: string;
  storeroom?: number;
  craft?: string;
  labor_type?: string;
}) => {
  const response = await api.get('/reports/dashboard/widgets', {
    params: { widget, ...params },
  });
  return response.data;
};

// Preventive Maintenance
export const getPMs = async (params?: Record<string, unknown>) => {
  const response = await api.get('/pm', { params });
  return response.data;
};

export const getPM = async (id: number) => {
  const response = await api.get(`/pm/${id}`);
  return response.data;
};

export const pausePMScheduler = async (paused: boolean) => {
  const response = await api.post(`/pm/pause`, null, { params: { paused } });
  return response.data;
};

export const getPMSchedulerStatus = async () => {
  const response = await api.get('/pm/status');
  return response.data;
};

export const createPM = async (data: Record<string, unknown>) => {
  const response = await api.post('/pm', data);
  return response.data;
};

export const generatePMWorkOrder = async (pmId: number) => {
  const response = await api.post(`/pm/${pmId}/generate-wo`);
  return response.data;
};

export const getDuePMs = async (daysAhead = 7) => {
  const response = await api.get('/pm/due', { params: { days_ahead: daysAhead } });
  return response.data;
};

// Inventory
export const getPartCategories = async () => {
  const response = await api.get('/inventory/categories');
  return response.data;
};

export const getParts = async (params?: Record<string, unknown>) => {
  const response = await api.get('/inventory/parts', { params });
  return response.data;
};

export const getPart = async (id: number) => {
  const response = await api.get(`/inventory/parts/${id}`);
  return response.data;
};

export const createPart = async (data: Record<string, unknown>) => {
  const response = await api.post('/inventory/parts', data);
  return response.data;
};

export const getLowStockParts = async () => {
  const response = await api.get('/inventory/parts/low-stock');
  return response.data;
};

export const getStorerooms = async () => {
  const response = await api.get('/inventory/storerooms');
  return response.data;
};

export const getVendors = async (params?: Record<string, unknown>) => {
  const response = await api.get('/inventory/vendors', { params });
  return response.data;
};

export const getPurchaseOrders = async (params?: Record<string, unknown>) => {
  const response = await api.get('/inventory/purchase-orders', { params });
  return response.data;
};

export const createPurchaseOrder = async (data: Record<string, unknown>) => {
  const response = await api.post('/inventory/purchase-orders', data);
  return response.data;
};

export const getPurchaseOrder = async (id: number) => {
  const response = await api.get(`/inventory/purchase-orders/${id}`);
  return response.data;
};

export const updatePOStatus = async (id: number, status: string) => {
  const response = await api.put(`/inventory/purchase-orders/${id}/status`, null, {
    params: { new_status: status },
  });
  return response.data;
};

export const receivePOLines = async (id: number, lines: { line_id: number; quantity_received: number }[]) => {
  const response = await api.post(`/inventory/purchase-orders/${id}/receive`, lines);
  return response.data;
};

export const getStoreroomStock = async (storeroomId: number) => {
  const response = await api.get(`/inventory/storerooms/${storeroomId}/stock`);
  return response.data;
};

export const getCycleCounts = async (params?: Record<string, unknown>) => {
  const response = await api.get('/inventory/cycle-counts', { params });
  return response.data;
};

export const createCycleCount = async (data: Record<string, unknown>) => {
  const response = await api.post('/inventory/cycle-counts', data);
  return response.data;
};

export const getCycleCount = async (id: number) => {
  const response = await api.get(`/inventory/cycle-counts/${id}`);
  return response.data;
};

export const recordCycleCount = async (
  id: number,
  lines: { line_id: number; counted_quantity: number; notes?: string; needs_recount?: boolean }[]
) => {
  const response = await api.post(`/inventory/cycle-counts/${id}/record`, { lines });
  return response.data;
};

export const getCycleCountPlans = async () => {
  const response = await api.get('/inventory/cycle-count-plans');
  return response.data;
};

export const createCycleCountPlan = async (data: Record<string, unknown>) => {
  const response = await api.post('/inventory/cycle-count-plans', data);
  return response.data;
};

export const pauseCycleCountPlan = async (id: number, paused: boolean) => {
  const response = await api.post(`/inventory/cycle-count-plans/${id}/pause`, null, { params: { paused } });
  return response.data;
};

export const pauseCycleCounts = async (paused: boolean) => {
  const response = await api.post('/inventory/cycle-counts/pause', null, { params: { paused } });
  return response.data;
};

export const getCycleCountSchedulerStatus = async () => {
  const response = await api.get('/inventory/cycle-counts/status');
  return response.data;
};

// Reports
export const getWorkOrderSummary = async (startDate?: string, endDate?: string) => {
  const response = await api.get('/reports/work-orders/summary', {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
};

export const getAssetSummary = async () => {
  const response = await api.get('/reports/assets/summary');
  return response.data;
};

export const getPMCompliance = async (startDate?: string, endDate?: string) => {
  const response = await api.get('/reports/pm/compliance', {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
};

export const getInventoryValue = async () => {
  const response = await api.get('/reports/inventory/value');
  return response.data;
};

export const getMTBFMTTR = async (assetId?: number) => {
  const response = await api.get('/reports/mtbf-mttr', {
    params: { asset_id: assetId },
  });
  return response.data;
};

// Report Generation
export const getReportTypes = async () => {
  const response = await api.get('/reports/report-types');
  return response.data;
};

export interface ReportParams {
  format?: 'json' | 'pdf' | 'excel' | 'csv';
  start_date?: string;
  end_date?: string;
  asset_id?: number;
  status?: string;
  priority?: string;
  work_type?: string;
  assigned_to?: number;
  criticality?: string;
  storeroom_id?: number;
}

export const generateReport = async (reportType: string, params: ReportParams = {}) => {
  const response = await api.get(`/reports/generate/${reportType}`, {
    params,
    responseType: params.format && params.format !== 'json' ? 'blob' : 'json',
  });
  return response;
};

export const downloadReport = async (reportType: string, params: ReportParams = {}) => {
  const response = await api.get(`/reports/generate/${reportType}`, {
    params,
    responseType: 'blob',
  });

  // Get filename from content-disposition header or generate one
  const contentDisposition = response.headers['content-disposition'];
  let filename = `${reportType}_report`;
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  } else {
    const ext = params.format === 'pdf' ? 'pdf' : params.format === 'excel' ? 'xlsx' : 'csv';
    filename = `${reportType}_${params.start_date || 'report'}_${params.end_date || ''}.${ext}`;
  }

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// Users
export const getUsers = async (params?: Record<string, unknown>) => {
  const response = await api.get('/users', { params });
  return response.data;
};

export const createUser = async (data: Record<string, unknown>) => {
  const response = await api.post('/users', data);
  return response.data;
};

export const updateUser = async (id: number, data: Record<string, unknown>) => {
  const response = await api.put(`/users/${id}`, data);
  return response.data;
};

// Auth - Profile
export const changePassword = async (currentPassword: string, newPassword: string) => {
  const response = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

export const createApiKey = async (name: string, expiresInDays?: number) => {
  const response = await api.post('/auth/api-keys', {
    name,
    expires_in_days: expiresInDays,
  });
  return response.data;
};

export const getApiKeys = async () => {
  const response = await api.get('/auth/api-keys');
  return response.data;
};

export const revokeApiKey = async (keyId: number) => {
  const response = await api.delete(`/auth/api-keys/${keyId}`);
  return response.data;
};

// Audit Logs
export const getAuditLogs = async (params?: {
  entity_type?: string;
  entity_id?: number;
  action?: string;
  user_id?: number;
  start_date?: string;
  end_date?: string;
  search?: string;
  page?: number;
  page_size?: number;
}) => {
  const response = await api.get('/audit-logs', { params });
  return response.data;
};

export const getEntityAuditLogs = async (entityType: string, entityId: number, params?: {
  page?: number;
  page_size?: number;
}) => {
  const response = await api.get(`/audit-logs/entity/${entityType}/${entityId}`, { params });
  return response.data;
};

export const getAuditStats = async (days = 30) => {
  const response = await api.get('/audit-logs/stats', { params: { days } });
  return response.data;
};
