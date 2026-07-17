export interface WeatherObservation {
  timestamp: string
  temperature: number
  relative_humidity: number
  precipitation: number
  surface_pressure: number
  cloud_cover: number
  wind_speed: number
  wind_direction: number
}

export interface Forecast {
  horizon_hours: number
  temperature_c: number
  rain_probability: number
  rain_expected: boolean
  rainfall_mm: number
}

export interface PredictionResponse {
  location: string
  generated_at: string
  forecasts: Forecast[]
}

export interface HealthResponse {
  status: string
  location: string
  models_loaded: boolean
}

export interface ObservationHistoryResponse {
  location: string
  source: string
  latest_timestamp: string
  observations: WeatherObservation[]
}

export type ConnectionStatus = 'checking' | 'online' | 'offline'
