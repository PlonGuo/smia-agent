import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Box, Heading } from '@chakra-ui/react';

const COLORS: Record<string, string> = {
  reddit: '#FF4500',
  youtube: '#FF0000',
  amazon: '#FF9900',
};

interface SourceDistributionProps {
  data: Record<string, number>;
}

export default function SourceDistribution({ data }: SourceDistributionProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
    color: COLORS[name] || '#888',
  }));

  if (chartData.length === 0) return null;

  return (
    <Box>
      <Heading size="sm" mb={3}>
        Source Distribution
      </Heading>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={90}
            dataKey="value"
            label={false}
          >
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid #333',
              borderRadius: '8px',
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
}
