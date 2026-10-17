const categoryLabel = {
  location: 'Location',
  injury: 'Injury',
  people: 'People',
  hazard: 'Hazard',
  time: 'Time',
}

export default function HighlightText({ item }) {
  const highlights = [...(item.highlights || [])].sort((a, b) => a.start - b.start)
  if (!highlights.length) return <span>{item.text}</span>
  const parts = []
  let cursor = 0
  highlights.forEach((highlight, index) => {
    if (highlight.start < cursor) return
    if (highlight.start > cursor) parts.push(<span key={`plain-${index}`}>{item.text.slice(cursor, highlight.start)}</span>)
    parts.push(
      <mark key={`mark-${index}`} className={`highlight highlight-${highlight.category}`}>
        {item.text.slice(highlight.start, highlight.end)}
      </mark>,
    )
    cursor = highlight.end
  })
  if (cursor < item.text.length) parts.push(<span key="tail">{item.text.slice(cursor)}</span>)
  return (
    <>
      <span>{parts}</span>
      <span className="bubble-tags" aria-label="Detected details">
        {[...new Set(highlights.map((highlight) => highlight.category))].map((category) => (
          <span className={`tag tag-${category}`} key={category}><i />{categoryLabel[category]}</span>
        ))}
      </span>
    </>
  )
}

