import { FileText, Eye, Download, Edit, Shield, Lock } from 'lucide-react';
import clsx from 'clsx';

const SENSITIVITY_COLORS = {
  PUBLIC: 'bg-green-100 text-green-700',
  INTERNAL: 'bg-blue-100 text-blue-700',
  CONFIDENTIAL: 'bg-orange-100 text-orange-700',
  RESTRICTED: 'bg-red-100 text-red-700',
};

const SENSITIVITY_ICONS = {
  PUBLIC: Shield,
  INTERNAL: Shield,
  CONFIDENTIAL: Lock,
  RESTRICTED: Lock,
};

function DocumentList({
  documents,
  loading,
  onView,
  onDownload,
  onModify,
  selectedDocument,
  onSelect,
}) {
  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
        <p className="mt-2 text-gray-500">Loading documents...</p>
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="font-medium">No documents found</p>
        <p className="text-sm mt-1">Documents in this department will appear here</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200">
      {documents.map((doc) => {
        // Map API field names: sensitivity (not sensitivity_level), document_id (not id), filename (not name), file_size_bytes (not size)
        const sensitivityLevel = doc.sensitivity?.toUpperCase() || doc.sensitivity_level || 'INTERNAL';
        const docId = doc.document_id || doc.id;
        const docName = doc.filename || doc.name || 'Unnamed Document';
        const docSize = doc.file_size_bytes || doc.size;
        
        const SensitivityIcon = SENSITIVITY_ICONS[sensitivityLevel] || Shield;
        const isSelected = selectedDocument?.document_id === docId || selectedDocument?.id === docId;

        return (
          <div
            key={docId}
            className={clsx(
              'p-4 transition-colors cursor-pointer',
              isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
            )}
            onClick={() => onSelect(doc)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-5 h-5 text-gray-500" />
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-900">{docName}</h3>
                  <div className="flex items-center space-x-3 mt-1">
                    <span
                      className={clsx(
                        'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded',
                        SENSITIVITY_COLORS[sensitivityLevel] || SENSITIVITY_COLORS.INTERNAL
                      )}
                    >
                      <SensitivityIcon className="w-3 h-3 mr-1" />
                      {sensitivityLevel}
                    </span>
                    <span className="text-xs text-gray-500">
                      {docSize ? `${(docSize / 1024).toFixed(1)} KB` : 'Unknown size'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <ActionButton
                  icon={Eye}
                  label="View"
                  onClick={(e) => {
                    e.stopPropagation();
                    onView(doc);
                  }}
                  color="blue"
                />
                <ActionButton
                  icon={Download}
                  label="Download"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDownload(doc);
                  }}
                  color="green"
                />
                <ActionButton
                  icon={Edit}
                  label="Modify"
                  onClick={(e) => {
                    e.stopPropagation();
                    onModify(doc);
                  }}
                  color="orange"
                />
              </div>
            </div>

            {isSelected && doc.description && (
              <div className="mt-3 pl-14">
                <p className="text-sm text-gray-600">{doc.description}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ActionButton({ icon: Icon, label, onClick, color }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600 hover:bg-blue-200',
    green: 'bg-green-100 text-green-600 hover:bg-green-200',
    orange: 'bg-orange-100 text-orange-600 hover:bg-orange-200',
  };

  return (
    <button
      onClick={onClick}
      className={clsx(
        'p-2 rounded-lg transition-colors',
        colors[color]
      )}
      title={label}
    >
      <Icon className="w-4 h-4" />
    </button>
  );
}

export default DocumentList;
