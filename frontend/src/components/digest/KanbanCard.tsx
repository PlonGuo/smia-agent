import {
  Badge,
  Box,
  Card,
  Flex,
  Link,
  Text,
} from '@chakra-ui/react';
import { ExternalLink, Star } from 'lucide-react';

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
  item: DigestItem;
}

const SOURCE_COLORS: Record<string, string> = {
  arxiv: 'red',
  github: 'gray',
  rss: 'orange',
  bluesky: 'blue',
};

export default function KanbanCard({ item }: Props) {
  return (
    <Card.Root className="glass-panel" p={3} mb={2}>
      <Flex justifyContent="space-between" alignItems="flex-start" gap={2}>
        <Box flex={1} minW={0}>
          <Link href={item.url} target="_blank" rel="noopener noreferrer">
            <Text fontWeight="medium" fontSize="sm" lineClamp={2}>
              {item.title}
              <ExternalLink size={12} style={{ display: 'inline', marginLeft: 4 }} />
            </Text>
          </Link>
        </Box>
        <Flex gap={0.5} flexShrink={0}>
          {Array.from({ length: item.importance }, (_, i) => (
            <Star key={i} size={10} fill="currentColor" />
          ))}
        </Flex>
      </Flex>

      <Text fontSize="xs" color="fg.muted" mt={1} lineClamp={2}>
        {item.why_it_matters}
      </Text>

      <Flex gap={1} mt={2} flexWrap="wrap" alignItems="center">
        <Badge
          variant="subtle"
          size="sm"
          colorPalette={SOURCE_COLORS[item.source] || 'gray'}
        >
          {item.source}
        </Badge>
        {item.author && (
          <Text fontSize="xs" color="fg.muted">
            {item.author}
          </Text>
        )}
        {item.also_on && item.also_on.length > 0 && (
          <Text fontSize="xs" color="fg.muted">
            +{item.also_on.join(', ')}
          </Text>
        )}
      </Flex>
    </Card.Root>
  );
}
