import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Save,
  Wrench,
} from 'lucide-react';
import { createWorkOrder, updateWorkOrder, getWorkOrder, getAssets, getAsset, getLocations, getUsers, getUserGroups } from '../lib/api';

interface WorkOrderFormData {
  title: string;
  description: string;
  work_type: string;
  priority: string;
  asset_id: number | null; // Primary asset
  asset_ids: number[]; // Additional assets for multi-asset work orders
  location_id: number | null;
  assigned_to_id: number | null;
  assigned_group_id: number | null;
  due_date: string;
  estimated_hours: number | null;
}

export default function WorkOrderForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const isEditMode = !!id;

  const preselectedAssetId = searchParams.get('asset_id');

  const [formData, setFormData] = useState<WorkOrderFormData>({
    title: '',
    description: '',
    work_type: 'CORRECTIVE',
    priority: 'MEDIUM',
    asset_id: preselectedAssetId ? Number(preselectedAssetId) : null,
    asset_ids: [],
    location_id: null,
    assigned_to_id: null,
    assigned_group_id: null,
    due_date: '',
    estimated_hours: null,
  });

  // Fetch work order data if editing
  const { data: workOrderData, isLoading: workOrderLoading } = useQuery({
    queryKey: ['work-order', id],
    queryFn: () => getWorkOrder(Number(id)),
    enabled: isEditMode,
  });

  // Fetch assets for dropdown
  const { data: assetsData } = useQuery({
    queryKey: ['assets-list'],
    queryFn: () => getAssets({ page_size: 100 }),
  });

  // Fetch preselected asset details
  const { data: preselectedAsset } = useQuery({
    queryKey: ['asset', preselectedAssetId],
    queryFn: () => getAsset(Number(preselectedAssetId)),
    enabled: !!preselectedAssetId && !isEditMode,
  });

  // Fetch locations for dropdown
  const { data: locationsData } = useQuery({
    queryKey: ['locations-list'],
    queryFn: () => getLocations({ page_size: 100 }),
  });

  // Fetch users for assignment dropdown
  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
  });

  // Fetch user groups for assignment dropdown (only active groups)
  const { data: userGroupsData } = useQuery({
    queryKey: ['user-groups', { page_size: 100 }],
    queryFn: () => getUserGroups({ page_size: 100 }),
  });

  // Populate form when editing
  useEffect(() => {
    if (workOrderData) {
      setFormData({
        title: workOrderData.title || '',
        description: workOrderData.description || '',
        work_type: workOrderData.work_type || 'CORRECTIVE',
        priority: workOrderData.priority || 'MEDIUM',
        asset_id: workOrderData.asset_id || null,
        asset_ids: workOrderData.multi_assets?.map((a: any) => a.asset_id) || [],
        location_id: workOrderData.location_id || null,
        assigned_to_id: workOrderData.assigned_to_id || null,
        assigned_group_id: workOrderData.assigned_group_id || null,
        due_date: workOrderData.due_date ? workOrderData.due_date.split('T')[0] : '',
        estimated_hours: workOrderData.estimated_hours || null,
      });
    }
  }, [workOrderData]);

  // Update title when asset is preselected (create mode only)
  useEffect(() => {
    if (preselectedAsset && !formData.title && !isEditMode) {
      setFormData(prev => ({
        ...prev,
        title: `Work Order for ${preselectedAsset.name}`,
        location_id: preselectedAsset.location_id || null,
      }));
    }
  }, [preselectedAsset, isEditMode]);

  const createMutation = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['work-orders'] });
      toast.success('Work order created successfully');
      navigate(`/work-orders/${data.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create work order');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateWorkOrder(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-orders'] });
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      toast.success('Work order updated successfully');
      navigate(`/work-orders/${id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update work order');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title.trim()) {
      toast.error('Title is required');
      return;
    }

    const submitData = {
      title: formData.title,
      description: formData.description || undefined,
      work_type: formData.work_type,
      priority: formData.priority,
      asset_id: formData.asset_id || undefined,
      asset_ids: formData.asset_ids.length > 0 ? formData.asset_ids : undefined,
      location_id: formData.location_id || undefined,
      assigned_to_id: formData.assigned_to_id || undefined,
      assigned_group_id: formData.assigned_group_id || undefined,
      due_date: formData.due_date || undefined,
      estimated_hours: formData.estimated_hours || undefined,
    };

    if (isEditMode) {
      updateMutation.mutate(submitData);
    } else {
      createMutation.mutate(submitData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (isEditMode && workOrderLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    // Fields that should be converted to numbers
    const numericFields = ['asset_id', 'location_id', 'assigned_to_id', 'assigned_group_id', 'estimated_hours'];

    let processedValue: string | number | null = value;
    if (value === '') {
      processedValue = null;
    } else if (numericFields.includes(name)) {
      processedValue = Number(value);
    }

    setFormData(prev => ({
      ...prev,
      [name]: processedValue,
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEditMode ? 'Edit Work Order' : 'Create Work Order'}
          </h1>
          <p className="text-gray-600">
            {isEditMode ? 'Update work order details' : 'Fill in the details to create a new work order'}
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            Work Order Details
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Title */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                className="input"
                placeholder="Enter work order title"
                required
              />
            </div>

            {/* Description */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                className="input"
                rows={3}
                placeholder="Describe the work to be done"
              />
            </div>

            {/* Work Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Work Type
              </label>
              <select
                name="work_type"
                value={formData.work_type}
                onChange={handleChange}
                className="input"
              >
                <option value="CORRECTIVE">Corrective</option>
                <option value="PREVENTIVE">Preventive</option>
                <option value="PREDICTIVE">Predictive</option>
                <option value="EMERGENCY">Emergency</option>
                <option value="PROJECT">Project</option>
                <option value="INSPECTION">Inspection</option>
                <option value="CALIBRATION">Calibration</option>
              </select>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="input"
              >
                <option value="EMERGENCY">Emergency (P1)</option>
                <option value="HIGH">High (P2)</option>
                <option value="MEDIUM">Medium (P3)</option>
                <option value="LOW">Low (P4)</option>
                <option value="SCHEDULED">Scheduled (P5)</option>
              </select>
            </div>

            {/* Primary Asset */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Primary Asset
              </label>
              <select
                name="asset_id"
                value={formData.asset_id || ''}
                onChange={handleChange}
                className="input"
              >
                <option value="">Select a primary asset</option>
                {assetsData?.items?.map((asset: { id: number; name: string; asset_num: string }) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.asset_num} - {asset.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Additional Assets */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Additional Assets
              </label>
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {formData.asset_ids.map((assetId) => {
                    const asset = assetsData?.items?.find((a: { id: number }) => a.id === assetId);
                    return (
                      <div key={assetId} className="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-full text-sm">
                        <span>{asset?.asset_num} - {asset?.name}</span>
                        <button
                          type="button"
                          onClick={() => setFormData(prev => ({
                            ...prev,
                            asset_ids: prev.asset_ids.filter(id => id !== assetId)
                          }))}
                          className="text-gray-500 hover:text-gray-700"
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
                <select
                  className="input"
                  value=""
                  onChange={(e) => {
                    const value = Number(e.target.value);
                    if (value && !formData.asset_ids.includes(value)) {
                      setFormData(prev => ({
                        ...prev,
                        asset_ids: [...prev.asset_ids, value]
                      }));
                    }
                    e.target.value = '';
                  }}
                >
                  <option value="">Add additional asset</option>
                  {assetsData?.items
                    ?.filter((asset: { id: number }) => 
                      asset.id !== formData.asset_id && 
                      !formData.asset_ids.includes(asset.id)
                    )
                    .map((asset: { id: number; name: string; asset_num: string }) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.asset_num} - {asset.name}
                      </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Select additional assets that will be affected by this work order
              </p>
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <select
                name="location_id"
                value={formData.location_id || ''}
                onChange={handleChange}
                className="input"
              >
                <option value="">Select a location</option>
                {locationsData?.items?.map((location: { id: number; name: string; code: string }) => (
                  <option key={location.id} value={location.id}>
                    {location.code} - {location.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Assigned To */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assigned To
              </label>
              <select
                name="assigned_to_id"
                value={formData.assigned_to_id || ''}
                onChange={handleChange}
                className="input"
              >
                <option value="">Select a user</option>
                {usersData?.items?.map((user: { id: number; first_name: string; last_name: string; email: string }) => (
                  <option key={user.id} value={user.id}>
                    {user.first_name} {user.last_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Assigned Group */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assigned Group
              </label>
              <select
                name="assigned_group_id"
                value={formData.assigned_group_id || ''}
                onChange={handleChange}
                className="input"
              >
                <option value="">Select a group</option>
                {userGroupsData?.items?.map((group: { id: number; name: string; is_active: boolean }) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Due Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Due Date
              </label>
              <input
                type="date"
                name="due_date"
                value={formData.due_date}
                onChange={handleChange}
                className="input"
              />
            </div>

            {/* Estimated Hours */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estimated Hours
              </label>
              <input
                type="number"
                name="estimated_hours"
                value={formData.estimated_hours || ''}
                onChange={handleChange}
                className="input"
                step="0.5"
                min="0"
                placeholder="0.0"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending}
            className="btn-primary flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {isPending ? (isEditMode ? 'Saving...' : 'Creating...') : (isEditMode ? 'Save Changes' : 'Create Work Order')}
          </button>
        </div>
      </form>
    </div>
  );
}
