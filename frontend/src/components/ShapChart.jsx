import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function ShapChart({ features }) {
  // Sort features by absolute importance
  const sortedFeatures = [...features].sort(
    (a, b) => Math.abs(b.importance) - Math.abs(a.importance)
  );

  // Format for display
  const chartData = sortedFeatures.map((f) => ({
    name: formatFeatureName(f.name),
    value: f.importance,
    fullName: f.name,
  }));

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={250}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <XAxis
            type="number"
            stroke="#6B7280"
            fontSize={12}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#6B7280"
            fontSize={12}
            width={90}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.value >= 0 ? '#3B82F6' : '#EF4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex justify-center space-x-6 mt-4">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-blue-500 rounded" />
          <span className="text-sm text-gray-600">Increases Risk</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded" />
          <span className="text-sm text-gray-600">Decreases Risk</span>
        </div>
      </div>

      {/* Feature explanation */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Feature Explanation</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          {chartData.slice(0, 3).map((f) => (
            <li key={f.fullName}>
              <span className="font-medium">{f.name}:</span>{' '}
              {getFeatureExplanation(f.fullName, f.value)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900 text-white px-3 py-2 rounded-lg shadow-lg">
        <p className="font-medium">{data.fullName}</p>
        <p className="text-sm text-gray-300">
          Impact: {data.value >= 0 ? '+' : ''}{(data.value * 100).toFixed(1)}%
        </p>
      </div>
    );
  }
  return null;
}

function formatFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .slice(0, 15);
}

function getFeatureExplanation(name, value) {
  const explanations = {
    access_frequency: value > 0
      ? 'High access frequency indicates unusual activity'
      : 'Normal access frequency',
    off_hours_ratio: value > 0
      ? 'Significant off-hours activity detected'
      : 'Activity within normal hours',
    cross_dept_access: value > 0
      ? 'Accessing documents outside their department'
      : 'Accessing documents within their department',
    download_volume: value > 0
      ? 'Higher than normal download volume'
      : 'Normal download volume',
    sensitivity_accessed: value > 0
      ? 'Accessing highly sensitive documents'
      : 'Accessing appropriately classified documents',
  };
  return explanations[name] || `Impact: ${(value * 100).toFixed(1)}%`;
}

export default ShapChart;
