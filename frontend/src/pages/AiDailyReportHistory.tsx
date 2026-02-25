import { useEffect, useState, useCallback } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Badge,
  Box,
  Button,
  Card,
  Flex,
  Heading,
  Link,
  Skeleton,
  Stack,
  Text,
} from '@chakra-ui/react';
import { useDigestPermissions } from '../hooks/useDigestPermissions';
import { listDigests } from '../lib/api';
import { toaster } from '../lib/toaster';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';

const PER_PAGE = 20;

export default function AiDailyReportHistory() {
  const { hasAccess, accessStatus } = useDigestPermissions();
  const [digests, setDigests] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDigests(page, PER_PAGE);
      setDigests(data.digests);
      setTotal(data.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load history';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    if (hasAccess) fetchData();
  }, [hasAccess, fetchData]);

  if (accessStatus === 'loading') {
    return (
      <Box>
        <Heading size="xl" mb={6}>Digest History</Heading>
        <Stack gap={4}>
          {[1, 2, 3].map((i) => <Skeleton key={i} height="80px" />)}
        </Stack>
      </Box>
    );
  }

  if (!hasAccess) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Access Required</Heading>
        <Text color="fg.muted">
          You need digest access to view history.
        </Text>
      </Box>
    );
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <Box>
      <Heading size="xl" mb={6}>Digest History</Heading>

      {loading ? (
        <Stack gap={4}>
          {[1, 2, 3].map((i) => (
            <Card.Root className="glass-panel" key={i} p={4}>
              <Skeleton height="20px" width="40%" mb={2} />
              <Skeleton height="14px" width="80%" />
            </Card.Root>
          ))}
        </Stack>
      ) : digests.length === 0 ? (
        <Box textAlign="center" py={12}>
          <Text fontSize="lg" color="fg.muted">No digests yet</Text>
          <Text color="fg.muted" fontSize="sm" mt={2}>
            Digests are generated daily when you visit the AI Daily Report page.
          </Text>
        </Box>
      ) : (
        <>
          <Stack gap={3}>
            {digests.map((d) => {
              const date = new Date(d.digest_date + 'T00:00:00');
              const formatted = date.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
              });
              const cats = d.category_counts || {};
              const topCats = Object.entries(cats)
                .sort(([, a]: any, [, b]: any) => b - a)
                .slice(0, 3);

              return (
                <Link asChild key={d.id}>
                  <RouterLink to={`/ai-daily-report/history/${d.id}`}>
                    <Card.Root className="glass-panel" p={4} cursor="pointer" _hover={{ opacity: 0.8 }}>
                      <Flex justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
                        <Box>
                          <Flex alignItems="center" gap={2} mb={1}>
                            <Calendar size={14} />
                            <Text fontWeight="medium">{formatted}</Text>
                            <Badge variant="subtle" size="sm">
                              {d.total_items || 0} items
                            </Badge>
                          </Flex>
                          {d.executive_summary && (
                            <Text fontSize="sm" color="fg.muted" lineClamp={1}>
                              {d.executive_summary}
                            </Text>
                          )}
                        </Box>
                        <Flex gap={1}>
                          {topCats.map(([cat, count]: any) => (
                            <Badge key={cat} variant="outline" size="sm">
                              {cat}: {count}
                            </Badge>
                          ))}
                        </Flex>
                      </Flex>
                    </Card.Root>
                  </RouterLink>
                </Link>
              );
            })}
          </Stack>

          {totalPages > 1 && (
            <Flex justifyContent="center" alignItems="center" gap={4} mt={6}>
              <Button
                className="btn-silicone"
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft size={16} />
                Previous
              </Button>
              <Text fontSize="sm" color="fg.muted">
                Page {page} of {totalPages}
              </Text>
              <Button
                className="btn-silicone"
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight size={16} />
              </Button>
            </Flex>
          )}
        </>
      )}
    </Box>
  );
}
