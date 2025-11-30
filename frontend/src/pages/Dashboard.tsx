import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  ClipboardList,
  AlertTriangle,
  Calendar,
  Users,
  DollarSign,
  BarChart3,
  Settings,
  Plus,
  X,
  ChevronDown,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { getDashboardMetrics, getDashboardWidget, getUsers, getStorerooms } from '../lib/api';
import { format, subDays } from 'date-fns';
import { useAuthStore } from '../stores/authStore';

const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Open (Active)', value: 'OPEN' },
  { label: 'Closed (Completed/Cancelled)', value: 'CLOSED' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Waiting Approval', value: 'WAITING_APPROVAL' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Scheduled', value: 'SCHEDULED' },
  { label: 'In Progress', value: 'IN_PROGRESS' },
  { label: 'On Hold', value: 'ON_HOLD' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

const PRIORITY_OPTIONS = [
  { label: 'All priorities', value: '' },
  { label: 'Emergency', value: 'EMERGENCY' },
  { label: 'High', value: 'HIGH' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'Low', value: 'LOW' },
  { label: 'Scheduled', value: 'SCHEDULED' },
];

const WORK_TYPE_OPTIONS = [
  { label: 'All work types', value: '' },
  { label: 'Corrective', value: 'CORRECTIVE' },
  { label: 'Emergency', value: 'EMERGENCY' },
  { label: 'Preventive', value: 'PREVENTIVE' },
  { label: 'Predictive', value: 'PREDICTIVE' },
  { label: 'Project', value: 'PROJECT' },
  { label: 'Inspection', value: 'INSPECTION' },
  { label: 'Calibration', value: 'CALIBRATION' },
];

const ASSET_STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Operating', value: 'OPERATING' },
  { label: 'Not Operating', value: 'NOT_OPERATING' },
  { label: 'In Repair', value: 'IN_REPAIR' },
  { label: 'Standby', value: 'STANDBY' },
  { label: 'Decommissioned', value: 'DECOMMISSIONED' },
];

const CRITICALITY_OPTIONS = [
  { label: 'All criticalities', value: '' },
  { label: 'Critical', value: 'CRITICAL' },
  { label: 'High', value: 'HIGH' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'Low', value: 'LOW' },
];

const LABOR_TYPE_OPTIONS = [
  { label: 'All labor types', value: '' },
  { label: 'Regular', value: 'REGULAR' },
  { label: 'Overtime', value: 'OVERTIME' },
  { label: 'Double Time', value: 'DOUBLE_TIME' },
  { label: 'Contract', value: 'CONTRACT' },
];

// Widget definitions
const AVAILABLE_WIDGETS = [
  { id: 'wo_by_status', name: 'Work Orders by Status', category: 'Work Orders', size: 'small' },
  { id: 'overdue_wo_count', name: 'Overdue Work Orders', category: 'Work Orders', size: 'small' },
  { id: 'wo_backlog_age', name: 'Backlog Aging', category: 'Work Orders', size: 'large' },
  { id: 'reactive_vs_preventive', name: 'Reactive vs Proactive', category: 'Work Orders', size: 'small' },
  { id: 'pm_compliance_rate', name: 'PM Compliance Rate', category: 'PM', size: 'small' },
  { id: 'upcoming_pms', name: 'Upcoming PMs', category: 'PM', size: 'medium' },
  { id: 'mttr', name: 'MTTR (Repair Time)', category: 'Reliability', size: 'small' },
  { id: 'mtbf', name: 'MTBF (Reliability)', category: 'Reliability', size: 'small' },
  { id: 'bad_actors', name: 'Bad Actors (High Cost Assets)', category: 'Assets', size: 'medium' },
  { id: 'downtime_by_asset', name: 'Downtime by Asset', category: 'Assets', size: 'medium' },
  { id: 'low_stock_items', name: 'Low Stock / Reorder Watch', category: 'Inventory', size: 'medium' },
  { id: 'overtime_hours', name: 'Overtime Hours', category: 'Labor', size: 'medium' },
  { id: 'data_integrity_score', name: 'Data Integrity Score', category: 'Quality', size: 'small' },
  { id: 'waiting_for_parts', name: 'Waiting for Parts Tracker', category: 'Work Orders', size: 'medium' },
];

type WidgetOptionType = 'select' | 'user' | 'storeroom' | 'text' | 'number';

interface WidgetOption {
  key: string;
  label: string;
  type: WidgetOptionType;
  description?: string;
  placeholder?: string;
  options?: { label: string; value: string | number }[];
}

