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

interface TemperatureChartProps {
  forecasts: HourlyForecast[]
  timezone: string
}

const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid #dde5e1',
  boxShadow: '0 8px 24px rgba(26, 48, 43, 0.08)',
}

function wholeDegrees(value: unknown): string {
  const temperature = Number(value)
  return Number.isFinite(temperature) ? `${Math.round(temperature)}°C` : '—'
}

function amPmTime(timestamp: unknown, timezone: string): string {
  const date = new Date(String(timestamp))
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-IN', { hour: 'numeric', hour12: true, timeZone: timezone }).format(date)
}

export function TemperatureChart({ forecasts, timezone }: TemperatureChartProps) {
  const data = forecasts.map((forecast) => ({
    time: forecast.timestamp,
    temperature: forecast.temperature,
  }))

  return (
    <article className="panel chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Temperature outlook · next 24 hours</p>
          <h2>Forecast trend</h2>
        </div>
        <span className="unit-label">°C</span>
      </div>
      <div className="chart-container" aria-label="Temperature prediction line chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="temperature-by-height" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#cf4d43" />
                <stop offset="36%" stopColor="#e49a42" />
                <stop offset="68%" stopColor="#22927d" />
                <stop offset="100%" stopColor="#427ec7" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e8eeeb" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#6d7c77', fontSize: 10 }} tickFormatter={(value) => amPmTime(value, timezone)} interval={2} />
            <YAxis width={42} axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} tickFormatter={wholeDegrees} domain={['dataMin - 2', 'dataMax + 2']} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(value) => amPmTime(value, timezone)} formatter={(value) => [wholeDegrees(value), 'Temperature']} />
            <Line type="monotone" dataKey="temperature" stroke="url(#temperature-by-height)" strokeWidth={3} dot={{ r: 3.5, fill: '#176b5b', stroke: '#f7faf8', strokeWidth: 2 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}
