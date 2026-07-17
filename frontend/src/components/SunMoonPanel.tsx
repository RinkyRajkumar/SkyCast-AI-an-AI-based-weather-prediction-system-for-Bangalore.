import type { DailyForecast } from '../types'

interface SunMoonPanelProps {
  forecast: DailyForecast
}

interface MoonPhase {
  label: string
  className: string
}

function formatTime(value: string): string {
  const date = new Date(`${value}+05:30`)
  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'Asia/Kolkata',
  }).format(date)
}

function daylightDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`
}

function moonPhase(date: string): MoonPhase {
  const daysSinceNewMoon = (Date.parse(`${date}T00:00:00Z`) - Date.UTC(2000, 0, 6, 18, 14)) / 86_400_000
  const phase = ((daysSinceNewMoon / 29.53058867) % 1 + 1) % 1
  if (phase < 0.03 || phase >= 0.97) return { label: 'New Moon', className: 'moon-new' }
  if (phase < 0.22) return { label: 'Waxing Crescent', className: 'moon-waxing-crescent' }
  if (phase < 0.28) return { label: 'First Quarter', className: 'moon-first-quarter' }
  if (phase < 0.47) return { label: 'Waxing Gibbous', className: 'moon-waxing-gibbous' }
  if (phase < 0.53) return { label: 'Full Moon', className: 'moon-full' }
  if (phase < 0.72) return { label: 'Waning Gibbous', className: 'moon-waning-gibbous' }
  if (phase < 0.78) return { label: 'Last Quarter', className: 'moon-last-quarter' }
  return { label: 'Waning Crescent', className: 'moon-waning-crescent' }
}

export function SunMoonPanel({ forecast }: SunMoonPanelProps) {
  const moon = moonPhase(forecast.date)

  return (
    <section className="sun-moon-card" aria-labelledby="sun-moon-heading">
      <div className="insight-header"><span id="sun-moon-heading">Sun &amp; Moon</span><span>For Bengaluru</span></div>
      <div className="sun-moon-row">
        <div className="solar-icon" aria-hidden="true" />
        <strong>{daylightDuration(forecast.daylight_duration_seconds)} of daylight</strong>
        <dl><div><dt>Rise</dt><dd>{formatTime(forecast.sunrise)}</dd></div><div><dt>Set</dt><dd>{formatTime(forecast.sunset)}</dd></div></dl>
      </div>
      <div className="sun-moon-row">
        <div className={`moon-icon ${moon.className}`} aria-hidden="true" />
        <div><strong>{moon.label}</strong><span>Approximate lunar phase</span></div>
        <p>Moonrise and moonset are not supplied by the live weather source.</p>
      </div>
    </section>
  )
}
