import { useState } from 'react';
import { Box, Button, Field, Input, Stack } from '@chakra-ui/react';
import { Search } from 'lucide-react';
import type { TimeRange } from '../../../shared/types';

interface AnalysisFormProps {
  onSubmit: (query: string, timeRange: TimeRange) => void;
  loading: boolean;
}

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: 'day', label: 'Past 24h' },
  { value: 'week', label: 'Past 7 days' },
  { value: 'month', label: 'Past 30 days' },
  { value: 'year', label: 'Past year' },
];

export default function AnalysisForm({ onSubmit, loading }: AnalysisFormProps) {
  const [query, setQuery] = useState('');
  const [timeRange, setTimeRange] = useState<TimeRange>('week');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setError('Query must be at least 3 characters');
      return;
    }
    setError('');
    onSubmit(trimmed, timeRange);
  };

  return (
    <form onSubmit={handleSubmit}>
      <Stack direction="row" gap={3}>
        <Field.Root invalid={!!error} flex={1}>
          <Input
            placeholder="Enter a topic to analyze (e.g., 'iPhone 16 reviews')"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (error) setError('');
            }}
            size="lg"
            disabled={loading}
          />
          {error && <Field.ErrorText>{error}</Field.ErrorText>}
        </Field.Root>
        <Box>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
            disabled={loading}
            style={{
              height: '48px',
              padding: '0 12px',
              borderRadius: '8px',
              border: '1px solid var(--chakra-colors-border)',
              background: 'transparent',
              color: 'inherit',
              fontSize: '14px',
              cursor: 'pointer',
              minWidth: '140px',
            }}
          >
            {TIME_RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </Box>
        <Button
          className="btn-silicone"
          type="submit"
          colorPalette="blue"
          size="lg"
          loading={loading}
          loadingText="Analyzing..."
          disabled={loading}
        >
          <Search size={18} />
          Analyze
        </Button>
      </Stack>
    </form>
  );
}
