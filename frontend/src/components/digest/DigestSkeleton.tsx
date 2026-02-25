import {
  Box,
  Flex,
  Heading,
  Skeleton,
  Stack,
  Text,
} from '@chakra-ui/react';
import { Loader2 } from 'lucide-react';

interface Props {
  status?: string;
}

const STAGE_LABELS: Record<string, string> = {
  collecting: 'Collecting data from arXiv, GitHub, RSS, Bluesky...',
  analyzing: 'AI is analyzing and categorizing items...',
  failed: 'Generation failed. Please try again later.',
};

export default function DigestSkeleton({ status }: Props) {
  const label = status ? STAGE_LABELS[status] || 'Preparing digest...' : 'Loading...';
  const isFailed = status === 'failed';

  return (
    <Box maxW="4xl" mx="auto" py={8}>
      <Flex alignItems="center" gap={3} mb={8} justifyContent="center">
        {!isFailed && (
          <Box animation="spin 1s linear infinite" display="inline-flex">
            <Loader2 size={24} />
          </Box>
        )}
        <Heading size="lg">{isFailed ? 'Generation Failed' : 'Generating Digest'}</Heading>
      </Flex>

      <Text textAlign="center" color="fg.muted" mb={8}>
        {label}
      </Text>

      {!isFailed && (
        <Stack gap={4}>
          {/* Fake kanban columns */}
          <Flex gap={4} flexWrap="wrap" justifyContent="center">
            {['Research', 'Tooling', 'Open Source'].map((cat) => (
              <Box key={cat} w="280px">
                <Skeleton height="20px" width="120px" mb={3} />
                <Stack gap={3}>
                  <Skeleton height="100px" borderRadius="md" />
                  <Skeleton height="80px" borderRadius="md" />
                </Stack>
              </Box>
            ))}
          </Flex>
        </Stack>
      )}
    </Box>
  );
}
