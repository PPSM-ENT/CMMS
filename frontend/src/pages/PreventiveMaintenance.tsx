import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Plus,
  Search,
  Calendar,
  Play,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { getPMs, generatePMWorkOrder } from '../lib/api';
import { format, isAfter, isBefore, addDays } from 'date-fns';

export default function PreventiveMaintenance() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['pms', { search, page }],
    queryFn: () => getPMs({ search, page, page_size: 20 }),
  });

  const generateMutation = useMutation({
    mutationFn: (pmId: number) => generatePMWorkOrder(pmId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pms'] });
      queryClient.invalidateQueries({ queryKey: ['work-orders'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast.success(`Work order ${data.wo_number} created`);
    },
    onError: () => toast.error('Failed to generate work order'),
  });

  const getDueStatus = (dueDate: string | null) => {
    if (!dueDate) return { label: 'No schedule', color: 'badge-gray' };
    const due = new Date(dueDate);
    const today = new Date();
    const nextWeek = addDays(today, 7);

    if (isBefore(due, today)) {
      return { label: 'Overdue', color: 'badge-red' };
    }
    if (isBefore(due, nextWeek)) {
      return { label: 'Due Soon', color: 'badge-yellow' };
    }
    return { label: 'Scheduled', color: 'badge-green' };
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Preventive Maintenance</h1>
          <p className="text-gray-600">Manage scheduled maintenance tasks</p>
        </div>
        <Link to="/pm/new" className="btn-primary flex items-center gap-2 w-fit">
          <Plus className="w-5 h-5" />
          New PM Schedule
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search PM schedules..."
              className="input pl-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* PM list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {data?.items?.map((pm: {
              id: number;
              pm_number: string;
              name: string;
              description?: string;
              is_active: boolean;
              trigger_type: string;
              frequency?: number;
              frequency_unit?: string;
              next_due_date?: string;
              asset_id?: number;
              last_wo_date?: string;
            }) => {
              const dueStatus = getDueStatus(pm.next_due_date || null);
              return (
                <div key={pm.id} className="card hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Calendar className="w-6 h-6 text-purple-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900">{pm.name}</h3>
                          <span className={`badge ${dueStatus.color}`}>
                            {dueStatus.label}
                          </span>
                          {!pm.is_active && (
                            <span className="badge badge-gray">Inactive</span>
                          )}
                        </div>
                        <p className="text-sm text-gray-500">{pm.pm_number}</p>
                        {pm.description && (
                          <p className="mt-1 text-sm text-gray-600">{pm.description}</p>
                        )}
                        <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-gray-500">
                          <span>
                            {pm.trigger_type === 'TIME' ? 'Time-based' :
                             pm.trigger_type === 'METER' ? 'Meter-based' :
                             pm.trigger_type}
                          </span>
                          {pm.frequency && pm.frequency_unit && (
                            <span>Every {pm.frequency} {pm.frequency_unit.toLowerCase()}</span>
                          )}
                          {pm.next_due_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              Due: {format(new Date(pm.next_due_date), 'MMM d, yyyy')}
                            </span>
                          )}
                          {pm.last_wo_date && (
                            <span>
                              Last completed: {format(new Date(pm.last_wo_date), 'MMM d, yyyy')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => generateMutation.mutate(pm.id)}
                        disabled={!pm.is_active || generateMutation.isPending}
                        className="btn-primary flex items-center gap-2"
                      >
                        <Play className="w-4 h-4" />
                        Generate WO
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {data?.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, data.total)} of {data.total} schedules
              </p>
              <div className="flex gap-2">
                <button
                  className="btn-secondary"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <button
                  className="btn-secondary"
                  disabled={page === data.pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {data?.items?.length === 0 && (
            <div className="card text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No PM schedules found</h3>
              <p className="text-gray-500 mt-1">Create your first preventive maintenance schedule</p>
              <Link to="/pm/new" className="btn-primary mt-4 inline-flex items-center gap-2">
                <Plus className="w-5 h-5" />
                Create PM Schedule
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
