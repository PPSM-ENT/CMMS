import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Wrench,
  MapPin,
  Calendar,
  DollarSign,
  Gauge,
  FileText,
  History,
} from 'lucide-react';
import { getAsset } from '../lib/api';

export default function AssetDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => getAsset(Number(id)),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!asset) {
    return <div>Asset not found</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link to="/assets" className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{asset.name}</h1>
            <p className="text-gray-600">{asset.asset_num}</p>
          </div>
        </div>
        <Link to={`/assets/${id}/edit`} className="btn-primary flex items-center gap-2">
          <Edit className="w-4 h-4" />
          Edit
        </Link>
      </div>

      {/* Status badges */}
      <div className="flex gap-2">
        <span className={`badge ${
          asset.status === 'OPERATING' ? 'badge-green' :
          asset.status === 'NOT_OPERATING' ? 'badge-red' :
          'badge-gray'
        }`}>
          {asset.status.replace(/_/g, ' ')}
        </span>
        <span className={`badge ${
          asset.criticality === 'CRITICAL' ? 'badge-red' :
          asset.criticality === 'HIGH' ? 'badge-yellow' :
          'badge-blue'
        }`}>
          {asset.criticality} Criticality
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Details card */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Asset Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Description</p>
                <p className="font-medium">{asset.description || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="font-medium">{asset.category || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Manufacturer</p>
                <p className="font-medium">{asset.manufacturer || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Model</p>
                <p className="font-medium">{asset.model || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Serial Number</p>
                <p className="font-medium">{asset.serial_number || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Barcode</p>
                <p className="font-medium">{asset.barcode || '-'}</p>
              </div>
            </div>
          </div>

          {/* Meters */}
          {asset.meters?.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Gauge className="w-5 h-5" />
                Meters
              </h2>
              <div className="space-y-3">
                {asset.meters.map((meter: {
                  id: number;
                  name: string;
                  code: string;
                  last_reading?: number;
                  unit_of_measure: string;
                  last_reading_date?: string;
                }) => (
                  <div key={meter.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium">{meter.name}</p>
                      <p className="text-sm text-gray-500">{meter.code}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-lg">
                        {meter.last_reading?.toLocaleString() || '0'} {meter.unit_of_measure}
                      </p>
                      {meter.last_reading_date && (
                        <p className="text-xs text-gray-500">
                          Last updated: {new Date(meter.last_reading_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Specifications */}
          {asset.specifications?.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Specifications
              </h2>
              <div className="space-y-2">
                {asset.specifications.map((spec: {
                  id: number;
                  attribute_name: string;
                  attribute_value?: string;
                  unit_of_measure?: string;
                }) => (
                  <div key={spec.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <span className="text-gray-600">{spec.attribute_name}</span>
                    <span className="font-medium">
                      {spec.attribute_value}
                      {spec.unit_of_measure && ` ${spec.unit_of_measure}`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Location */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Location
            </h3>
            <p className="text-gray-600">{asset.location_id || 'Not assigned'}</p>
          </div>

          {/* Dates */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Important Dates
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Purchase Date</span>
                <span>{asset.purchase_date || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Install Date</span>
                <span>{asset.install_date || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Warranty Expires</span>
                <span>{asset.warranty_expiry || '-'}</span>
              </div>
            </div>
          </div>

          {/* Financial */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Financial
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Purchase Price</span>
                <span>${asset.purchase_price?.toLocaleString() || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Residual Value</span>
                <span>${asset.residual_value?.toLocaleString() || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Useful Life</span>
                <span>{asset.useful_life_years ? `${asset.useful_life_years} years` : '-'}</span>
              </div>
            </div>
          </div>

          {/* Quick actions */}
          <div className="card">
            <h3 className="font-semibold mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                to={`/work-orders/new?asset_id=${asset.id}`}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Wrench className="w-4 h-4" />
                Create Work Order
              </Link>
              <Link
                to={`/work-orders?asset_id=${asset.id}`}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                <History className="w-4 h-4" />
                View Work Order History
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
