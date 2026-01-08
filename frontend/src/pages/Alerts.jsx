import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsAPI, authAPI } from '../api/client';
import { formatDateTimeIST } from '../utils/dateUtils';
import RiskBadge from '../components/RiskBadge';
import {
  AlertTriangle,
  Search,
  Filter,
  CheckCircle,
  Clock,
  User,
  ChevronRight,
  X,
} from 'lucide-react';

const SEVERITY_OPTIONS = ['ALL', 'critical', 'high', 'medium', 'low'];
const STATUS_OPTIONS = ['ALL', 'open', 'investigating', 'resolved', 'dismissed'];

function Alerts() {
  const [filters, setFilters] = useState({
    severity: 'ALL',
    status: 'ALL',
    search: '',
  });
  const [selectedAlert, setSelectedAlert] = useState(null);
  const queryClient = useQueryClient();
  const user = authAPI.getStoredUser();

  // Fetch alerts (only for analysts/admins)
  const { data: alertsData, isLoading, error } = useQuery({
    queryKey: ['alerts', filters],
    queryFn: () =>
      alertsAPI.list({
        severity: filters.severity !== 'ALL' ? filters.severity : undefined,
        status: filters.status !== 'ALL' ? filters.status : undefined,
        limit: 50,
      }),
    enabled: user && (user.role === 'ANALYST' || user.role === 'ADMIN'),
  });

  // Update alert mutation
  const updateAlertMutation = useMutation({
    mutationFn: ({ alertId, data }) => alertsAPI.update(alertId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts']);
    },
  });

  // Assign alert mutation
  const assignAlertMutation = useMutation({
    mutationFn: ({ alertId, analystId }) => alertsAPI.assign(alertId, analystId),
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts']);
    },
  });

  // Resolve alert mutation
  const resolveAlertMutation = useMutation({
    mutationFn: ({ alertId, resolution }) => alertsAPI.resolve(alertId, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts']);
      setSelectedAlert(null);
    },
  });

  const handleAssignToMe = (alertId) => {
    assignAlertMutation.mutate({ alertId, analystId: user?.id });
  };

  const handleResolve = (alertId, resolution) => {
    resolveAlertMutation.mutate({ alertId, resolution });
  };

  const filteredAlerts = (alertsData?.alerts || []).filter((alert) =>
    (alert.summary || '').toLowerCase().includes(filters.search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Security Alerts</h1>
          <p className="text-gray-500 mt-1">
            Monitor and manage insider threat alerts
          </p>
        </div>
        <div className="flex items-center space-x-2 px-4 py-2 bg-red-50 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          <span className="text-sm font-medium text-red-700">
            {alertsData?.alerts?.filter((a) => a.status === 'open').length || 0} Open
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={filters.search}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
          </div>

          {/* Severity Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={filters.severity}
              onChange={(e) => setFilters((f) => ({ ...f, severity: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none capitalize"
            >
              {SEVERITY_OPTIONS.map((opt) => (
                <option key={opt} value={opt} className="capitalize">
                  {opt === 'ALL' ? 'All Severities' : opt.charAt(0).toUpperCase() + opt.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <select
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none capitalize"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt} className="capitalize">
                {opt === 'ALL' ? 'All Status' : opt.charAt(0).toUpperCase() + opt.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Alerts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alert List */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="divide-y divide-gray-200">
              {isLoading ? (
                <div className="p-8 text-center">
                  <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
                  <p className="mt-2 text-gray-500">Loading alerts...</p>
                </div>
                  ) : user && (user.role !== 'ANALYST' && user.role !== 'ADMIN') ? (
                    <div className="p-8 text-center text-gray-500">
                      <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>Alerts are visible to security analysts only.</p>
                    </div>
                  ) : filteredAlerts.length > 0 ? (
                filteredAlerts.map((alert) => (
                  <AlertRow
                    key={alert.alert_id}
                    alert={alert}
                    selected={selectedAlert?.alert_id === alert.alert_id}
                    onClick={() => setSelectedAlert(alert)}
                    onAssign={() => handleAssignToMe(alert.alert_id)}
                  />
                ))
              ) : (
                <div className="p-8 text-center text-gray-500">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No alerts found</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Alert Details Panel */}
        <div className="lg:col-span-1">
          {selectedAlert ? (
            <AlertDetailPanel
              alert={selectedAlert}
              onClose={() => setSelectedAlert(null)}
              onResolve={handleResolve}
            />
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center text-gray-500">
              <ChevronRight className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Select an alert to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Alert Row Component
function AlertRow({ alert, selected, onClick, onAssign }) {
  return (
    <div
      className={`p-4 cursor-pointer transition-colors ${
        selected ? 'bg-blue-50' : 'hover:bg-gray-50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <RiskBadge level={alert.priority} />
          <div>
            <p className="font-medium text-gray-900 line-clamp-1">{alert.summary}</p>
            <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
              <span className="flex items-center">
                <User className="w-4 h-4 mr-1" />
                User {alert.user_id}
              </span>
              <span className="flex items-center">
                <Clock className="w-4 h-4 mr-1" />
                {formatDateTimeIST(alert.created_at)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <StatusBadge status={alert.status} />
          {alert.status === 'open' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAssign();
              }}
              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
            >
              Assign
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Status Badge Component
function StatusBadge({ status }) {
  const styles = {
    open: 'bg-red-100 text-red-700',
    investigating: 'bg-yellow-100 text-yellow-700',
    resolved: 'bg-green-100 text-green-700',
    dismissed: 'bg-gray-100 text-gray-700',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded capitalize ${styles[status] || styles.open}`}>
      {status}
    </span>
  );
}

// Alert Detail Panel Component
function AlertDetailPanel({ alert, onClose, onResolve }) {
  const [resolution, setResolution] = useState('');
  
  // Extract ML explanation from alert details
  const details = alert.details || {};
  const mlExplanation = details.ml_explanation;
  const riskIndicators = details.risk_indicators || [];
  const sensitivityMismatch = details.sensitivity_mismatch;
  const userDeclared = details.user_declared_sensitivity;
  const mlPredicted = details.ml_predicted_sensitivity;
  const mlConfidence = details.ml_confidence;
  const isCrossDepartment = details.is_cross_department;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Alert Details</h3>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
        <div>
          <RiskBadge level={alert.priority} />
          <p className="mt-2 text-gray-900 font-medium">{alert.summary}</p>
        </div>

        {/* ML Sensitivity Mismatch Alert */}
        {sensitivityMismatch && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm font-semibold text-red-800 mb-3">
              ⚠️ Sensitivity Classification Mismatch
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-600">User declared:</div>
              <div className="font-medium text-gray-900 uppercase">{userDeclared}</div>
              <div className="text-gray-600">ML predicted:</div>
              <div className="font-medium text-red-700 uppercase">{mlPredicted}</div>
              {mlConfidence && (
                <>
                  <div className="text-gray-600">ML confidence:</div>
                  <div className="font-medium text-gray-900">{(mlConfidence * 100).toFixed(0)}%</div>
                </>
              )}
            </div>
            <p className="text-xs text-red-600 mt-2">
              The user may be attempting to downgrade document sensitivity to bypass security controls.
            </p>
          </div>
        )}

        {/* Cross-Department Alert */}
        {isCrossDepartment && !sensitivityMismatch && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm font-semibold text-amber-800 mb-1">
              ⚠️ Cross-Department Activity
            </p>
            <p className="text-sm text-amber-700">
              User from {details.user_department} uploaded to {details.target_department}
            </p>
          </div>
        )}

        {/* ML Explanation */}
        {mlExplanation && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm font-semibold text-blue-800 mb-2">ML Analysis</p>
            <p className="text-sm text-blue-700">{mlExplanation}</p>
          </div>
        )}

        {/* Risk Indicators */}
        {riskIndicators.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Risk Indicators Detected:</p>
            <div className="flex flex-wrap gap-2">
              {riskIndicators.map((indicator, idx) => (
                <span 
                  key={idx} 
                  className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded"
                >
                  {indicator}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          <InfoRow label="Alert ID" value={alert.alert_id} />
          <InfoRow label="User ID" value={alert.user_id} />
          <InfoRow label="Event ID" value={alert.event_id} />
          {details.filename && <InfoRow label="Document" value={details.filename} />}
          <InfoRow label="Status" value={<StatusBadge status={alert.status} />} />
          <InfoRow
            label="Created"
            value={formatDateTimeIST(alert.created_at)}
          />
          {alert.assigned_to && (
            <InfoRow label="Assigned To" value={`Analyst ${alert.assigned_to}`} />
          )}
        </div>

        {alert.status !== 'resolved' && (
          <div className="space-y-3 pt-4 border-t border-gray-200">
            <label className="block text-sm font-medium text-gray-700">
              Resolution Notes
            </label>
            <textarea
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="Enter resolution notes..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
              rows={3}
            />
            <button
              onClick={() => onResolve(alert.alert_id, resolution)}
              className="w-full py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <CheckCircle className="w-5 h-5 mr-2" />
              Resolve Alert
            </button>
          </div>
        )}

        {alert.resolution && (
          <div className="pt-4 border-t border-gray-200">
            <p className="text-sm font-medium text-gray-700">Resolution:</p>
            <p className="mt-1 text-sm text-gray-600">{alert.resolution}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Info Row Component
function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default Alerts;
