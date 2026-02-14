import { useState } from 'react';
import { Box, Heading, Text, Stack, Progress } from '@chakra-ui/react';
import type { TrendReport } from '../../../shared/types';
import { analyzeQuery } from '../lib/api';
import { toaster } from '../lib/toaster';
import AnalysisForm from '../components/AnalysisForm';
import ReportViewer from '../components/ReportViewer';

const PROGRESS_STAGES = [
  'Understanding query...',
  'Fetching data from sources...',
  'Cleaning noise...',
  'Analyzing with AI...',
  'Generating report...',
];

export default function Analyze() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<TrendReport | null>(null);
  const [stage, setStage] = useState(0);

  const handleAnalyze = async (query: string) => {
    setLoading(true);
    setReport(null);
    setStage(0);

    const interval = setInterval(() => {
      setStage((s) => Math.min(s + 1, PROGRESS_STAGES.length - 1));
    }, 3000);

    try {
      const result = await analyzeQuery(query);
      setReport(result.report);
      toaster.success({ title: 'Analysis complete' });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      toaster.error({ title: 'Analysis failed', description: message });
    } finally {
      clearInterval(interval);
      setLoading(false);
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

        {report && <ReportViewer report={report} />}
      </Stack>
    </Box>
  );
}
