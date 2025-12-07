import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  Package,
  AlertTriangle,
  Truck,
  Store,
  ClipboardList,
  ClipboardCheck,
} from 'lucide-react';
import {
  getParts,
  getLowStockParts,
  getStorerooms,
  getPurchaseOrders,
  getCycleCounts,
  createCycleCount,
  getCycleCount,
  recordCycleCount,
  getPartCategories,
  getCycleCountPlans,
  createCycleCountPlan,
  pauseCycleCountPlan,
  pauseCycleCounts,
  pausePMScheduler,
  getCycleCountSchedulerStatus,
  getPMSchedulerStatus,
} from '../lib/api';

type TabType = 'parts' | 'low-stock' | 'purchase-orders' | 'storerooms' | 'cycle-counts';

export default function Inventory() {
  const [activeTab, setActiveTab] = useState<TabType>('parts');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const [selectedCycleCountId, setSelectedCycleCountId] = useState<number | null>(null);
  const [countFilters, setCountFilters] = useState({
    storeroom_id: '',
    category_id: '',
    bin_prefix: '',
    used_in_last_days: '',
    usage_start_date: '',
    usage_end_date: '',
    include_zero_movement: true,
    line_limit: '',
  });
  const [lineEntries, setLineEntries] = useState<Record<number, string>>({});
  const [planForm, setPlanForm] = useState({
    name: 'Scheduled Transacted Count',
    storeroom_id: '',
    frequency_value: 7,
    frequency_unit: 'DAYS',
    next_run_date: '',
  });

  const { data: parts, isLoading: partsLoading } = useQuery({
    queryKey: ['parts', { search, page }],
    queryFn: () => getParts({ search, page, page_size: 20 }),
    enabled: activeTab === 'parts',
  });

  const { data: lowStockParts, isLoading: lowStockLoading } = useQuery({
    queryKey: ['low-stock-parts'],
    queryFn: getLowStockParts,
    enabled: activeTab === 'low-stock',
  });

  const { data: storerooms, isLoading: storeroomsLoading } = useQuery({
    queryKey: ['storerooms'],
    queryFn: getStorerooms,
    enabled: activeTab === 'storerooms' || activeTab === 'cycle-counts',
  });

  const { data: purchaseOrders, isLoading: poLoading } = useQuery({
    queryKey: ['purchase-orders', { page }],
    queryFn: () => getPurchaseOrders({ page, page_size: 20 }),
    enabled: activeTab === 'purchase-orders',
  });

  const { data: categories } = useQuery({
    queryKey: ['part-categories'],
    queryFn: getPartCategories,
    enabled: activeTab === 'cycle-counts',
  });

  const { data: cycleCounts, isLoading: cycleCountsLoading } = useQuery({
    queryKey: ['cycle-counts'],
    queryFn: () => getCycleCounts({ page: 1, page_size: 50 }),
    enabled: activeTab === 'cycle-counts',
  });

  const { data: cycleCountPlans, refetch: refetchPlans } = useQuery({
    queryKey: ['cycle-count-plans'],
    queryFn: getCycleCountPlans,
    enabled: activeTab === 'cycle-counts',
  });

  const { data: cycleCountStatus, refetch: refetchCycleStatus } = useQuery({
    queryKey: ['cycle-count-status'],
    queryFn: getCycleCountSchedulerStatus,
    enabled: activeTab === 'cycle-counts',
  });

  const { data: pmStatus, refetch: refetchPmStatus } = useQuery({
    queryKey: ['pm-status'],
    queryFn: getPMSchedulerStatus,
    enabled: activeTab === 'cycle-counts',
  });

  const { data: cycleCountDetail, isLoading: cycleCountDetailLoading } = useQuery({
    queryKey: ['cycle-count', selectedCycleCountId],
    queryFn: () => getCycleCount(Number(selectedCycleCountId)),
    enabled: activeTab === 'cycle-counts' && !!selectedCycleCountId,
  });

  useEffect(() => {
    if (activeTab === 'cycle-counts' && cycleCounts?.items?.length && !selectedCycleCountId) {
      setSelectedCycleCountId(cycleCounts.items[0].id);
    }
  }, [activeTab, cycleCounts, selectedCycleCountId]);

  useEffect(() => {
    if (cycleCountDetail?.lines) {
      const next: Record<number, string> = {};
      cycleCountDetail.lines.forEach((line: any) => {
        next[line.id] =
          line.counted_quantity !== null && line.counted_quantity !== undefined
            ? String(line.counted_quantity)
            : '';
      });
      setLineEntries(next);
    }
  }, [cycleCountDetail]);

  const createCycleCountMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCycleCount(payload),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['cycle-counts'] });
      setSelectedCycleCountId(data.id);
      setLineEntries({});
    },
  });

  const recordCycleCountMutation = useMutation({
    mutationFn: ({ id, lines }: { id: number; lines: { line_id: number; counted_quantity: number; notes?: string }[] }) =>
      recordCycleCount(id, lines),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cycle-counts'] });
      queryClient.invalidateQueries({ queryKey: ['cycle-count', variables.id] });
    },
  });

  const createPlanMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCycleCountPlan(payload),
    onSuccess: () => {
      refetchPlans();
    },
  });

  const pausePlanMutation = useMutation({
    mutationFn: ({ id, paused }: { id: number; paused: boolean }) => pauseCycleCountPlan(id, paused),
    onSuccess: () => refetchPlans(),
  });

  const pauseCycleCountsMutation = useMutation({
    mutationFn: (paused: boolean) => pauseCycleCounts(paused),
    onSuccess: () => refetchCycleStatus(),
  });

  const pausePmMutation = useMutation({
    mutationFn: (paused: boolean) => pausePMScheduler(paused),
    onSuccess: () => refetchPmStatus(),
  });

  const handleCreateCycleCount = () => {
    if (!countFilters.storeroom_id) return;
    const payload: Record<string, unknown> = {
      storeroom_id: Number(countFilters.storeroom_id),
      include_zero_movement: countFilters.include_zero_movement,
    };
    if (countFilters.category_id) payload.category_ids = [Number(countFilters.category_id)];
    if (countFilters.bin_prefix) payload.bin_prefix = countFilters.bin_prefix;
    if (countFilters.used_in_last_days) payload.used_in_last_days = Number(countFilters.used_in_last_days);
    if (countFilters.usage_start_date) payload.usage_start_date = countFilters.usage_start_date;
    if (countFilters.usage_end_date) payload.usage_end_date = countFilters.usage_end_date;
    if (countFilters.line_limit) payload.line_limit = Number(countFilters.line_limit);
    createCycleCountMutation.mutate(payload);
  };

  const handleRecordCounts = () => {
    if (!selectedCycleCountId || !cycleCountDetail?.lines) return;
    const payloadLines = cycleCountDetail.lines
      .filter((line: any) => lineEntries[line.id] !== undefined && lineEntries[line.id] !== '')
      .map((line: any) => ({
        line_id: line.id,
        counted_quantity: Number(lineEntries[line.id]),
      }));

    if (!payloadLines.length) return;
    recordCycleCountMutation.mutate({ id: selectedCycleCountId, lines: payloadLines });
  };

  const handleCreatePlan = () => {
    if (!planForm.storeroom_id) return;
    createPlanMutation.mutate({
      name: planForm.name,
      storeroom_id: Number(planForm.storeroom_id),
      frequency_value: Number(planForm.frequency_value),
      frequency_unit: planForm.frequency_unit,
      next_run_date: planForm.next_run_date || undefined,
      used_in_last_days: countFilters.used_in_last_days ? Number(countFilters.used_in_last_days) : undefined,
      usage_start_date: countFilters.usage_start_date || undefined,
      usage_end_date: countFilters.usage_end_date || undefined,
      transacted_only: true,
      include_zero_movement: false,
      line_limit: countFilters.line_limit ? Number(countFilters.line_limit) : undefined,
      bin_prefix: countFilters.bin_prefix || undefined,
      category_ids: countFilters.category_id ? [Number(countFilters.category_id)] : undefined,
      template_type: 'CUSTOM',
    });
  };

  const toggleCyclePause = () => {
    const desired = !(cycleCountStatus?.pause_cycle_counts ?? false);
    pauseCycleCountsMutation.mutate(desired);
  };

  const togglePmPause = () => {
    const desired = !(pmStatus?.pause_pm ?? false);
    pausePmMutation.mutate(desired);
  };

  const tabs = [
    { id: 'parts' as TabType, label: 'Parts', icon: Package },
    { id: 'low-stock' as TabType, label: 'Low Stock', icon: AlertTriangle },
    { id: 'purchase-orders' as TabType, label: 'Purchase Orders', icon: Truck },
    { id: 'storerooms' as TabType, label: 'Storerooms', icon: Store },
    { id: 'cycle-counts' as TabType, label: 'Cycle Counts', icon: ClipboardList },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-gray-600">Manage parts, stock levels, and purchasing</p>
        </div>
        <div className="flex gap-2">
          <Link to="/inventory/parts/new" className="btn-primary flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Add Part
          </Link>
          <Link to="/inventory/po/new" className="btn-secondary flex items-center gap-2">
            <Truck className="w-5 h-5" />
            New PO
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setPage(1);
              }}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.id === 'low-stock' && lowStockParts?.length > 0 && (
                <span className="ml-1 px-2 py-0.5 text-xs bg-red-100 text-red-600 rounded-full">
                  {lowStockParts.length}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Search */}
      {(activeTab === 'parts' || activeTab === 'purchase-orders') && (
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder={`Search ${activeTab === 'parts' ? 'parts' : 'purchase orders'}...`}
            className="input pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {/* Parts Tab */}
      {activeTab === 'parts' && (
        partsLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Part</th>
                    <th>Category</th>
                    <th>Unit Cost</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {parts?.items?.map((part: {
                    id: number;
                    part_number: string;
                    name: string;
                    description?: string;
                    category_id?: number;
                    unit_cost: number;
                    status: string;
                  }) => (
                    <tr key={part.id}>
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                            <Package className="w-5 h-5 text-gray-500" />
                          </div>
                          <div>
                            <p className="font-medium">{part.name}</p>
                            <p className="text-xs text-gray-500">{part.part_number}</p>
                          </div>
                        </div>
                      </td>
                      <td className="text-gray-600">{part.category_id || '-'}</td>
                      <td className="font-medium">${part.unit_cost.toFixed(2)}</td>
                      <td>
                        <span className={`badge ${
                          part.status === 'ACTIVE' ? 'badge-green' : 'badge-gray'
                        }`}>
                          {part.status}
                        </span>
                      </td>
                      <td>
                        <Link
                          to={`/inventory/parts/${part.id}`}
                          className="text-primary-600 hover:underline text-sm"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      {/* Low Stock Tab */}
      {activeTab === 'low-stock' && (
        lowStockLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : lowStockParts?.length > 0 ? (
          <div className="space-y-4">
            {lowStockParts.map((part: {
              id: number;
              part_number: string;
              name: string;
              total_on_hand: number;
              total_available: number;
              stock_levels: Array<{
                reorder_point?: number;
                storeroom_id: number;
              }>;
            }) => (
              <div key={part.id} className="card border-l-4 border-l-orange-500">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-6 h-6 text-orange-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{part.name}</h3>
                      <p className="text-sm text-gray-500">{part.part_number}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-orange-600">{part.total_on_hand}</p>
                    <p className="text-sm text-gray-500">
                      Reorder point: {part.stock_levels[0]?.reorder_point || 0}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card text-center py-12">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">All parts in stock</h3>
            <p className="text-gray-500 mt-1">No parts are below their reorder point</p>
          </div>
        )
      )}

      {/* Purchase Orders Tab */}
      {activeTab === 'purchase-orders' && (
        poLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>PO Number</th>
                    <th>Vendor</th>
                    <th>Status</th>
                    <th>Total</th>
                    <th>Order Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {purchaseOrders?.items?.map((po: {
                    id: number;
                    po_number: string;
                    vendor_id: number;
                    status: string;
                    total: number;
                    order_date?: string;
                  }) => (
                    <tr key={po.id}>
                      <td className="font-medium">{po.po_number}</td>
                      <td className="text-gray-600">Vendor #{po.vendor_id}</td>
                      <td>
                        <span className={`badge ${
                          po.status === 'RECEIVED' ? 'badge-green' :
                          po.status === 'ORDERED' ? 'badge-blue' :
                          po.status === 'DRAFT' ? 'badge-gray' :
                          'badge-yellow'
                        }`}>
                          {po.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="font-medium">${po.total.toLocaleString()}</td>
                      <td className="text-gray-600">{po.order_date || '-'}</td>
                      <td>
                        <Link
                          to={`/inventory/po/${po.id}`}
                          className="text-primary-600 hover:underline text-sm"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      {/* Storerooms Tab */}
      {activeTab === 'storerooms' && (
        storeroomsLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {storerooms?.map((storeroom: {
              id: number;
              code: string;
              name: string;
              description?: string;
              is_default: boolean;
              is_active: boolean;
            }) => (
              <div key={storeroom.id} className="card">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                    <Store className="w-6 h-6 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{storeroom.name}</h3>
                      {storeroom.is_default && (
                        <span className="badge badge-blue">Default</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500">{storeroom.code}</p>
                    {storeroom.description && (
                      <p className="text-sm text-gray-600 mt-1">{storeroom.description}</p>
                    )}
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t">
                  <Link
                    to={`/inventory/storerooms/${storeroom.id}`}
                    className="text-primary-600 hover:underline text-sm"
                  >
                    View Stock
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Cycle Counts Tab */}
      {activeTab === 'cycle-counts' && (
        cycleCountsLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="card flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Cycle Count Scheduler</p>
                  <p className="font-medium">
                    {cycleCountStatus?.pause_cycle_counts ? 'Paused' : 'Running'}
                  </p>
                </div>
                <button
                  onClick={toggleCyclePause}
                  className="btn-secondary"
                  disabled={pauseCycleCountsMutation.isLoading}
                >
                  {cycleCountStatus?.pause_cycle_counts ? 'Resume' : 'Pause'}
                </button>
              </div>
              <div className="card flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">PM / WO Scheduler</p>
                  <p className="font-medium">{pmStatus?.pause_pm ? 'Paused' : 'Running'}</p>
                </div>
                <button
                  onClick={togglePmPause}
                  className="btn-secondary"
                  disabled={pausePmMutation.isLoading}
                >
                  {pmStatus?.pause_pm ? 'Resume' : 'Pause'}
                </button>
              </div>
            </div>
            <div className="card">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                <div>
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <ClipboardCheck className="w-5 h-5" />
                    Start Cycle Count
                  </h2>
                  <p className="text-sm text-gray-500">
                    Build a count by storeroom, bin, classification, or recent work-order usage.
                  </p>
                </div>
                <button
                  onClick={handleCreateCycleCount}
                  disabled={createCycleCountMutation.isLoading || !countFilters.storeroom_id}
                  className="btn-primary flex items-center gap-2 self-start md:self-auto"
                >
                  {createCycleCountMutation.isLoading ? (
                    <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <ClipboardCheck className="w-4 h-4" />
                  )}
                  Start Count
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-sm text-gray-500">Storeroom</label>
                  <select
                    className="input mt-1"
                    value={countFilters.storeroom_id}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, storeroom_id: e.target.value }))}
                  >
                    <option value="">Select storeroom</option>
                    {storerooms?.map((room: any) => (
                      <option key={room.id} value={room.id}>{room.code} - {room.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Category</label>
                  <select
                    className="input mt-1"
                    value={countFilters.category_id}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, category_id: e.target.value }))}
                  >
                    <option value="">Any</option>
                    {categories?.map((cat: any) => (
                      <option key={cat.id} value={cat.id}>{cat.code} - {cat.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Bin prefix</label>
                  <input
                    className="input mt-1"
                    placeholder="A-01"
                    value={countFilters.bin_prefix}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, bin_prefix: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Used in last (days)</label>
                  <input
                    type="number"
                    className="input mt-1"
                    value={countFilters.used_in_last_days}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, used_in_last_days: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Usage start</label>
                  <input
                    type="date"
                    className="input mt-1"
                    value={countFilters.usage_start_date}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, usage_start_date: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Usage end</label>
                  <input
                    type="date"
                    className="input mt-1"
                    value={countFilters.usage_end_date}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, usage_end_date: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Line limit</label>
                  <input
                    type="number"
                    className="input mt-1"
                    placeholder="e.g. 50"
                    value={countFilters.line_limit}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, line_limit: e.target.value }))}
                  />
                </div>
                <div className="flex items-center gap-2 mt-5">
                  <input
                    type="checkbox"
                    checked={countFilters.include_zero_movement}
                    onChange={(e) => setCountFilters((prev) => ({ ...prev, include_zero_movement: e.target.checked }))}
                  />
                  <span className="text-sm text-gray-600">Include parts with no recent movement</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">Cycle Count Sessions</h2>
                  <span className="text-sm text-gray-500">{cycleCounts?.total || 0} total</span>
                </div>
                {cycleCounts?.items?.length ? (
                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Status</th>
                          <th>Lines</th>
                          <th>Storeroom</th>
                          <th>Variance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cycleCounts.items.map((count: any) => (
                          <tr
                            key={count.id}
                            className={`cursor-pointer ${selectedCycleCountId === count.id ? 'bg-primary-50' : ''}`}
                            onClick={() => setSelectedCycleCountId(count.id)}
                          >
                            <td className="font-medium">{count.name}</td>
                            <td>
                              <span className={`badge ${
                                count.status === 'COMPLETED' ? 'badge-green' :
                                count.status === 'IN_PROGRESS' ? 'badge-blue' :
                                count.status === 'CANCELLED' ? 'badge-red' : 'badge-gray'
                              }`}>
                                {count.status.replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td className="text-gray-700">{count.total_lines}</td>
                            <td className="text-gray-600">{count.storeroom_code || '-'}</td>
                            <td className={count.total_variance === 0 ? 'text-gray-600' : 'text-red-600'}>
                              {count.total_variance?.toFixed ? count.total_variance.toFixed(2) : count.total_variance}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500">No cycle count sessions yet.</p>
                )}
              </div>

              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">Count Lines</h2>
                  {cycleCountDetail?.status && (
                    <span className={`badge ${
                      cycleCountDetail.status === 'COMPLETED' ? 'badge-green' :
                      cycleCountDetail.status === 'IN_PROGRESS' ? 'badge-blue' :
                      'badge-gray'
                    }`}>
                      {cycleCountDetail.status}
                    </span>
                  )}
                </div>
                {cycleCountDetailLoading ? (
                  <div className="flex items-center justify-center h-40">
                    <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : cycleCountDetail?.lines?.length ? (
                  <div className="space-y-3">
                    <div className="table-container">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Part</th>
                            <th>Bin</th>
                            <th className="text-right">Expected</th>
                            <th className="text-right">Counted</th>
                            <th className="text-right">Variance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cycleCountDetail.lines.map((line: any) => (
                            <tr key={line.id}>
                              <td>
                                <div className="font-medium">{line.part_number}</div>
                                <div className="text-sm text-gray-500">{line.part_name}</div>
                              </td>
                              <td>{line.bin_location || '-'}</td>
                              <td className="text-right text-gray-700">{line.expected_quantity}</td>
                              <td className="text-right">
                                <input
                                  type="number"
                                  className="input w-28 text-right"
                                  value={lineEntries[line.id] ?? ''}
                                  onChange={(e) => setLineEntries((prev) => ({
                                    ...prev,
                                    [line.id]: e.target.value,
                                  }))}
                                />
                              </td>
                              <td className="text-right">
                                {line.variance !== null && line.variance !== undefined
                                  ? line.variance.toFixed(2)
                                  : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="flex justify-end">
                      <button
                        onClick={handleRecordCounts}
                        disabled={recordCycleCountMutation.isLoading}
                        className="btn-primary"
                      >
                        {recordCycleCountMutation.isLoading ? 'Saving...' : 'Save Counts'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500">Select a cycle count to view lines.</p>
                )}
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">Scheduled Cycle Count Plans</h2>
                <button
                  onClick={handleCreatePlan}
                  disabled={createPlanMutation.isLoading || !planForm.storeroom_id}
                  className="btn-primary"
                >
                  {createPlanMutation.isLoading ? 'Saving...' : 'Save Plan'}
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
                <div>
                  <label className="text-sm text-gray-500">Plan name</label>
                  <input
                    className="input mt-1"
                    value={planForm.name}
                    onChange={(e) => setPlanForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Storeroom</label>
                  <select
                    className="input mt-1"
                    value={planForm.storeroom_id}
                    onChange={(e) => setPlanForm((p) => ({ ...p, storeroom_id: e.target.value }))}
                  >
                    <option value="">Select</option>
                    {storerooms?.map((room: any) => (
                      <option key={room.id} value={room.id}>{room.code} - {room.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Every</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      className="input mt-1 w-20"
                      value={planForm.frequency_value}
                      onChange={(e) => setPlanForm((p) => ({ ...p, frequency_value: Number(e.target.value) }))}
                    />
                    <select
                      className="input mt-1"
                      value={planForm.frequency_unit}
                      onChange={(e) => setPlanForm((p) => ({ ...p, frequency_unit: e.target.value }))}
                    >
                      <option value="DAYS">Days</option>
                      <option value="WEEKS">Weeks</option>
                      <option value="MONTHS">Months</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Next run date</label>
                  <input
                    type="date"
                    className="input mt-1"
                    value={planForm.next_run_date}
                    onChange={(e) => setPlanForm((p) => ({ ...p, next_run_date: e.target.value }))}
                  />
                </div>
              </div>

              {cycleCountPlans?.length ? (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Next Run</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {cycleCountPlans.map((plan: any) => (
                        <tr key={plan.id}>
                          <td className="font-medium">{plan.name}</td>
                          <td className="text-gray-600">{plan.next_run_date || '-'}</td>
                          <td>
                            <span className={`badge ${plan.is_paused ? 'badge-gray' : 'badge-green'}`}>
                              {plan.is_paused ? 'Paused' : 'Active'}
                            </span>
                          </td>
                          <td className="text-right">
                            <button
                              className="btn-secondary text-sm"
                              onClick={() => pausePlanMutation.mutate({ id: plan.id, paused: !plan.is_paused })}
                              disabled={pausePlanMutation.isLoading}
                            >
                              {plan.is_paused ? 'Resume' : 'Pause'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500">No scheduled plans yet.</p>
              )}
            </div>
          </div>
        )
      )}
    </div>
  );
}
