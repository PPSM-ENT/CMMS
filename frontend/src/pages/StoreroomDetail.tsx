import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Warehouse,
  Package,
  AlertTriangle,
  TrendingDown,
} from 'lucide-react';
import { getStorerooms, getStoreroomStock, getParts } from '../lib/api';

interface StockLevel {
  id: number;
  part_id: number;
  quantity: number;
  bin_location: string | null;
  min_quantity: number;
  max_quantity: number;
  reorder_point: number;
  last_counted: string | null;
}

interface Storeroom {
  id: number;
  code: string;
  name: string;
  description: string | null;
  address: string | null;
  is_active: boolean;
}

export default function StoreroomDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: storerooms } = useQuery({
    queryKey: ['storerooms-list'],
    queryFn: getStorerooms,
  });

  const storeroom = storerooms?.find((s: Storeroom) => s.id === Number(id));

  const { data: stockLevels, isLoading: stockLoading } = useQuery({
    queryKey: ['storeroom-stock', id],
    queryFn: () => getStoreroomStock(Number(id)),
    enabled: !!id,
  });

  const { data: partsData } = useQuery({
    queryKey: ['parts-list'],
    queryFn: () => getParts({ page_size: 500 }),
  });

  const getPartInfo = (partId: number) => {
    const part = partsData?.items?.find((p: { id: number }) => p.id === partId);
    return part || null;
  };

  const isLoading = !storerooms || stockLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!storeroom) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Storeroom not found</p>
        <button onClick={() => navigate('/inventory')} className="btn-primary mt-4">
          Back to Inventory
        </button>
      </div>
    );
  }

  const lowStockItems = stockLevels?.filter(
    (s: StockLevel) => s.quantity <= s.reorder_point
  ) || [];

  const totalItems = stockLevels?.length || 0;
  const totalQuantity = stockLevels?.reduce(
    (sum: number, s: StockLevel) => sum + s.quantity,
    0
  ) || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{storeroom.name}</h1>
              <span className={`badge ${storeroom.is_active ? 'badge-green' : 'badge-red'}`}>
                {storeroom.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="text-gray-600">{storeroom.code}</p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Package className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Items</p>
              <p className="text-2xl font-bold">{totalItems}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <Warehouse className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Quantity</p>
              <p className="text-2xl font-bold">{totalQuantity}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-lg ${lowStockItems.length > 0 ? 'bg-orange-100' : 'bg-gray-100'}`}>
              <TrendingDown className={`w-6 h-6 ${lowStockItems.length > 0 ? 'text-orange-600' : 'text-gray-600'}`} />
            </div>
            <div>
              <p className="text-sm text-gray-600">Low Stock Items</p>
              <p className="text-2xl font-bold">{lowStockItems.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Storeroom Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Warehouse className="w-5 h-5" />
          Storeroom Information
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Code</p>
            <p className="font-medium">{storeroom.code}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Name</p>
            <p className="font-medium">{storeroom.name}</p>
          </div>
          {storeroom.description && (
            <div className="col-span-2">
              <p className="text-sm text-gray-500">Description</p>
              <p className="font-medium">{storeroom.description}</p>
            </div>
          )}
          {storeroom.address && (
            <div className="col-span-2">
              <p className="text-sm text-gray-500">Address</p>
              <p className="font-medium">{storeroom.address}</p>
            </div>
          )}
        </div>
      </div>

      {/* Low Stock Alert */}
      {lowStockItems.length > 0 && (
        <div className="card border-l-4 border-l-orange-500">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-6 h-6 text-orange-500 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-orange-800">Low Stock Alert</h3>
              <p className="text-sm text-orange-700 mt-1">
                {lowStockItems.length} item(s) are at or below reorder point
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {lowStockItems.slice(0, 5).map((stock: StockLevel) => {
                  const part = getPartInfo(stock.part_id);
                  return (
                    <span key={stock.id} className="badge bg-orange-100 text-orange-800">
                      {part?.part_number || `Part #${stock.part_id}`}
                    </span>
                  );
                })}
                {lowStockItems.length > 5 && (
                  <span className="badge bg-gray-100 text-gray-800">
                    +{lowStockItems.length - 5} more
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stock Levels Table */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Package className="w-5 h-5" />
          Stock Levels
        </h2>
        {stockLevels && stockLevels.length > 0 ? (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Part</th>
                  <th>Bin Location</th>
                  <th className="text-right">Quantity</th>
                  <th className="text-right">Min</th>
                  <th className="text-right">Reorder Point</th>
                  <th className="text-right">Max</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {stockLevels.map((stock: StockLevel) => {
                  const part = getPartInfo(stock.part_id);
                  const isLow = stock.quantity <= stock.reorder_point;
                  const isOut = stock.quantity === 0;
                  return (
                    <tr key={stock.id}>
                      <td>
                        <Link
                          to={`/inventory/parts/${stock.part_id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {part ? (
                            <div>
                              <p className="font-medium">{part.part_number}</p>
                              <p className="text-sm text-gray-500">{part.name}</p>
                            </div>
                          ) : (
                            `Part #${stock.part_id}`
                          )}
                        </Link>
                      </td>
                      <td>{stock.bin_location || '-'}</td>
                      <td className="text-right font-medium">{stock.quantity}</td>
                      <td className="text-right text-gray-500">{stock.min_quantity}</td>
                      <td className="text-right text-gray-500">{stock.reorder_point}</td>
                      <td className="text-right text-gray-500">{stock.max_quantity}</td>
                      <td>
                        {isOut ? (
                          <span className="badge badge-red">Out of Stock</span>
                        ) : isLow ? (
                          <span className="badge badge-yellow">Low Stock</span>
                        ) : (
                          <span className="badge badge-green">In Stock</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No stock items in this storeroom</p>
        )}
      </div>
    </div>
  );
}
