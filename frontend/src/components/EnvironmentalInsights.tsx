import type { ClimateNewsItem, DailyForecast, EnvironmentalInsights as EnvironmentalInsightsData, WeatherLocation } from '../types'
import { BengaluruRadarMap } from './BengaluruRadarMap'
import { ClimateNewsPanel } from './ClimateNewsPanel'
import { SunMoonPanel } from './SunMoonPanel'

interface EnvironmentalInsightsProps {
  insight: EnvironmentalInsightsData
  dailyForecast?: DailyForecast
  news?: ClimateNewsItem[]
  location: WeatherLocation
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

export function EnvironmentalInsights({ insight, dailyForecast, news = [], location }: EnvironmentalInsightsProps) {
  const uvProgress = `${Math.min(insight.uv_index / 11, 1) * 100}%`
  const pollenReadings = insight.pollen_readings ?? []
  const pollenAvailable = insight.pollen_available ?? false
  const pollenOutlook = insight.pollen_outlook ?? 'Pollen data unavailable'
  const pollenDescription = insight.pollen_description ?? `The live weather provider does not currently supply pollen coverage for ${location.name}.`

  return (
    <section className="environment-insights" aria-label="Environmental insights">
      <article className="insight-card">
        <div className="insight-header"><span>Air quality</span><span>Live {location.name} reading</span></div>
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
      <article className={`pollen-insight-card ${pollenAvailable ? 'pollen-covered' : 'pollen-unavailable'}`}>
        <div className="insight-header"><span>Pollen &amp; allergy outlook</span><span>Next 24 hours</span></div>
        <div className="pollen-content">
          <div className="pollen-mark" aria-hidden="true"><span /></div>
          <div className="pollen-copy">
            <div><strong>{pollenOutlook}</strong><span>{location.name} pollen forecast</span></div>
            <p>{pollenDescription}</p>
            {pollenReadings.length ? (
              <div className="pollen-readings" aria-label="Pollen concentrations">
                {pollenReadings.map((reading) => (
                  <span key={reading.pollen_type}><b>{reading.pollen_type}</b> {reading.concentration.toFixed(1)} grains/m&sup3;</span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </article>
      <BengaluruRadarMap location={location} />
      {dailyForecast ? <SunMoonPanel forecast={dailyForecast} location={location} /> : null}
      {news.length ? <ClimateNewsPanel articles={news} location={location} /> : null}
    </section>
  )
}
