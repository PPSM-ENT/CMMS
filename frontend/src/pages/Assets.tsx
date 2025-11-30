import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  Filter,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Wrench,
  AlertCircle,
} from 'lucide-react';
import { getAssets } from '../lib/api';

const statusColors: Record<string, string> = {
  OPERATING: 'badge-green',
  NOT_OPERATING: 'badge-red',
  IN_REPAIR: 'badge-yellow',
  STANDBY: 'badge-blue',
  DECOMMISSIONED: 'badge-gray',
};

const criticalityColors: Record<string, string> = {
  CRITICAL: 'text-red-600 bg-red-50',
  HIGH: 'text-orange-600 bg-orange-50',
  MEDIUM: 'text-yellow-600 bg-yellow-50',
  LOW: 'text-green-600 bg-green-50',
};

const QUICK_FILTERS = [
  { key: '', label: 'All assets' },
  { key: 'critical', label: 'Critical Assets' },
  { key: 'down', label: 'Down / In Repair' },
  { key: 'warranty_90', label: 'Warranty Expiring (90d)' },
  { key: 'recent', label: 'Recently Added' },
];

const INITIAL_FILTERS = {
  quickFilter: '',
  locationIds: '',
  createdFrom: '',
  createdTo: '',
  installFrom: '',
  installTo: '',
  warrantyBefore: '',
  hasOpenWorkOrders: false,
  customFilters: '',
};

export default function Assets() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [criticalityFilter, setCriticalityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [filters, setFilters] = useState(INITIAL_FILTERS);

  const updateFilter = (field: keyof typeof INITIAL_FILTERS, value: string | boolean) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters(INITIAL_FILTERS);
    setStatusFilter('');
    setCriticalityFilter('');
    setCategoryFilter('');
    setSearch('');
    setPage(1);
  };

  const params: Record<string, unknown> = {
    search,
    status: statusFilter || undefined,
    criticality: criticalityFilter || undefined,
    category: categoryFilter || undefined,
    quick_filter: filters.quickFilter || undefined,
    page,
    page_size: 20,
    location_ids: filters.locationIds || undefined,
    created_from: filters.createdFrom || undefined,
    created_to: filters.createdTo || undefined,
    install_from: filters.installFrom || undefined,
    install_to: filters.installTo || undefined,
    warranty_before: filters.warrantyBefore || undefined,
    custom_filters: filters.customFilters.trim() || undefined,
  };

  if (filters.hasOpenWorkOrders) {
    params.has_open_work_orders = true;
  }

  const { data, isLoading } = useQuery({
    queryKey: ['assets', { search, status: statusFilter, page, filters, criticalityFilter, categoryFilter }],
    queryFn: () => getAssets(params),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assets</h1>
          <p className="text-gray-600">Manage your equipment and machinery</p>
        </div>
        <Link to="/assets/new" className="btn-primary flex items-center gap-2 w-fit">
          <Plus className="w-5 h-5" />
          Add Asset
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
                placeholder="Search assets..."
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
                <option value="OPERATING">Operating</option>
                <option value="NOT_OPERATING">Not Operating</option>
                <option value="IN_REPAIR">In Repair</option>
                <option value="STANDBY">Standby</option>
                <option value="DECOMMISSIONED">Decommissioned</option>
              </select>
              <select
                className="input w-40"
                value={criticalityFilter}
                onChange={(e) => {
                  setCriticalityFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Criticalities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
              <input
                type="text"
                className="input w-48"
                placeholder="Category"
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(1);
                }}
              />
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
            {QUICK_FILTERS.map((option) => (
              <button
                key={option.key || 'all'}
                className={`px-3 py-1 rounded-full border ${
                  filters.quickFilter === option.key
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'border-gray-300 text-gray-600 hover:border-primary-500'
                }`}
                onClick={() => {
                  updateFilter('quickFilter', option.key);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>

          {showAdvancedFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-gray-100 pt-4">
              <div>
                <label className="text-xs font-medium text-gray-500">Location IDs</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="101,102"
                  value={filters.locationIds}
                  onChange={(e) => updateFilter('locationIds', e.target.value)}
                />
              </div>
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
                <label className="text-xs font-medium text-gray-500">Install Date Between</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="date"
                    className="input"
                    value={filters.installFrom}
                    onChange={(e) => updateFilter('installFrom', e.target.value)}
                  />
                  <input
                    type="date"
                    className="input"
                    value={filters.installTo}
                    onChange={(e) => updateFilter('installTo', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Warranty Expiring Before</label>
                <input
                  type="date"
                  className="input mt-1"
                  value={filters.warrantyBefore}
                  onChange={(e) => updateFilter('warrantyBefore', e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="open-wo"
                  type="checkbox"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.hasOpenWorkOrders}
                  onChange={(e) => updateFilter('hasOpenWorkOrders', e.target.checked)}
                />
                <label htmlFor="open-wo" className="text-sm text-gray-700">
                  Only show assets with open work orders
                </label>
              </div>
              <div className="md:col-span-3">
                <label className="text-xs font-medium text-gray-500">Custom Filter Expression</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="status:in:OPERATING,IN_REPAIR"
                  value={filters.customFilters}
                  onChange={(e) => updateFilter('customFilters', e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use <strong>field:operator:value</strong> syntax just like the dashboard widgets.
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

      {/* Assets list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="card overflow-hidden p-0">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Location</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Criticality</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data?.items?.map((asset: {
                    id: number;
                    asset_num: string;
                    name: string;
                    location_id?: number;
                    category?: string;
                    status: string;
                    criticality: string;
                    manufacturer?: string;
                    model?: string;
                  }) => (
                    <tr key={asset.id}>
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                            <Wrench className="w-5 h-5 text-gray-500" />
                          </div>
                          <div>
                            <p className="font-medium">{asset.name}</p>
                            <p className="text-xs text-gray-500">{asset.asset_num}</p>
                          </div>
                        </div>
                      </td>
                      <td className="text-gray-600">{asset.location_id || '-'}</td>
                      <td className="text-gray-600">{asset.category || '-'}</td>
                      <td>
                        <span className={`badge ${statusColors[asset.status] || 'badge-gray'}`}>
                          {asset.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${criticalityColors[asset.criticality]}`}>
                          {asset.criticality}
                        </span>
                      </td>
                      <td>
                        <Link
                          to={`/assets/${asset.id}`}
                          className="text-primary-600 hover:text-primary-700"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {data?.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, data.total)} of {data.total} assets
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
              <h3 className="text-lg font-medium text-gray-900">No assets found</h3>
              <p className="text-gray-500 mt-1">Try adjusting your search or filters</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
