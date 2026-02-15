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

export async function analyzeQuery(query: string): Promise<AnalyzeResponse> {
  return apiClient<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify({ query }),
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
