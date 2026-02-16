import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Badge,
  Card,
  Flex,
  Heading,
  IconButton,
  Link,
  Text,
} from '@chakra-ui/react';
import type { TrendReport } from '../../../shared/types';
import { Trash2, Clock } from 'lucide-react';

const SENTIMENT_COLOR: Record<string, string> = {
  Positive: 'green',
  Negative: 'red',
  Neutral: 'gray',
};

interface ReportCardProps {
  report: TrendReport;
  onDelete: (id: string) => void;
}

export default function ReportCard({ report, onDelete }: ReportCardProps) {
  const dateStr = report.created_at
    ? new Date(report.created_at).toLocaleDateString()
    : '';

  return (
    <Card.Root
      className="glass-panel"
      cursor="pointer"
    >
      <Card.Body>
        <Flex justifyContent="space-between" alignItems="flex-start" gap={2}>
          <Link asChild flex={1}>
            <RouterLink to={`/reports/${report.id}`}>
              <Box>
                <Heading size="sm" mb={1}>
                  {report.topic}
                </Heading>
                <Text fontSize="sm" color="fg.muted" lineClamp={2}>
                  {report.summary}
                </Text>
                <Flex mt={3} gap={2} alignItems="center" flexWrap="wrap">
                  <Badge
                    colorPalette={SENTIMENT_COLOR[report.sentiment]}
                    size="sm"
                  >
                    {report.sentiment}
                  </Badge>
                  {report.source && (
                    <Badge variant="outline" size="sm">
                      {report.source}
                    </Badge>
                  )}
                  {dateStr && (
                    <Flex alignItems="center" gap={1} fontSize="xs" color="fg.muted">
                      <Clock size={12} />
                      {dateStr}
                    </Flex>
                  )}
                </Flex>
              </Box>
            </RouterLink>
          </Link>
          <IconButton className="btn-silicone"
            aria-label="Delete report"
            variant="ghost"
            size="sm"
            colorPalette="red"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (report.id) onDelete(report.id);
            }}
          >
            <Trash2 size={16} />
          </IconButton>
        </Flex>
      </Card.Body>
    </Card.Root>
  );
}
