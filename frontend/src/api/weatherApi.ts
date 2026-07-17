import axios, { AxiosError } from 'axios'
import type {
  EnvironmentalInsights,
  ClimateNewsResponse,
  ObservationHistoryResponse,
  PredictionResponse,
  LocationSearchResponse,
  WeatherLocation,
  WeatherObservation,
} from '../types'

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL?.trim()
export const API_BASE_URL = (configuredApiUrl || 'http://localhost:8000').replace(/\/$/, '')

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

function locationParams(location?: WeatherLocation) {
  if (!location) return undefined
  return {
    name: location.name,
    latitude: location.latitude,
    longitude: location.longitude,
    timezone: location.timezone,
    country: location.country ?? undefined,
    admin1: location.admin1 ?? undefined,
  }
}

export async function getLocations(query: string, signal?: AbortSignal): Promise<LocationSearchResponse> {
  const response = await apiClient.get<LocationSearchResponse>('/api/locations', { params: { query }, signal })
  return response.data
}

export async function getObservations(location?: WeatherLocation, signal?: AbortSignal): Promise<ObservationHistoryResponse> {
  const response = await apiClient.get<ObservationHistoryResponse>('/api/observations', { params: locationParams(location), signal })
  return response.data
}

export async function getEnvironment(location?: WeatherLocation, signal?: AbortSignal): Promise<EnvironmentalInsights> {
  const response = await apiClient.get<EnvironmentalInsights>('/api/environment', { params: locationParams(location), signal })
  return response.data
}

export async function getClimateNews(location?: WeatherLocation, signal?: AbortSignal): Promise<ClimateNewsResponse> {
  const response = await apiClient.get<ClimateNewsResponse>('/api/climate-news', { params: locationParams(location), signal })
  return response.data
}

export async function getPrediction(
  observations: WeatherObservation[],
  signal?: AbortSignal,
): Promise<PredictionResponse> {
  const response = await apiClient.post<PredictionResponse>('/predict', { observations }, { signal })
  return response.data
}

export function getApiErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) {
    return error instanceof Error ? error.message : 'An unexpected error occurred.'
  }
  if (!error.response) {
    return 'The SkyCast backend is unavailable. Check that FastAPI is running and try again.'
  }
  const detail = error.response.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg ?? 'Invalid input').join(' · ')
  }
  return `The prediction request failed with status ${error.response.status}.`
}

export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof AxiosError && !error.response
}
