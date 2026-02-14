import {
  Box,
  Badge,
  Card,
  Heading,
  Text,
  Stack,
  Flex,
  Tag,
  Separator,
  Link,
} from '@chakra-ui/react';
import type { TrendReport } from '../../../shared/types';
import SentimentChart from './charts/SentimentChart';
import SourceDistribution from './charts/SourceDistribution';
import { ExternalLink, Clock, Cpu } from 'lucide-react';

const SENTIMENT_COLOR: Record<string, string> = {
  Positive: 'green',
  Negative: 'red',
  Neutral: 'gray',
};

interface ReportViewerProps {
  report: TrendReport;
}

export default function ReportViewer({ report }: ReportViewerProps) {
  const sentimentTimeline = report.charts_data?.sentiment_timeline as
    | Array<{ date: string; score: number }>
    | undefined;

  return (
    <Stack gap={6}>
      {/* Header */}
      <Card.Root>
        <Card.Body>
          <Flex justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={4}>
            <Box>
              <Heading size="lg">{report.topic}</Heading>
              <Flex gap={2} mt={2} alignItems="center">
                <Badge colorPalette={SENTIMENT_COLOR[report.sentiment]}>
                  {report.sentiment}
                </Badge>
                <Text fontSize="sm" color="fg.muted">
                  Score: {(report.sentiment_score * 100).toFixed(0)}%
                </Text>
              </Flex>
            </Box>
            <Flex gap={4} fontSize="sm" color="fg.muted">
              {report.processing_time_seconds && (
                <Flex alignItems="center" gap={1}>
                  <Clock size={14} />
                  {report.processing_time_seconds}s
                </Flex>
              )}
              {report.token_usage?.total && (
                <Flex alignItems="center" gap={1}>
                  <Cpu size={14} />
                  {String(report.token_usage.total)} tokens
                </Flex>
              )}
            </Flex>
          </Flex>
        </Card.Body>
      </Card.Root>

      {/* Summary */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Summary</Heading>
        </Card.Header>
        <Card.Body>
          <Text>{report.summary}</Text>
        </Card.Body>
      </Card.Root>

      {/* Key Insights */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Key Insights</Heading>
        </Card.Header>
        <Card.Body>
          <Stack as="ul" gap={2} pl={4} listStyleType="disc">
            {report.key_insights.map((insight, i) => (
              <Box as="li" key={i}>
                <Text>{insight}</Text>
              </Box>
            ))}
          </Stack>
        </Card.Body>
      </Card.Root>

      {/* Charts */}
      <Flex gap={6} flexWrap="wrap">
        <Box flex={1} minW="300px">
          <Card.Root>
            <Card.Body>
              {sentimentTimeline ? (
                <SentimentChart data={sentimentTimeline} />
              ) : (
                <Text color="fg.muted" fontSize="sm">
                  No sentiment timeline data available
                </Text>
              )}
            </Card.Body>
          </Card.Root>
        </Box>
        <Box flex={1} minW="300px">
          <Card.Root>
            <Card.Body>
              <SourceDistribution data={report.source_breakdown} />
            </Card.Body>
          </Card.Root>
        </Box>
      </Flex>

      {/* Top Discussions */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Top Discussions</Heading>
        </Card.Header>
        <Card.Body>
          <Stack gap={3} separator={<Separator />}>
            {report.top_discussions.map((d, i) => (
              <Flex key={i} justifyContent="space-between" alignItems="center" gap={3}>
                <Box flex={1}>
                  <Link href={d.url} target="_blank" rel="noopener">
                    <Flex alignItems="center" gap={1}>
                      <Text fontWeight="medium">{d.title}</Text>
                      <ExternalLink size={12} />
                    </Flex>
                  </Link>
                  {d.snippet && (
                    <Text fontSize="sm" color="fg.muted" mt={1}>
                      {d.snippet}
                    </Text>
                  )}
                </Box>
                <Flex gap={2} alignItems="center" flexShrink={0}>
                  <Badge variant="subtle">
                    {d.source}
                  </Badge>
                  {d.score != null && (
                    <Text fontSize="sm" color="fg.muted">
                      {d.score}
                    </Text>
                  )}
                </Flex>
              </Flex>
            ))}
          </Stack>
        </Card.Body>
      </Card.Root>

      {/* Keywords */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Keywords</Heading>
        </Card.Header>
        <Card.Body>
          <Flex gap={2} flexWrap="wrap">
            {report.keywords.map((kw) => (
              <Tag.Root key={kw} size="lg" variant="subtle" colorPalette="blue">
                <Tag.Label>{kw}</Tag.Label>
              </Tag.Root>
            ))}
          </Flex>
        </Card.Body>
      </Card.Root>
    </Stack>
  );
}
