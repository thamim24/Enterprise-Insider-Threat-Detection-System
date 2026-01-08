import { useState } from 'react';
import { X, Upload, AlertTriangle, CheckCircle, FileText } from 'lucide-react';

const DEPARTMENTS = ['HR', 'FINANCE', 'LEGAL', 'IT'];
const SENSITIVITY_LEVELS = ['PUBLIC', 'INTERNAL', 'CONFIDENTIAL'];

function DocumentUploadModal({ onUpload, onClose, userDepartment, isUploading }) {
  const [filename, setFilename] = useState('');
  const [content, setContent] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState(userDepartment);
  const [sensitivity, setSensitivity] = useState('INTERNAL');
  const [showCrossDeptWarning, setShowCrossDeptWarning] = useState(false);

  // Check if cross-department upload
  const isCrossDepartment = selectedDepartment !== userDepartment;

  const handleDepartmentChange = (dept) => {
    setSelectedDepartment(dept);
    if (dept !== userDepartment) {
      setShowCrossDeptWarning(true);
    } else {
      setShowCrossDeptWarning(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!filename.trim() || !content.trim()) {
      alert('Please provide both filename and content');
      return;
    }
    onUpload({
      filename: filename.trim(),
      content,
      department: selectedDepartment,
      sensitivity,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <Upload className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Upload New Document
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto max-h-[60vh]">
          {/* Cross-department warning */}
          {isCrossDepartment && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-red-800">
                    Cross-Department Upload Warning
                  </h4>
                  <p className="text-sm text-red-700 mt-1">
                    You are attempting to upload a document to the <strong>{selectedDepartment}</strong> department,
                    which is different from your department (<strong>{userDepartment}</strong>).
                  </p>
                  <p className="text-sm text-red-700 mt-2">
                    This action will trigger a <strong>HIGH PRIORITY SECURITY ALERT</strong> and will be flagged 
                    as anomalous behavior by the ML pipeline.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Filename */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Document Name <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder="e.g., quarterly_report.pdf"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          </div>

          {/* Department Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Department <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-4 gap-2">
              {DEPARTMENTS.map((dept) => (
                <button
                  key={dept}
                  type="button"
                  onClick={() => handleDepartmentChange(dept)}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                    selectedDepartment === dept
                      ? dept === userDepartment
                        ? 'bg-blue-600 text-white'
                        : 'bg-red-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {dept}
                  {dept === userDepartment && (
                    <span className="ml-1 text-xs opacity-75">(yours)</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Sensitivity Level */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sensitivity Level
            </label>
            <div className="grid grid-cols-3 gap-2">
              {SENSITIVITY_LEVELS.map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => setSensitivity(level)}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                    sensitivity === level
                      ? level === 'CONFIDENTIAL'
                        ? 'bg-red-500 text-white'
                        : level === 'INTERNAL'
                        ? 'bg-yellow-500 text-white'
                        : 'bg-green-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          {/* Document Content */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Document Content <span className="text-red-500">*</span>
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter or paste document content here..."
              rows={10}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              {content.length.toLocaleString()} characters
            </p>
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
          <div className="text-sm text-gray-500">
            {isCrossDepartment ? (
              <span className="text-red-600 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1" />
                Alert will be triggered
              </span>
            ) : (
              <span className="text-green-600 flex items-center">
                <CheckCircle className="w-4 h-4 mr-1" />
                Normal upload
              </span>
            )}
          </div>
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isUploading || !filename.trim() || !content.trim()}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2 ${
                isCrossDepartment
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isUploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>{isCrossDepartment ? 'Upload (Alert)' : 'Upload'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DocumentUploadModal;
