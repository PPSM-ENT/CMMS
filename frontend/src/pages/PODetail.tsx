import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  ShoppingCart,
  Building2,
  Calendar,
  Package,
  CheckCircle,
  XCircle,
  Truck,
  FileText,
} from 'lucide-react';
import { getPurchaseOrder, updatePOStatus, receivePOLines, getVendors, getParts } from '../lib/api';

const statusColors: Record<string, string> = {
  DRAFT: 'badge-gray',
  PENDING_APPROVAL: 'badge-yellow',
  APPROVED: 'badge-blue',
  ORDERED: 'badge-blue',
  PARTIALLY_RECEIVED: 'badge-yellow',
  RECEIVED: 'badge-green',
  CANCELLED: 'badge-red',
};

const statusLabels: Record<string, string> = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Approved',
  ORDERED: 'Ordered',
  PARTIALLY_RECEIVED: 'Partially Received',
  RECEIVED: 'Received',
  CANCELLED: 'Cancelled',
};

interface POLine {
  id: number;
  line_number: number;
  part_id: number;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  quantity_received: number;
  storeroom_id: number | null;
}

interface PurchaseOrder {
  id: number;
  po_number: string;
  vendor_id: number;
  status: string;
  expected_date: string | null;
  order_date: string | null;
  received_date: string | null;
  ship_to_storeroom_id: number | null;
  notes: string | null;
  subtotal: number;
  tax: number;
  shipping_cost: number;
  total: number;
  created_at: string;
  lines: POLine[];
}

