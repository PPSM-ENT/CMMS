import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  Package,
  AlertTriangle,
  Truck,
  Store,
} from 'lucide-react';
import { getParts, getLowStockParts, getStorerooms, getPurchaseOrders } from '../lib/api';

type TabType = 'parts' | 'low-stock' | 'purchase-orders' | 'storerooms';

export default function Inventory() {
  const [activeTab, setActiveTab] = useState<TabType>('parts');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

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
    enabled: activeTab === 'storerooms',
  });

  const { data: purchaseOrders, isLoading: poLoading } = useQuery({
    queryKey: ['purchase-orders', { page }],
    queryFn: () => getPurchaseOrders({ page, page_size: 20 }),
    enabled: activeTab === 'purchase-orders',
  });

  const tabs = [
    { id: 'parts' as TabType, label: 'Parts', icon: Package },
    { id: 'low-stock' as TabType, label: 'Low Stock', icon: AlertTriangle },
    { id: 'purchase-orders' as TabType, label: 'Purchase Orders', icon: Truck },
    { id: 'storerooms' as TabType, label: 'Storerooms', icon: Store },
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
    </div>
  );
}
