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
