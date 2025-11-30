import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Edit,
  Clock,
  User,
  Wrench,
  CheckCircle,
  PlayCircle,
  PauseCircle,
  MessageSquare,
  Send,
  Plus,
  Package,
  DollarSign,
  ClipboardList,
  X,
  Check,
  Trash2,
  AlertTriangle,
  MapPin,
  ExternalLink,
} from 'lucide-react';
import {
  getWorkOrder,
  updateWorkOrderStatus,
  addComment,
  addLaborTransaction,
  addMaterialTransaction,
  updateWorkOrderTask,
  getUsers,
  getParts,
  getStorerooms,
  deleteWorkOrder,
  getUserGroups,
  getAsset,
  StatusUpdateData,
} from '../lib/api';
import { useAuthStore } from '../stores/authStore';
import { format } from 'date-fns';

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  WAITING_APPROVAL: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-blue-100 text-blue-800',
  SCHEDULED: 'bg-blue-100 text-blue-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  ON_HOLD: 'bg-red-100 text-red-800',
  COMPLETED: 'bg-green-100 text-green-800',
  CLOSED: 'bg-gray-100 text-gray-800',
  CANCELLED: 'bg-gray-100 text-gray-800',
};

const priorityColors: Record<string, string> = {
  EMERGENCY: 'badge-red',
  HIGH: 'badge-yellow',
  MEDIUM: 'badge-blue',
  LOW: 'badge-gray',
  SCHEDULED: 'badge-gray',
};

const statusActions: Record<string, { label: string; next: string; icon: React.ReactNode; color: string }[]> = {
  DRAFT: [
    { label: 'Submit for Approval', next: 'WAITING_APPROVAL', icon: <Send className="w-4 h-4" />, color: 'btn-primary' },
  ],
  WAITING_APPROVAL: [
    { label: 'Approve', next: 'APPROVED', icon: <CheckCircle className="w-4 h-4" />, color: 'btn-success' },
  ],
  APPROVED: [
    { label: 'Start Work', next: 'IN_PROGRESS', icon: <PlayCircle className="w-4 h-4" />, color: 'btn-primary' },
  ],
  SCHEDULED: [
    { label: 'Start Work', next: 'IN_PROGRESS', icon: <PlayCircle className="w-4 h-4" />, color: 'btn-primary' },
  ],
  IN_PROGRESS: [
    { label: 'Put On Hold', next: 'ON_HOLD', icon: <PauseCircle className="w-4 h-4" />, color: 'btn-secondary' },
    { label: 'Complete', next: 'COMPLETED', icon: <CheckCircle className="w-4 h-4" />, color: 'btn-success' },
  ],
  ON_HOLD: [
    { label: 'Resume', next: 'IN_PROGRESS', icon: <PlayCircle className="w-4 h-4" />, color: 'btn-primary' },
  ],
  COMPLETED: [
    { label: 'Close', next: 'CLOSED', icon: <CheckCircle className="w-4 h-4" />, color: 'btn-success' },
  ],
};

interface Task {
  id: number;
  sequence: number;
  description: string;
  instructions?: string;
  is_completed: boolean;
  completed_at?: string;
  estimated_hours?: number;
}

interface LaborTransaction {
  id: number;
  user_id: number;
  hours: number;
  labor_type: string;
  hourly_rate: number;
  total_cost: number;
  craft?: string;
  notes?: string;
  start_time?: string;
  end_time?: string;
  created_at: string;
}

interface MaterialTransaction {
  id: number;
  part_id: number;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  transaction_type: string;
  storeroom_id?: number;
  notes?: string;
  created_at: string;
}

interface Comment {
  id: number;
  comment: string;
  user_id: number;
  created_at: string;
}

