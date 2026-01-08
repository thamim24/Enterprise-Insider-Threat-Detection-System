import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsAPI, eventsAPI, authAPI } from '../api/client';
import { formatDateTimeIST } from '../utils/dateUtils';
import DepartmentTabs from '../components/DepartmentTabs';
import DocumentList from '../components/DocumentList';
import DocumentEditor from '../components/DocumentEditor';
import DocumentUploadModal from '../components/DocumentUploadModal';
import RiskBadge from '../components/RiskBadge';
import {
  FileText,
  Download,
  Eye,
  Edit,
  AlertTriangle,
  Clock,
  Activity,
  X,
  Upload,
} from 'lucide-react';

const DEPARTMENTS = ['HR', 'FINANCE', 'LEGAL', 'IT'];

function UserDashboard() {
  const [activeDepartment, setActiveDepartment] = useState('HR');
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [actionResult, setActionResult] = useState(null);
  const [viewingDocument, setViewingDocument] = useState(null);  // Document being viewed
  const [documentContent, setDocumentContent] = useState(null);  // Document content modal
  const [editingDocument, setEditingDocument] = useState(null);  // Document being edited
  const [editContent, setEditContent] = useState(null);          // Content for editor
  const [editAccessInfo, setEditAccessInfo] = useState(null);    // Access info for editor
  const [isSaving, setIsSaving] = useState(false);               // Save in progress
  const [showUploadModal, setShowUploadModal] = useState(false); // Upload modal state
  const [isUploading, setIsUploading] = useState(false);         // Upload in progress
  const queryClient = useQueryClient();
  const user = authAPI.getStoredUser();

  // Fetch documents for active department
  const { data: documentsData, isLoading: loadingDocs } = useQuery({
    queryKey: ['documents', activeDepartment],
    queryFn: () => documentsAPI.list({ department: activeDepartment }),
  });

  // Extract documents array from response
  const documents = documentsData?.documents || [];

  // Fetch user's recent events
  const { data: eventsData } = useQuery({
    queryKey: ['events', 'recent'],
    queryFn: () => eventsAPI.history({ limit: 10 }),
    refetchInterval: 10000, // Refresh every 10 seconds for real-time updates
  });

  // Extract events array from response (API returns array directly)
  const recentEvents = Array.isArray(eventsData) ? eventsData : (eventsData?.events || []);

  // Event ingestion mutation
  const ingestEventMutation = useMutation({
    mutationFn: (eventData) => eventsAPI.ingest(eventData),
    onSuccess: (data) => {
      setActionResult(data);
      queryClient.invalidateQueries(['events']);
      // Clear result after 5 seconds
      setTimeout(() => setActionResult(null), 5000);
    },
  });

  // Helper to map document field names
  const getDocFields = (document) => ({
    docId: document.document_id || document.id,
    docName: document.filename || document.name || 'Unknown',
    docDepartment: document.department || activeDepartment,
    docSensitivity: document.sensitivity || document.sensitivity_level || 'internal',
    docSize: document.file_size_bytes || document.size || 0,
  });

  // Ingest event to ML pipeline
  const ingestEvent = (action, document) => {
    const { docId, docName, docDepartment, docSize } = getDocFields(document);
    
    const eventData = {
      document_id: docId,
      document_name: docName,
      target_department: docDepartment,
      action: action.toLowerCase(),
      bytes_transferred: action.toLowerCase() === 'download' ? docSize : 0,
      source_ip: null,
      device_info: navigator.userAgent,
      session_id: null,
    };

    ingestEventMutation.mutate(eventData);
  };

  // Handle VIEW action - show document content
  const handleViewDocument = async (document) => {
    const { docId, docName } = getDocFields(document);
    
    try {
      // Record the view event
      ingestEvent('view', document);
      
      // Fetch document content
      const response = await documentsAPI.view(docId);
      setViewingDocument(document);
      setDocumentContent(response);
    } catch (error) {
      console.error('Failed to view document:', error);
      alert('Failed to view document: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Handle DOWNLOAD action
  const handleDownloadDocument = async (document) => {
    const { docId, docName } = getDocFields(document);
    
    try {
      // Record the download event
      ingestEvent('download', document);
      
      // Get actual file content from backend (use proxy /api path)
      const response = await fetch(`/api/documents/${docId}/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      // Get filename from Content-Disposition header or use default .txt
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = docName.replace(/\.(pdf|xlsx|docx|vsdx)$/i, '') + '.txt';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }
      
      // Get the actual content as blob
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = filename;
      window.document.body.appendChild(a);
      a.click();
      window.document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download document:', error);
      alert('Failed to download document: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Handle MODIFY action - Open real document editor
  const handleModifyDocument = async (document) => {
    const { docId, docName } = getDocFields(document);
    
    try {
      // First, fetch the document content
      const response = await documentsAPI.view(docId);
      
      // Open the editor with the content
      setEditingDocument(document);
      setEditContent(response.content || response.text || '');
      setEditAccessInfo(response.access_info || {});
    } catch (error) {
      console.error('Failed to open document for editing:', error);
      alert('Failed to open document: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Handle save from document editor
  const handleSaveDocument = async (newContent, originalContent) => {
    if (!editingDocument) return;
    
    const { docId, docName, docDepartment, docSize } = getDocFields(editingDocument);
    setIsSaving(true);
    
    try {
      // Record the modify event with the new content
      const eventData = {
        document_id: docId,
        document_name: docName,
        target_department: docDepartment,
        action: 'modify',
        bytes_transferred: newContent.length,
        source_ip: null,
        device_info: navigator.userAgent,
        session_id: null,
        // Include the modified content for integrity verification
        document_content: newContent,
        metadata: {
          original_length: originalContent.length,
          new_length: newContent.length,
          change_percent: Math.abs((newContent.length - originalContent.length) / originalContent.length * 100).toFixed(1)
        }
      };
      
      // Ingest the modify event
      const result = await eventsAPI.ingest(eventData);
      
      // Show result
      setActionResult(result);
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries(['events']);
      queryClient.invalidateQueries(['documents']);
      
      // Close editor
      setEditingDocument(null);
      setEditContent(null);
      setEditAccessInfo(null);
      
      // Clear result after 5 seconds
      setTimeout(() => setActionResult(null), 5000);
    } catch (error) {
      console.error('Failed to save document:', error);
      alert('Failed to save document: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsSaving(false);
    }
  };

  // Cancel editing
  const handleCancelEdit = () => {
    setEditingDocument(null);
    setEditContent(null);
    setEditAccessInfo(null);
  };

  // Handle document upload
  const handleUploadDocument = async (uploadData) => {
    setIsUploading(true);
    try {
      const result = await documentsAPI.upload(
        uploadData.filename,
        uploadData.content,
        uploadData.department,
        uploadData.sensitivity
      );
      
      // Build result message with ML classification info
      let message = result.message || 'Document uploaded successfully';
      let risk_level = 'LOW';
      let risk_score = result.risk_score || 0.1;
      
      // Check for sensitivity mismatch (ML vs user-declared)
      if (result.sensitivity_mismatch) {
        risk_level = 'HIGH';
        message = `⚠️ SENSITIVITY MISMATCH: You declared "${result.user_declared_sensitivity?.toUpperCase()}" but ML detected "${result.ml_predicted_sensitivity?.toUpperCase()}" (${(result.ml_confidence * 100).toFixed(0)}% confidence). ${result.ml_explanation || ''}`;
      } else if (result.anomaly_triggered) {
        risk_level = 'HIGH';
        message = result.warning || 'Cross-department upload detected';
      } else if (result.ml_predicted_sensitivity) {
        // Show ML confirmation
        message = `✓ ${result.message}. ML verified: ${result.ml_predicted_sensitivity?.toUpperCase()} (${(result.ml_confidence * 100).toFixed(0)}% confidence)`;
      }
      
      setActionResult({
        risk_level,
        risk_score,
        message,
        action: 'upload',
        document_name: result.filename,
        ml_predicted_sensitivity: result.ml_predicted_sensitivity,
        ml_confidence: result.ml_confidence,
        sensitivity_mismatch: result.sensitivity_mismatch,
      });
      
      // Refresh document list
      queryClient.invalidateQueries(['documents']);
      queryClient.invalidateQueries(['events']);
      
      // Close modal
      setShowUploadModal(false);
      
      // Keep result longer if there's a mismatch (8 seconds) otherwise 5 seconds
      const timeout = result.sensitivity_mismatch ? 8000 : 5000;
      setTimeout(() => setActionResult(null), timeout);
    } catch (error) {
      console.error('Failed to upload document:', error);
      alert('Failed to upload document: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsUploading(false);
    }
  };

  // Close document viewer
  const closeDocumentViewer = () => {
    setViewingDocument(null);
    setDocumentContent(null);
  };

  return (
    <div className="space-y-6">
      {/* Document Upload Modal */}
      {showUploadModal && (
        <DocumentUploadModal
          onUpload={handleUploadDocument}
          onClose={() => setShowUploadModal(false)}
          userDepartment={user?.department || 'IT'}
          isUploading={isUploading}
        />
      )}

      {/* Document Editor Modal - Real-time editing */}
      {editingDocument && editContent !== null && (
        <DocumentEditor
          document={editingDocument}
          initialContent={editContent}
          onSave={handleSaveDocument}
          onCancel={handleCancelEdit}
          isSaving={isSaving}
          accessInfo={editAccessInfo}
        />
      )}

      {/* Document Viewer Modal */}
      {viewingDocument && documentContent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center space-x-3">
                <FileText className="w-5 h-5 text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">
                  {getDocFields(viewingDocument).docName}
                </h3>
              </div>
              <button
                onClick={closeDocumentViewer}
                className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>Department:</strong> {documentContent.document?.department || viewingDocument.department}
                  {' | '}
                  <strong>Sensitivity:</strong> {(documentContent.document?.sensitivity || viewingDocument.sensitivity || 'internal').toUpperCase()}
                </p>
                {documentContent.access_info?.is_cross_department && (
                  <p className="text-sm text-amber-600 mt-1 flex items-center">
                    <AlertTriangle className="w-4 h-4 mr-1" />
                    Cross-department access - this action has been logged
                  </p>
                )}
              </div>
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg border border-gray-200 text-sm">
                  {documentContent.content || documentContent.document?.content_preview || 'No content available'}
                </pre>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
              <button
                onClick={() => handleDownloadDocument(viewingDocument)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center space-x-2"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
              <button
                onClick={closeDocumentViewer}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Access</h1>
          <p className="text-gray-500 mt-1">
            Browse and access documents across departments
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
        >
          <Upload className="w-5 h-5 mr-2" />
          Upload Document
        </button>
      </div>

      {/* Alert banner for action result */}
      {actionResult && (
        <div
          className={`p-4 rounded-lg border ${
            actionResult.risk_level === 'HIGH' || actionResult.risk_level === 'CRITICAL'
              ? 'bg-red-50 border-red-200'
              : actionResult.risk_level === 'MEDIUM'
              ? 'bg-yellow-50 border-yellow-200'
              : 'bg-green-50 border-green-200'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              {actionResult.sensitivity_mismatch ? (
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
              ) : (
                <Activity className="w-5 h-5 text-gray-600 flex-shrink-0" />
              )}
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  {actionResult.sensitivity_mismatch ? 'ML Security Alert' : 'Action Recorded'}
                </p>
                <p className="text-sm text-gray-700 mt-1">
                  {actionResult.message}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Risk Score: {((actionResult.risk_score || 0) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            <RiskBadge level={actionResult.risk_level} />
          </div>
        </div>
      )}

      {/* Department Tabs */}
      <DepartmentTabs
        departments={DEPARTMENTS}
        activeTab={activeDepartment}
        onTabChange={setActiveDepartment}
        userDepartment={user?.department}
      />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document List */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {activeDepartment} Documents
              </h2>
              {activeDepartment !== user?.department && (
                <p className="text-sm text-amber-600 mt-1 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-1" />
                  Cross-department access - actions will be monitored
                </p>
              )}
            </div>
            
            <DocumentList
              documents={documents}
              loading={loadingDocs}
              onView={handleViewDocument}
              onDownload={handleDownloadDocument}
              onModify={handleModifyDocument}
              selectedDocument={selectedDocument}
              onSelect={setSelectedDocument}
            />
          </div>
        </div>

        {/* Recent Activity Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
            </div>
            
            <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
              {recentEvents.length > 0 ? (
                recentEvents.map((event, index) => (
                  <div
                    key={event.event_id || event.id || index}
                    className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-shrink-0">
                      {(event.action === 'view' || event.action === 'VIEW') && <Eye className="w-4 h-4 text-blue-500" />}
                      {(event.action === 'download' || event.action === 'DOWNLOAD') && <Download className="w-4 h-4 text-green-500" />}
                      {(event.action === 'modify' || event.action === 'MODIFY') && <Edit className="w-4 h-4 text-orange-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {event.action?.toUpperCase()} - {event.document_name || event.metadata?.document_name || 'Document'}
                      </p>
                      <p className="text-xs text-gray-500 flex items-center mt-1">
                        <Clock className="w-3 h-3 mr-1" />
                        {formatDateTimeIST(event.timestamp)}
                      </p>
                      {event.is_cross_department && (
                        <p className="text-xs text-amber-600 mt-1">⚠️ Cross-department</p>
                      )}
                    </div>
                    <RiskBadge level={event.risk_level?.toUpperCase() || 'LOW'} size="sm" />
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No recent activity</p>
                  <p className="text-xs mt-1">Your document actions will appear here</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UserDashboard;
