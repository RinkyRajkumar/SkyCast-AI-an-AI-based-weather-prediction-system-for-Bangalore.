import type { DailyForecast, EnvironmentalInsights as EnvironmentalInsightsData } from '../types'
import { BengaluruRadarMap } from './BengaluruRadarMap'
import { SunMoonPanel } from './SunMoonPanel'

interface EnvironmentalInsightsProps {
  insight: EnvironmentalInsightsData
  dailyForecast?: DailyForecast
}

function airTone(label: string): string {
  if (label === 'Good') return 'insight-good'
  if (label === 'Fair' || label === 'Moderate') return 'insight-fair'
  return 'insight-poor'
}

function dustTone(outlook: string): string {
  if (outlook === 'Low') return 'insight-good'
  if (outlook === 'Moderate') return 'insight-fair'
  return 'insight-poor'
}

function uvTone(index: number): string {
  if (index < 3) return 'uv-low'
  if (index < 6) return 'uv-moderate'
  if (index < 8) return 'uv-high'
  return 'uv-very-high'
}

export function EnvironmentalInsights({ insight, dailyForecast }: EnvironmentalInsightsProps) {
  const uvProgress = `${Math.min(insight.uv_index / 11, 1) * 100}%`

  return (
    <section className="environment-insights" aria-label="Environmental insights">
      <article className="insight-card">
        <div className="insight-header"><span>Air quality</span><span>Live Bengaluru reading</span></div>
        <div className="insight-main">
          <div className="insight-title"><span aria-hidden="true">AQ</span><strong>Air quality</strong></div>
          <div className={`insight-level ${airTone(insight.air_quality_label)}`}>
            <strong>{insight.air_quality_label}</strong><span>US AQI {insight.us_aqi}</span>
          </div>
        </div>
        <p>{insight.air_quality_description}</p>
        <small>PM2.5 {insight.pm2_5.toFixed(1)} &micro;g/m&sup3; &middot; PM10 {insight.pm10.toFixed(1)} &micro;g/m&sup3;</small>
      </article>

      <article className="insight-card insight-card-compact">
        <div className="insight-header"><span>Allergy outlook</span><span>Outdoor conditions</span></div>
        <div className="insight-main">
          <div className="insight-title"><span aria-hidden="true">OD</span><strong>Outdoor dust</strong></div>
          <div className={`insight-level ${dustTone(insight.dust_outlook)}`}>
            <strong>{insight.dust_outlook}</strong><span>PM10-based</span>
          </div>
        </div>
        <p>{insight.dust_description}</p>
      </article>

      <article className="uv-insight-card">
        <div className="insight-header"><span>UV index</span><span>Live sun exposure</span></div>
        <div className="uv-content">
          <div className={`uv-orb ${uvTone(insight.uv_index)}`} aria-hidden="true"><span>{insight.uv_index.toFixed(1)}</span></div>
          <div className="uv-copy">
            <div><strong>{insight.uv_label}</strong><span>Current UV index</span></div>
            <p>{insight.uv_description}</p>
            <div className="uv-scale" aria-label={`UV index ${insight.uv_index}, ${insight.uv_label}`}>
              <div className="uv-scale-track"><span style={{ width: uvProgress }} /></div>
              <div className="uv-scale-labels"><span>0</span><span>3</span><span>6</span><span>8</span><span>11+</span></div>
            </div>
          </div>
        </div>
      </article>
      <BengaluruRadarMap />
      {dailyForecast ? <SunMoonPanel forecast={dailyForecast} /> : null}
    </section>
  )
}
