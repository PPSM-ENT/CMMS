import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Package, DollarSign, Warehouse, TrendingUp } from 'lucide-react';
import { getPart } from '../lib/api';

export default function PartDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: part, isLoading } = useQuery({
    queryKey: ['part', id],
    queryFn: () => getPart(Number(id)),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!part) {
    return (
      <div className="text-center py-12">
        <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Part not found</h3>
        <Link to="/inventory" className="text-primary-600 hover:underline mt-2 inline-block">
          Return to Inventory
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link to="/inventory" className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{part.name}</h1>
            <p className="text-gray-600">{part.part_number}</p>
          </div>
        </div>
        <span className={`badge ${part.status === 'ACTIVE' ? 'badge-green' : 'badge-gray'}`}>
          {part.status}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Package className="w-5 h-5" />
              Part Details
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Description</p>
                <p className="font-medium">{part.description || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="font-medium">{part.category?.name || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Unit of Measure</p>
                <p className="font-medium">{part.uom}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Manufacturer</p>
                <p className="font-medium">{part.manufacturer || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Manufacturer Part #</p>
                <p className="font-medium">{part.manufacturer_part_number || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Primary Vendor</p>
                <p className="font-medium">{part.primary_vendor?.name || '-'}</p>
              </div>
            </div>
          </div>

          {part.stock_levels?.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Warehouse className="w-5 h-5" />
                Stock Levels
              </h2>
              <div className="overflow-x-auto">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Storeroom</th>
                      <th>On Hand</th>
                      <th>Available</th>
                      <th>Reorder Point</th>
                      <th>Bin Location</th>
                    </tr>
                  </thead>
                  <tbody>
                    {part.stock_levels.map((stock: {
                      id: number;
                      storeroom_id: number;
                      current_balance: number;
                      available_quantity: number;
                      reorder_point: number;
                      bin_location: string;
                    }) => (
                      <tr key={stock.id}>
                        <td>Storeroom {stock.storeroom_id}</td>
                        <td>{stock.current_balance}</td>
                        <td>{stock.available_quantity}</td>
                        <td>{stock.reorder_point || '-'}</td>
                        <td>{stock.bin_location || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Pricing
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Unit Cost</span>
                <span className="font-medium">${part.unit_cost?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Average Cost</span>
                <span className="font-medium">${part.average_cost?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Last Cost</span>
                <span className="font-medium">${part.last_cost?.toFixed(2) || '0.00'}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Stock Settings
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Min Quantity</span>
                <span>{part.min_quantity || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Max Quantity</span>
                <span>{part.max_quantity || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Reorder Point</span>
                <span>{part.reorder_point || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Reorder Qty</span>
                <span>{part.reorder_quantity || '-'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
