import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HourlyForecast } from '../types'

interface RainProbabilityChartProps {
  forecasts: HourlyForecast[]
}

const tooltipStyle = { borderRadius: 12, border: '1px solid #dde5e1' }

function amPmTime(timestamp: unknown): string {
  const hour = Number(String(timestamp).slice(11, 13))
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) return '—'
  const displayHour = hour % 12 || 12
  return `${displayHour} ${hour < 12 ? 'AM' : 'PM'}`
}

export function RainProbabilityChart({ forecasts }: RainProbabilityChartProps) {
  const data = forecasts.map((forecast) => ({
    time: forecast.timestamp,
    probability: Math.round(forecast.precipitation_probability),
  }))

  return (
    <article className="panel chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Precipitation outlook · next 24 hours</p>
          <h2>Rain probability</h2>
        </div>
        <span className="unit-label">%</span>
      </div>
      <div className="chart-container" aria-label="Rain probability line chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="rain-probability-by-height" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d65f54" />
                <stop offset="52%" stopColor="#e0aa42" />
                <stop offset="100%" stopColor="#4eaa9c" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e8eeeb" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} tickFormatter={amPmTime} interval={2} />
            <YAxis width={38} domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={amPmTime} formatter={(value) => [`${value ?? 0}%`, 'Rain probability']} />
            <Line type="monotone" dataKey="probability" stroke="url(#rain-probability-by-height)" strokeWidth={3} dot={{ r: 5, fill: '#5ba89a', stroke: '#f7faf8', strokeWidth: 3 }} activeDot={{ r: 7 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}
