import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { ArrowLeft, Save, ShoppingCart, Plus, Trash2 } from 'lucide-react';
import { createPurchaseOrder, getVendors, getParts, getStorerooms } from '../lib/api';

interface POLineItem {
  part_id: number | null;
  quantity: number;
  unit_cost: number;
  storeroom_id: number | null;
}

interface POFormData {
  vendor_id: number | null;
  ship_to_storeroom_id: number | null;
  expected_date: string;
  notes: string;
  lines: POLineItem[];
}

export default function PurchaseOrderForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<POFormData>({
    vendor_id: null,
    ship_to_storeroom_id: null,
    expected_date: '',
    notes: '',
    lines: [{ part_id: null, quantity: 1, unit_cost: 0, storeroom_id: null }],
  });

  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-list'],
    queryFn: () => getVendors({ page_size: 100 }),
  });

  const { data: partsData } = useQuery({
    queryKey: ['parts-list'],
    queryFn: () => getParts({ page_size: 500 }),
  });

  const { data: storeroomsData } = useQuery({
    queryKey: ['storerooms-list'],
    queryFn: getStorerooms,
  });

  const createMutation = useMutation({
    mutationFn: createPurchaseOrder,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      toast.success('Purchase order created successfully');
      navigate(`/inventory/po/${data.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create purchase order');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.vendor_id) {
      toast.error('Vendor is required');
      return;
    }

    const validLines = formData.lines.filter(line => line.part_id && line.quantity > 0);
    if (validLines.length === 0) {
      toast.error('At least one line item is required');
      return;
    }

    const submitData: Record<string, unknown> = {
      vendor_id: formData.vendor_id,
      ship_to_storeroom_id: formData.ship_to_storeroom_id || undefined,
      expected_date: formData.expected_date || undefined,
      notes: formData.notes || undefined,
      lines: validLines.map((line, index) => ({
        line_number: index + 1,
        part_id: line.part_id,
        quantity: line.quantity,
        unit_cost: line.unit_cost,
        storeroom_id: line.storeroom_id || formData.ship_to_storeroom_id || undefined,
      })),
    };

    createMutation.mutate(submitData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value === '' ? null : value,
    }));
  };

  const handleLineChange = (index: number, field: keyof POLineItem, value: string | number | null) => {
    setFormData(prev => ({
      ...prev,
      lines: prev.lines.map((line, i) =>
        i === index ? { ...line, [field]: value } : line
      ),
    }));
  };

  const addLine = () => {
    setFormData(prev => ({
      ...prev,
      lines: [...prev.lines, { part_id: null, quantity: 1, unit_cost: 0, storeroom_id: null }],
    }));
  };

  const removeLine = (index: number) => {
    if (formData.lines.length > 1) {
      setFormData(prev => ({
        ...prev,
        lines: prev.lines.filter((_, i) => i !== index),
      }));
    }
  };

  const calculateTotal = () => {
    return formData.lines.reduce((total, line) => total + (line.quantity * line.unit_cost), 0);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create Purchase Order</h1>
          <p className="text-gray-600">Order parts from a vendor</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" />
            Order Details
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Vendor <span className="text-red-500">*</span>
              </label>
              <select name="vendor_id" value={formData.vendor_id || ''} onChange={handleChange} className="input" required>
                <option value="">Select a vendor</option>
                {vendorsData?.items?.map((vendor: { id: number; name: string; code: string }) => (
                  <option key={vendor.id} value={vendor.id}>{vendor.code} - {vendor.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ship To Storeroom</label>
              <select name="ship_to_storeroom_id" value={formData.ship_to_storeroom_id || ''} onChange={handleChange} className="input">
                <option value="">Select a storeroom</option>
                {storeroomsData?.map((storeroom: { id: number; name: string; code: string }) => (
                  <option key={storeroom.id} value={storeroom.id}>{storeroom.code} - {storeroom.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Expected Date</label>
              <input type="date" name="expected_date" value={formData.expected_date} onChange={handleChange} className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <input type="text" name="notes" value={formData.notes} onChange={handleChange} className="input" placeholder="Optional notes" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Line Items</h2>
            <button type="button" onClick={addLine} className="btn-secondary flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Add Line
            </button>
          </div>
          <div className="space-y-4">
            {formData.lines.map((line, index) => (
              <div key={index} className="grid grid-cols-12 gap-4 items-end p-4 bg-gray-50 rounded-lg">
                <div className="col-span-5">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Part</label>
                  <select
                    value={line.part_id || ''}
                    onChange={(e) => {
                      const partId = e.target.value ? Number(e.target.value) : null;
                      handleLineChange(index, 'part_id', partId);
                      const selectedPart = partsData?.items?.find((p: { id: number }) => p.id === partId);
                      if (selectedPart) {
                        handleLineChange(index, 'unit_cost', selectedPart.unit_cost || 0);
                      }
                    }}
                    className="input"
                  >
                    <option value="">Select a part</option>
                    {partsData?.items?.map((part: { id: number; name: string; part_number: string }) => (
                      <option key={part.id} value={part.id}>{part.part_number} - {part.name}</option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                  <input
                    type="number"
                    value={line.quantity}
                    onChange={(e) => handleLineChange(index, 'quantity', Number(e.target.value))}
                    className="input"
                    min="1"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Unit Cost</label>
                  <input
                    type="number"
                    value={line.unit_cost}
                    onChange={(e) => handleLineChange(index, 'unit_cost', Number(e.target.value))}
                    className="input"
                    step="0.01"
                    min="0"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Line Total</label>
                  <p className="py-2 font-medium">${(line.quantity * line.unit_cost).toFixed(2)}</p>
                </div>
                <div className="col-span-1">
                  <button
                    type="button"
                    onClick={() => removeLine(index)}
                    disabled={formData.lines.length === 1}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t flex justify-end">
            <div className="text-right">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">${calculateTotal().toFixed(2)}</p>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={createMutation.isPending} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            {createMutation.isPending ? 'Creating...' : 'Create Purchase Order'}
          </button>
        </div>
      </form>
    </div>
  );
}
