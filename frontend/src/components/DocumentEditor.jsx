import { useState, useEffect } from 'react';
import { X, Save, AlertTriangle, Clock, FileText, Edit3, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

/**
 * Real-time Document Editor Component
 * Allows users to modify document content with risk warnings
 */
function DocumentEditor({
  document,
  initialContent,
  onSave,
  onCancel,
  isSaving,
  accessInfo,
}) {
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [lastModified, setLastModified] = useState(null);
  
  // Get document fields
  const docName = document?.filename || document?.name || 'Unnamed Document';
  const docDepartment = document?.department || 'Unknown';
  const sensitivity = (document?.sensitivity || document?.sensitivity_level || 'internal').toUpperCase();
  const isCrossDepartment = accessInfo?.is_cross_department || false;

  useEffect(() => {
    // Extract text content from response
    const textContent = typeof initialContent === 'string' 
      ? initialContent 
      : initialContent?.content || initialContent?.text || '';
    setContent(textContent);
    setOriginalContent(textContent);
    setHasChanges(false);
  }, [initialContent]);

  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setContent(newContent);
    setHasChanges(newContent !== originalContent);
    setLastModified(new Date());
  };

  const handleSave = () => {
    if (hasChanges) {
      onSave(content, originalContent);
    }
  };

  const handleReset = () => {
    setContent(originalContent);
    setHasChanges(false);
    setLastModified(null);
  };

  // Calculate change statistics
  const charDiff = content.length - originalContent.length;
  const changePercent = originalContent.length > 0 
    ? Math.abs((content.length - originalContent.length) / originalContent.length * 100).toFixed(1)
    : 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Edit3 className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                Editing: {docName}
                {hasChanges && (
                  <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full">
                    Unsaved Changes
                  </span>
                )}
              </h3>
              <p className="text-sm text-gray-500">
                Department: {docDepartment} | Sensitivity: {sensitivity}
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            title="Close editor"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Warning Banner for Cross-Department */}
        {isCrossDepartment && (
          <div className="px-6 py-3 bg-red-50 border-b border-red-200">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <p className="font-semibold">⚠️ HIGH RISK: Cross-Department Modification</p>
                <p className="text-sm">
                  You are editing a document from a different department. This action is 
                  <strong> heavily monitored</strong> and will generate a <strong>HIGH RISK</strong> alert.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Sensitivity Warning */}
        {sensitivity === 'CONFIDENTIAL' || sensitivity === 'RESTRICTED' ? (
          <div className="px-6 py-2 bg-amber-50 border-b border-amber-200">
            <div className="flex items-center space-x-2 text-amber-800">
              <AlertTriangle className="w-4 h-4" />
              <p className="text-sm">
                This is a <strong>{sensitivity}</strong> document. All modifications are logged and audited.
              </p>
            </div>
          </div>
        ) : null}

        {/* Editor Area */}
        <div className="flex-1 p-6 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                {content.length} characters
              </span>
              {hasChanges && (
                <span className={clsx(
                  "flex items-center gap-1",
                  charDiff > 0 ? "text-green-600" : charDiff < 0 ? "text-red-600" : ""
                )}>
                  {charDiff > 0 ? '+' : ''}{charDiff} chars ({changePercent}% change)
                </span>
              )}
              {lastModified && (
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  Last edit: {lastModified.toLocaleTimeString()}
                </span>
              )}
            </div>
            {hasChanges && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
            )}
          </div>
          
          <textarea
            value={content}
            onChange={handleContentChange}
            className={clsx(
              "flex-1 w-full p-4 border rounded-lg resize-none font-mono text-sm",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
              isCrossDepartment 
                ? "border-red-300 bg-red-50/30" 
                : hasChanges 
                  ? "border-yellow-300 bg-yellow-50/30"
                  : "border-gray-300 bg-gray-50"
            )}
            placeholder="Document content..."
            spellCheck={false}
          />
        </div>

        {/* Footer with Actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            {isCrossDepartment ? (
              <span className="text-red-600 font-medium">
                ⚠️ Cross-department modifications generate HIGH RISK alerts
              </span>
            ) : (
              <span>Modifications are tracked for security auditing</span>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg transition-colors",
                hasChanges && !isSaving
                  ? isCrossDepartment
                    ? "bg-red-600 hover:bg-red-700 text-white"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-gray-300 text-gray-500 cursor-not-allowed"
              )}
            >
              {isSaving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  {isCrossDepartment ? 'Save (High Risk)' : 'Save Changes'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DocumentEditor;