const BASE_FILTERS = {
  status: {
    key: 'status',
    label: 'Work Order Status',
    type: 'select' as const,
    options: STATUS_OPTIONS,
    description: 'Scope the data down to a single lifecycle state.',
  },
  priority: {
    key: 'priority',
    label: 'Priority',
    type: 'select' as const,
    options: PRIORITY_OPTIONS,
    description: 'Focus on critical work first.',
  },
  work_type: {
    key: 'work_type',
    label: 'Work Type',
    type: 'select' as const,
    options: WORK_TYPE_OPTIONS,
    description: 'Choose between reactive, preventive, project, etc.',
  },
  owner: {
    key: 'assigned_to',
    label: 'Assigned To',
    type: 'user' as const,
    description: 'Limit the widget to a specific technician or planner.',
  },
  asset_status: {
    key: 'asset_status',
    label: 'Asset Status',
    type: 'select' as const,
    options: ASSET_STATUS_OPTIONS,
    description: 'Only show assets currently in a given status.',
  },
  criticality: {
    key: 'criticality',
    label: 'Asset Criticality',
    type: 'select' as const,
    options: CRITICALITY_OPTIONS,
    description: 'Highlight critical equipment or lower-impact assets.',
  },
  storeroom: {
    key: 'storeroom',
    label: 'Storeroom',
    type: 'storeroom' as const,
    description: 'Filter inventory widgets down to a single storeroom.',
  },
  craft: {
    key: 'craft',
    label: 'Craft / Trade',
    type: 'text' as const,
    placeholder: 'e.g., Electrician, Millwright',
    description: 'Match the labor craft recorded on time entries.',
  },
  labor_type: {
    key: 'labor_type',
    label: 'Labor Type',
    type: 'select' as const,
    options: LABOR_TYPE_OPTIONS,
    description: 'Compare overtime vs. regular or contract hours.',
  },
};

const buildFilters = (...options: WidgetOption[]) => options.map(option => ({ ...option }));

const WIDGET_CONFIGS: Record<string, WidgetOption[]> = {
  'wo_by_status': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'wo_backlog_age': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'overdue_wo_count': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'reactive_vs_preventive': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'pm_compliance_rate': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'bad_actors': buildFilters(
    BASE_FILTERS.asset_status,
    BASE_FILTERS.criticality
  ),
  'downtime_by_asset': buildFilters(
    BASE_FILTERS.asset_status,
    BASE_FILTERS.criticality
  ),
  'low_stock_items': buildFilters(
    BASE_FILTERS.storeroom
  ),
  'overtime_hours': buildFilters(
    BASE_FILTERS.craft,
    BASE_FILTERS.labor_type
  ),
  'data_integrity_score': buildFilters(
    BASE_FILTERS.work_type,
    BASE_FILTERS.priority,
    BASE_FILTERS.owner
  ),
  'waiting_for_parts': buildFilters(
    BASE_FILTERS.priority,
    BASE_FILTERS.work_type,
    BASE_FILTERS.owner
  ),
  'mtbf': buildFilters(
    BASE_FILTERS.work_type,
    BASE_FILTERS.priority,
    BASE_FILTERS.owner
  ),
  'mttr': buildFilters(
    BASE_FILTERS.work_type,
    BASE_FILTERS.priority,
    BASE_FILTERS.owner
  ),
  // Widgets not listed default to zero configuration controls
};

// Default widgets
const DEFAULT_WIDGETS = [
  'wo_by_status',
  'overdue_wo_count',
  'pm_compliance_rate',
  'wo_backlog_age',
  'reactive_vs_preventive',
  'bad_actors',
  'low_stock_items',
  'upcoming_pms',
  'data_integrity_score',
  'overtime_hours',
];

interface WidgetProps {
  id: string;
  settings?: Record<string, any>;
  startDate: string;
  endDate: string;
  onRemove: () => void;
  onConfigure: () => void;
}

