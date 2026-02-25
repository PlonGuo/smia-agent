import {
  Badge,
  Box,
  Flex,
  Heading,
  Stack,
  Text,
} from '@chakra-ui/react';
import { Calendar, Clock, Hash, Layers } from 'lucide-react';

interface Props {
  digest: {
    digest_date: string;
    executive_summary?: string;
    total_items?: number;
    trending_keywords?: string[];
    processing_time_seconds?: number;
    category_counts?: Record<string, number>;
    source_counts?: Record<string, number>;
  };
}

export default function DigestHeader({ digest }: Props) {
  const date = new Date(digest.digest_date + 'T00:00:00');
  const formattedDate = date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <Box className="glass-panel" p={6} mb={6}>
      <Flex alignItems="flex-start" justifyContent="space-between" flexWrap="wrap" gap={4}>
        <Box flex={1} minW="300px">
          <Flex alignItems="center" gap={2} mb={2}>
            <Calendar size={18} />
            <Heading size="lg">{formattedDate}</Heading>
          </Flex>

          {digest.executive_summary && (
            <Text color="fg.muted" mb={4} maxW="2xl">
              {digest.executive_summary}
            </Text>
          )}

          {/* Trending keywords */}
          {digest.trending_keywords && digest.trending_keywords.length > 0 && (
            <Flex gap={2} flexWrap="wrap" mb={3}>
              <Hash size={14} style={{ marginTop: 4 }} />
              {digest.trending_keywords.map((kw) => (
                <Badge key={kw} variant="subtle" size="sm">
                  {kw}
                </Badge>
              ))}
            </Flex>
          )}
        </Box>

        {/* Stats */}
        <Stack gap={2} minW="150px">
          <Flex alignItems="center" gap={2}>
            <Layers size={14} />
            <Text fontSize="sm" color="fg.muted">
              {digest.total_items || 0} items analyzed
            </Text>
          </Flex>
          {digest.processing_time_seconds && (
            <Flex alignItems="center" gap={2}>
              <Clock size={14} />
              <Text fontSize="sm" color="fg.muted">
                {digest.processing_time_seconds}s processing
              </Text>
            </Flex>
          )}
          {digest.source_counts && (
            <Flex gap={2} flexWrap="wrap">
              {Object.entries(digest.source_counts).map(([src, count]) => (
                <Badge key={src} variant="outline" size="sm">
                  {src}: {count}
                </Badge>
              ))}
            </Flex>
          )}
        </Stack>
      </Flex>
    </Box>
  );
}
