import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Save,
  Calendar,
} from 'lucide-react';
import { createPM, getAssets, getLocations, getUsers } from '../lib/api';

interface PMFormData {
  name: string;
  description: string;
  asset_id: number | null;
  location_id: number | null;
  trigger_type: string;
  schedule_type: string;
  frequency: number | null;
  frequency_unit: string;
  next_due_date: string;
  lead_time_days: number;
  warning_days: number;
  assigned_to_id: number | null;
  assigned_team: string;
  priority: string;
  estimated_hours: number | null;
  is_active: boolean;
}

export default function PMForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<PMFormData>({
    name: '',
    description: '',
    asset_id: null,
    location_id: null,
    trigger_type: 'TIME',
    schedule_type: 'FIXED',
    frequency: 30,
    frequency_unit: 'DAYS',
    next_due_date: '',
    lead_time_days: 7,
    warning_days: 3,
    assigned_to_id: null,
    assigned_team: '',
    priority: 'MEDIUM',
    estimated_hours: null,
    is_active: true,
  });

  // Fetch assets for dropdown
  const { data: assetsData } = useQuery({
    queryKey: ['assets-list'],
    queryFn: () => getAssets({ page_size: 100 }),
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

  const createMutation = useMutation({
    mutationFn: createPM,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pms'] });
      toast.success('PM schedule created successfully');
      navigate('/pm');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create PM schedule');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }

    if (!formData.frequency || formData.frequency <= 0) {
      toast.error('Frequency must be greater than 0');
      return;
    }

    const submitData: Record<string, unknown> = {
      name: formData.name,
      description: formData.description || undefined,
      asset_id: formData.asset_id || undefined,
      location_id: formData.location_id || undefined,
      trigger_type: formData.trigger_type,
      schedule_type: formData.schedule_type,
      frequency: formData.frequency,
      frequency_unit: formData.frequency_unit,
      next_due_date: formData.next_due_date || undefined,
      lead_time_days: formData.lead_time_days,
      warning_days: formData.warning_days,
      assigned_to_id: formData.assigned_to_id || undefined,
      assigned_team: formData.assigned_team || undefined,
      priority: formData.priority,
      estimated_hours: formData.estimated_hours || undefined,
      is_active: formData.is_active,
    };

    createMutation.mutate(submitData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;

    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({
        ...prev,
        [name]: checked,
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value === '' ? null : value,
      }));
    }
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
          <h1 className="text-2xl font-bold text-gray-900">Create PM Schedule</h1>
          <p className="text-gray-600">Set up a new preventive maintenance schedule</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Basic Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Name */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="input"
                placeholder="e.g., Monthly Equipment Inspection"
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
                placeholder="Describe the maintenance task"
              />
            </div>

            {/* Asset */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Asset
              </label>
              <select
                name="asset_id"
                value={formData.asset_id || ''}
                onChange={handleChange}
                className="input"
              >
                <option value="">Select an asset</option>
                {assetsData?.items?.map((asset: { id: number; name: string; asset_num: string }) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.asset_num} - {asset.name}
                  </option>
                ))}
              </select>
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

            {/* Active Status */}
            <div className="flex items-center">
              <input
                type="checkbox"
                name="is_active"
                checked={formData.is_active}
                onChange={handleChange}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label className="ml-2 text-sm font-medium text-gray-700">
                Active
              </label>
            </div>
          </div>
        </div>

        {/* Schedule Configuration */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Schedule Configuration</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Trigger Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Trigger Type
              </label>
              <select
                name="trigger_type"
                value={formData.trigger_type}
                onChange={handleChange}
                className="input"
              >
                <option value="TIME">Time-based</option>
                <option value="METER">Meter-based</option>
                <option value="CONDITION">Condition-based</option>
                <option value="TIME_OR_METER">Time or Meter (first trigger)</option>
                <option value="TIME_AND_METER">Time and Meter (both must be met)</option>
              </select>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Schedule Type
              </label>
              <select
                name="schedule_type"
                value={formData.schedule_type}
                onChange={handleChange}
                className="input"
              >
                <option value="FIXED">Fixed (from scheduled date)</option>
                <option value="FLOATING">Floating (from completion date)</option>
              </select>
            </div>

            {/* Frequency */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Frequency <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="frequency"
                value={formData.frequency || ''}
                onChange={handleChange}
                className="input"
                min="1"
                required
              />
            </div>

            {/* Frequency Unit */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Frequency Unit
              </label>
              <select
                name="frequency_unit"
                value={formData.frequency_unit}
                onChange={handleChange}
                className="input"
              >
                <option value="DAYS">Days</option>
                <option value="WEEKS">Weeks</option>
                <option value="MONTHS">Months</option>
                <option value="YEARS">Years</option>
              </select>
            </div>

            {/* Next Due Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Next Due Date
              </label>
              <input
                type="date"
                name="next_due_date"
                value={formData.next_due_date}
                onChange={handleChange}
                className="input"
              />
            </div>

            {/* Lead Time Days */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Lead Time (days)
              </label>
              <input
                type="number"
                name="lead_time_days"
                value={formData.lead_time_days}
                onChange={handleChange}
                className="input"
                min="0"
              />
              <p className="text-xs text-gray-500 mt-1">Days before due to generate work order</p>
            </div>

            {/* Warning Days */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Warning (days)
              </label>
              <input
                type="number"
                name="warning_days"
                value={formData.warning_days}
                onChange={handleChange}
                className="input"
                min="0"
              />
              <p className="text-xs text-gray-500 mt-1">Days before due to show warning</p>
            </div>
          </div>
        </div>

        {/* Assignment & Priority */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Assignment & Priority</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                {usersData?.items?.map((user: { id: number; first_name: string; last_name: string }) => (
                  <option key={user.id} value={user.id}>
                    {user.first_name} {user.last_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Assigned Team */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assigned Team
              </label>
              <input
                type="text"
                name="assigned_team"
                value={formData.assigned_team}
                onChange={handleChange}
                className="input"
                placeholder="e.g., Maintenance Team A"
              />
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
            disabled={createMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {createMutation.isPending ? 'Creating...' : 'Create PM Schedule'}
          </button>
        </div>
      </form>
    </div>
  );
}
