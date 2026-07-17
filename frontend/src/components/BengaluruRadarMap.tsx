import type { WeatherLocation } from '../types'

interface WeatherRadarMapProps {
  location: WeatherLocation
}

function radarUrl(location: WeatherLocation): string {
  const params = new URLSearchParams({
    lat: String(location.latitude), lon: String(location.longitude), detailLat: String(location.latitude), detailLon: String(location.longitude),
    zoom: '10', level: 'surface', overlay: 'radar', product: 'radar', menu: '', message: '', marker: '', calendar: 'now',
    pressure: '', type: 'map', location: 'coordinates', detail: '', metricWind: 'default', metricTemp: 'default', radarRange: '-1',
  })
  return `https://embed.windy.com/embed2.html?${params}`
}

export function BengaluruRadarMap({ location }: WeatherRadarMapProps) {
  return (
    <section className="radar-card" aria-labelledby="radar-heading">
      <div className="insight-header">
        <span id="radar-heading">{location.name} weather radar</span>
        <a href="https://www.windy.com" target="_blank" rel="noreferrer">Live radar by Windy</a>
      </div>
      <iframe
        className="radar-frame"
        title={`Live weather radar for ${location.name}`}
        src={radarUrl(location)}
        loading="lazy"
        referrerPolicy="no-referrer"
        allowFullScreen
      />
    </section>
  )
}