function Widget({ id, settings, startDate, endDate, onRemove, onConfigure }: WidgetProps) {
  const widgetDef = AVAILABLE_WIDGETS.find(w => w.id === id);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['widget', id, startDate, endDate, settings],
    queryFn: () => {
      // Validate dates before making request
      if (!startDate || !endDate) {
        throw new Error('Invalid date range');
      }
      return getDashboardWidget(id, {
        start_date: startDate,
        end_date: endDate,
        ...settings
      });
    },
    staleTime: 60000,
    retry: false, // Don't retry on error to prevent infinite loops
    refetchOnWindowFocus: false, // Prevent refetching when window regains focus
  });

  const renderContent = () => {
    // Handle loading state
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      );
    }

    // Handle error state
    if (error || data?.error) {
      const errorMsg = data?.error || (error as Error)?.message || 'Unknown error';
      return (
        <div className="flex flex-col items-center justify-center h-32 text-red-500 text-center p-2">
          <AlertTriangle className="w-5 h-5 mb-2" />
          <div className="text-sm">Error loading data</div>
          <div className="text-xs mt-1 text-gray-600">{errorMsg}</div>
        </div>
      );
    }

    // Handle empty data
    const widgetData = data?.data;
    if (!widgetData) return <div className="text-gray-500 text-center py-4">No data</div>;

    // Render based on widget type
    try {
      switch (id) {
      case 'wo_by_status':
      case 'wo_by_priority':
      case 'wo_by_type':
      case 'assets_by_status':
      case 'assets_by_criticality':
      case 'failure_codes':
        return (
          <div className="space-y-2">
            {Object.entries(widgetData).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm truncate">{key.replace(/_/g, ' ')}</span>
                <span className="font-semibold">{value as number}</span>
              </div>
            ))}
          </div>
        );

      case 'labor_hours_by_craft':
        return (
          <div className="space-y-2">
            {Object.entries(widgetData).map(([craft, hours]) => (
              <div key={craft} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm">{craft}</span>
                <span className="font-semibold">{(hours as number).toFixed(1)} hrs</span>
              </div>
            ))}
          </div>
        );

      case 'overdue_wo_count':
        return (
          <div className="text-center py-4">
            <p className="text-4xl font-bold text-red-600">{widgetData.count}</p>
            <p className="text-sm text-gray-500 mt-2">Overdue Work Orders</p>
          </div>
        );

      case 'avg_completion_time':
        return (
          <div className="text-center py-4">
            <p className="text-4xl font-bold text-blue-600">{widgetData.avg_hours}</p>
            <p className="text-sm text-gray-500 mt-2">Average Hours to Complete</p>
          </div>
        );

      case 'cost_summary':
        return (
          <div className="space-y-3">
            <div className="flex justify-between items-center p-2 bg-blue-50 rounded">
              <span className="text-sm">Labor</span>
              <span className="font-semibold">${widgetData.labor.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center p-2 bg-green-50 rounded">
              <span className="text-sm">Material</span>
              <span className="font-semibold">${widgetData.material.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center p-2 bg-purple-50 rounded border-t-2 border-purple-200">
              <span className="text-sm font-medium">Total</span>
              <span className="font-bold">${widgetData.total.toLocaleString()}</span>
            </div>
          </div>
        );

      case 'pm_compliance_rate':
        const complianceColor = widgetData.compliance_rate >= 90 ? 'text-green-600' :
          widgetData.compliance_rate >= 70 ? 'text-yellow-600' : 'text-red-600';
        return (
          <div className="text-center py-4">
            <p className={`text-4xl font-bold ${complianceColor}`}>{widgetData.compliance_rate}%</p>
            <p className="text-sm text-gray-500 mt-2">PM Compliance</p>
            <p className="text-xs text-gray-400">{widgetData.on_time} of {widgetData.total} on time</p>
          </div>
        );

      case 'data_integrity_score':
        const integrityColor = widgetData.score >= 90 ? 'text-green-600' :
          widgetData.score >= 70 ? 'text-yellow-600' : 'text-red-600';
        return (
          <div className="text-center py-4">
            <p className={`text-4xl font-bold ${integrityColor}`}>{widgetData.score}%</p>
            <p className="text-sm text-gray-500 mt-2">WO Data Completeness</p>
            <p className="text-xs text-gray-400">{widgetData.valid} of {widgetData.total} closed WOs have failure/cause/remedy</p>
          </div>
        );

      case 'mttr':
      case 'mtbf':
        return (
          <div className="text-center py-4">
            <p className="text-4xl font-bold text-indigo-600">{widgetData.avg_hours?.toFixed(2) || widgetData.avg_hours || 0}h</p>
            <p className="text-sm text-gray-500 mt-2">{id === 'mttr' ? 'Mean Time To Repair' : 'Mean Time Between Failures'}</p>
            <p className="text-xs text-gray-400">{widgetData.sample_size || 0} samples</p>
          </div>
        );

      case 'reactive_vs_preventive':
        return (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm">Reactive</span>
              <span className="font-semibold text-red-600">{widgetData.reactive} ({widgetData.reactive_pct}%)</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div className="bg-red-500 h-4 rounded-l-full" style={{ width: `${widgetData.reactive_pct}%` }}></div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Preventive</span>
              <span className="font-semibold text-green-600">{widgetData.preventive} ({widgetData.preventive_pct}%)</span>
            </div>
          </div>
        );

      case 'open_wo_by_user':
      case 'completed_wo_by_user':
      case 'user_workload':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ name: string; count?: number; wo_count?: number; est_hours?: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm truncate flex-1">{item.name}</span>
                <div className="text-right">
                  <span className="font-semibold">{item.count || item.wo_count}</span>
                  {item.est_hours !== undefined && (
                    <span className="text-xs text-gray-500 ml-2">({item.est_hours}h)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        );

      case 'labor_cost_by_user':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ name: string; total_cost: number; total_hours: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm truncate flex-1">{item.name}</span>
                <div className="text-right">
                  <span className="font-semibold">${item.total_cost.toLocaleString()}</span>
                  <span className="text-xs text-gray-500 ml-2">({item.total_hours.toFixed(1)}h)</span>
                </div>
              </div>
            ))}
          </div>
        );

      case 'labor_type_breakdown':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ type: string; hours: number; cost: number }>).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm">{item.type}</span>
                <div className="text-right">
                  <span className="font-semibold">{item.hours.toFixed(1)}h</span>
                  <span className="text-xs text-gray-500 ml-2">${item.cost.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        );

      case 'overtime_hours':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ user_id: number; name: string; hours: number; cost: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-orange-50 rounded">
                <span className="text-sm truncate flex-1">{item.name}</span>
                <div className="text-right">
                  <span className="font-semibold text-orange-700">{item.hours.toFixed(1)}h</span>
                  <span className="text-xs text-gray-500 ml-2">${item.cost.toLocaleString()}</span>
                </div>
              </div>
            ))}
            {(widgetData as Array<unknown>).length === 0 && (
              <p className="text-center text-gray-500 py-4">No overtime logged in this window</p>
            )}
          </div>
        );

      case 'material_cost_by_part':
      case 'most_used_parts':
      case 'least_used_parts':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ part_number: string; name: string; total_cost?: number; quantity?: number; total_qty?: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.part_number}</span>
                  <span className="text-xs text-gray-500 ml-2">{item.name}</span>
                </div>
                <span className="font-semibold">
                  {item.total_cost !== undefined ? `$${item.total_cost.toLocaleString()}` :
                    item.quantity !== undefined ? item.quantity : item.total_qty}
                </span>
              </div>
            ))}
          </div>
        );

      case 'low_stock_items':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ part_number: string; name: string; current: number; reorder_point: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-red-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.part_number}</span>
                </div>
                <span className="text-sm text-red-600">
                  {item.current} / {item.reorder_point}
                </span>
              </div>
            ))}
            {(widgetData as Array<unknown>).length === 0 && (
              <p className="text-center text-green-600 py-4">All stock levels OK</p>
            )}
          </div>
        );

      case 'assets_most_wo':
      case 'assets_highest_cost':
      case 'bad_actors':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ asset_num: string; name: string; wo_count?: number; total_cost?: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.asset_num}</span>
                  <span className="text-xs text-gray-500 ml-2">{item.name}</span>
                </div>
                <span className="font-semibold">
                  {item.wo_count !== undefined ? item.wo_count : `$${item.total_cost?.toLocaleString()}`}
                </span>
              </div>
            ))}
          </div>
        );

      case 'downtime_by_asset':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ asset_num: string; name: string; downtime_hours: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm truncate flex-1">{item.asset_num}</span>
                <span className="font-semibold text-red-600">{item.downtime_hours.toFixed(1)}h</span>
              </div>
            ))}
          </div>
        );

      case 'inventory_value_by_storeroom':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ code: string; name: string; value: number }>).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm">{item.code} - {item.name}</span>
                <span className="font-semibold">${item.value.toLocaleString()}</span>
              </div>
            ))}
          </div>
        );

      case 'upcoming_pms':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ pm_number: string; name: string; next_due: string }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.pm_number}</span>
                  <span className="text-xs text-gray-500 ml-2">{item.name}</span>
                </div>
                <span className="text-sm text-purple-600">
                  {item.next_due ? format(new Date(item.next_due), 'MMM d') : '-'}
                </span>
              </div>
            ))}
          </div>
        );

      case 'wo_backlog_age':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ wo_number: string; title: string; age_days: number; priority: string }>).slice(0, 10).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.wo_number}</span>
                  <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${item.priority === 'EMERGENCY' ? 'bg-red-100 text-red-700' :
                    item.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>{item.priority}</span>
                </div>
                <span className={`text-sm ${item.age_days > 7 ? 'text-red-600' : 'text-gray-600'}`}>
                  {item.age_days}d old
                </span>
              </div>
            ))}
          </div>
        );

      case 'waiting_for_parts':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ wo_number: string; title: string; age_days: number; priority?: string }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-yellow-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.wo_number}</span>
                  {item.priority && (
                    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${item.priority === 'EMERGENCY' ? 'bg-red-100 text-red-700' :
                      item.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>{item.priority}</span>
                  )}
                </div>
                <span className="text-sm text-yellow-700">{item.age_days}d waiting</span>
              </div>
            ))}
            {(widgetData as Array<unknown>).length === 0 && (
              <p className="text-center text-green-600 py-4">Nothing blocked by parts right now</p>
            )}
          </div>
        );

      case 'recent_completions':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ wo_number: string; title: string; completed_at: string; total_cost: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="truncate flex-1">
                  <span className="text-sm font-medium">{item.wo_number}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm">${item.total_cost.toLocaleString()}</span>
                  <span className="text-xs text-gray-500 ml-2">
                    {item.completed_at ? format(new Date(item.completed_at), 'MMM d') : '-'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        );

      case 'wo_by_location':
        return (
          <div className="space-y-2">
            {(widgetData as Array<{ name: string; wo_count: number }>).slice(0, 8).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm truncate flex-1">{item.name}</span>
                <span className="font-semibold">{item.wo_count}</span>
              </div>
            ))}
          </div>
        );

      case 'wo_created_trend':
      case 'wo_completed_trend':
      case 'cost_trend_labor':
      case 'cost_trend_material':
        const trendData = widgetData as Array<{ date: string; count?: number; cost?: number }>;
        const maxVal = Math.max(...trendData.map(d => d.count || d.cost || 0));
        return (
          <div className="space-y-1">
            {trendData.slice(-14).map((item, i) => {
              const val = item.count || item.cost || 0;
              const pct = maxVal > 0 ? (val / maxVal) * 100 : 0;
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-16">{format(new Date(item.date), 'MMM d')}</span>
                  <div className="flex-1 bg-gray-100 rounded h-4">
                    <div className="bg-blue-500 h-4 rounded" style={{ width: `${pct}%` }}></div>
                  </div>
                  <span className="text-xs w-12 text-right">
                    {item.count !== undefined ? item.count : `$${(item.cost || 0).toLocaleString()}`}
                  </span>
                </div>
              );
            })}
          </div>
        );

      default:
        return <div className="text-gray-500 text-center py-4">Widget not implemented</div>;
    }
    } catch (err) {
      console.error(`Error rendering widget ${id}:`, err);
      return (
        <div className="flex flex-col items-center justify-center h-32 text-red-500 text-center p-2">
          <AlertTriangle className="w-5 h-5 mb-2" />
          <div className="text-sm">Error rendering widget</div>
          <div className="text-xs mt-1 text-gray-600">Please try refreshing</div>
        </div>
      );
    }
  };

  return (
    <div className={`card relative ${widgetDef?.size === 'large' ? 'lg:col-span-2' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          {widgetDef?.name || id}
        </h3>
        <div className="flex items-center gap-1">
          {(WIDGET_CONFIGS[id] || []).length > 0 && (
            <button
              onClick={onConfigure}
              className="p-1 hover:bg-gray-100 rounded"
              title="Configure widget"
            >
              <Settings className="w-4 h-4 text-gray-400" />
            </button>
          )}
          <button
            onClick={() => refetch()}
            className="p-1 hover:bg-gray-100 rounded"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={onRemove}
            className="p-1 hover:bg-gray-100 rounded"
            title="Remove widget"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>
      <div className="min-h-[100px]">
        {renderContent()}
      </div>
    </div>
  );
}

interface WidgetConfig {
  id: string;
  settings?: Record<string, any>;
}

// Error boundary component for widgets
function WidgetErrorBoundary({ children }: { children: React.ReactNode }) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (hasError) {
      // Reset error state after a short delay
      const timer = setTimeout(() => setHasError(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [hasError]);

  if (hasError) {
    return (
      <div className="card text-center py-8">
        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 font-medium">Widget Error</p>
        <p className="text-sm text-gray-500 mt-1">This widget encountered an error</p>
      </div>
    );
  }

  return (
    <ErrorBoundary onError={() => setHasError(true)}>
      {children}
    </ErrorBoundary>
  );
}

function ErrorBoundary({ children, onError }: { children: React.ReactNode; onError: () => void }) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (hasError) {
      onError();
    }
  }, [hasError, onError]);

  if (hasError) {
    return null;
  }

  return children;
}

export default function Dashboard() {
  const [activeWidgets, setActiveWidgets] = useState<WidgetConfig[]>(() => {
    const saved = localStorage.getItem('dashboard-widgets');
    const validIds = new Set(AVAILABLE_WIDGETS.map(w => w.id));
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Migrate old string array format
        if (Array.isArray(parsed) && typeof parsed[0] === 'string') {
          return parsed
            .filter((id: string) => validIds.has(id))
            .map((id: string) => ({ id }));
        }
        return (parsed as WidgetConfig[]).filter(w => validIds.has(w.id));
      } catch (e) {
        console.error('Failed to parse saved widgets', e);
      }
    }
    return DEFAULT_WIDGETS.filter(id => validIds.has(id)).map(id => ({ id }));
  });
  const [showWidgetSelector, setShowWidgetSelector] = useState(false);
  const [configuringWidget, setConfiguringWidget] = useState<number | null>(null); // Index of widget being configured
  const [dateRange, setDateRange] = useState(() => {
    try {
      const today = new Date();
      const thirtyDaysAgo = subDays(today, 30);
      return {
        start: format(thirtyDaysAgo, 'yyyy-MM-dd'),
        end: format(today, 'yyyy-MM-dd'),
      };
    } catch (e) {
      console.error('Error initializing date range:', e);
      // Fallback to safe default dates
      return {
        start: '2023-01-01',
        end: '2023-12-31',
      };
    }
  });
  const [showDatePicker, setShowDatePicker] = useState(false);
  
  // Save widgets to localStorage
  useEffect(() => {
    localStorage.setItem('dashboard-widgets', JSON.stringify(activeWidgets));
  }, [activeWidgets]);

  const { data: metrics } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: getDashboardMetrics,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const currentWidgetConfig = configuringWidget !== null ? activeWidgets[configuringWidget] : null;
  const configOptionsForCurrentWidget = currentWidgetConfig ? (WIDGET_CONFIGS[currentWidgetConfig.id] || []) : [];
  const needsUserOptions = configOptionsForCurrentWidget.some((option) => option.type === 'user');
  const needsStoreroomOptions = configOptionsForCurrentWidget.some((option) => option.type === 'storeroom');

  const { data: usersData, isLoading: loadingUsers } = useQuery({
    queryKey: ['users', 'widget-config'],
    queryFn: () => getUsers({ page_size: 200 }),
    enabled: needsUserOptions,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const { data: storeroomsData, isLoading: loadingStorerooms } = useQuery({
    queryKey: ['storerooms', 'widget-config'],
    queryFn: getStorerooms,
    enabled: needsStoreroomOptions,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const toArray = (payload: any) => {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.results)) return payload.results;
    return [];
  };

  const userDropdownOptions = toArray(usersData)
    .map((user: any) => {
      const parts = [user?.first_name, user?.last_name].filter(Boolean);
      const fallback = user?.username || user?.email || `User ${user?.id}`;
      return {
        label: (parts.join(' ') || fallback || '').trim(),
        value: user?.id,
      };
    })
    .filter(option => option.value !== undefined && option.value !== null)
    .sort((a, b) => a.label.localeCompare(b.label));

  const storeroomDropdownOptions = toArray(storeroomsData)
    .map((storeroom: any) => {
      const code = storeroom?.code;
      const name = storeroom?.name;
      const label = [code, name].filter(Boolean).join(' — ') || `Storeroom ${storeroom?.id || ''}`;
      return {
        label: label.trim(),
        value: storeroom?.id,
      };
    })
    .filter(option => option.value !== undefined && option.value !== null)
    .sort((a, b) => a.label.localeCompare(b.label));

  const addWidget = (widgetId: string) => {
    setActiveWidgets([...activeWidgets, { id: widgetId }]);
    setShowWidgetSelector(false);
  };

  const removeWidget = (index: number) => {
    const newWidgets = [...activeWidgets];
    newWidgets.splice(index, 1);
    setActiveWidgets(newWidgets);
  };

  const resetWidgets = () => {
    setActiveWidgets(DEFAULT_WIDGETS.map(id => ({ id })));
  };

  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Group widgets by category for selector
  const widgetsByCategory = AVAILABLE_WIDGETS.reduce((acc, widget) => {
    if (!acc[widget.category]) acc[widget.category] = [];
    acc[widget.category].push(widget);
    return acc;
  }, {} as Record<string, typeof AVAILABLE_WIDGETS>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Overview of your maintenance operations</p>
        </div>
        <div className="flex items-center gap-2">
          
          {/* Date Range Picker */}
          <div className="relative">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="btn-secondary flex items-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              {format(new Date(dateRange.start), 'MMM d')} - {format(new Date(dateRange.end), 'MMM d')}
              <ChevronDown className="w-4 h-4" />
            </button>
            {showDatePicker && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setShowDatePicker(false)} />
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border z-40 p-4">
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm text-gray-600">Start Date</label>
                      <input
                        type="date"
                        className="input mt-1"
                        value={dateRange.start}
                        onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">End Date</label>
                      <input
                        type="date"
                        className="input mt-1"
                        value={dateRange.end}
                        onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="btn-secondary flex-1 text-sm"
                        onClick={() => {
                          setDateRange({
                            start: format(subDays(new Date(), 7), 'yyyy-MM-dd'),
                            end: format(new Date(), 'yyyy-MM-dd'),
                          });
                        }}
                      >
                        7 Days
                      </button>
                      <button
                        className="btn-secondary flex-1 text-sm"
                        onClick={() => {
                          setDateRange({
                            start: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
                            end: format(new Date(), 'yyyy-MM-dd'),
                          });
                        }}
                      >
                        30 Days
                      </button>
                      <button
                        className="btn-secondary flex-1 text-sm"
                        onClick={() => {
                          setDateRange({
                            start: format(subDays(new Date(), 90), 'yyyy-MM-dd'),
                            end: format(new Date(), 'yyyy-MM-dd'),
                          });
                        }}
                      >
                        90 Days
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          <button
            onClick={() => setShowWidgetSelector(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Widget
          </button>
          <button
            onClick={resetWidgets}
            className="btn-secondary"
            title="Reset to default widgets"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/work-orders" className="card hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <ClipboardList className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{metrics?.work_orders?.open || 0}</p>
              <p className="text-sm text-gray-500">Open WOs</p>
            </div>
          </div>
        </Link>
        <Link to="/work-orders?status=overdue" className="card hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{metrics?.work_orders?.overdue || 0}</p>
              <p className="text-sm text-gray-500">Overdue</p>
            </div>
          </div>
        </Link>
        <Link to="/pm" className="card hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Calendar className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{metrics?.preventive_maintenance?.due_today || 0}</p>
              <p className="text-sm text-gray-500">PMs Due</p>
            </div>
          </div>
        </Link>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">${((metrics?.costs?.total_this_month || 0) / 1000).toFixed(1)}k</p>
              <p className="text-sm text-gray-500">Cost MTD</p>
            </div>
          </div>
        </div>
      </div>

      {/* Widget Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {activeWidgets.map((widget, index) => (
          <div key={`${widget.id}-${index}`}>
            <WidgetErrorBoundary>
              <Widget
                id={widget.id}
                settings={widget.settings}
                startDate={dateRange.start}
                endDate={dateRange.end}
                onRemove={() => removeWidget(index)}
                onConfigure={() => setConfiguringWidget(index)}
              />
            </WidgetErrorBoundary>
          </div>
        ))}
      </div>

      {activeWidgets.length === 0 && (
        <div className="card text-center py-12">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No widgets configured</h3>
          <p className="text-gray-500 mt-1">Add widgets to customize your dashboard</p>
          <button
            onClick={() => setShowWidgetSelector(true)}
            className="btn-primary mt-4 inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Widget
          </button>
        </div>
      )}

      {/* Widget Selector Modal */}
      {showWidgetSelector && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Add Widget</h2>
              <button onClick={() => setShowWidgetSelector(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="overflow-y-auto flex-1">
              {Object.entries(widgetsByCategory).map(([category, widgets]) => (
                <div key={category} className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">{category}</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {widgets.map((widget) => {
                      const existingCount = activeWidgets.filter(w => w.id === widget.id).length;
                      return (
                        <button
                          key={widget.id}
                          onClick={() => addWidget(widget.id)}
                          className={`p-3 rounded-lg border text-left transition-colors ${existingCount
                            ? 'bg-primary-50/70 border-primary-200'
                            : 'bg-white border-gray-200 hover:border-primary-500 hover:bg-primary-50'
                            }`}
                        >
                          <p className="font-medium text-sm">{widget.name}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {widget.size === 'large' ? 'Wide widget' : widget.size === 'medium' ? 'Standard' : 'Compact'}
                          </p>
                          <p className="text-[11px] text-gray-500 mt-1">
                            {existingCount ? `On dashboard (${existingCount})` : 'Not added yet'}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Widget Configuration Modal */}
      {configuringWidget !== null && (() => {
        const widgetId = activeWidgets[configuringWidget].id;
        const configOptions = configOptionsForCurrentWidget;
        const currentSettings = activeWidgets[configuringWidget].settings || {};

        if (configOptions.length === 0) {
          // No configuration available
          return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl p-6 w-full max-w-md">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold">Configure Widget</h2>
                  <button onClick={() => setConfiguringWidget(null)} className="text-gray-500 hover:text-gray-700">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-gray-600">This widget has no configuration options.</p>
                <div className="mt-6 flex justify-end">
                  <button onClick={() => setConfiguringWidget(null)} className="btn-secondary">
                    Close
                  </button>
                </div>
              </div>
            </div>
          );
        }

        const updateSetting = (key: string, value: any) => {
          const newWidgets = [...activeWidgets];
          const nextSettings = { ...(newWidgets[configuringWidget].settings || {}) };
          if (value === undefined || value === '') {
            delete nextSettings[key];
          } else {
            nextSettings[key] = value;
          }
          newWidgets[configuringWidget] = {
            ...newWidgets[configuringWidget],
            settings: nextSettings,
          };
          setActiveWidgets(newWidgets);
        };

        const renderControl = (option: WidgetOption) => {
          const rawValue = currentSettings[option.key];
          const value = rawValue ?? '';
          switch (option.type) {
            case 'select':
              return (
                <select
                  className="input"
                  value={value}
                  onChange={(e) => updateSetting(option.key, e.target.value || undefined)}
                >
                  {(option.options || []).map((opt) => (
                    <option key={`${option.key}-${opt.value}`} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              );
            case 'text':
              return (
                <input
                  type="text"
                  className="input"
                  value={value}
                  placeholder={option.placeholder || ''}
                  onChange={(e) => updateSetting(option.key, e.target.value)}
                />
              );
            case 'number':
              return (
                <input
                  type="number"
                  className="input"
                  value={value}
                  placeholder={option.placeholder || ''}
                  onChange={(e) => updateSetting(option.key, e.target.value ? Number(e.target.value) : undefined)}
                />
              );
            case 'user':
              if (loadingUsers) {
                return (
                  <div className="input bg-gray-50 text-gray-500">Loading team members...</div>
                );
              }
              return (
                <select
                  className="input"
                  value={value ? String(value) : ''}
                  onChange={(e) => updateSetting(option.key, e.target.value ? Number(e.target.value) : undefined)}
                >
                  <option value="">All people</option>
                  {userDropdownOptions.map((opt) => (
                    <option key={`user-${opt.value}`} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              );
            case 'storeroom':
              if (loadingStorerooms) {
                return <div className="input bg-gray-50 text-gray-500">Loading storerooms...</div>;
              }
              return (
                <select
                  className="input"
                  value={value ? String(value) : ''}
                  onChange={(e) => updateSetting(option.key, e.target.value ? Number(e.target.value) : undefined)}
                >
                  <option value="">All storerooms</option>
                  {storeroomDropdownOptions.map((opt) => (
                    <option key={`storeroom-${opt.value}`} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              );
            default:
              return null;
          }
        };

        return (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">Configure Widget</h2>
                <button onClick={() => setConfiguringWidget(null)} className="text-gray-500 hover:text-gray-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {configOptions.map((option) => (
                  <div key={option.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{option.label}</label>
                    {renderControl(option)}
                    {option.description && (
                      <p className="text-xs text-gray-500 mt-1">{option.description}</p>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-6 flex justify-end gap-2">
                <button
                  onClick={() => {
                    // Clear all settings
                    const newWidgets = [...activeWidgets];
                    newWidgets[configuringWidget] = {
                      ...newWidgets[configuringWidget],
                      settings: {}
                    };
                    setActiveWidgets(newWidgets);
                  }}
                  className="btn-secondary"
                >
                  Clear Filters
                </button>
                <button
                  onClick={() => setConfiguringWidget(null)}
                  className="btn-primary"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
