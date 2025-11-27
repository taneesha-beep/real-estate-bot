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

const COLORS = ['#899878', '#222725', '#e4e6c3', '#121113', '#f7f7f2'];

export default function TrendChart({ title, data }) {
  if (!data) return null;

  const labels = data.labels;
  const datasets = data.datasets;

  // Convert to Recharts format
  const chartData = labels.map((year, i) => {
    const row = { year };
    datasets.forEach((ds) => {
      row[ds.area] = ds.values[i];
    });
    return row;
  });

  return (
    <div className="card mt-4 shadow-sm chart-card">
      <div className="card-body">
        <div className="chart-header">
          <h5 className="card-title">{title}</h5>
        </div>
        
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(137, 152, 120, 0.2)" />
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
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '2px solid #899878',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
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
                  strokeWidth={3}
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