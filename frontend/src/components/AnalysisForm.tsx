import { useState } from 'react';
import { Button, Field, Input, Stack } from '@chakra-ui/react';
import { Search } from 'lucide-react';

interface AnalysisFormProps {
  onSubmit: (query: string) => void;
  loading: boolean;
}

export default function AnalysisForm({ onSubmit, loading }: AnalysisFormProps) {
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setError('Query must be at least 3 characters');
      return;
    }
    setError('');
    onSubmit(trimmed);
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