export default function PODetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [receiveQuantities, setReceiveQuantities] = useState<Record<number, number>>({});

  const { data: po, isLoading, error } = useQuery({
    queryKey: ['purchase-order', id],
    queryFn: () => getPurchaseOrder(Number(id)),
    enabled: !!id,
  });

  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-list'],
    queryFn: () => getVendors({ page_size: 100 }),
  });

  const { data: partsData } = useQuery({
    queryKey: ['parts-list'],
    queryFn: () => getParts({ page_size: 500 }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status }: { status: string }) => updatePOStatus(Number(id), status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-order', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('Status updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update status');
    },
  });

  const receiveMutation = useMutation({
    mutationFn: (lines: { line_id: number; quantity_received: number }[]) =>
      receivePOLines(Number(id), lines),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-order', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['parts'] });
      toast.success('Items received successfully');
      setShowReceiveModal(false);
      setReceiveQuantities({});
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to receive items');
    },
  });

  const getVendorName = (vendorId: number) => {
    const vendor = vendorsData?.items?.find((v: { id: number }) => v.id === vendorId);
    return vendor ? `${vendor.code} - ${vendor.name}` : `Vendor #${vendorId}`;
  };

  const getPartName = (partId: number) => {
    const part = partsData?.items?.find((p: { id: number }) => p.id === partId);
    return part ? `${part.part_number} - ${part.name}` : `Part #${partId}`;
  };

  const handleReceive = () => {
    const linesToReceive = Object.entries(receiveQuantities)
      .filter(([, qty]) => qty > 0)
      .map(([lineId, qty]) => ({
        line_id: Number(lineId),
        quantity_received: qty,
      }));

    if (linesToReceive.length === 0) {
      toast.error('Please enter quantities to receive');
      return;
    }

    receiveMutation.mutate(linesToReceive);
  };

  const openReceiveModal = () => {
    const initialQuantities: Record<number, number> = {};
    po?.lines?.forEach((line: POLine) => {
      const remaining = line.quantity - line.quantity_received;
      if (remaining > 0) {
        initialQuantities[line.id] = remaining;
      }
    });
    setReceiveQuantities(initialQuantities);
    setShowReceiveModal(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !po) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Purchase order not found</p>
        <button onClick={() => navigate('/inventory')} className="btn-primary mt-4">
          Back to Inventory
        </button>
      </div>
    );
  }

  const canApprove = po.status === 'PENDING_APPROVAL';
  const canOrder = po.status === 'APPROVED';
  const canReceive = ['ORDERED', 'PARTIALLY_RECEIVED'].includes(po.status);
  const canCancel = !['RECEIVED', 'CANCELLED'].includes(po.status);

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
              <h1 className="text-2xl font-bold text-gray-900">{po.po_number}</h1>
              <span className={`badge ${statusColors[po.status] || 'badge-gray'}`}>
                {statusLabels[po.status] || po.status}
              </span>
            </div>
            <p className="text-gray-600">{getVendorName(po.vendor_id)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {canApprove && (
            <>
              <button
                onClick={() => statusMutation.mutate({ status: 'APPROVED' })}
                disabled={statusMutation.isPending}
                className="btn-success flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Approve
              </button>
              <button
                onClick={() => statusMutation.mutate({ status: 'CANCELLED' })}
                disabled={statusMutation.isPending}
                className="btn-danger flex items-center gap-2"
              >
                <XCircle className="w-4 h-4" />
                Reject
              </button>
            </>
          )}
          {canOrder && (
            <button
              onClick={() => statusMutation.mutate({ status: 'ORDERED' })}
              disabled={statusMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              <ShoppingCart className="w-4 h-4" />
              Mark as Ordered
            </button>
          )}
          {canReceive && (
            <button
              onClick={openReceiveModal}
              className="btn-success flex items-center gap-2"
            >
              <Truck className="w-4 h-4" />
              Receive Items
            </button>
          )}
          {canCancel && po.status !== 'PENDING_APPROVAL' && (
            <button
              onClick={() => statusMutation.mutate({ status: 'CANCELLED' })}
              disabled={statusMutation.isPending}
              className="btn-danger flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Order Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Order Info Card */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ShoppingCart className="w-5 h-5" />
              Order Information
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Vendor</p>
                <p className="font-medium">{getVendorName(po.vendor_id)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Expected Date</p>
                <p className="font-medium">
                  {po.expected_date
                    ? new Date(po.expected_date).toLocaleDateString()
                    : 'Not set'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Order Date</p>
                <p className="font-medium">
                  {po.order_date
                    ? new Date(po.order_date).toLocaleDateString()
                    : 'Not ordered yet'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Received Date</p>
                <p className="font-medium">
                  {po.received_date
                    ? new Date(po.received_date).toLocaleDateString()
                    : 'Not received yet'}
                </p>
              </div>
              {po.notes && (
                <div className="col-span-2">
                  <p className="text-sm text-gray-500">Notes</p>
                  <p className="font-medium">{po.notes}</p>
                </div>
              )}
            </div>
          </div>

          {/* Line Items */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Package className="w-5 h-5" />
              Line Items
            </h2>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Part</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Received</th>
                    <th className="text-right">Unit Cost</th>
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {po.lines?.map((line: POLine) => (
                    <tr key={line.id}>
                      <td>{line.line_number}</td>
                      <td>
                        <Link
                          to={`/inventory/parts/${line.part_id}`}
                          className="text-primary-600 hover:underline"
                        >
                          {getPartName(line.part_id)}
                        </Link>
                      </td>
                      <td className="text-right">{line.quantity}</td>
                      <td className="text-right">
                        <span
                          className={
                            line.quantity_received >= line.quantity
                              ? 'text-green-600'
                              : line.quantity_received > 0
                              ? 'text-yellow-600'
                              : ''
                          }
                        >
                          {line.quantity_received}
                        </span>
                      </td>
                      <td className="text-right">${line.unit_cost.toFixed(2)}</td>
                      <td className="text-right font-medium">${line.total_cost.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Summary Sidebar */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Order Summary
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Subtotal</span>
                <span className="font-medium">${po.subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tax</span>
                <span className="font-medium">${po.tax.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Shipping</span>
                <span className="font-medium">${po.shipping_cost.toFixed(2)}</span>
              </div>
              <div className="border-t pt-3 flex justify-between">
                <span className="font-semibold">Total</span>
                <span className="font-bold text-xl">${po.total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Timeline
            </h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <div>
                  <p className="text-sm font-medium">Created</p>
                  <p className="text-xs text-gray-500">
                    {new Date(po.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {po.order_date && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full" />
                  <div>
                    <p className="text-sm font-medium">Ordered</p>
                    <p className="text-xs text-gray-500">
                      {new Date(po.order_date).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
              {po.received_date && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full" />
                  <div>
                    <p className="text-sm font-medium">Received</p>
                    <p className="text-xs text-gray-500">
                      {new Date(po.received_date).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {po.ship_to_storeroom_id && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                Ship To
              </h2>
              <Link
                to={`/inventory/storerooms/${po.ship_to_storeroom_id}`}
                className="text-primary-600 hover:underline"
              >
                View Storeroom
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Receive Modal */}
      {showReceiveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Receive Items</h2>
            <div className="space-y-4">
              {po.lines
                ?.filter((line: POLine) => line.quantity - line.quantity_received > 0)
                .map((line: POLine) => {
                  const remaining = line.quantity - line.quantity_received;
                  return (
                    <div key={line.id} className="p-4 bg-gray-50 rounded-lg">
                      <p className="font-medium">{getPartName(line.part_id)}</p>
                      <p className="text-sm text-gray-500 mb-2">
                        Ordered: {line.quantity} | Received: {line.quantity_received} | Remaining:{' '}
                        {remaining}
                      </p>
                      <div className="flex items-center gap-2">
                        <label className="text-sm">Receive:</label>
                        <input
                          type="number"
                          value={receiveQuantities[line.id] || 0}
                          onChange={(e) =>
                            setReceiveQuantities((prev) => ({
                              ...prev,
                              [line.id]: Math.min(Number(e.target.value), remaining),
                            }))
                          }
                          min="0"
                          max={remaining}
                          className="input w-24"
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
            <div className="flex justify-end gap-4 mt-6">
              <button
                onClick={() => setShowReceiveModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleReceive}
                disabled={receiveMutation.isPending}
                className="btn-primary"
              >
                {receiveMutation.isPending ? 'Receiving...' : 'Confirm Receipt'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
