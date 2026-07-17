import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Forecast } from '../types'

interface RainProbabilityChartProps {
  forecasts: Forecast[]
}

const COLORS = { low: '#63a89b', moderate: '#e2a53b', high: '#db685c' } as const
const tooltipStyle = { borderRadius: 12, border: '1px solid #dde5e1' }

function barColor(probability: number): string {
  if (probability >= 0.7) return COLORS.high
  if (probability >= 0.4) return COLORS.moderate
  return COLORS.low
}

export function RainProbabilityChart({ forecasts }: RainProbabilityChartProps) {
  const data = forecasts.map((forecast) => ({
    horizon: `${forecast.horizon_hours}h`,
    probability: Math.round(forecast.rain_probability * 100),
  }))
  return (
    <article className="panel chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Precipitation outlook</p>
          <h2>Rain probability</h2>
        </div>
        <span className="unit-label">%</span>
      </div>
      <div className="chart-container" aria-label="Rain probability bar chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8eeeb" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="horizon" axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} />
            <YAxis width={38} domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} />
            <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value}%`, 'Rain probability']} />
            <Bar dataKey="probability" radius={[7, 7, 2, 2]} maxBarSize={46}>
              {data.map((entry) => (
                <Cell key={entry.horizon} fill={barColor(entry.probability / 100)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}
