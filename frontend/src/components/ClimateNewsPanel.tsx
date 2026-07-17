import type { ClimateNewsItem, WeatherLocation } from '../types'

interface ClimateNewsPanelProps {
  articles: ClimateNewsItem[]
  location: WeatherLocation
}

function formatPublishedAt(value: string): string {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value))
}

export function ClimateNewsPanel({ articles, location }: ClimateNewsPanelProps) {
  return (
    <section className="climate-news-card" aria-labelledby="climate-news-title">
      <div className="insight-header">
        <span id="climate-news-title">Climate &amp; weather news</span>
        <span>Current topics for {location.name}</span>
      </div>
      <div className="climate-news-list">
        {articles.map((article) => (
          <a
            className="climate-news-item"
            href={article.url}
            key={`${article.url}-${article.published_at}`}
            rel="noreferrer"
            target="_blank"
          >
            <span className="news-kicker">Climate &amp; weather</span>
            <strong>{article.title}</strong>
            <span className="news-meta">{article.source} &middot; {formatPublishedAt(article.published_at)}</span>
            <span className="news-arrow" aria-hidden="true">&rarr;</span>
          </a>
        ))}
      </div>
    </section>
  )
}
