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

export interface ObservationHistoryResponse {
  location: string
  latitude: number
  longitude: number
  timezone: string
  model_supported: boolean
  source: string
  latest_timestamp: string
  observations: WeatherObservation[]
  hourly_forecasts: HourlyForecast[]
  daily_forecasts: DailyForecast[]
}

export interface WeatherLocation {
  name: string
  latitude: number
  longitude: number
  timezone: string
  country?: string | null
  admin1?: string | null
}

export interface LocationSearchResponse {
  query: string
  results: WeatherLocation[]
}

export interface HourlyForecast {
  timestamp: string
  temperature: number
  precipitation_probability: number
  weather_code: number
}

export interface DailyForecast {
  date: string
  weather_code: number
  temperature_max: number
  temperature_min: number
  precipitation_probability: number
  precipitation_sum: number
  sunrise: string
  sunset: string
  daylight_duration_seconds: number
}

export interface EnvironmentalInsights {
  location: string
  source: string
  observed_at: string
  us_aqi: number
  pm2_5: number
  pm10: number
  air_quality_label: string
  air_quality_description: string
  dust_outlook: string
  dust_description: string
  uv_index: number
  uv_label: string
  uv_description: string
  pollen_available: boolean
  pollen_outlook: string
  pollen_description: string
  pollen_readings: PollenReading[]
}

export interface PollenReading {
  pollen_type: string
  concentration: number
}

export interface ClimateNewsItem {
  title: string
  url: string
  source: string
  published_at: string
}

export interface ClimateNewsResponse {
  source: string
  fetched_at: string
  articles: ClimateNewsItem[]
}
