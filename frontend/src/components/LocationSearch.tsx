import { useEffect, useState } from 'react'
import { getApiErrorMessage, getLocations } from '../api/weatherApi'
import type { WeatherLocation } from '../types'

interface LocationSearchProps {
  onSelect: (location: WeatherLocation) => void
}

function locationLabel(location: WeatherLocation): string {
  return [location.name, location.admin1, location.country]
    .filter((part, index, parts) => Boolean(part) && parts.indexOf(part) === index)
    .join(', ')
}

export function LocationSearch({ onSelect }: LocationSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<WeatherLocation[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const normalizedQuery = query.trim()
    if (normalizedQuery.length < 2) {
      setResults([])
      setError('')
      setIsSearching(false)
      return undefined
    }
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setIsSearching(true)
      setError('')
      void getLocations(normalizedQuery, controller.signal)
        .then((response) => {
          if (!controller.signal.aborted) setResults(response.results)
        })
        .catch((requestError) => {
          if (!controller.signal.aborted) {
            setResults([])
            setError(getApiErrorMessage(requestError))
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setIsSearching(false)
        })
    }, 300)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query])

  function selectLocation(result: WeatherLocation) {
    onSelect(result)
    setQuery('')
    setResults([])
    setError('')
  }

  return (
    <div className="location-search" role="search">
      <label className="sr-only" htmlFor="location-search-input">Search for a city or location</label>
      <span className="location-search-icon" aria-hidden="true" />
      <input
        id="location-search-input"
        autoComplete="off"
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search city/location"
        type="search"
        value={query}
      />
      {isSearching ? <span className="location-search-status">Searching</span> : null}
      {(results.length > 0 || error || (query.trim().length >= 2 && !isSearching)) ? (
        <div className="location-results" role="listbox" aria-label="Location results">
          {results.map((result) => (
            <button
              className="location-result"
              key={`${result.latitude}-${result.longitude}-${result.timezone}`}
              onClick={() => selectLocation(result)}
              role="option"
              type="button"
            >
              <strong>{result.name}</strong>
              <span>{locationLabel(result)}</span>
            </button>
          ))}
          {!isSearching && !error && results.length === 0 ? <p>No matching locations found.</p> : null}
          {error ? <p>{error}</p> : null}
        </div>
      ) : null}
    </div>
  )
}
