import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  TrendingUp,
  Clock,
  DollarSign,
  CheckCircle,
  Package,
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
  LineChart,
  Line,
} from 'recharts';
import { getWorkOrderSummary, getAssetSummary, getPMCompliance, getInventoryValue } from '../lib/api';
import { format, subDays } from 'date-fns';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

type ReportTab = 'work-orders' | 'assets' | 'pm-compliance' | 'inventory';

export default function Reports() {
  const [activeTab, setActiveTab] = useState<ReportTab>('work-orders');
  const [dateRange] = useState({
    start: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
    end: format(new Date(), 'yyyy-MM-dd'),
  });

  const { data: woSummary, isLoading: woLoading } = useQuery({
    queryKey: ['wo-summary', dateRange],
    queryFn: () => getWorkOrderSummary(dateRange.start, dateRange.end),
    enabled: activeTab === 'work-orders',
  });

  const { data: assetSummary, isLoading: assetLoading } = useQuery({
    queryKey: ['asset-summary'],
    queryFn: getAssetSummary,
    enabled: activeTab === 'assets',
  });

  const { data: pmCompliance, isLoading: pmLoading } = useQuery({
    queryKey: ['pm-compliance', dateRange],
    queryFn: () => getPMCompliance(dateRange.start, dateRange.end),
    enabled: activeTab === 'pm-compliance',
  });

  const { data: inventoryValue, isLoading: invLoading } = useQuery({
    queryKey: ['inventory-value'],
    queryFn: getInventoryValue,
    enabled: activeTab === 'inventory',
  });

  const tabs = [
    { id: 'work-orders' as ReportTab, label: 'Work Orders', icon: BarChart3 },
    { id: 'assets' as ReportTab, label: 'Assets', icon: TrendingUp },
    { id: 'pm-compliance' as ReportTab, label: 'PM Compliance', icon: CheckCircle },
    { id: 'inventory' as ReportTab, label: 'Inventory', icon: Package },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-gray-600">Insights into your maintenance operations</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Work Orders Report */}
      {activeTab === 'work-orders' && (
        woLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="card">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <BarChart3 className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Created</p>
                    <p className="text-2xl font-bold">{woSummary?.counts?.created || 0}</p>
                  </div>
                </div>
              </div>
              <div className="card">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Completed</p>
                    <p className="text-2xl font-bold">{woSummary?.counts?.completed || 0}</p>
                  </div>
                </div>
              </div>
              <div className="card">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Clock className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Avg Completion</p>
                    <p className="text-2xl font-bold">{woSummary?.performance?.average_completion_hours || 0}h</p>
                  </div>
                </div>
              </div>
              <div className="card">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-orange-100 rounded-lg">
                    <DollarSign className="w-6 h-6 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Total Cost</p>
                    <p className="text-2xl font-bold">${(woSummary?.costs?.total || 0).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="card">
                <h3 className="font-semibold mb-4">Work Orders by Type</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={Object.entries(woSummary?.by_type || {}).map(([name, value]) => ({ name, value }))}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill="#3B82F6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="card">
                <h3 className="font-semibold mb-4">Work Orders by Priority</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={Object.entries(woSummary?.by_priority || {}).map(([name, value]) => ({ name, value }))}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {Object.entries(woSummary?.by_priority || {}).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )
      )}

      {/* Assets Report */}
      {activeTab === 'assets' && (
        assetLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-semibold mb-2">Total Active Assets</h3>
              <p className="text-4xl font-bold text-primary-600">{assetSummary?.total_active || 0}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="card">
                <h3 className="font-semibold mb-4">Assets by Status</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={Object.entries(assetSummary?.by_status || {}).map(([name, value]) => ({ name, value }))}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="value"
                        label
                      >
                        {Object.entries(assetSummary?.by_status || {}).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="card">
                <h3 className="font-semibold mb-4">Assets by Criticality</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={Object.entries(assetSummary?.by_criticality || {}).map(([name, value]) => ({ name, value }))}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill="#8B5CF6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {assetSummary?.top_by_work_orders?.length > 0 && (
              <div className="card">
                <h3 className="font-semibold mb-4">Top Assets by Work Orders</h3>
                <div className="space-y-3">
                  {assetSummary.top_by_work_orders.slice(0, 5).map((asset: {
                    asset_num: string;
                    name: string;
                    work_order_count: number;
                  }, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium">{asset.name}</p>
                        <p className="text-sm text-gray-500">{asset.asset_num}</p>
                      </div>
                      <span className="badge badge-blue">{asset.work_order_count} WOs</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      )}

      {/* PM Compliance Report */}
      {activeTab === 'pm-compliance' && (
        pmLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
              <h3 className="font-semibold text-green-800 mb-2">PM Compliance Rate</h3>
              <p className="text-5xl font-bold text-green-600">
                {pmCompliance?.compliance?.compliance_rate || 0}%
              </p>
              <p className="text-sm text-green-700 mt-2">
                {pmCompliance?.compliance?.completed_on_time || 0} of {pmCompliance?.compliance?.total_pm_work_orders || 0} completed on time
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card">
                <p className="text-sm text-gray-500">Completed On Time</p>
                <p className="text-2xl font-bold text-green-600">{pmCompliance?.compliance?.completed_on_time || 0}</p>
              </div>
              <div className="card">
                <p className="text-sm text-gray-500">Completed Late</p>
                <p className="text-2xl font-bold text-yellow-600">{pmCompliance?.compliance?.completed_late || 0}</p>
              </div>
              <div className="card">
                <p className="text-sm text-gray-500">Not Completed</p>
                <p className="text-2xl font-bold text-red-600">{pmCompliance?.compliance?.not_completed || 0}</p>
              </div>
            </div>
          </div>
        )
      )}

      {/* Inventory Report */}
      {activeTab === 'inventory' && (
        invLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card">
                <p className="text-sm text-gray-500">Total Inventory Value</p>
                <p className="text-3xl font-bold text-primary-600">
                  ${(inventoryValue?.summary?.total_value || 0).toLocaleString()}
                </p>
              </div>
              <div className="card">
                <p className="text-sm text-gray-500">Total Quantity</p>
                <p className="text-3xl font-bold">{inventoryValue?.summary?.total_quantity || 0}</p>
              </div>
              <div className="card">
                <p className="text-sm text-gray-500">Unique Parts</p>
                <p className="text-3xl font-bold">{inventoryValue?.summary?.unique_parts || 0}</p>
              </div>
            </div>

            {inventoryValue?.top_value_items?.length > 0 && (
              <div className="card">
                <h3 className="font-semibold mb-4">Top Value Items</h3>
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Part</th>
                        <th>Quantity</th>
                        <th>Unit Cost</th>
                        <th>Total Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {inventoryValue.top_value_items.slice(0, 10).map((item: {
                        part_number: string;
                        name: string;
                        quantity: number;
                        unit_cost: number;
                        total_value: number;
                      }, index: number) => (
                        <tr key={index}>
                          <td>
                            <p className="font-medium">{item.name}</p>
                            <p className="text-xs text-gray-500">{item.part_number}</p>
                          </td>
                          <td>{item.quantity}</td>
                          <td>${item.unit_cost.toFixed(2)}</td>
                          <td className="font-medium">${item.total_value.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}
