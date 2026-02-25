import { Component, useState } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import {
  Badge,
  Box,
  Button,
  Flex,
  Stack,
  Text,
} from '@chakra-ui/react';
import KanbanCard from './KanbanCard';

interface DigestItem {
  title: string;
  url: string;
  source: string;
  category: string;
  importance: number;
  why_it_matters: string;
  also_on?: string[];
  snippet?: string;
  author?: string;
}

interface Props {
  items: DigestItem[];
}

const CATEGORY_COLORS: Record<string, string> = {
  Breakthrough: 'purple',
  Research: 'blue',
  Tooling: 'teal',
  'Open Source': 'green',
  Infrastructure: 'cyan',
  Product: 'orange',
  Policy: 'yellow',
  Safety: 'red',
  Other: 'gray',
};

const CATEGORY_ORDER = [
  'Breakthrough', 'Research', 'Tooling', 'Open Source',
  'Infrastructure', 'Product', 'Policy', 'Safety', 'Other',
];

export default function KanbanBoard({ items }: Props) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Group items by category
  const grouped: Record<string, DigestItem[]> = {};
  for (const item of items) {
    const cat = item.category || 'Other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(item);
  }

  // Sort items within each category by importance (desc)
  for (const cat of Object.keys(grouped)) {
    grouped[cat].sort((a, b) => b.importance - a.importance);
  }

  // Order categories
  const categories = CATEGORY_ORDER.filter((c) => grouped[c]);

  // Mobile: filter by selected category
  const mobileItems = selectedCategory
    ? grouped[selectedCategory] || []
    : items.sort((a, b) => b.importance - a.importance);

  return (
    <Box>
      {/* Mobile: Category tabs */}
      <Flex
        display={{ base: 'flex', lg: 'none' }}
        gap={2}
        mb={4}
        overflowX="auto"
        pb={2}
        css={{ '&::-webkit-scrollbar': { display: 'none' } }}
      >
        <Button
          className="btn-silicone"
          size="xs"
          variant={selectedCategory === null ? 'subtle' : 'ghost'}
          onClick={() => setSelectedCategory(null)}
          flexShrink={0}
        >
          All ({items.length})
        </Button>
        {categories.map((cat) => (
          <Button
            className="btn-silicone"
            key={cat}
            size="xs"
            variant={selectedCategory === cat ? 'subtle' : 'ghost'}
            onClick={() => setSelectedCategory(cat)}
            flexShrink={0}
          >
            {cat} ({grouped[cat].length})
          </Button>
        ))}
      </Flex>

      {/* Mobile: Filtered list */}
      <Stack display={{ base: 'flex', lg: 'none' }} gap={0}>
        {mobileItems.map((item, i) => (
          <ErrorBoundaryCard key={`${item.url}-${i}`}>
            <KanbanCard item={item} />
          </ErrorBoundaryCard>
        ))}
      </Stack>

      {/* Desktop: Kanban columns */}
      <Flex
        display={{ base: 'none', lg: 'flex' }}
        gap={4}
        overflowX="auto"
        pb={4}
        alignItems="flex-start"
      >
        {categories.map((cat) => (
          <Box
            key={cat}
            minW="280px"
            maxW="320px"
            flex="1"
          >
            <Flex alignItems="center" gap={2} mb={3}>
              <Badge
                colorPalette={CATEGORY_COLORS[cat] || 'gray'}
                variant="subtle"
                size="sm"
              >
                {cat}
              </Badge>
              <Text fontSize="xs" color="fg.muted">
                {grouped[cat].length}
              </Text>
            </Flex>
            <Stack gap={0}>
              {grouped[cat].map((item, i) => (
                <ErrorBoundaryCard key={`${item.url}-${i}`}>
                  <KanbanCard item={item} />
                </ErrorBoundaryCard>
              ))}
            </Stack>
          </Box>
        ))}
      </Flex>
    </Box>
  );
}

/** Minimal error boundary wrapper per card (S8). */
class ErrorBoundaryCard extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('KanbanCard render error:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <Box p={2} borderWidth="1px" borderColor="red.300" borderRadius="md" mb={2}>
          <Text fontSize="xs" color="red.500">Failed to render card</Text>
        </Box>
      );
    }
    return this.props.children;
  }
}
