import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Box, Heading } from '@chakra-ui/react';
import { useColorMode } from '../../hooks/useColorMode';

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

  const { colorMode } = useColorMode();
  const isDark = colorMode === 'dark';

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
              background: isDark ? '#1a1a2e' : '#ffffff',
              color: isDark ? '#e2e8f0' : '#1a202c',
              border: isDark ? '1px solid #333' : '1px solid #e2e8f0',
              borderRadius: '8px',
            }}
            cursor={{ fill: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
}
