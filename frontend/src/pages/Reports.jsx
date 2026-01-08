import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { reportsAPI, mlAPI } from '../api/client';
import { formatDateTimeIST } from '../utils/dateUtils';
import RiskBadge from '../components/RiskBadge';
import {
  FileText,
  Download,
  Calendar,
  Clock,
  TrendingUp,
  AlertTriangle,
  Users,
  RefreshCw,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

function Reports() {
  const [reportType, setReportType] = useState('daily');
  const [generating, setGenerating] = useState(false);

  // Fetch daily report
  const { data: dailyReport, refetch: refetchDaily } = useQuery({
    queryKey: ['reports', 'daily'],
    queryFn: () => reportsAPI.daily(),
    enabled: reportType === 'daily',
  });

  // Fetch weekly report
  const { data: weeklyReport, refetch: refetchWeekly } = useQuery({
    queryKey: ['reports', 'weekly'],
    queryFn: () => reportsAPI.weekly(),
    enabled: reportType === 'weekly',
  });

  // Fetch REAL alerts by day data
  const { data: alertsTrendData } = useQuery({
    queryKey: ['alerts-by-day'],
    queryFn: () => mlAPI.getAlertsByDay(7),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch report summary for real stats
  const { data: reportSummaryData } = useQuery({
    queryKey: ['report-summary'],
    queryFn: () => mlAPI.getReportSummary(),
    refetchInterval: 30000,
  });

  // Generate report mutation
  const generateReportMutation = useMutation({
    mutationFn: (type) => {
      // Build proper request payload for the API
      const now = new Date();
      const startDate = type === 'weekly' 
        ? new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        : new Date(now.getTime() - 24 * 60 * 60 * 1000);
      
      return reportsAPI.generate({
        title: `${type.charAt(0).toUpperCase() + type.slice(1)} Security Report`,
        report_type: type,
        start_date: startDate.toISOString(),
        end_date: now.toISOString(),
        include_alerts: true,
        include_explanations: true,
        description: `Auto-generated ${type} security report`
      });
    },
    onSuccess: () => {
      setGenerating(false);
      if (reportType === 'daily') refetchDaily();
      else refetchWeekly();
    },
  });

  const currentReport = reportType === 'daily' ? dailyReport : weeklyReport;

  // ALWAYS use reportSummaryData for stats cards - it has real-time data
  // currentReport is only used for downloading generated reports
  const statsData = reportSummaryData || {};

  // Use REAL alerts by day data from API
  const alertsByDay = alertsTrendData?.data || [];

  const handleGenerateReport = () => {
    setGenerating(true);
    generateReportMutation.mutate(reportType);
  };

  // Download report as JSON (can be converted to PDF in production)
  const handleDownloadReport = () => {
    // Use reportSummaryData which has real-time stats
    const dataSource = reportSummaryData || {};
    
    if (!dataSource.total_events && dataSource.total_events !== 0) {
      alert('No report data available. Please wait for data to load.');
      return;
    }

    // Create report content from real-time summary data
    const reportContent = {
      title: `${reportType.charAt(0).toUpperCase() + reportType.slice(1)} Security Report`,
      generated_at: new Date().toISOString(),
      period: dataSource.period || reportType,
      summary: {
        total_events: dataSource.total_events || 0,
        alerts_generated: dataSource.alerts_generated || 0,
        anomalies_detected: dataSource.high_risk_count || 0,
        documents_accessed: dataSource.users_analyzed || 0,
        average_risk_score: dataSource.avg_risk_score || 0,
        critical_alerts: dataSource.critical_count || 0,
      },
      top_risk_events: dataSource.top_events || [],
      xai_summary: 'ML-based threat detection with LIME/SHAP explanations',
    };

    // Download as JSON file
    const blob = new Blob([JSON.stringify(reportContent, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security_report_${reportType}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Security Reports</h1>
          <p className="text-gray-500 mt-1">
            Generate and view threat detection reports
          </p>
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={generating}
          className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {generating ? (
            <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
          ) : (
            <FileText className="w-5 h-5 mr-2" />
          )}
          Generate Report
        </button>
      </div>

      {/* Report Type Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1 inline-flex">
        <button
          onClick={() => setReportType('daily')}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            reportType === 'daily'
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Daily Report
        </button>
        <button
          onClick={() => setReportType('weekly')}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            reportType === 'weekly'
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Weekly Report
        </button>
      </div>

      {/* Report Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Total Events"
          value={statsData?.total_events || 0}
          icon={TrendingUp}
          color="blue"
        />
        <SummaryCard
          title="Alerts Generated"
          value={statsData?.alerts_generated || 0}
          icon={AlertTriangle}
          color="red"
        />
        <SummaryCard
          title="Users Analyzed"
          value={statsData?.users_analyzed || 0}
          icon={Users}
          color="purple"
        />
        <SummaryCard
          title="High Risk Events"
          value={statsData?.high_risk_count || 0}
          icon={AlertTriangle}
          color="orange"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alert Trend Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Activity by Day
          </h2>
          <p className="text-sm text-gray-500 mb-4">Real-time data from the last 7 days</p>
          {alertsByDay.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={alertsByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="day" stroke="#6B7280" fontSize={12} />
                <YAxis stroke="#6B7280" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                  formatter={(value, name) => {
                    const labels = {
                      events: 'Total Events',
                      alerts: 'Alerts',
                      high_risk: 'High Risk Events'
                    };
                    return [value, labels[name] || name];
                  }}
                />
                <Legend />
                <Bar dataKey="events" fill="#3B82F6" name="Events" radius={[4, 4, 0, 0]} />
                <Bar dataKey="alerts" fill="#EF4444" name="Alerts" radius={[4, 4, 0, 0]} />
                <Bar dataKey="high_risk" fill="#F59E0B" name="High Risk" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-500">
              <div className="text-center">
                <AlertTriangle className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No activity data available</p>
                <p className="text-sm">Events will appear here as they occur</p>
              </div>
            </div>
          )}
        </div>

        {/* Report Details */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Report Details
          </h2>
          <div className="space-y-4">
            <DetailRow
              icon={Calendar}
              label="Report Period"
              value={reportType === 'daily' ? 'Last 24 Hours' : 'Last 7 Days'}
            />
            <DetailRow
              icon={Clock}
              label="Generated At"
              value={
                statsData?.generated_at
                  ? formatDateTimeIST(statsData.generated_at)
                  : 'N/A'
              }
            />
            <DetailRow
              icon={TrendingUp}
              label="Average Risk Score"
              value={`${((statsData?.avg_risk_score || 0) * 100).toFixed(1)}%`}
            />
            <DetailRow
              icon={AlertTriangle}
              label="Critical Alerts"
              value={statsData?.critical_count || 0}
            />
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <button
              onClick={handleDownloadReport}
              className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Download className="w-5 h-5 mr-2" />
              Download Report (JSON)
            </button>
          </div>
        </div>
      </div>

      {/* Top Risk Events Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Top Risk Events
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Event
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {(statsData?.top_events || []).length > 0 ? (
                statsData.top_events.map((event, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {event.action}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {event.user}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {event.department}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {(event.risk_score * 100).toFixed(1)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <RiskBadge level={event.severity} size="sm" />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTimeIST(event.timestamp)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No events in the report period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Summary Card Component
function SummaryCard({ title, value, icon: Icon, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className={`inline-flex p-3 rounded-lg ${colors[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <p className="mt-4 text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{title}</p>
    </div>
  );
}

// Detail Row Component
function DetailRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <Icon className="w-5 h-5 text-gray-400" />
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default Reports;
