import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { alertsAPI, reportsAPI, mlAPI, eventsAPI } from '../api/client';
import { formatDateTimeIST, formatTimeIST } from '../utils/dateUtils';
import ShapChart from '../components/ShapChart';
import LimeViewer from '../components/LimeViewer';
import DiffViewer from '../components/DiffViewer';
import RiskBadge from '../components/RiskBadge';
import useWebSocket from '../hooks/useWebSocket';
import {
  BarChart3,
  Activity,
  FileWarning,
  Users,
  TrendingUp,
  AlertTriangle,
  Brain,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const RISK_COLORS = {
  CRITICAL: '#DC2626',
  HIGH: '#EA580C',
  MEDIUM: '#CA8A04',
  LOW: '#16A34A',
};

function AnalystDashboard() {
  const [selectedUser, setSelectedUser] = useState(null);
  const [expandedAlerts, setExpandedAlerts] = useState(new Set());
  const [selectedModification, setSelectedModification] = useState(null);
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [liveEvents, setLiveEvents] = useState([]);
  
  const queryClient = useQueryClient();

  // WebSocket for real-time updates
  const { isConnected, messages, connectionError } = useWebSocket((message) => {
    console.log('📨 Real-time update:', message);
    
    // Handle different message types
    if (message.type === 'new_alert') {
      // Add complete alert to live alerts at the top
      if (message.alert) {
        setLiveAlerts(prev => [{
          ...message.alert,
          isNew: true
        }, ...prev.slice(0, 9)]); // Keep last 10
      }
      
      // Invalidate alerts query to refresh
      queryClient.invalidateQueries(['alerts']);
      
      // Show notification
      if (message.alert?.priority === 'critical' || message.alert?.priority === 'high') {
        showNotification(
          `🚨 ${message.alert.summary || 'Security Alert'}`,
          message.alert.priority
        );
      }
    }
    
    if (message.type === 'new_event') {
      // Add to live events
      setLiveEvents(prev => [{
        event_id: message.event_id,
        user_id: message.user_id,
        action: message.action,
        document_name: message.document_name,
        risk_score: message.risk_score,
        risk_level: message.risk_level,
        timestamp: message.timestamp,
        isNew: true
      }, ...prev.slice(0, 9)]); // Keep last 10
      
      // Invalidate related queries
      queryClient.invalidateQueries(['events']);
      queryClient.invalidateQueries(['ml', 'top-risk-users']);
      queryClient.invalidateQueries(['ml', 'anomaly-timeline']);
    }
    
    if (message.type === 'system_status') {
      // Update pipeline status
      queryClient.invalidateQueries(['ml', 'status']);
    }
  });

  // Helper function for notifications
  const showNotification = (title, level) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body: `${level.toUpperCase()} risk alert detected`,
        icon: '/favicon.ico'
      });
    }
  };

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Fetch alerts summary
  const { data: alertsData, isLoading: loadingAlerts } = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => alertsAPI.list({ page_size: 100 }),  // Use page_size instead of limit
  });

  // Fetch daily report
  const { data: dailyReport, isLoading: loadingReport } = useQuery({
    queryKey: ['reports', 'daily'],
    queryFn: () => reportsAPI.daily(),
  });

  // Fetch ML pipeline status - REAL DATA
  const { data: pipelineStatus, isLoading: loadingStatus } = useQuery({
    queryKey: ['ml', 'status'],
    queryFn: () => mlAPI.status(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch anomaly timeline - REAL DATA
  const { data: timelineData } = useQuery({
    queryKey: ['ml', 'anomaly-timeline'],
    queryFn: () => mlAPI.getAnomalyTimeline(24),
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch top risk users - REAL DATA
  const { data: topRiskData } = useQuery({
    queryKey: ['ml', 'top-risk-users'],
    queryFn: () => mlAPI.getTopRiskUsers(5),
    refetchInterval: 60000,
  });

  // Fetch document modifications - REAL DATA
  const { data: modificationsData } = useQuery({
    queryKey: ['ml', 'document-modifications'],
    queryFn: () => mlAPI.getDocumentModifications(10),
    refetchInterval: 15000, // Refresh every 15 seconds
  });

  // Fetch feature importance - REAL DATA from events
  const { data: featureImportanceData } = useQuery({
    queryKey: ['ml', 'feature-importance'],
    queryFn: () => mlAPI.getFeatureImportance(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch recent events - ALL EVENTS for analyst view
  const { data: recentEventsData } = useQuery({
    queryKey: ['events', 'all'],
    queryFn: () => eventsAPI.getAll({ limit: 10 }),
    refetchInterval: 15000, // Refresh every 15 seconds
  });

  // Use real data from API or empty defaults (NO fake fallbacks)
  const anomalyTimeline = timelineData?.timeline || [];
  
  // Calculate risk distribution from real alerts (merge DB alerts + live alerts)
  const dbAlerts = alertsData?.alerts || [];
  const allAlerts = [...liveAlerts, ...dbAlerts];
  const alerts = allAlerts.filter((alert, index, self) => 
    index === self.findIndex(a => a.alert_id === alert.alert_id)
  ); // Deduplicate
  
  const riskDistribution = [
    { name: 'Critical', value: alerts.filter(a => a.severity === 'CRITICAL' || a.priority === 'CRITICAL').length, color: RISK_COLORS.CRITICAL },
    { name: 'High', value: alerts.filter(a => a.severity === 'HIGH' || a.priority === 'HIGH').length, color: RISK_COLORS.HIGH },
    { name: 'Medium', value: alerts.filter(a => a.severity === 'MEDIUM' || a.priority === 'MEDIUM').length, color: RISK_COLORS.MEDIUM },
    { name: 'Low', value: alerts.filter(a => a.severity === 'LOW' || a.priority === 'LOW').length, color: RISK_COLORS.LOW },
  ];

  // Use real top risk users from API - filter to show only users with activity
  const topRiskUsers = (topRiskData?.users || [])
    .filter(u => u.event_count > 0 || u.risk_score > 0)  // Only show users with activity
    .slice(0, 5)  // Top 5
    .map(u => ({
      user: u.username,
      department: u.department,
      riskScore: u.risk_score,
      anomalyCount: u.anomaly_count,
      eventCount: u.event_count
    }));

  // Recent alerts sorted by time (not priority) to show mix of alert levels
  const recentAlerts = [...alerts]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 10); // Show top 10 most recent

  // Show loading state
  const isLoading = loadingAlerts || loadingReport || loadingStatus;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analyst Dashboard</h1>
          <p className="text-gray-500 mt-1">
            ML-powered insider threat analysis and explainability
            {pipelineStatus?.last_updated && (
              <span className="ml-2 text-xs text-gray-400">
                Last updated: {formatTimeIST(pipelineStatus.last_updated)}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* Real-time connection status */}
          <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg border ${
            isConnected ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            }`} />
            <span className={`text-xs font-medium ${
              isConnected ? 'text-green-700' : 'text-gray-500'
            }`}>
              {isConnected ? 'Live' : 'Connecting...'}
            </span>
            {connectionError && (
              <span className="text-xs text-red-600">({connectionError})</span>
            )}
          </div>
          
          {/* Pipeline status */}
          <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
            pipelineStatus?.pipeline_active ? 'bg-blue-50' : 'bg-gray-50'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              pipelineStatus?.pipeline_active ? 'bg-blue-500 animate-pulse' : 'bg-gray-400'
            }`} />
            <span className={`text-sm ${
              pipelineStatus?.pipeline_active ? 'text-blue-700' : 'text-gray-500'
            }`}>
              {pipelineStatus?.pipeline_active ? 'Pipeline Active' : 'Loading...'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Cards - ALL REAL DATA, NO FAKE FALLBACKS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Alerts"
          value={alertsData?.stats?.open ?? (isLoading ? '...' : 0)}
          icon={AlertTriangle}
          trend={pipelineStatus?.alerts_today > 0 ? `+${pipelineStatus.alerts_today} today` : 'No new alerts'}
          trendUp={pipelineStatus?.alerts_today > 0}
          color="red"
        />
        <StatCard
          title="Users Monitored"
          value={pipelineStatus?.users_monitored ?? (isLoading ? '...' : 0)}
          icon={Users}
          trend="Active users"
          trendUp={true}
          color="blue"
        />
        <StatCard
          title="Documents Scanned"
          value={pipelineStatus?.documents_processed ?? (isLoading ? '...' : 0)}
          icon={FileText}
          trend={`${pipelineStatus?.healthy_documents || 0} healthy`}
          trendUp={true}
          color="purple"
        />
        <StatCard
          title="Anomalies Today"
          value={pipelineStatus?.anomalies_today ?? (isLoading ? '...' : 0)}
          icon={Activity}
          trend={`Avg risk: ${((pipelineStatus?.avg_risk_score_today || 0) * 100).toFixed(0)}%`}
          trendUp={false}
          color="orange"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomaly Timeline Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Anomaly Score Timeline (24h)</h2>
            <span className="text-xs text-gray-400">
              {anomalyTimeline.length > 0 ? `${anomalyTimeline.reduce((sum, t) => sum + t.event_count, 0)} events` : 'No events yet'}
            </span>
          </div>
          {anomalyTimeline.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={anomalyTimeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="time" stroke="#6B7280" fontSize={12} />
                <YAxis stroke="#6B7280" fontSize={12} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                  formatter={(value, name) => [
                    typeof value === 'number' ? value.toFixed(3) : value,
                    name === 'avg_score' ? 'Avg Risk' : name === 'max_score' ? 'Max Risk' : 'Events'
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="avg_score"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', r: 3 }}
                  activeDot={{ r: 5 }}
                  name="Avg Risk"
                />
                <Line
                  type="monotone"
                  dataKey="max_score"
                  stroke="#EF4444"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Max Risk"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No events recorded yet</p>
                <p className="text-sm">Perform document actions to see data</p>
              </div>
            </div>
          )}
        </div>

        {/* Risk Distribution Pie Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Alert Distribution</h2>
          {riskDistribution.some(r => r.value > 0) ? (
            <>
              <div className="flex items-center justify-center">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={riskDistribution.filter(r => r.value > 0)}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {riskDistribution.filter(r => r.value > 0).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center space-x-4 mt-4">
                {riskDistribution.filter(r => r.value > 0).map((item) => (
                  <div key={item.name} className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-sm text-gray-600">{item.name}: {item.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <AlertTriangle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No alerts recorded yet</p>
                <p className="text-sm">Alerts will appear when risk thresholds are exceeded</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SHAP Feature Importance & LIME Explanation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SHAP Feature Importance */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-2 mb-6">
            <Brain className="w-5 h-5 text-purple-500" />
            <h2 className="text-lg font-semibold text-gray-900">SHAP Feature Importance</h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            Feature importance based on actual event analysis
            {featureImportanceData?.total_events > 0 && (
              <span className="ml-2 text-xs text-gray-400">
                ({featureImportanceData.total_events} events analyzed)
              </span>
            )}
          </p>
          {(featureImportanceData?.features || []).length > 0 ? (
            <ShapChart
              features={(featureImportanceData?.features || []).map(f => ({
                name: f.name,
                importance: f.importance
              }))}
            />
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Brain className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No feature importance data yet</p>
                <p className="text-sm">Perform document actions to generate data</p>
              </div>
            </div>
          )}
        </div>

        {/* Top Risk Users */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-2 mb-6">
            <TrendingUp className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-semibold text-gray-900">Top Risk Users (24h)</h2>
          </div>
          {topRiskUsers.length > 0 ? (
            <div className="space-y-4">
              {topRiskUsers.map((user, index) => (
                <div
                  key={user.user}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                  onClick={() => setSelectedUser(user)}
                >
                  <div className="flex items-center space-x-4">
                    <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-sm font-medium">
                      {index + 1}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{user.user}</p>
                      <p className="text-sm text-gray-500">{user.department}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-semibold ${user.riskScore >= 0.6 ? 'text-red-600' : user.riskScore >= 0.3 ? 'text-yellow-600' : 'text-green-600'}`}>
                      {(user.riskScore * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-gray-500">{user.eventCount} events</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No user activity yet</p>
                <p className="text-sm">User risk scores will appear after actions</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Alerts with Explanations */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Alerts with Explanations</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentAlerts.length > 0 ? (
            recentAlerts.map((alert) => {
              const alertId = alert.alert_id || alert.id;
              return (
                <AlertItem
                  key={alertId}
                  alert={alert}
                  expanded={expandedAlerts.has(alertId)}
                  onToggle={() => {
                    setExpandedAlerts(prev => {
                      const newSet = new Set(prev);
                      if (newSet.has(alertId)) {
                        newSet.delete(alertId);
                      } else {
                        newSet.add(alertId);
                      }
                      return newSet;
                    });
                  }}
                />
              );
            })
          ) : (
            <div className="p-8 text-center text-gray-500">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No recent alerts</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity Feed - Real-time events */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity (All Users)</h2>
          <span className="text-xs text-gray-400">Auto-refreshes every 15s</span>
        </div>
        <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
          {(Array.isArray(recentEventsData) ? recentEventsData : []).length > 0 ? (
            (Array.isArray(recentEventsData) ? recentEventsData : []).map((event) => (
              <div key={event.event_id} className="px-6 py-3 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${
                      event.risk_score >= 0.6 ? 'bg-red-500' : 
                      event.risk_score >= 0.3 ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        <span className="text-blue-600">{event.username}</span>
                        {' '}{event.action === 'view' ? 'viewed' : event.action === 'download' ? 'downloaded' : event.action === 'upload' ? 'uploaded' : event.action === 'modify' ? 'modified' : event.action + 'ed'}{' '}
                        <span className="text-gray-600">{event.document_name}</span>
                      </p>
                      <p className="text-xs text-gray-500">
                        {event.user_department} → {event.target_department}
                        {event.is_cross_department && (
                          <span className="ml-2 text-amber-600">⚠️ Cross-dept</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-semibold ${
                      event.risk_score >= 0.6 ? 'text-red-600' : 
                      event.risk_score >= 0.3 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {(event.risk_score * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-gray-400">
                      {formatTimeIST(event.timestamp)}
                    </p>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No activity yet</p>
              <p className="text-sm">User actions will appear here in real-time</p>
            </div>
          )}
        </div>
      </div>

      {/* Document Integrity Section - REAL MODIFICATIONS */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2">
            <FileWarning className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold text-gray-900">Document Integrity Alerts</h2>
          </div>
          <span className="text-xs text-gray-400">
            {modificationsData?.total || 0} modifications tracked
          </span>
        </div>
        
        {(modificationsData?.modifications || []).length > 0 ? (
          <div className="space-y-4">
            {/* Modification List */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-h-[600px] overflow-y-auto">
              {(modificationsData?.modifications || []).map((mod) => (
                <div 
                  key={mod.modification_id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedModification?.modification_id === mod.modification_id
                      ? 'border-blue-500 bg-blue-50'
                      : mod.is_cross_department
                        ? 'border-red-200 bg-red-50 hover:border-red-400'
                        : 'border-gray-200 hover:border-gray-400'
                  }`}
                  onClick={() => setSelectedModification(
                    selectedModification?.modification_id === mod.modification_id ? null : mod
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-900 truncate max-w-[60%]">
                      {mod.document_name}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      mod.risk_score >= 0.6 ? 'bg-red-100 text-red-700' :
                      mod.risk_score >= 0.4 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {(mod.risk_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    <span className="text-blue-600 font-medium">{mod.username}</span>
                    <span>•</span>
                    <span>{mod.user_department} → {mod.target_department}</span>
                    {mod.is_cross_department && (
                      <span className="text-red-600">⚠️ Cross-dept</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs">
                    <span className="text-gray-400">
                      {formatDateTimeIST(mod.modified_at)}
                    </span>
                    <span className={mod.chars_added > mod.chars_removed ? 'text-green-600' : 'text-red-600'}>
                      {mod.chars_added > 0 && `+${mod.chars_added}`}
                      {mod.chars_removed > 0 && ` -${mod.chars_removed}`}
                      {' '}chars ({mod.change_percent}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Selected Modification Diff View */}
            {selectedModification && (
              <div className="mt-6 p-4 border border-blue-200 rounded-lg bg-blue-50/50">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-900">
                    Diff: {selectedModification.document_name}
                  </h3>
                  <button 
                    onClick={() => setSelectedModification(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                <DiffViewer
                  original={selectedModification.original_content || 'No original content recorded'}
                  tampered={selectedModification.modified_content || 'No modified content recorded'}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <FileWarning className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No document modifications recorded yet</p>
            <p className="text-sm">Modify documents from User Dashboard to see changes here</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ title, value, icon: Icon, trend, trendUp, color }) {
  const colors = {
    red: 'bg-red-50 text-red-600',
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <span
          className={`text-sm font-medium ${
            trendUp ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {trend}
        </span>
      </div>
      <p className="mt-4 text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{title}</p>
    </div>
  );
}

// Alert Item Component
function AlertItem({ alert, expanded, onToggle }) {
  // Extract ML explanation from alert details if available
  const details = alert.details || {};
  const mlExplanation = details.ml_explanation;
  const riskIndicators = details.risk_indicators || [];
  const sensitivityMismatch = details.sensitivity_mismatch;
  const userDeclared = details.user_declared_sensitivity;
  const mlPredicted = details.ml_predicted_sensitivity;
  const mlConfidence = details.ml_confidence;

  return (
    <div className="px-6 py-4">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center space-x-4">
          <RiskBadge level={alert.severity} />
          <div>
            <p className="font-medium text-gray-900">{alert.description}</p>
            <p className="text-sm text-gray-500">
              User: {alert.user_id} • {formatDateTimeIST(alert.created_at)}
            </p>
          </div>
        </div>
        <button className="p-2 hover:bg-gray-100 rounded-lg">
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium text-gray-900 mb-2">Explanation</h4>
          
          {/* Show ML Sensitivity Mismatch explanation if available */}
          {sensitivityMismatch && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm font-semibold text-red-800 mb-2">
                ⚠️ Sensitivity Mismatch Detected
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
            </div>
          )}

          {/* Show ML explanation text */}
          {mlExplanation && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-semibold text-blue-800 mb-1">ML Analysis</p>
              <p className="text-sm text-blue-700">{mlExplanation}</p>
            </div>
          )}

          {/* Show risk indicators if available */}
          {riskIndicators.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-semibold text-gray-700 mb-2">Risk Indicators Found:</p>
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

          {/* Show LIME highlights if available (for batch-analyzed documents) */}
          {alert.explanation?.highlights && alert.explanation.highlights.length > 0 ? (
            <LimeViewer
              text={alert.metadata?.document_content || details.document_content || 'Document content...'}
              highlights={alert.explanation.highlights}
            />
          ) : (
            /* Show document content preview if no LIME highlights */
            (alert.metadata?.document_content || details.document_content) && (
              <div className="p-3 bg-white border border-gray-200 rounded-lg">
                <p className="text-xs text-gray-500 mb-2">Document Content Preview:</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {(alert.metadata?.document_content || details.document_content || '').slice(0, 500)}
                  {(alert.metadata?.document_content || details.document_content || '').length > 500 && '...'}
                </p>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}

export default AnalystDashboard;
