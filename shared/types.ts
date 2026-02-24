export type Sentiment = 'Positive' | 'Negative' | 'Neutral';

export interface TopDiscussion {
  title: string;
  url: string;
  source: 'reddit' | 'youtube' | 'amazon';
  score?: number;
  snippet?: string;
}

export interface TrendReport {
  topic: string;
  sentiment: Sentiment;
  sentiment_score: number;
  summary: string;
  key_insights: string[];
  top_discussions: TopDiscussion[];
  keywords: string[];
  source_breakdown: Record<string, number>;
  charts_data: {
    sentiment_timeline?: Array<{ date: string; score: number }>;
    source_distribution?: Array<{ source: string; count: number }>;
  };
  id?: string;
  user_id?: string;
  query?: string;
  source?: 'web' | 'telegram';
  processing_time_seconds?: number;
  langfuse_trace_id?: string;
  token_usage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  created_at?: string;
}

export type TimeRange = 'day' | 'week' | 'month' | 'year';

export interface AnalyzeRequest {
  query: string;
  time_range?: TimeRange;
  force_refresh?: boolean;
}

export interface AnalyzeResponse {
  report: TrendReport;
  message: string;
  cached: boolean;
}

export interface ReportsListResponse {
  reports: TrendReport[];
  total: number;
  page: number;
  per_page: number;
}

export interface BindCodeResponse {
  bind_code: string;
  expires_at: string;
}

export interface BindConfirmRequest {
  telegram_user_id: number;
  bind_code: string;
}

// --- AI Daily Digest types ---

export type DigestCategory =
  | 'Breakthrough'
  | 'Research'
  | 'Tooling'
  | 'Open Source'
  | 'Infrastructure'
  | 'Product'
  | 'Policy'
  | 'Safety'
  | 'Other';

export type DigestStatus = 'collecting' | 'analyzing' | 'completed' | 'failed' | 'not_found';

export type AccessRequestStatus = 'pending' | 'approved' | 'rejected';

export type DigestAccessLevel = 'admin' | 'approved' | 'pending' | 'rejected' | 'none';

export interface DigestItem {
  title: string;
  url: string;
  source: string;
  category: DigestCategory;
  importance: number; // 1-5
  why_it_matters: string;
  also_on: string[];
}

export interface DailyDigest {
  id: string;
  digest_date: string;
  status: DigestStatus;
  executive_summary: string;
  items: DigestItem[];
  top_highlights: string[];
  trending_keywords: string[];
  category_counts: Record<string, number>;
  source_counts: Record<string, number>;
  source_health: Record<string, string>;
  total_items: number;
  model_used: string;
  processing_time_seconds: number;
  langfuse_trace_id?: string;
  token_usage?: Record<string, number>;
  prompt_version?: string;
  created_at: string;
  updated_at: string;
}

export interface DigestStatusResponse {
  status: DigestStatus;
  digest_id?: string;
  digest?: DailyDigest;
}

export interface AccessRequestCreate {
  reason: string;
}

export interface AccessRequestResponse {
  id: string;
  email: string;
  reason: string;
  status: AccessRequestStatus;
  rejection_reason?: string;
  created_at: string;
}

export interface BookmarkCreate {
  digest_id: string;
  item_url: string;
  item_title?: string;
}

export interface FeedbackCreate {
  digest_id: string;
  item_url?: string;
  vote: 1 | -1;
}

export interface DigestListResponse {
  digests: DailyDigest[];
  total: number;
  page: number;
  per_page: number;
}

export interface ShareTokenResponse {
  token: string;
  expires_at: string;
  url: string;
}
