import { useState, type ChangeEvent } from 'react'
import type { WeatherObservation } from '../types'

interface WeatherInputFormProps {
  observation?: WeatherObservation
  observationCount: number
  isLoading: boolean
  source?: string
  onHistoryLoaded: (observations: WeatherObservation[]) => void
}

const numericKeys = [
  'temperature',
  'relative_humidity',
  'precipitation',
  'surface_pressure',
  'cloud_cover',
  'wind_speed',
  'wind_direction',
] as const

function isObservation(value: unknown): value is WeatherObservation {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  if (typeof item.timestamp !== 'string' || Number.isNaN(Date.parse(item.timestamp))) return false
  return numericKeys.every((key) => typeof item[key] === 'number' && Number.isFinite(item[key]))
}

export function WeatherInputForm({
  observation,
  observationCount,
  isLoading,
  source,
  onHistoryLoaded,
}: WeatherInputFormProps) {
  const [fileError, setFileError] = useState('')

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const parsed: unknown = JSON.parse(await file.text())
      const candidate = Array.isArray(parsed)
        ? parsed
        : (parsed as { observations?: unknown })?.observations
      if (!Array.isArray(candidate) || candidate.length === 0 || !candidate.every(isObservation)) {
        throw new Error('Use an array of valid hourly observations or an API request object.')
      }
      onHistoryLoaded(candidate)
      setFileError('')
    } catch (error) {
      setFileError(error instanceof Error ? error.message : 'Could not read the selected file.')
    } finally {
      event.target.value = ''
    }
  }

  const hasHistory = observationCount >= 169 && observation
  return (
    <section className="panel input-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Model inputs</p>
          <h2>Weather observations</h2>
        </div>
        <span className={`history-count ${hasHistory ? 'history-ready' : ''}`}>
          {observationCount} hourly records
        </span>
      </div>

      <div className="history-status" aria-live="polite">
        <div>
          <strong>
            {hasHistory ? `${observationCount} hourly records loaded` : 'Loading Bengaluru weather history…'}
          </strong>
          <p>
            {hasHistory
              ? `Latest observation: ${observation.timestamp}`
              : 'Requesting the latest contiguous records from Open-Meteo.'}
          </p>
        </div>
        <span className="source-label">Source: {source || 'Open-Meteo'}</span>
      </div>

      <p className="form-hint">
        {isLoading
          ? 'Forecasting begins automatically when valid history is available.'
          : 'Forecasts are generated automatically from the latest weather history.'}
      </p>

      <details className="developer-tools">
        <summary>Developer tools</summary>
        <div className="history-upload">
          <div>
            <strong>Use local observation history</strong>
            <p>Optional JSON override for testing. It must contain at least 169 contiguous records.</p>
          </div>
          <label className="upload-button">
            Choose JSON
            <input type="file" accept="application/json,.json" onChange={handleFile} />
          </label>
        </div>
        {fileError ? <p className="field-error" role="alert">{fileError}</p> : null}
      </details>
    </section>
  )
}
