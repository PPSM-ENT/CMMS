import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { ArrowLeft, Save, Wrench } from 'lucide-react';
import { createAsset, updateAsset, getAsset, getLocations } from '../lib/api';

interface AssetFormData {
  asset_num: string;
  name: string;
  description: string;
  location_id: number | null;
  category: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  barcode: string;
  status: string;
  criticality: string;
  purchase_date: string;
  purchase_price: number | null;
  install_date: string;
  warranty_expiry: string;
}

export default function AssetForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEditMode = !!id;

  const [formData, setFormData] = useState<AssetFormData>({
    asset_num: '',
    name: '',
    description: '',
    location_id: null,
    category: '',
    asset_type: '',
    manufacturer: '',
    model: '',
    serial_number: '',
    barcode: '',
    status: 'OPERATING',
    criticality: 'MEDIUM',
    purchase_date: '',
    purchase_price: null,
    install_date: '',
    warranty_expiry: '',
  });

  const { data: assetData, isLoading: assetLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => getAsset(Number(id)),
    enabled: isEditMode,
  });

  const { data: locationsData } = useQuery({
    queryKey: ['locations-list'],
    queryFn: () => getLocations({ page_size: 100 }),
  });

  // Populate form when editing
  useEffect(() => {
    if (assetData) {
      setFormData({
        asset_num: assetData.asset_num || '',
        name: assetData.name || '',
        description: assetData.description || '',
        location_id: assetData.location_id || null,
        category: assetData.category || '',
        asset_type: assetData.asset_type || '',
        manufacturer: assetData.manufacturer || '',
        model: assetData.model || '',
        serial_number: assetData.serial_number || '',
        barcode: assetData.barcode || '',
        status: assetData.status || 'OPERATING',
        criticality: assetData.criticality || 'MEDIUM',
        purchase_date: assetData.purchase_date || '',
        purchase_price: assetData.purchase_price || null,
        install_date: assetData.install_date || '',
        warranty_expiry: assetData.warranty_expiry || '',
      });
    }
  }, [assetData]);

  const createMutation = useMutation({
    mutationFn: createAsset,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Asset created successfully');
      navigate(`/assets/${data.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create asset');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateAsset(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', id] });
      toast.success('Asset updated successfully');
      navigate(`/assets/${id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update asset');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.asset_num.trim()) {
      toast.error('Asset number is required');
      return;
    }
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }

    const submitData: Record<string, unknown> = {
      asset_num: formData.asset_num,
      name: formData.name,
      description: formData.description || undefined,
      location_id: formData.location_id || undefined,
      category: formData.category || undefined,
      asset_type: formData.asset_type || undefined,
      manufacturer: formData.manufacturer || undefined,
      model: formData.model || undefined,
      serial_number: formData.serial_number || undefined,
      barcode: formData.barcode || undefined,
      status: formData.status,
      criticality: formData.criticality,
      purchase_date: formData.purchase_date || undefined,
      purchase_price: formData.purchase_price || undefined,
      install_date: formData.install_date || undefined,
      warranty_expiry: formData.warranty_expiry || undefined,
    };

    if (isEditMode) {
      updateMutation.mutate(submitData);
    } else {
      createMutation.mutate(submitData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (isEditMode && assetLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

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
          <h1 className="text-2xl font-bold text-gray-900">
            {isEditMode ? 'Edit Asset' : 'Add New Asset'}
          </h1>
          <p className="text-gray-600">
            {isEditMode ? 'Update asset information' : 'Register a new asset in the system'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            Basic Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Asset Number <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="asset_num"
                value={formData.asset_num}
                onChange={handleChange}
                className="input"
                placeholder="e.g., PUMP-001"
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
                placeholder="e.g., Main Cooling Pump"
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
                placeholder="Describe the asset"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
              <select name="location_id" value={formData.location_id || ''} onChange={handleChange} className="input">
                <option value="">Select a location</option>
                {locationsData?.items?.map((loc: { id: number; name: string; code: string }) => (
                  <option key={loc.id} value={loc.id}>{loc.code} - {loc.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <input type="text" name="category" value={formData.category} onChange={handleChange} className="input" placeholder="e.g., Pumps" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asset Type</label>
              <input type="text" name="asset_type" value={formData.asset_type} onChange={handleChange} className="input" placeholder="e.g., Centrifugal" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select name="status" value={formData.status} onChange={handleChange} className="input">
                <option value="OPERATING">Operating</option>
                <option value="NOT_OPERATING">Not Operating</option>
                <option value="IN_REPAIR">In Repair</option>
                <option value="STANDBY">Standby</option>
                <option value="DECOMMISSIONED">Decommissioned</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Criticality</label>
              <select name="criticality" value={formData.criticality} onChange={handleChange} className="input">
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Manufacturer Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer</label>
              <input type="text" name="manufacturer" value={formData.manufacturer} onChange={handleChange} className="input" placeholder="e.g., Grundfos" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
              <input type="text" name="model" value={formData.model} onChange={handleChange} className="input" placeholder="e.g., CR 32-4" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Serial Number</label>
              <input type="text" name="serial_number" value={formData.serial_number} onChange={handleChange} className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Barcode</label>
              <input type="text" name="barcode" value={formData.barcode} onChange={handleChange} className="input" />
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Financial & Dates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Date</label>
              <input type="date" name="purchase_date" value={formData.purchase_date} onChange={handleChange} className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Price</label>
              <input type="number" name="purchase_price" value={formData.purchase_price || ''} onChange={handleChange} className="input" step="0.01" min="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Install Date</label>
              <input type="date" name="install_date" value={formData.install_date} onChange={handleChange} className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Warranty Expiry</label>
              <input type="date" name="warranty_expiry" value={formData.warranty_expiry} onChange={handleChange} className="input" />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={isPending} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            {isPending ? (isEditMode ? 'Saving...' : 'Creating...') : (isEditMode ? 'Save Changes' : 'Create Asset')}
          </button>
        </div>
      </form>
    </div>
  );
}
