import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  FileText,
  Download,
  Calendar,
  Filter,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Wrench,
  Clock,
  Package,
  ClipboardCheck,
  FileSpreadsheet,
  File,
} from 'lucide-react';
import {
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
import { getReportTypes, generateReport, downloadReport, ReportParams, getUsers } from '../lib/api';
import { format, subDays } from 'date-fns';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

const categoryIcons: Record<string, React.ReactNode> = {
  'Work Orders': <BarChart3 className="w-5 h-5" />,
  'Assets': <Wrench className="w-5 h-5" />,
  'Preventive Maintenance': <ClipboardCheck className="w-5 h-5" />,
  'Labor': <Clock className="w-5 h-5" />,
  'Inventory': <Package className="w-5 h-5" />,
};

interface ReportType {
  id: string;
  name: string;
  description: string;
}

interface ReportData {
  report?: { name: string; description: string };
  period?: { start: string; end: string };
  summary?: Record<string, unknown>;
  summary_metrics?: Array<{ label: string; value: string | number }>;
  sections?: Array<{
    title: string;
    headers: string[];
    rows: Array<Array<string | number>>;
  }>;
  [key: string]: unknown;
}

export default function Reports() {
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    'Work Orders': true,
    'Assets': true,
    'Preventive Maintenance': true,
    'Labor': true,
    'Inventory': true,
  });
  const [filters, setFilters] = useState<ReportParams>({
    start_date: format(subDays(new Date(), 90), 'yyyy-MM-dd'),
    end_date: format(new Date(), 'yyyy-MM-dd'),
  });
  const [showFilters, setShowFilters] = useState(false);
  const [reportData, setReportData] = useState<ReportData | null>(null);

  // Queries
  const { data: reportTypesData } = useQuery({
    queryKey: ['report-types'],
    queryFn: getReportTypes,
  });

  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
  });

  // Mutations
  const generateMutation = useMutation({
    mutationFn: ({ reportType, params }: { reportType: string; params: ReportParams }) =>
      generateReport(reportType, { ...params, format: 'json' }),
    onSuccess: (response) => {
      setReportData(response.data);
    },
    onError: () => {
      toast.error('Failed to generate report');
    },
  });

  const downloadMutation = useMutation({
    mutationFn: ({ reportType, params }: { reportType: string; params: ReportParams }) =>
      downloadReport(reportType, params),
    onSuccess: () => {
      toast.success('Report downloaded successfully');
    },
    onError: () => {
      toast.error('Failed to download report');
    },
  });

  const handleGenerateReport = () => {
    if (!selectedReport) {
      toast.error('Please select a report type');
      return;
    }
    generateMutation.mutate({ reportType: selectedReport, params: filters });
  };

  const handleDownload = (format: 'pdf' | 'excel' | 'csv') => {
    if (!selectedReport) {
      toast.error('Please select a report type');
      return;
    }
    downloadMutation.mutate({
      reportType: selectedReport,
      params: { ...filters, format },
    });
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const categories = reportTypesData?.categories || {};

  // Find selected report info
  let selectedReportInfo: ReportType | null = null;
  for (const reports of Object.values(categories) as ReportType[][]) {
    const found = reports.find((r: ReportType) => r.id === selectedReport);
    if (found) {
      selectedReportInfo = found;
      break;
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600">Generate and export maintenance reports</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Report Selection Sidebar */}
        <div className="lg:col-span-1">
          <div className="card">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Report Types
            </h2>
            <div className="space-y-1">
              {Object.entries(categories).map(([category, reports]) => (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center justify-between p-2 text-left hover:bg-gray-50 rounded-lg"
                  >
                    <span className="flex items-center gap-2 font-medium text-gray-700">
                      {categoryIcons[category] || <FileText className="w-5 h-5" />}
                      {category}
                    </span>
                    {expandedCategories[category] ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  {expandedCategories[category] && (
                    <div className="ml-4 space-y-1 mt-1">
                      {(reports as ReportType[]).map((report) => (
                        <button
                          key={report.id}
                          onClick={() => {
                            setSelectedReport(report.id);
                            setReportData(null);
                          }}
                          className={`w-full text-left p-2 rounded-lg text-sm transition-colors ${
                            selectedReport === report.id
                              ? 'bg-primary-50 text-primary-700 font-medium'
                              : 'text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          {report.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Selected Report Info & Filters */}
          {selectedReportInfo && (
            <div className="card">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">{selectedReportInfo.name}</h2>
                  <p className="text-gray-600 text-sm">{selectedReportInfo.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <Filter className="w-4 h-4" />
                    Filters
                  </button>
                  <button
                    onClick={handleGenerateReport}
                    disabled={generateMutation.isPending}
                    className="btn-primary flex items-center gap-2"
                  >
                    {generateMutation.isPending ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <BarChart3 className="w-4 h-4" />
                    )}
                    Generate
                  </button>
                </div>
              </div>

              {/* Filters Panel */}
              {showFilters && (
                <div className="mt-4 pt-4 border-t">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <label className="label">Start Date</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="date"
                          className="input pl-10"
                          value={filters.start_date || ''}
                          onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                        />
                      </div>
                    </div>
                    <div>
                      <label className="label">End Date</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="date"
                          className="input pl-10"
                          value={filters.end_date || ''}
                          onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                        />
                      </div>
                    </div>
                    {(selectedReport?.startsWith('wo_') || selectedReport?.startsWith('labor')) && (
                      <div>
                        <label className="label">Assigned To</label>
                        <select
                          className="input"
                          value={filters.assigned_to || ''}
                          onChange={(e) =>
                            setFilters({
                              ...filters,
                              assigned_to: e.target.value ? parseInt(e.target.value) : undefined,
                            })
                          }
                        >
                          <option value="">All Users</option>
                          {usersData?.items?.map(
                            (user: { id: number; first_name: string; last_name: string }) => (
                              <option key={user.id} value={user.id}>
                                {user.first_name} {user.last_name}
                              </option>
                            )
                          )}
                        </select>
                      </div>
                    )}
                    {selectedReport?.startsWith('wo_') && (
                      <div>
                        <label className="label">Priority</label>
                        <select
                          className="input"
                          value={filters.priority || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, priority: e.target.value || undefined })
                          }
                        >
                          <option value="">All Priorities</option>
                          <option value="EMERGENCY">Emergency</option>
                          <option value="HIGH">High</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="LOW">Low</option>
                        </select>
                      </div>
                    )}
                    {selectedReport?.startsWith('wo_') && (
                      <div>
                        <label className="label">Work Type</label>
                        <select
                          className="input"
                          value={filters.work_type || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, work_type: e.target.value || undefined })
                          }
                        >
                          <option value="">All Types</option>
                          <option value="CORRECTIVE">Corrective</option>
                          <option value="PREVENTIVE">Preventive</option>
                          <option value="EMERGENCY">Emergency</option>
                          <option value="PREDICTIVE">Predictive</option>
                          <option value="PROJECT">Project</option>
                          <option value="INSPECTION">Inspection</option>
                          <option value="CALIBRATION">Calibration</option>
                        </select>
                      </div>
                    )}
                    {selectedReport === 'wo_summary' && (
                      <div>
                        <label className="label">Status</label>
                        <select
                          className="input"
                          value={filters.status || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, status: e.target.value || undefined })
                          }
                        >
                          <option value="">All Statuses</option>
                          <option value="DRAFT">Draft</option>
                          <option value="WAITING_APPROVAL">Waiting Approval</option>
                          <option value="APPROVED">Approved</option>
                          <option value="SCHEDULED">Scheduled</option>
                          <option value="IN_PROGRESS">In Progress</option>
                          <option value="ON_HOLD">On Hold</option>
                          <option value="COMPLETED">Completed</option>
                          <option value="CLOSED">Closed</option>
                          <option value="CANCELLED">Cancelled</option>
                        </select>
                      </div>
                    )}
                    {selectedReport?.startsWith('asset_') && (
                      <div>
                        <label className="label">Criticality</label>
                        <select
                          className="input"
                          value={filters.criticality || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, criticality: e.target.value || undefined })
                          }
                        >
                          <option value="">All</option>
                          <option value="CRITICAL">Critical</option>
                          <option value="HIGH">High</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="LOW">Low</option>
                        </select>
                      </div>
                    )}
                  </div>
                  <div className="flex justify-end mt-4">
                    <button
                      onClick={() =>
                        setFilters({
                          start_date: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
                          end_date: format(new Date(), 'yyyy-MM-dd'),
                        })
                      }
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Reset Filters
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Report Results */}
          {reportData && (
            <div className="space-y-6">
              {/* Export Buttons */}
              <div className="card">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <h3 className="font-semibold">Export Report</h3>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => handleDownload('pdf')}
                      disabled={downloadMutation.isPending}
                      className="btn-secondary flex items-center gap-2"
                    >
                      <File className="w-4 h-4" />
                      PDF
                    </button>
                    <button
                      onClick={() => handleDownload('excel')}
                      disabled={downloadMutation.isPending}
                      className="btn-secondary flex items-center gap-2"
                    >
                      <FileSpreadsheet className="w-4 h-4" />
                      Excel
                    </button>
                    <button
                      onClick={() => handleDownload('csv')}
                      disabled={downloadMutation.isPending}
                      className="btn-secondary flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      CSV
                    </button>
                  </div>
                </div>
              </div>

              {/* Summary Metrics */}
              {reportData.summary_metrics && reportData.summary_metrics.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {reportData.summary_metrics.map((metric, index) => (
                    <div key={index} className="card text-center">
                      <p className="text-sm text-gray-500">{metric.label}</p>
                      <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Charts for specific reports */}
              {reportData.by_status && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="card">
                    <h3 className="font-semibold mb-4">By Status</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={Object.entries(reportData.by_status as Record<string, number>).map(
                              ([name, value]) => ({ name, value })
                            )}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={80}
                            dataKey="value"
                            label={({ name, percent }) =>
                              `${name} ${(percent * 100).toFixed(0)}%`
                            }
                          >
                            {Object.keys(reportData.by_status as Record<string, number>).map(
                              (_, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={COLORS[index % COLORS.length]}
                                />
                              )
                            )}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  {reportData.by_type && (
                    <div className="card">
                      <h3 className="font-semibold mb-4">By Type</h3>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={Object.entries(
                              reportData.by_type as Record<string, number>
                            ).map(([name, value]) => ({ name, value }))}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="value" fill="#3B82F6" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Data Tables */}
              {reportData.sections &&
                reportData.sections.map((section, sectionIndex) => (
                  <div key={sectionIndex} className="card">
                    {section.title && (
                      <h3 className="font-semibold mb-4">{section.title}</h3>
                    )}
                    {section.headers && section.rows && (
                      <div className="overflow-x-auto">
                        <table className="table">
                          <thead>
                            <tr>
                              {section.headers.map((header, index) => (
                                <th key={index}>{header}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {section.rows.slice(0, 50).map((row, rowIndex) => (
                              <tr key={rowIndex}>
                                {row.map((cell, cellIndex) => (
                                  <td key={cellIndex}>
                                    {typeof cell === 'number'
                                      ? cell.toLocaleString()
                                      : cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {section.rows.length > 50 && (
                          <p className="text-sm text-gray-500 mt-2 text-center">
                            Showing 50 of {section.rows.length} rows. Export to see all data.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}

              {/* Alternative data displays for specific report types */}
              {reportData.work_orders && Array.isArray(reportData.work_orders) && !reportData.sections && (
                <div className="card">
                  <h3 className="font-semibold mb-4">Work Orders</h3>
                  <div className="overflow-x-auto">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>WO Number</th>
                          <th>Title</th>
                          <th>Type</th>
                          <th>Priority</th>
                          <th>Status</th>
                          <th>Cost</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {(reportData.work_orders as Array<Record<string, unknown>>)
                          .slice(0, 50)
                          .map((wo, index) => (
                            <tr key={index}>
                              <td className="font-medium">{wo.wo_number as string}</td>
                              <td>{wo.title as string}</td>
                              <td>{wo.type as string || '-'}</td>
                              <td>
                                <span
                                  className={`badge ${
                                    wo.priority === 'EMERGENCY'
                                      ? 'badge-red'
                                      : wo.priority === 'HIGH'
                                      ? 'badge-yellow'
                                      : 'badge-gray'
                                  }`}
                                >
                                  {wo.priority as string}
                                </span>
                              </td>
                              <td>{wo.status as string}</td>
                              <td>${((wo.total_cost as number) || 0).toLocaleString()}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {reportData.technicians && Array.isArray(reportData.technicians) && !reportData.sections && (
                <div className="card">
                  <h3 className="font-semibold mb-4">Technicians</h3>
                  <div className="overflow-x-auto">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Hours</th>
                          <th>Cost</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {(reportData.technicians as Array<Record<string, unknown>>).map(
                          (tech, index) => (
                            <tr key={index}>
                              <td className="font-medium">{tech.name as string}</td>
                              <td>{((tech.total_hours as number) || 0).toFixed(1)}</td>
                              <td>${((tech.total_cost as number) || 0).toLocaleString()}</td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {reportData.assets && Array.isArray(reportData.assets) && !reportData.sections && (
                <div className="card">
                  <h3 className="font-semibold mb-4">Assets</h3>
                  <div className="overflow-x-auto">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Asset #</th>
                          <th>Name</th>
                          <th>Criticality</th>
                          <th>Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {(reportData.assets as Array<Record<string, unknown>>)
                          .slice(0, 50)
                          .map((asset, index) => (
                            <tr key={index}>
                              <td className="font-medium">{asset.asset_num as string}</td>
                              <td>{asset.asset_name || asset.name as string}</td>
                              <td>
                                <span
                                  className={`badge ${
                                    asset.criticality === 'CRITICAL'
                                      ? 'badge-red'
                                      : asset.criticality === 'HIGH'
                                      ? 'badge-yellow'
                                      : 'badge-blue'
                                  }`}
                                >
                                  {asset.criticality as string || '-'}
                                </span>
                              </td>
                              <td>
                                {asset.total_cost !== undefined && (
                                  <span>${((asset.total_cost as number) || 0).toLocaleString()}</span>
                                )}
                                {asset.downtime_hours !== undefined && (
                                  <span>{(asset.downtime_hours as number).toFixed(1)} hrs downtime</span>
                                )}
                                {asset.mtbf_hours !== undefined && (
                                  <span>MTBF: {asset.mtbf_hours as string} hrs</span>
                                )}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* No Report Selected State */}
          {!selectedReport && (
            <div className="card text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Report</h3>
              <p className="text-gray-500">Choose a report type from the sidebar to get started</p>
            </div>
          )}

          {/* Report Selected but not generated */}
          {selectedReport && !reportData && !generateMutation.isPending && (
            <div className="card text-center py-12">
              <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Generate</h3>
              <p className="text-gray-500 mb-4">
                Click "Generate" to create your {selectedReportInfo?.name}
              </p>
              <button onClick={handleGenerateReport} className="btn-primary">
                Generate Report
              </button>
            </div>
          )}

          {/* Loading State */}
          {generateMutation.isPending && (
            <div className="card text-center py-12">
              <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">Generating Report...</h3>
              <p className="text-gray-500">Please wait while we compile your data</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
