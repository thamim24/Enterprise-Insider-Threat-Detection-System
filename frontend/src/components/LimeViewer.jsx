import clsx from 'clsx';

function LimeViewer({ text, highlights = [] }) {
  if (!text) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No text content available</p>
      </div>
    );
  }

  // If no highlights provided, show plain text
  if (!highlights || highlights.length === 0) {
    return (
      <div className="p-4 bg-white border border-gray-200 rounded-lg">
        <p className="text-sm text-gray-700 leading-relaxed">{text}</p>
        <p className="text-xs text-gray-500 mt-4 italic">
          No LIME highlights available for this document
        </p>
      </div>
    );
  }

  // Sort highlights by position
  const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);

  // Build highlighted text segments
  const segments = [];
  let lastEnd = 0;

  sortedHighlights.forEach((highlight, index) => {
    // Add text before this highlight
    if (highlight.start > lastEnd) {
      segments.push({
        type: 'text',
        content: text.slice(lastEnd, highlight.start),
      });
    }

    // Add highlighted segment
    segments.push({
      type: 'highlight',
      content: text.slice(highlight.start, highlight.end),
      weight: highlight.weight,
      word: highlight.word,
    });

    lastEnd = highlight.end;
  });

  // Add remaining text
  if (lastEnd < text.length) {
    segments.push({
      type: 'text',
      content: text.slice(lastEnd),
    });
  }

  return (
    <div className="space-y-4">
      {/* Highlighted text display */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg">
        <p className="text-sm leading-relaxed">
          {segments.map((segment, index) => {
            if (segment.type === 'text') {
              return <span key={index}>{segment.content}</span>;
            }

            const intensity = Math.abs(segment.weight);
            const isPositive = segment.weight > 0;

            return (
              <span
                key={index}
                className={clsx(
                  'px-1 py-0.5 rounded cursor-help transition-all',
                  isPositive
                    ? intensity > 0.5
                      ? 'bg-red-300 text-red-900'
                      : 'bg-red-100 text-red-700'
                    : intensity > 0.5
                    ? 'bg-green-300 text-green-900'
                    : 'bg-green-100 text-green-700'
                )}
                title={`Weight: ${segment.weight.toFixed(3)}`}
              >
                {segment.content}
              </span>
            );
          })}
        </p>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center space-x-6">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-red-200 rounded" />
          <span className="text-sm text-gray-600">Increases Sensitivity</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-green-200 rounded" />
          <span className="text-sm text-gray-600">Decreases Sensitivity</span>
        </div>
      </div>

      {/* Top contributing words */}
      {highlights.length > 0 && (
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            Top Contributing Words
          </h4>
          <div className="flex flex-wrap gap-2">
            {sortedHighlights
              .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
              .slice(0, 10)
              .map((h, index) => (
                <span
                  key={index}
                  className={clsx(
                    'px-2 py-1 text-xs font-medium rounded-full',
                    h.weight > 0
                      ? 'bg-red-100 text-red-700'
                      : 'bg-green-100 text-green-700'
                  )}
                >
                  {h.word}: {h.weight > 0 ? '+' : ''}{(h.weight * 100).toFixed(1)}%
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default LimeViewer;
