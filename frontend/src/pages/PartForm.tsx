import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { ArrowLeft, Save, Package } from 'lucide-react';
import { createPart, getVendors } from '../lib/api';

interface PartFormData {
  part_number: string;
  name: string;
  description: string;
  category_id: number | null;
  uom: string;
  unit_cost: number | null;
  primary_vendor_id: number | null;
  manufacturer: string;
  manufacturer_part_number: string;
  min_quantity: number | null;
  max_quantity: number | null;
  reorder_point: number | null;
  reorder_quantity: number | null;
}

export default function PartForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<PartFormData>({
    part_number: '',
    name: '',
    description: '',
    category_id: null,
    uom: 'EA',
    unit_cost: null,
    primary_vendor_id: null,
    manufacturer: '',
    manufacturer_part_number: '',
    min_quantity: null,
    max_quantity: null,
    reorder_point: null,
    reorder_quantity: null,
  });

  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-list'],
    queryFn: () => getVendors({ page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: createPart,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['parts'] });
      toast.success('Part created successfully');
      navigate(`/inventory/parts/${data.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create part');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.part_number.trim()) {
      toast.error('Part number is required');
      return;
    }
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }

    const submitData: Record<string, unknown> = {
      part_number: formData.part_number,
      name: formData.name,
      description: formData.description || undefined,
      category_id: formData.category_id || undefined,
      uom: formData.uom,
      unit_cost: formData.unit_cost || 0,
      average_cost: formData.unit_cost || 0,
      last_cost: formData.unit_cost || 0,
      primary_vendor_id: formData.primary_vendor_id || undefined,
      manufacturer: formData.manufacturer || undefined,
      manufacturer_part_number: formData.manufacturer_part_number || undefined,
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Add New Part</h1>
          <p className="text-gray-600">Register a new part in the inventory</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Package className="w-5 h-5" />
            Basic Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Part Number <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="part_number"
                value={formData.part_number}
                onChange={handleChange}
                className="input"
                placeholder="e.g., BRG-6205"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="input"
                placeholder="e.g., Ball Bearing 6205"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                className="input"
                rows={3}
                placeholder="Describe the part"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Unit of Measure</label>
              <select name="uom" value={formData.uom} onChange={handleChange} className="input">
                <option value="EA">Each (EA)</option>
                <option value="BOX">Box</option>
                <option value="CASE">Case</option>
                <option value="FT">Feet (FT)</option>
                <option value="GAL">Gallon (GAL)</option>
                <option value="KG">Kilogram (KG)</option>
                <option value="L">Liter (L)</option>
                <option value="M">Meter (M)</option>
                <option value="PACK">Pack</option>
                <option value="ROLL">Roll</option>
                <option value="SET">Set</option>
                <option value="TUBE">Tube</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Unit Cost</label>
              <input
                type="number"
                name="unit_cost"
                value={formData.unit_cost || ''}
                onChange={handleChange}
                className="input"
                step="0.01"
                min="0"
                placeholder="0.00"
              />
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Vendor & Manufacturer</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Primary Vendor</label>
              <select name="primary_vendor_id" value={formData.primary_vendor_id || ''} onChange={handleChange} className="input">
                <option value="">Select a vendor</option>
                {vendorsData?.items?.map((vendor: { id: number; name: string; code: string }) => (
                  <option key={vendor.id} value={vendor.id}>{vendor.code} - {vendor.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer</label>
              <input type="text" name="manufacturer" value={formData.manufacturer} onChange={handleChange} className="input" placeholder="e.g., SKF" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer Part Number</label>
              <input type="text" name="manufacturer_part_number" value={formData.manufacturer_part_number} onChange={handleChange} className="input" />
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Stock Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reorder Point</label>
              <input type="number" name="reorder_point" value={formData.reorder_point || ''} onChange={handleChange} className="input" min="0" placeholder="Minimum stock before reorder" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reorder Quantity</label>
              <input type="number" name="reorder_quantity" value={formData.reorder_quantity || ''} onChange={handleChange} className="input" min="0" placeholder="Quantity to order" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Quantity</label>
              <input type="number" name="min_quantity" value={formData.min_quantity || ''} onChange={handleChange} className="input" min="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Quantity</label>
              <input type="number" name="max_quantity" value={formData.max_quantity || ''} onChange={handleChange} className="input" min="0" />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={createMutation.isPending} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            {createMutation.isPending ? 'Creating...' : 'Create Part'}
          </button>
        </div>
      </form>
    </div>
  );
}
