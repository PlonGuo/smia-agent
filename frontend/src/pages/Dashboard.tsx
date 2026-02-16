import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Button,
  Card,
  Flex,
  Heading,
  Input,
  Skeleton,
  Stack,
  Text,
  NativeSelect,
} from '@chakra-ui/react';
import type { TrendReport } from '../../../shared/types';
import { getReports, deleteReport, type ReportsParams } from '../lib/api';
import { toaster } from '../lib/toaster';
import ReportCard from '../components/ReportCard';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';

const PER_PAGE = 9;

export default function Dashboard() {
  const [reports, setReports] = useState<TrendReport[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [sentiment, setSentiment] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const params: ReportsParams = {
        page,
        per_page: PER_PAGE,
      };
      if (sentiment) params.sentiment = sentiment;
      if (search) params.search = search;

      const data = await getReports(params);
      setReports(data.reports);
      setTotal(data.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load reports';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoading(false);
    }
  }, [page, sentiment, search]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleDelete = async (id: string) => {
    try {
      await deleteReport(id);
      toaster.success({ title: 'Report deleted' });
      fetchReports();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed';
      toaster.error({ title: 'Error', description: msg });
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <Box>
      <Heading size="xl" mb={6}>
        Dashboard
      </Heading>

      {/* Filters */}
      <Flex gap={4} mb={6} flexWrap="wrap" alignItems="flex-end">
        <form onSubmit={handleSearch}>
          <Flex gap={2}>
            <Input
              placeholder="Search reports..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              size="sm"
              w="250px"
            />
            <Button className="btn-silicone" type="submit" size="sm" variant="outline">
              <Search size={14} />
            </Button>
          </Flex>
        </form>

        <NativeSelect.Root size="sm" w="160px">
          <NativeSelect.Field
            value={sentiment}
            onChange={(e) => {
              setSentiment(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Sentiments</option>
            <option value="Positive">Positive</option>
            <option value="Negative">Negative</option>
            <option value="Neutral">Neutral</option>
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
      </Flex>

      {/* Reports list */}
      {loading ? (
        <Stack gap={4}>
          {[1, 2, 3].map((i) => (
            <Card.Root className="glass-panel" key={i} p={4}>
              <Skeleton height="20px" width="60%" mb={2} />
              <Skeleton height="14px" width="40%" mb={3} />
              <Skeleton height="14px" width="80%" />
            </Card.Root>
          ))}
        </Stack>
      ) : reports.length === 0 ? (
        <Box textAlign="center" py={12}>
          <Text fontSize="lg" color="fg.muted" mb={2}>
            No reports yet
          </Text>
          <Text color="fg.muted" fontSize="sm">
            Go to the Analyze page to create your first report.
          </Text>
        </Box>
      ) : (
        <>
          <Stack gap={4}>
            {reports.map((r) => (
              <ReportCard key={r.id} report={r} onDelete={handleDelete} />
            ))}
          </Stack>

          {totalPages > 1 && (
            <Flex justifyContent="center" alignItems="center" gap={4} mt={6}>
              <Button className="btn-silicone"
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
              <Button className="btn-silicone"
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
