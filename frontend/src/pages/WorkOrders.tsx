import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  Filter,
  ChevronRight,
  ClipboardList,
  AlertCircle,
  Clock,
  User,
  Users,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { getWorkOrders, getUsers } from '../lib/api';
import { format } from 'date-fns';

const statusColors: Record<string, string> = {
  DRAFT: 'badge-gray',
  WAITING_APPROVAL: 'badge-yellow',
  APPROVED: 'badge-blue',
  SCHEDULED: 'badge-blue',
  IN_PROGRESS: 'badge-yellow',
  ON_HOLD: 'badge-red',
  COMPLETED: 'badge-green',
  CLOSED: 'badge-gray',
  CANCELLED: 'badge-gray',
};

const priorityColors: Record<string, string> = {
  EMERGENCY: 'text-red-600',
  HIGH: 'text-orange-600',
  MEDIUM: 'text-yellow-600',
  LOW: 'text-green-600',
  SCHEDULED: 'text-blue-600',
};

const typeIcons: Record<string, string> = {
  CORRECTIVE: 'bg-red-100 text-red-600',
  PREVENTIVE: 'bg-blue-100 text-blue-600',
  PREDICTIVE: 'bg-purple-100 text-purple-600',
  EMERGENCY: 'bg-red-100 text-red-600',
  PROJECT: 'bg-gray-100 text-gray-600',
  INSPECTION: 'bg-green-100 text-green-600',
};

const QUICK_LOOKUPS = [
  { key: '', label: 'All records' },
  { key: 'overdue', label: 'Overdue' },
  { key: 'my_open', label: 'My Open WOs' },
  { key: 'completed_last_7', label: 'Completed (7d)' },
  { key: 'safety', label: 'Safety / Inspection' },
];

const INITIAL_FILTERS = {
  createdFrom: '',
  createdTo: '',
  dueFrom: '',
  dueTo: '',
  assignedTo: '',
  assignedTeam: '',
  quickFilter: '',
  downtimeOnly: false,
  laborUserId: '',
  laborCraft: '',
  customFilters: '',
};

