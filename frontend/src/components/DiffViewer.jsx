import { useMemo } from 'react';
import { diffWords } from 'diff';
import { FileWarning, Plus, Minus } from 'lucide-react';

function DiffViewer({ original, tampered, title }) {
  const diff = useMemo(() => {
    if (!original || !tampered) return [];
    return diffWords(original, tampered);
  }, [original, tampered]);

  const stats = useMemo(() => {
    let added = 0;
    let removed = 0;
    diff.forEach((part) => {
      if (part.added) added += part.value.length;
      if (part.removed) removed += part.value.length;
    });
    return { added, removed };
  }, [diff]);

  if (!original && !tampered) {
    return (
      <div className="text-center py-8 text-gray-500">
        <FileWarning className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No document comparison available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {title && (
        <h3 className="text-sm font-medium text-gray-700">{title}</h3>
      )}

      {/* Stats bar */}
      <div className="flex items-center space-x-4 text-sm">
        <div className="flex items-center space-x-1 text-green-600">
          <Plus className="w-4 h-4" />
          <span>{stats.added} characters added</span>
        </div>
        <div className="flex items-center space-x-1 text-red-600">
          <Minus className="w-4 h-4" />
          <span>{stats.removed} characters removed</span>
        </div>
      </div>

      {/* Diff display */}
      <div className="p-4 bg-gray-900 rounded-lg overflow-x-auto">
        <pre className="text-sm font-mono leading-relaxed whitespace-pre-wrap">
          {diff.map((part, index) => {
            if (part.added) {
              return (
                <span
                  key={index}
                  className="bg-green-500/30 text-green-300 px-0.5"
                >
                  {part.value}
                </span>
              );
            }
            if (part.removed) {
              return (
                <span
                  key={index}
                  className="bg-red-500/30 text-red-300 px-0.5 line-through"
                >
                  {part.value}
                </span>
              );
            }
            return (
              <span key={index} className="text-gray-300">
                {part.value}
              </span>
            );
          })}
        </pre>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center space-x-6 text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-2 bg-green-500/30 rounded" />
          <span className="text-gray-600">Added</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-2 bg-red-500/30 rounded" />
          <span className="text-gray-600">Removed</span>
        </div>
      </div>

      {/* Side by side view */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Original</h4>
          <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700 max-h-64 overflow-y-auto font-mono">
            <pre className="whitespace-pre-wrap break-words">{original}</pre>
          </div>
        </div>
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Tampered</h4>
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-gray-700 max-h-64 overflow-y-auto font-mono">
            <pre className="whitespace-pre-wrap break-words">{tampered}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DiffViewer;