export default function WorkOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((state) => state.user);
  const isAdmin = currentUser?.is_superuser || currentUser?.role === 'admin';

  // Form state
  const [newComment, setNewComment] = useState('');
  const [activeTab, setActiveTab] = useState<'details' | 'labor' | 'materials' | 'tasks'>('details');
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Modal state
  const [showLaborModal, setShowLaborModal] = useState(false);
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);

  // Completion form
  const [completionForm, setCompletionForm] = useState({
    completion_notes: '',
    failure_code: '',
    failure_cause: '',
    failure_remedy: '',
    downtime_hours: '',
    asset_was_down: false,
  });

  // Labor form - user selection for admins, rate/craft come from user profile on backend
  const [laborForm, setLaborForm] = useState({
    user_id: '',
    hours: '',
    labor_type: 'REGULAR',
    notes: '',
  });

  // Material form
  const [materialForm, setMaterialForm] = useState({
    part_id: '',
    quantity: '1',
    unit_cost: '',
    storeroom_id: '',
    transaction_type: 'ISSUE',
    notes: '',
  });

  // Queries
  const { data: workOrder, isLoading } = useQuery({
    queryKey: ['work-order', id],
    queryFn: () => getWorkOrder(Number(id)),
    enabled: !!id,
  });

  const { data: asset } = useQuery({
    queryKey: ['asset', workOrder?.asset_id],
    queryFn: () => getAsset(workOrder!.asset_id!),
    enabled: !!workOrder?.asset_id,
  });

  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
  });

  const { data: partsData } = useQuery({
    queryKey: ['parts-list'],
    queryFn: () => getParts({ page_size: 500 }),
  });

  const { data: storeroomsData } = useQuery({
    queryKey: ['storerooms-list'],
    queryFn: getStorerooms,
  });

  const { data: userGroupsData } = useQuery({
    queryKey: ['user-groups-list'],
    queryFn: () => getUserGroups(),
  });

  // Mutations
  const statusMutation = useMutation({
    mutationFn: (data: StatusUpdateData) =>
      updateWorkOrderStatus(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      queryClient.invalidateQueries({ queryKey: ['work-orders'] });
      toast.success('Status updated');
      setShowCompletionModal(false);
    },
    onError: () => toast.error('Failed to update status'),
  });

  const commentMutation = useMutation({
    mutationFn: (comment: string) => addComment(Number(id), comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      setNewComment('');
      toast.success('Comment added');
    },
  });

  const laborMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => addLaborTransaction(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      setShowLaborModal(false);
      setLaborForm({
        user_id: '',
        hours: '',
        labor_type: 'REGULAR',
        notes: '',
      });
      toast.success('Labor entry recorded');
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to add labor entry';
      toast.error(message);
      console.error('Labor error:', axiosError?.response?.data);
    },
  });

  const materialMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => addMaterialTransaction(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      queryClient.invalidateQueries({ queryKey: ['parts'] });
      setShowMaterialModal(false);
      setMaterialForm({
        part_id: '',
        quantity: '1',
        unit_cost: '',
        storeroom_id: '',
        transaction_type: 'ISSUE',
        notes: '',
      });
      toast.success('Material transaction recorded');
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to add material';
      toast.error(message);
      console.error('Material error:', axiosError?.response?.data);
    },
  });

  const taskMutation = useMutation({
    mutationFn: ({ taskId, data }: { taskId: number; data: Record<string, unknown> }) =>
      updateWorkOrderTask(Number(id), taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-order', id] });
      toast.success('Task updated');
    },
    onError: () => toast.error('Failed to update task'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteWorkOrder(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['work-orders'] });
      toast.success('Work order deleted successfully');
      navigate('/work-orders');
    },
    onError: (error: Error) => toast.error(error.message || 'Failed to delete work order'),
  });

  // Handlers
  const handleAddLabor = () => {
    if (!laborForm.hours || parseFloat(laborForm.hours) <= 0) {
      toast.error('Please enter valid hours');
      return;
    }
    const data: Record<string, unknown> = {
      hours: parseFloat(laborForm.hours),
      labor_type: laborForm.labor_type,
      notes: laborForm.notes || undefined,
    };
    // Include user_id if specified (admin selecting a user)
    if (laborForm.user_id) {
      data.user_id = parseInt(laborForm.user_id);
    }
    laborMutation.mutate(data);
  };

  const handleAddMaterial = () => {
    if (!materialForm.part_id) {
      toast.error('Please select a part');
      return;
    }
    if (!materialForm.quantity || parseFloat(materialForm.quantity) <= 0) {
      toast.error('Please enter valid quantity');
      return;
    }
    materialMutation.mutate({
      part_id: parseInt(materialForm.part_id),
      quantity: parseFloat(materialForm.quantity),
      unit_cost: parseFloat(materialForm.unit_cost) || 0,
      storeroom_id: materialForm.storeroom_id ? parseInt(materialForm.storeroom_id) : undefined,
      transaction_type: materialForm.transaction_type,
      notes: materialForm.notes || undefined,
    });
  };

  const handleToggleTask = (task: Task) => {
    taskMutation.mutate({
      taskId: task.id,
      data: { is_completed: !task.is_completed },
    });
  };

  const handleStatusChange = (newStatus: string) => {
    // Show completion modal for completing work orders
    if (newStatus === 'COMPLETED') {
      setShowCompletionModal(true);
    } else {
      statusMutation.mutate({ status: newStatus });
    }
  };

  const handleComplete = () => {
    const data: StatusUpdateData = {
      status: 'COMPLETED',
      completion_notes: completionForm.completion_notes || undefined,
      failure_code: completionForm.failure_code || undefined,
      failure_cause: completionForm.failure_cause || undefined,
      failure_remedy: completionForm.failure_remedy || undefined,
      downtime_hours: completionForm.downtime_hours ? parseFloat(completionForm.downtime_hours) : undefined,
      asset_was_down: completionForm.asset_was_down,
    };
    statusMutation.mutate(data);
  };

  const getUserName = (userId: number) => {
    const user = usersData?.items?.find((u: { id: number }) => u.id === userId);
    return user ? `${user.first_name} ${user.last_name}` : `User #${userId}`;
  };

  const getPartInfo = (partId: number) => {
    return partsData?.items?.find((p: { id: number }) => p.id === partId);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!workOrder) {
    return <div>Work order not found</div>;
  }

  const actions = statusActions[workOrder.status] || [];
  const canAddEntries = ['IN_PROGRESS', 'ON_HOLD'].includes(workOrder.status) || isAdmin;
  const completedTasksCount = workOrder.tasks?.filter((t: Task) => t.is_completed).length || 0;
  const totalTasksCount = workOrder.tasks?.length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/work-orders" className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900">{workOrder.title}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[workOrder.status]}`}>
                {workOrder.status.replace(/_/g, ' ')}
              </span>
              <span className={`badge ${priorityColors[workOrder.priority] || 'badge-gray'}`}>
                {workOrder.priority}
              </span>
            </div>
            <p className="text-gray-600">{workOrder.wo_number}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {actions.map((action) => (
            <button
              key={action.next}
              onClick={() => handleStatusChange(action.next)}
              disabled={statusMutation.isPending}
              className={`${action.color} flex items-center gap-2`}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
          <Link to={`/work-orders/${id}/edit`} className="btn-secondary flex items-center gap-2">
            <Edit className="w-4 h-4" />
            Edit
          </Link>
          {isAdmin && (
            <button
              onClick={() => setShowDeleteModal(true)}
              className="btn-danger flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {[
            { id: 'details', label: 'Details', icon: ClipboardList },
            { id: 'tasks', label: `Tasks (${completedTasksCount}/${totalTasksCount})`, icon: CheckCircle },
            { id: 'labor', label: `Labor (${workOrder.labor_transactions?.length || 0})`, icon: Clock },
            { id: 'materials', label: `Materials (${workOrder.material_transactions?.length || 0})`, icon: Package },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Details Tab */}
          {activeTab === 'details' && (
            <>
              <div className="card">
                <h2 className="text-lg font-semibold mb-4">Work Order Details</h2>
                <div className="space-y-4">
                  {workOrder.description && (
                    <div>
                      <p className="text-sm text-gray-500">Description</p>
                      <p className="mt-1">{workOrder.description}</p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Type</p>
                      <p className="font-medium">{workOrder.work_type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Priority</p>
                      <p className="font-medium">{workOrder.priority}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Due Date</p>
                      <p className="font-medium">
                        {workOrder.due_date ? format(new Date(workOrder.due_date), 'MMM d, yyyy') : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Estimated Hours</p>
                      <p className="font-medium">{workOrder.estimated_hours || '-'}</p>
                    </div>
                  </div>
                  {(workOrder.failure_code || workOrder.failure_cause || workOrder.failure_remedy) && (
                    <div className="pt-4 border-t">
                      <h3 className="font-medium mb-2">Failure Information</h3>
                      <div className="grid grid-cols-1 gap-2 text-sm">
                        {workOrder.failure_code && (
                          <div><span className="text-gray-500">Code:</span> {workOrder.failure_code}</div>
                        )}
                        {workOrder.failure_cause && (
                          <div><span className="text-gray-500">Cause:</span> {workOrder.failure_cause}</div>
                        )}
                        {workOrder.failure_remedy && (
                          <div><span className="text-gray-500">Remedy:</span> {workOrder.failure_remedy}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Comments */}
              <div className="card">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  Comments ({workOrder.comments?.length || 0})
                </h2>
                <div className="space-y-4">
                  {workOrder.comments?.map((comment: Comment) => (
                    <div key={comment.id} className="flex gap-3">
                      <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-gray-600" />
                      </div>
                      <div className="flex-1">
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-xs font-medium text-gray-700 mb-1">{getUserName(comment.user_id)}</p>
                          <p className="text-sm">{comment.comment}</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {format(new Date(comment.created_at), 'MMM d, yyyy h:mm a')}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-primary-600" />
                    </div>
                    <div className="flex-1">
                      <textarea
                        className="input resize-none"
                        rows={2}
                        placeholder="Add a comment..."
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                      />
                      <button
                        className="btn-primary mt-2 flex items-center gap-2"
                        disabled={!newComment.trim() || commentMutation.isPending}
                        onClick={() => commentMutation.mutate(newComment)}
                      >
                        <Send className="w-4 h-4" />
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Tasks Tab */}
          {activeTab === 'tasks' && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Tasks</h2>
                {totalTasksCount > 0 && (
                  <span className="text-sm text-gray-500">
                    {completedTasksCount} of {totalTasksCount} completed
                  </span>
                )}
              </div>
              {workOrder.tasks?.length > 0 ? (
                <div className="space-y-2">
                  {workOrder.tasks.map((task: Task) => (
                    <div
                      key={task.id}
                      className={`flex items-start gap-3 p-4 rounded-lg border ${
                        task.is_completed ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <button
                        onClick={() => handleToggleTask(task)}
                        disabled={taskMutation.isPending || !canAddEntries}
                        className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                          task.is_completed
                            ? 'bg-green-500 text-white'
                            : 'border-2 border-gray-300 hover:border-primary-500'
                        } ${!canAddEntries ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {task.is_completed && <Check className="w-4 h-4" />}
                      </button>
                      <div className="flex-1">
                        <p className={`font-medium ${task.is_completed ? 'line-through text-gray-500' : ''}`}>
                          {task.sequence}. {task.description}
                        </p>
                        {task.instructions && (
                          <p className="text-sm text-gray-500 mt-1">{task.instructions}</p>
                        )}
                        {task.estimated_hours && (
                          <p className="text-xs text-gray-400 mt-1">Est. {task.estimated_hours} hrs</p>
                        )}
                        {task.completed_at && (
                          <p className="text-xs text-green-600 mt-1">
                            Completed {format(new Date(task.completed_at), 'MMM d, h:mm a')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No tasks defined for this work order</p>
              )}
            </div>
          )}

          {/* Labor Tab */}
          {activeTab === 'labor' && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Labor Entries
                </h2>
                {canAddEntries && (
                  <button
                    type="button"
                    onClick={() => setShowLaborModal(true)}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Labor
                  </button>
                )}
              </div>
              {workOrder.labor_transactions?.length > 0 ? (
                <div className="space-y-3">
                  {workOrder.labor_transactions.map((labor: LaborTransaction) => (
                    <div key={labor.id} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium">{getUserName(labor.user_id)}</p>
                          <p className="text-sm text-gray-500">
                            {labor.hours} hrs @ ${labor.hourly_rate}/hr ({labor.labor_type})
                          </p>
                          {labor.craft && <p className="text-sm text-gray-500">Craft: {labor.craft}</p>}
                          {labor.notes && <p className="text-sm text-gray-500 mt-1">{labor.notes}</p>}
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">${labor.total_cost.toFixed(2)}</p>
                          <p className="text-xs text-gray-500">
                            {format(new Date(labor.created_at), 'MMM d, h:mm a')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No labor entries recorded</p>
              )}
            </div>
          )}

          {/* Materials Tab */}
          {activeTab === 'materials' && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Materials Used
                </h2>
                {canAddEntries && (
                  <button
                    type="button"
                    onClick={() => setShowMaterialModal(true)}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Material
                  </button>
                )}
              </div>
              {workOrder.material_transactions?.length > 0 ? (
                <div className="space-y-3">
                  {workOrder.material_transactions.map((material: MaterialTransaction) => {
                    const part = getPartInfo(material.part_id);
                    return (
                      <div key={material.id} className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium">
                              {part ? `${part.part_number} - ${part.name}` : `Part #${material.part_id}`}
                            </p>
                            <p className="text-sm text-gray-500">
                              Qty: {material.quantity} @ ${material.unit_cost.toFixed(2)} each
                            </p>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              material.transaction_type === 'ISSUE' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                            }`}>
                              {material.transaction_type}
                            </span>
                            {material.notes && <p className="text-sm text-gray-500 mt-1">{material.notes}</p>}
                          </div>
                          <div className="text-right">
                            <p className="font-semibold">${material.total_cost.toFixed(2)}</p>
                            <p className="text-xs text-gray-500">
                              {format(new Date(material.created_at), 'MMM d, h:mm a')}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No materials used</p>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assignment */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <User className="w-4 h-4" />
              Assignment
            </h3>
            <p className="text-gray-600">
              {workOrder.assigned_to_id ? getUserName(workOrder.assigned_to_id) : 'Unassigned'}
            </p>
            {workOrder.assigned_group_id && (
              <p className="text-sm text-gray-500 mt-1">
                Group: {userGroupsData?.find((g: { id: number }) => g.id === workOrder.assigned_group_id)?.name || 'Unknown Group'}
              </p>
            )}
            {workOrder.assigned_team && (
              <p className="text-sm text-gray-500 mt-1">Team: {workOrder.assigned_team}</p>
            )}
          </div>

          {/* Asset */}
          {workOrder.asset_id && (
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Wrench className="w-4 h-4" />
                  Asset
                </h3>
                <Link
                  to={`/assets/${workOrder.asset_id}`}
                  className="text-primary-600 hover:text-primary-700"
                  title="View full asset details"
                >
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </div>
              {asset ? (
                <div className="space-y-3">
                  <div>
                    <p className="font-medium text-gray-900">{asset.name}</p>
                    <p className="text-sm text-gray-500">{asset.asset_num}</p>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      asset.status === 'OPERATING' ? 'bg-green-100 text-green-800' :
                      asset.status === 'NOT_OPERATING' ? 'bg-red-100 text-red-800' :
                      asset.status === 'STANDBY' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {asset.status?.replace(/_/g, ' ')}
                    </span>
                    {asset.criticality && (
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        asset.criticality === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                        asset.criticality === 'HIGH' ? 'bg-yellow-100 text-yellow-800' :
                        asset.criticality === 'MEDIUM' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {asset.criticality}
                      </span>
                    )}
                  </div>
                  <div className="space-y-2 text-sm border-t pt-3">
                    {asset.category && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Category</span>
                        <span className="text-gray-900">{asset.category}</span>
                      </div>
                    )}
                    {asset.manufacturer && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Manufacturer</span>
                        <span className="text-gray-900">{asset.manufacturer}</span>
                      </div>
                    )}
                    {asset.model && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Model</span>
                        <span className="text-gray-900">{asset.model}</span>
                      </div>
                    )}
                    {asset.serial_number && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Serial #</span>
                        <span className="text-gray-900 font-mono text-xs">{asset.serial_number}</span>
                      </div>
                    )}
                    {asset.location_name && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-500 flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          Location
                        </span>
                        <span className="text-gray-900">{asset.location_name}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">Loading asset details...</div>
              )}
            </div>
          )}

          {/* Time tracking */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Time Tracking
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Created</span>
                <span>{format(new Date(workOrder.created_at), 'MMM d, yyyy')}</span>
              </div>
              {workOrder.actual_start && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Started</span>
                  <span>{format(new Date(workOrder.actual_start), 'MMM d, h:mm a')}</span>
                </div>
              )}
              {workOrder.actual_end && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Completed</span>
                  <span>{format(new Date(workOrder.actual_end), 'MMM d, h:mm a')}</span>
                </div>
              )}
              <div className="pt-2 border-t">
                <div className="flex justify-between">
                  <span className="text-gray-600">Estimated</span>
                  <span>{workOrder.estimated_hours || 0} hrs</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span>Actual</span>
                  <span>{workOrder.actual_labor_hours?.toFixed(1) || 0} hrs</span>
                </div>
              </div>
            </div>
          </div>

          {/* Costs */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Costs
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Labor</span>
                <span>${(workOrder.actual_labor_cost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Materials</span>
                <span>${(workOrder.actual_material_cost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between font-semibold text-base pt-2 border-t">
                <span>Total</span>
                <span>${(workOrder.total_cost || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Completion Notes */}
          {workOrder.completion_notes && (
            <div className="card">
              <h3 className="font-semibold mb-3">Completion Notes</h3>
              <p className="text-sm text-gray-600">{workOrder.completion_notes}</p>
            </div>
          )}
        </div>
      </div>

      {/* Labor Modal */}
      {showLaborModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Log Time</h2>
              <button onClick={() => setShowLaborModal(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Hourly rate and craft are automatically applied from the user's profile.
            </p>
            <div className="space-y-4">
              {/* User selection - for admins to log time for other users */}
              {isAdmin && (
                <div>
                  <label className="label">Technician</label>
                  <select
                    className="input"
                    value={laborForm.user_id}
                    onChange={(e) => setLaborForm({ ...laborForm, user_id: e.target.value })}
                  >
                    <option value="">Myself (default)</option>
                    {usersData?.items?.map((u: { id: number; first_name: string; last_name: string; job_title?: string; hourly_rate?: number }) => (
                      <option key={u.id} value={u.id}>
                        {u.first_name} {u.last_name} {u.job_title ? `(${u.job_title})` : ''} {u.hourly_rate ? `- $${u.hourly_rate}/hr` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Hours Worked *</label>
                  <input
                    type="number"
                    className="input"
                    step="0.25"
                    min="0.25"
                    value={laborForm.hours}
                    onChange={(e) => setLaborForm({ ...laborForm, hours: e.target.value })}
                    placeholder="0.0"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="label">Type</label>
                  <select
                    className="input"
                    value={laborForm.labor_type}
                    onChange={(e) => setLaborForm({ ...laborForm, labor_type: e.target.value })}
                  >
                    <option value="REGULAR">Regular</option>
                    <option value="OVERTIME">Overtime</option>
                    <option value="DOUBLE_TIME">Double Time</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Notes (optional)</label>
                <textarea
                  className="input"
                  rows={2}
                  value={laborForm.notes}
                  onChange={(e) => setLaborForm({ ...laborForm, notes: e.target.value })}
                  placeholder="Describe work performed..."
                />
              </div>
              <div className="flex justify-end gap-4">
                <button type="button" onClick={() => setShowLaborModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddLabor}
                  disabled={laborMutation.isPending || !laborForm.hours}
                  className="btn-primary"
                >
                  {laborMutation.isPending ? 'Adding...' : 'Log Time'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Material Modal */}
      {showMaterialModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Add Material</h2>
              <button onClick={() => setShowMaterialModal(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="label">Part</label>
                <select
                  className="input"
                  value={materialForm.part_id}
                  onChange={(e) => {
                    const partId = e.target.value;
                    const part = partsData?.items?.find((p: { id: number }) => p.id === Number(partId));
                    setMaterialForm({
                      ...materialForm,
                      part_id: partId,
                      unit_cost: part?.unit_cost?.toString() || '',
                    });
                  }}
                >
                  <option value="">Select a part</option>
                  {partsData?.items?.map((part: { id: number; part_number: string; name: string; unit_cost: number }) => (
                    <option key={part.id} value={part.id}>
                      {part.part_number} - {part.name} (${part.unit_cost?.toFixed(2) || '0.00'})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Quantity</label>
                  <input
                    type="number"
                    className="input"
                    min="1"
                    value={materialForm.quantity}
                    onChange={(e) => setMaterialForm({ ...materialForm, quantity: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Unit Cost</label>
                  <input
                    type="number"
                    className="input"
                    step="0.01"
                    min="0"
                    value={materialForm.unit_cost}
                    onChange={(e) => setMaterialForm({ ...materialForm, unit_cost: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Transaction Type</label>
                  <select
                    className="input"
                    value={materialForm.transaction_type}
                    onChange={(e) => setMaterialForm({ ...materialForm, transaction_type: e.target.value })}
                  >
                    <option value="ISSUE">Issue (Use)</option>
                    <option value="RETURN">Return</option>
                  </select>
                </div>
                <div>
                  <label className="label">From Storeroom</label>
                  <select
                    className="input"
                    value={materialForm.storeroom_id}
                    onChange={(e) => setMaterialForm({ ...materialForm, storeroom_id: e.target.value })}
                  >
                    <option value="">N/A</option>
                    {storeroomsData?.map((sr: { id: number; code: string; name: string }) => (
                      <option key={sr.id} value={sr.id}>
                        {sr.code} - {sr.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Notes</label>
                <textarea
                  className="input"
                  rows={2}
                  value={materialForm.notes}
                  onChange={(e) => setMaterialForm({ ...materialForm, notes: e.target.value })}
                  placeholder="Additional details..."
                />
              </div>
              {materialForm.quantity && materialForm.unit_cost && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm text-gray-500">Total Cost</p>
                  <p className="text-xl font-bold">
                    ${(parseFloat(materialForm.quantity) * parseFloat(materialForm.unit_cost)).toFixed(2)}
                  </p>
                </div>
              )}
              <div className="flex justify-end gap-4">
                <button type="button" onClick={() => setShowMaterialModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddMaterial}
                  disabled={materialMutation.isPending}
                  className="btn-primary"
                >
                  {materialMutation.isPending ? 'Adding...' : 'Add Material'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Completion Modal */}
      {showCompletionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Complete Work Order</h2>
              <button
                onClick={() => {
                  setShowCompletionModal(false);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Summary Section */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold mb-3">Work Order Summary</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Total Labor</p>
                  <p className="font-medium">{workOrder.actual_labor_hours?.toFixed(1) || 0} hrs</p>
                  <p className="text-gray-500">${(workOrder.actual_labor_cost || 0).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Total Materials</p>
                  <p className="font-medium">{workOrder.material_transactions?.length || 0} items</p>
                  <p className="text-gray-500">${(workOrder.actual_material_cost || 0).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Tasks Completed</p>
                  <p className="font-medium">{completedTasksCount} of {totalTasksCount}</p>
                </div>
                <div>
                  <p className="text-gray-500">Total Cost</p>
                  <p className="font-semibold text-lg">${(workOrder.total_cost || 0).toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="label">Completion Notes *</label>
                <textarea
                  className="input"
                  rows={3}
                  value={completionForm.completion_notes}
                  onChange={(e) => setCompletionForm({ ...completionForm, completion_notes: e.target.value })}
                  placeholder="Describe the work performed and outcome..."
                />
              </div>

              {/* Downtime */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Downtime Hours</label>
                  <input
                    type="number"
                    className="input"
                    step="0.5"
                    min="0"
                    value={completionForm.downtime_hours}
                    onChange={(e) => setCompletionForm({ ...completionForm, downtime_hours: e.target.value })}
                    placeholder="0.0"
                  />
                </div>
                <div className="flex items-center pt-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={completionForm.asset_was_down}
                      onChange={(e) => setCompletionForm({ ...completionForm, asset_was_down: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm">Asset was down during work</span>
                  </label>
                </div>
              </div>

              {/* Failure Information */}
              <div className="pt-4 border-t">
                <h3 className="font-medium mb-3">Failure Information (if applicable)</h3>
                <div className="space-y-3">
                  <div>
                    <label className="label">Failure Code</label>
                    <input
                      type="text"
                      className="input"
                      value={completionForm.failure_code}
                      onChange={(e) => setCompletionForm({ ...completionForm, failure_code: e.target.value })}
                      placeholder="e.g., MECH-001, ELEC-003"
                    />
                  </div>
                  <div>
                    <label className="label">Failure Cause</label>
                    <input
                      type="text"
                      className="input"
                      value={completionForm.failure_cause}
                      onChange={(e) => setCompletionForm({ ...completionForm, failure_cause: e.target.value })}
                      placeholder="Root cause of the failure..."
                    />
                  </div>
                  <div>
                    <label className="label">Failure Remedy</label>
                    <input
                      type="text"
                      className="input"
                      value={completionForm.failure_remedy}
                      onChange={(e) => setCompletionForm({ ...completionForm, failure_remedy: e.target.value })}
                      placeholder="How the failure was resolved..."
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-4 pt-4 border-t">
                <button
                  onClick={() => {
                    setShowCompletionModal(false);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleComplete}
                  disabled={statusMutation.isPending}
                  className="btn-success flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  {statusMutation.isPending ? 'Completing...' : 'Complete Work Order'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Delete Work Order</h2>
                <p className="text-sm text-gray-500">This action cannot be undone</p>
              </div>
            </div>

            <div className="mb-6">
              <p className="text-gray-600">
                Are you sure you want to delete work order <span className="font-semibold">{workOrder.wo_number}</span>?
              </p>
              <p className="text-sm text-gray-500 mt-2">
                This will permanently delete the work order and all associated data including:
              </p>
              <ul className="text-sm text-gray-500 mt-1 ml-4 list-disc">
                <li>Labor transactions ({workOrder.labor_transactions?.length || 0})</li>
                <li>Material transactions ({workOrder.material_transactions?.length || 0})</li>
                <li>Tasks ({workOrder.tasks?.length || 0})</li>
                <li>Comments ({workOrder.comments?.length || 0})</li>
                <li>Status history</li>
              </ul>
            </div>

            <div className="flex justify-end gap-4">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="btn-danger flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                {deleteMutation.isPending ? 'Deleting...' : 'Delete Work Order'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
