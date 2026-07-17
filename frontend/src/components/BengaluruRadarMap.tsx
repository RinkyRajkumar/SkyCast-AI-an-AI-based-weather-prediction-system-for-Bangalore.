const BENGALURU_RADAR_URL = 'https://embed.windy.com/embed2.html?lat=12.9716&lon=77.5946&detailLat=12.9716&detailLon=77.5946&zoom=10&level=surface&overlay=radar&product=radar&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=default&metricTemp=default&radarRange=-1'

export function BengaluruRadarMap() {
  return (
    <section className="radar-card" aria-labelledby="radar-heading">
      <div className="insight-header">
        <span id="radar-heading">Bengaluru weather radar</span>
        <a href="https://www.windy.com" target="_blank" rel="noreferrer">Live radar by Windy</a>
      </div>
      <iframe
        className="radar-frame"
        title="Live weather radar for Bengaluru"
        src={BENGALURU_RADAR_URL}
        loading="lazy"
        referrerPolicy="no-referrer"
        allowFullScreen
      />
    </section>
  )
}
