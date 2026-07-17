import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Forecast } from '../types'

interface TemperatureChartProps {
  forecasts: Forecast[]
}

const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid #dde5e1',
  boxShadow: '0 8px 24px rgba(26, 48, 43, 0.08)',
}

export function TemperatureChart({ forecasts }: TemperatureChartProps) {
  const data = forecasts.map((forecast) => ({
    horizon: `${forecast.horizon_hours}h`,
    temperature: forecast.temperature_c,
  }))
  return (
    <article className="panel chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Temperature outlook</p>
          <h2>Forecast trend</h2>
        </div>
        <span className="unit-label">°C</span>
      </div>
      <div className="chart-container" aria-label="Temperature prediction line chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8eeeb" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="horizon" axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} />
            <YAxis width={42} axisLine={false} tickLine={false} tick={{ fill: '#6d7c77' }} domain={['dataMin - 2', 'dataMax + 2']} />
            <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${Number(value).toFixed(1)} °C`, 'Temperature']} />
            <Line type="monotone" dataKey="temperature" stroke="#176b5b" strokeWidth={3} dot={{ r: 5, fill: '#176b5b', stroke: '#f7faf8', strokeWidth: 3 }} activeDot={{ r: 7 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}
