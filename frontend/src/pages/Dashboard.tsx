import { useEffect, useState, useCallback, useRef } from 'react';
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
const CACHE_PREFIX = 'smia_dashboard:';

/** Build a sessionStorage key from current filter params. */
function cacheKey(page: number, sentiment: string, search: string) {
  return `${CACHE_PREFIX}page=${page}&sentiment=${sentiment}&search=${search}`;
}

interface CachedData {
  reports: TrendReport[];
  total: number;
}

/** Try to read cached dashboard data for the given params. */
function readCache(page: number, sentiment: string, search: string): CachedData | null {
  try {
    const raw = sessionStorage.getItem(cacheKey(page, sentiment, search));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Write dashboard data to sessionStorage cache. */
function writeCache(page: number, sentiment: string, search: string, data: CachedData) {
  try {
    sessionStorage.setItem(cacheKey(page, sentiment, search), JSON.stringify(data));
  } catch {
    // sessionStorage full — ignore
  }
}

export default function Dashboard() {
  const [reports, setReports] = useState<TrendReport[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [sentiment, setSentiment] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // Track whether we showed cached data (skip showing skeleton on background refresh)
  const hasCachedData = useRef(false);

  const fetchReports = useCallback(async () => {
    // Check cache first — if hit, show cached data immediately
    const cached = readCache(page, sentiment, search);
    if (cached && cached.reports.length > 0) {
      setReports(cached.reports);
      setTotal(cached.total);
      setLoading(false);
      hasCachedData.current = true;
    } else {
      hasCachedData.current = false;
      setLoading(true);
    }

    // Always fetch fresh data in background
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
      writeCache(page, sentiment, search, { reports: data.reports, total: data.total });
    } catch (err: unknown) {
      // Only show error if we don't have cached data to fall back on
      if (!hasCachedData.current) {
        const msg = err instanceof Error ? err.message : 'Failed to load reports';
        toaster.error({ title: 'Error', description: msg });
      }
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
      // Clear all dashboard caches so deleted report doesn't reappear from stale cache
      for (let i = sessionStorage.length - 1; i >= 0; i--) {
        const key = sessionStorage.key(i);
        if (key?.startsWith(CACHE_PREFIX)) sessionStorage.removeItem(key);
      }
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
