import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Box, Heading } from '@chakra-ui/react';

interface DataPoint {
  date: string;
  score: number;
}

interface SentimentChartProps {
  data: DataPoint[];
}

export default function SentimentChart({ data }: SentimentChartProps) {
  if (!data || data.length === 0) return null;

  return (
    <Box>
      <Heading size="sm" mb={3}>
        Sentiment Timeline
      </Heading>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="date" stroke="#888" fontSize={12} />
          <YAxis domain={[0, 1]} stroke="#888" fontSize={12} />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid #333',
              borderRadius: '8px',
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#4ade80"
            strokeWidth={2}
            dot={{ fill: '#4ade80', r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}
