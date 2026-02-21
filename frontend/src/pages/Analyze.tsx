import { useState, useEffect, useCallback } from 'react';
import { Badge, Box, Button, Flex, Heading, Text, Stack, Progress } from '@chakra-ui/react';
import type { TrendReport, TimeRange } from '../../../shared/types';
import { analyzeQuery } from '../lib/api';
import { toaster } from '../lib/toaster';
import AnalysisForm from '../components/AnalysisForm';
import ReportViewer from '../components/ReportViewer';
import { RefreshCw, Zap } from 'lucide-react';

const PROGRESS_STAGES = [
  'Understanding query...',
  'Fetching data from sources...',
  'Cleaning noise...',
  'Analyzing with AI...',
  'Generating report...',
];

const STORAGE_KEY = 'smia_analyze_report';
const REFRESH_FLAG = 'smia_analyze_refreshing';

export default function Analyze() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<TrendReport | null>(() => {
    // On mount: restore from sessionStorage only if it's a page refresh
    if (sessionStorage.getItem(REFRESH_FLAG)) {
      sessionStorage.removeItem(REFRESH_FLAG);
      try {
        const cached = sessionStorage.getItem(STORAGE_KEY);
        return cached ? JSON.parse(cached) : null;
      } catch {
        return null;
      }
    }
    // Navigation: clear cache and start fresh
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  });
  const [isCached, setIsCached] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const [lastTimeRange, setLastTimeRange] = useState<TimeRange>('week');
  const [stage, setStage] = useState(0);

  // Set refresh flag on beforeunload so we know it's a reload, not navigation
  useEffect(() => {
    const onBeforeUnload = () => {
      sessionStorage.setItem(REFRESH_FLAG, '1');
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, []);

  // Persist report to sessionStorage whenever it changes
  const updateReport = useCallback((r: TrendReport | null) => {
    setReport(r);
    if (r) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(r));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const handleAnalyze = async (
    query: string,
    timeRange: TimeRange,
    forceRefresh: boolean = false,
  ) => {
    setLoading(true);
    updateReport(null);
    setIsCached(false);
    setLastQuery(query);
    setLastTimeRange(timeRange);
    setStage(0);

    const interval = setInterval(() => {
      setStage((s) => Math.min(s + 1, PROGRESS_STAGES.length - 1));
    }, 3000);

    try {
      const result = await analyzeQuery(query, timeRange, forceRefresh);
      updateReport(result.report);
      setIsCached(result.cached);
      if (result.cached) {
        toaster.success({ title: 'Loaded from cache (instant)' });
      } else {
        toaster.success({ title: 'Analysis complete' });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      toaster.error({ title: 'Analysis failed', description: message });
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  };

  const handleRegenerate = () => {
    if (lastQuery) {
      handleAnalyze(lastQuery, lastTimeRange, true);
    }
  };

  return (
    <Box>
      <Stack gap={6}>
        <Box>
          <Heading size="xl" mb={2}>
            Analyze a Topic
          </Heading>
          <Text color="fg.muted">
            Enter a product, trend, or topic to get AI-powered intelligence
            from Reddit, YouTube, and Amazon.
          </Text>
        </Box>

        <AnalysisForm onSubmit={handleAnalyze} loading={loading} />

        {loading && (
          <Stack gap={3}>
            <Progress.Root
              value={((stage + 1) / PROGRESS_STAGES.length) * 100}
            >
              <Progress.Track>
                <Progress.Range />
              </Progress.Track>
            </Progress.Root>
            <Text fontSize="sm" color="fg.muted" textAlign="center">
              {PROGRESS_STAGES[stage]}
            </Text>
          </Stack>
        )}

        {report && (
          <>
            {isCached && (
              <Flex alignItems="center" gap={3}>
                <Badge colorPalette="yellow" size="lg">
                  <Zap size={14} />
                  Cached Result
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleRegenerate}
                  disabled={loading}
                >
                  <RefreshCw size={14} />
                  Regenerate
                </Button>
              </Flex>
            )}
            <ReportViewer report={report} />
          </>
        )}
      </Stack>
    </Box>
  );
}
