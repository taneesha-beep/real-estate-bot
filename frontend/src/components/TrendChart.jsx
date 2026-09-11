import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

// Earthy series colors in a fixed order; each is >= 3:1 on the white card and
// adjacent pairs stay distinguishable with common color-vision deficiencies.
const COLORS = ['#5f8a2c', '#2f78a8', '#c4572a', '#8e4a9a', '#b88a00'];

export default function TrendChart({ title, data }) {
  if (!data) return null;

  const labels = data.labels ?? [];
  const datasets = data.datasets ?? [];
  // Missing years arrive as null and are drawn as gaps; an all-null chart is empty.
  const hasValues = datasets.some((ds) => ds.values.some((v) => v != null));

  if (!hasValues) {
    return (
      <div className="card mt-4 chart-card">
        <div className="card-body">
          <div className="chart-header">
            <h2 className="card-title">{title}</h2>
          </div>
          <p className="table-info mb-0">No data available to chart for this query.</p>
        </div>
      </div>
    );
  }

  // Convert to Recharts format
  const chartData = labels.map((year, i) => {
    const row = { year };
    datasets.forEach((ds) => {
      row[ds.area] = ds.values[i];
    });
    return row;
  });

  return (
    <div className="card mt-4 chart-card">
      <div className="card-body">
        <div className="chart-header">
          <h2 className="card-title">{title}</h2>
        </div>
        
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e6eb" />
              <XAxis 
                dataKey="year" 
                stroke="#222725"
                style={{ fontSize: '0.9rem', fontWeight: 500 }}
              />
              <YAxis 
                stroke="#222725"
                style={{ fontSize: '0.9rem', fontWeight: 500 }}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd2da',
                  borderRadius: '4px',
                  boxShadow: 'none'
                }}
                labelStyle={{ color: '#121113', fontWeight: 600 }}
              />
              <Legend 
                wrapperStyle={{
                  paddingTop: '20px',
                  fontSize: '0.95rem',
                  fontWeight: 500
                }}
              />
              {datasets.map((ds, index) => (
                <Line
                  key={ds.area}
                  type="monotone"
                  dataKey={ds.area}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={2}
                  isAnimationActive={false}
                  dot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
                  activeDot={{ r: 6, strokeWidth: 2 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}