export default function WorkOrders() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [filters, setFilters] = useState(INITIAL_FILTERS);

  const { data: userResponse } = useQuery({
    queryKey: ['users', 'filterable'],
    queryFn: () => getUsers({ page: 1, page_size: 200, is_active: true }),
  });
  const userOptions = userResponse?.items || [];

  

  const updateFilter = (field: keyof typeof INITIAL_FILTERS, value: string | boolean) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters(INITIAL_FILTERS);
    setStatusFilter('');
    setTypeFilter('');
    setSearch('');
    setPage(1);
  };

  const params: Record<string, unknown> = {
    search,
    status: statusFilter || undefined,
    work_type: typeFilter || undefined,
    page,
    page_size: 20,
    created_from: filters.createdFrom || undefined,
    created_to: filters.createdTo || undefined,
    due_from: filters.dueFrom || undefined,
    due_to: filters.dueTo || undefined,
    assigned_to_id: filters.assignedTo ? Number(filters.assignedTo) : undefined,
    assigned_team: filters.assignedTeam || undefined,
    quick_filter: filters.quickFilter || undefined,
    labor_craft: filters.laborCraft || undefined,
    custom_filters: filters.customFilters.trim() || undefined,
  };

  if (filters.downtimeOnly) {
    params.downtime_only = true;
  }
  if (filters.laborUserId) {
    params.labor_user_id = Number(filters.laborUserId);
  }

  const { data, isLoading } = useQuery({
    queryKey: ['work-orders', { search, status: statusFilter, work_type: typeFilter, page, filters }],
    queryFn: () => getWorkOrders(params),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Orders</h1>
          <p className="text-gray-600">Track and manage maintenance tasks</p>
        </div>
        <Link to="/work-orders/new" className="btn-primary flex items-center gap-2 w-fit">
          <Plus className="w-5 h-5" />
          New Work Order
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search work orders..."
                className="input pl-10"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                className="input w-40"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
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
              <select
                className="input w-40"
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Types</option>
                <option value="CORRECTIVE">Corrective</option>
                <option value="PREVENTIVE">Preventive</option>
                <option value="EMERGENCY">Emergency</option>
                <option value="INSPECTION">Inspection</option>
                <option value="PROJECT">Project</option>
              </select>
              <button
                className="btn-secondary flex items-center gap-2"
                onClick={() => setShowAdvancedFilters((prev) => !prev)}
              >
                <Filter className="w-4 h-4" />
                Advanced
                {showAdvancedFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-sm">
            {QUICK_LOOKUPS.map((option) => (
              <button
                key={option.key || 'all'}
                className={`px-3 py-1 rounded-full border ${
                  filters.quickFilter === option.key
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'border-gray-300 text-gray-600 hover:border-primary-500'
                }`}
                onClick={() => updateFilter('quickFilter', option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>

          {showAdvancedFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-gray-100 pt-4">
              <div>
                <label className="text-xs font-medium text-gray-500">Created Between</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="date"
                    className="input"
                    value={filters.createdFrom}
                    onChange={(e) => updateFilter('createdFrom', e.target.value)}
                  />
                  <input
                    type="date"
                    className="input"
                    value={filters.createdTo}
                    onChange={(e) => updateFilter('createdTo', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Due Date Between</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="date"
                    className="input"
                    value={filters.dueFrom}
                    onChange={(e) => updateFilter('dueFrom', e.target.value)}
                  />
                  <input
                    type="date"
                    className="input"
                    value={filters.dueTo}
                    onChange={(e) => updateFilter('dueTo', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Assigned To</label>
                <select
                  className="input mt-1"
                  value={filters.assignedTo}
                  onChange={(e) => updateFilter('assignedTo', e.target.value)}
                >
                  <option value="">Anyone</option>
                  {userOptions.map((user: any) => (
                    <option key={user.id} value={user.id}>
                      {user.first_name} {user.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Assigned Team</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="Line 1 Mechanics"
                  value={filters.assignedTeam}
                  onChange={(e) => updateFilter('assignedTeam', e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Labor Recorded By</label>
                <select
                  className="input mt-1"
                  value={filters.laborUserId}
                  onChange={(e) => updateFilter('laborUserId', e.target.value)}
                >
                  <option value="">Anyone</option>
                  {userOptions.map((user: any) => (
                    <option key={user.id} value={user.id}>
                      {user.first_name} {user.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Labor Craft Contains</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="Electrician"
                  value={filters.laborCraft}
                  onChange={(e) => updateFilter('laborCraft', e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="downtime-only"
                  type="checkbox"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.downtimeOnly}
                  onChange={(e) => updateFilter('downtimeOnly', e.target.checked)}
                />
                <label htmlFor="downtime-only" className="text-sm text-gray-700">
                  Only show downtime events
                </label>
              </div>
              <div className="md:col-span-3">
                <label className="text-xs font-medium text-gray-500">Custom Filter Expression</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="priority:eq:HIGH|asset_status:eq:OPERATING"
                  value={filters.customFilters}
                  onChange={(e) => updateFilter('customFilters', e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use <strong>field:operator:value</strong>. Chain with <code>|</code> for multiple rules.
                </p>
              </div>
              <div className="md:col-span-3 flex justify-end gap-3">
                <button className="btn-secondary" onClick={clearFilters}>
                  Clear Filters
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Work orders list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {data?.items?.map((wo: {
              id: number;
              wo_number: string;
              title: string;
              description?: string;
              status: string;
              work_type: string;
              priority: string;
              asset_id?: number;
              assigned_to_id?: number;
              assigned_group_name?: string;
              due_date?: string;
              created_at: string;
              total_cost: number;
            }) => (
              <Link
                key={wo.id}
                to={`/work-orders/${wo.id}`}
                className="card hover:shadow-md transition-shadow flex items-start gap-4"
              >
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${typeIcons[wo.work_type] || 'bg-gray-100'}`}>
                  <ClipboardList className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{wo.title}</h3>
                        <span className={`badge ${statusColors[wo.status]}`}>
                          {wo.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">{wo.wo_number}</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  </div>
                  {wo.description && (
                    <p className="mt-2 text-sm text-gray-600 line-clamp-2">{wo.description}</p>
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-500">
                    <span className={`font-medium ${priorityColors[wo.priority]}`}>
                      {wo.priority}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {wo.due_date ? format(new Date(wo.due_date), 'MMM d, yyyy') : 'No due date'}
                    </span>
                    {wo.assigned_to_id && (
                      <span className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        Assigned
                      </span>
                    )}
                    {wo.assigned_group_name && (
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {wo.assigned_group_name}
                      </span>
                    )}
                    {wo.total_cost > 0 && (
                      <span className="font-medium text-gray-700">
                        ${wo.total_cost.toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {data?.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, data.total)} of {data.total} work orders
              </p>
              <div className="flex gap-2">
                <button
                  className="btn-secondary"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <button
                  className="btn-secondary"
                  disabled={page === data.pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {data?.items?.length === 0 && (
            <div className="card text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No work orders found</h3>
              <p className="text-gray-500 mt-1">Try adjusting your search or filters</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
