import type {
  AnalyzeResponse,
  ReportsListResponse,
  TrendReport,
  BindCodeResponse,
} from '../../../shared/types';
import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function analyzeQuery(
  query: string,
  timeRange: string = 'week',
  forceRefresh: boolean = false,
): Promise<AnalyzeResponse> {
  return apiClient<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      query,
      time_range: timeRange,
      force_refresh: forceRefresh,
    }),
  });
}

export interface ReportsParams {
  page?: number;
  per_page?: number;
  sentiment?: string;
  source?: string;
  search?: string;
  from_date?: string;
  to_date?: string;
}

export async function getReports(
  params: ReportsParams = {}
): Promise<ReportsListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') searchParams.set(k, String(v));
  });
  const qs = searchParams.toString();
  return apiClient<ReportsListResponse>(`/reports${qs ? `?${qs}` : ''}`);
}

export async function getReport(id: string): Promise<TrendReport> {
  return apiClient<TrendReport>(`/reports/${id}`);
}

export async function deleteReport(id: string): Promise<void> {
  return apiClient<void>(`/reports/${id}`, { method: 'DELETE' });
}

export async function getBindCode(): Promise<BindCodeResponse> {
  return apiClient<BindCodeResponse>('/bind/code');
}

// ---------------------------------------------------------------------------
// AI Daily Report
// ---------------------------------------------------------------------------

export async function getDigestAccessStatus(): Promise<string> {
  const data = await apiClient<{ access: string }>('/ai-daily-report/status');
  return data.access;
}

export async function getTodayDigest(): Promise<{
  status: string;
  digest_id: string;
  digest?: DailyDigest;
  claimed?: boolean;
}> {
  return apiClient('/ai-daily-report/today');
}

export async function getDigest(id: string): Promise<{ digest: DailyDigest }> {
  return apiClient(`/ai-daily-report/${id}`);
}

export async function listDigests(
  page = 1,
  perPage = 20,
): Promise<{ digests: DailyDigest[]; total: number; page: number; per_page: number }> {
  return apiClient(`/ai-daily-report/list?page=${page}&per_page=${perPage}`);
}

export async function requestDigestAccess(
  email: string,
  reason: string,
): Promise<{ status: string }> {
  return apiClient('/ai-daily-report/access-request', {
    method: 'POST',
    body: JSON.stringify({ email, reason }),
  });
}

export async function createShareToken(
  digestId: string,
): Promise<{ token: string; url: string; expires_at: string }> {
  return apiClient(`/ai-daily-report/share?digest_id=${digestId}`, {
    method: 'POST',
  });
}

export async function getSharedDigest(
  token: string,
): Promise<{ digest: DailyDigest }> {
  return apiClient(`/ai-daily-report/shared/${token}`);
}

// Bookmarks
export async function getBookmarks(page = 1): Promise<{ bookmarks: Bookmark[] }> {
  return apiClient(`/bookmarks/?page=${page}`);
}

export async function createBookmark(
  digestId: string,
  itemUrl: string,
  itemTitle: string,
): Promise<{ bookmark: Bookmark }> {
  return apiClient('/bookmarks/', {
    method: 'POST',
    body: JSON.stringify({ digest_id: digestId, item_url: itemUrl, item_title: itemTitle }),
  });
}

export async function deleteBookmark(id: string): Promise<void> {
  return apiClient(`/bookmarks/${id}`, { method: 'DELETE' });
}

// Feedback
export async function voteFeedback(
  digestId: string,
  itemUrl: string,
  vote: number,
): Promise<{ feedback: Feedback }> {
  return apiClient('/feedback/vote', {
    method: 'POST',
    body: JSON.stringify({ digest_id: digestId, item_url: itemUrl, vote }),
  });
}

export async function getDigestFeedback(
  digestId: string,
): Promise<{ votes: Feedback[] }> {
  return apiClient(`/feedback/digest/${digestId}`);
}

// Admin
export async function getAccessRequests(
  status?: string,
): Promise<{ requests: AccessRequest[] }> {
  const qs = status ? `?status=${status}` : '';
  return apiClient(`/admin/requests${qs}`);
}

export async function approveRequest(id: string): Promise<{ status: string }> {
  return apiClient(`/admin/requests/${id}/approve`, { method: 'POST' });
}

export async function rejectRequest(
  id: string,
  reason?: string,
): Promise<{ status: string }> {
  return apiClient(`/admin/requests/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function getAdmins(): Promise<{ admins: Admin[] }> {
  return apiClient('/admin/admins');
}

export async function addAdmin(email: string): Promise<{ admin: Admin }> {
  return apiClient(`/admin/admins?email=${encodeURIComponent(email)}`, {
    method: 'POST',
  });
}

export async function removeAdmin(id: string): Promise<void> {
  return apiClient(`/admin/admins/${id}`, { method: 'DELETE' });
}

// Types for digest API responses (lightweight, used by API layer only)
interface DailyDigest {
  id: string;
  digest_date: string;
  status: string;
  executive_summary?: string;
  items?: DigestItemData[];
  top_highlights?: string[];
  trending_keywords?: string[];
  category_counts?: Record<string, number>;
  source_counts?: Record<string, number>;
  total_items?: number;
  source_health?: Record<string, string>;
  model_used?: string;
  processing_time_seconds?: number;
  created_at?: string;
}

interface DigestItemData {
  title: string;
  url: string;
  source: string;
  category: string;
  importance: number;
  why_it_matters: string;
  also_on?: string[];
  snippet?: string;
  author?: string;
}

interface Bookmark {
  id: string;
  user_id: string;
  digest_id: string;
  item_url: string;
  item_title?: string;
  created_at: string;
}

interface Feedback {
  id: string;
  user_id: string;
  digest_id: string;
  item_url: string;
  vote: number;
}

interface AccessRequest {
  id: string;
  user_id: string;
  email: string;
  reason: string;
  status: string;
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  created_at: string;
}

interface Admin {
  id: string;
  user_id: string;
  email: string;
  created_at: string;
}
