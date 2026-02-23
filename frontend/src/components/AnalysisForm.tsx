import { useState, useRef, useEffect } from 'react';
import { Box, Button, Field } from '@chakra-ui/react';
import { Search, ChevronDown, Check, Clock } from 'lucide-react';
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
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedLabel =
    TIME_RANGE_OPTIONS.find((o) => o.value === timeRange)?.label ?? 'Past 7 days';

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      <Box className="neu-surface">
        {/* Mobile: stacked | Desktop ≥13": single row */}
        <div className="neu-form-layout">
          {/* Neomorphic Search Input */}
          <Field.Root invalid={!!error} className="neu-form-input">
            <input
              className="neu-input"
              placeholder="Enter a topic to analyze (e.g., 'iPhone 16 reviews')"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (error) setError('');
              }}
              disabled={loading}
              style={{ width: '100%', height: '50px' }}
            />
            {error && <Field.ErrorText mt={1}>{error}</Field.ErrorText>}
          </Field.Root>

          {/* Neomorphic Accordion Dropdown */}
          <div className="neu-accordion neu-form-dropdown" ref={dropdownRef}>
            <button
              type="button"
              className="neu-accordion-trigger"
              data-open={dropdownOpen}
              onClick={() => !loading && setDropdownOpen((o) => !o)}
              disabled={loading}
              style={{ height: '50px' }}
            >
              <Clock size={14} style={{ flexShrink: 0, opacity: 0.6 }} />
              <span>{selectedLabel}</span>
              <ChevronDown
                className="neu-accordion-chevron"
                data-open={dropdownOpen}
              />
            </button>

            {dropdownOpen && (
              <div className="neu-accordion-panel">
                {TIME_RANGE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className="neu-accordion-option"
                    data-selected={opt.value === timeRange}
                    onClick={() => {
                      setTimeRange(opt.value);
                      setDropdownOpen(false);
                    }}
                  >
                    {opt.value === timeRange && <Check size={14} />}
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Neomorphic Analyze Button */}
          <Button
            className="btn-neu neu-form-btn"
            type="submit"
            size="lg"
            loading={loading}
            loadingText="Analyzing..."
            disabled={loading}
            style={{ height: '50px' }}
          >
            <Search size={18} />
            Analyze
          </Button>
        </div>
      </Box>
    </form>
  );
}
