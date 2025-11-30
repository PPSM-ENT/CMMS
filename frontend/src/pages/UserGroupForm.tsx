import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Save,
  UserPlus,
  UserMinus,
  Users,
} from 'lucide-react';
import { 
  getUserGroup, 
  createUserGroup, 
  updateUserGroup, 
  getUsers, 
  addGroupMember, 
  removeGroupMember 
} from '../lib/api';
import { UpdateUserGroupData, AddGroupMemberData } from '../lib/userGroups';

interface UserGroupFormData {
  name: string;
  description: string;
  is_active: boolean;
}

interface MemberFormData {
  user_id: number | '';
  role: string;
  sequence: number;
}

export default function UserGroupForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEditMode = !!id;

  const [formData, setFormData] = useState<UserGroupFormData>({
    name: '',
    description: '',
    is_active: true,
  });

  const [memberForm, setMemberForm] = useState<MemberFormData>({
    user_id: '',
    role: '',
    sequence: 0,
  });

  // Fetch user group data if editing
  const { data: groupData, isLoading: groupLoading } = useQuery({
    queryKey: ['user-group', id],
    queryFn: () => getUserGroup(Number(id)),
    enabled: isEditMode,
  });

  // Fetch all users for dropdown
  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
  });

  // Populate form when editing
  useEffect(() => {
    if (groupData) {
      setFormData({
        name: groupData.name || '',
        description: groupData.description || '',
        is_active: groupData.is_active,
      });
    }
  }, [groupData]);

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string; members: Array<{ user_id: number; role?: string }> }) =>
      createUserGroup({
        name: data.name,
        description: data.description,
        members: data.members.map(m => ({ user_id: m.user_id, role: m.role, sequence: 0 }))
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-groups'] }); // Invalidates all user-groups queries
      toast.success('User group created successfully');
      navigate(`/settings/user-groups/${data.id}`);
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to create user group';
      toast.error(message);
      console.error('Create group error:', axiosError?.response?.data);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateUserGroupData) => updateUserGroup(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-groups'] });
      queryClient.invalidateQueries({ queryKey: ['user-group', id] });
      toast.success('User group updated successfully');
      navigate(`/settings/user-groups/${id}`);
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to update user group';
      toast.error(message);
      console.error('Update group error:', axiosError?.response?.data);
    },
  });

  const addMemberMutation = useMutation({
    mutationFn: (data: AddGroupMemberData) => addGroupMember(Number(id), data),
    onSuccess: (data) => {
      queryClient.setQueryData(['user-group', id], data);
      toast.success('Member added to group');
      setMemberForm({ user_id: '', role: '', sequence: 0 });
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to add member';
      toast.error(message);
      console.error('Add member error:', axiosError?.response?.data);
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: number) => removeGroupMember(Number(id), memberId),
    onSuccess: (data) => {
      queryClient.setQueryData(['user-group', id], data);
      toast.success('Member removed from group');
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to remove member';
      toast.error(message);
      console.error('Remove member error:', axiosError?.response?.data);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('Group name is required');
      return;
    }

    if (isEditMode) {
      const submitData: UpdateUserGroupData = {
        name: formData.name || undefined,
        description: formData.description || undefined,
        is_active: formData.is_active,
      };
      updateMutation.mutate(submitData);
    } else {
      const submitData = {
        name: formData.name,
        description: formData.description || '',
        members: []
      };
      createMutation.mutate(submitData);
    }
  };

  const handleAddMember = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!memberForm.user_id) {
      toast.error('Please select a user');
      return;
    }

    addMemberMutation.mutate({
      user_id: Number(memberForm.user_id),
      role: memberForm.role || undefined,
      sequence: memberForm.sequence || 0
    });
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isAddingMember = addMemberMutation.isPending;
  const isRemovingMember = removeMemberMutation.isPending;

  if (isEditMode && groupLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleMemberChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setMemberForm(prev => ({
      ...prev,
      [name]: name === 'sequence' ? Number(value) : value,
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
            {isEditMode ? 'Edit User Group' : 'Create User Group'}
          </h1>
          <p className="text-gray-600">
            {isEditMode ? 'Update user group details and members' : 'Create a new user group for work assignment'}
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5" />
            Group Details
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Name */}
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
                placeholder="Enter group name"
                required
              />
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <div className="flex items-center gap-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="is_active"
                    checked={formData.is_active}
                    onChange={handleChange}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Active</span>
                </label>
              </div>
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
                placeholder="Describe the purpose of this group"
              />
            </div>
          </div>
        </div>

        {/* Members */}
        {isEditMode && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <UserPlus className="w-5 h-5" />
              Group Members ({groupData?.members?.length || 0})
            </h2>

            <div className="space-y-4">
              {/* Add Member Form */}
              <form onSubmit={handleAddMember} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="md:col-span-2">
                  <select
                    name="user_id"
                    value={memberForm.user_id}
                    onChange={handleMemberChange}
                    className="input"
                    disabled={isAddingMember}
                  >
                    <option value="">Select a user to add</option>
                    {usersData?.items
                      ?.filter((user: any) => 
                        !groupData?.members?.some((m: any) => m.user_id === user.id)
                      )
                      .map((user: any) => (
                        <option key={user.id} value={user.id}>
                          {user.first_name} {user.last_name} - {user.email}
                        </option>
                    ))}
                  </select>
                </div>
                <div>
                  <input
                    type="text"
                    name="role"
                    value={memberForm.role}
                    onChange={handleMemberChange}
                    className="input"
                    placeholder="Role"
                    disabled={isAddingMember}
                  />
                </div>
                <div>
                  <input
                    type="number"
                    name="sequence"
                    value={memberForm.sequence}
                    onChange={handleMemberChange}
                    className="input"
                    placeholder="Sequence"
                    disabled={isAddingMember}
                  />
                </div>
                <div className="md:col-span-4">
                  <button
                    type="submit"
                    disabled={isAddingMember}
                    className="btn-primary flex items-center gap-2"
                  >
                    <UserPlus className="w-4 h-4" />
                    {isAddingMember ? 'Adding...' : 'Add Member'}
                  </button>
                </div>
              </form>

              {/* Members List */}
              <div className="space-y-2">
                {groupData?.members?.map((member: any) => {
                  const user = usersData?.items?.find((u: any) => u.id === member.user_id);
                  return (
                    <div key={member.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <div className="font-medium">{user?.first_name} {user?.last_name}</div>
                        <div className="text-sm text-gray-500">{user?.email}</div>
                        <div className="flex gap-2">
                          {member.role && <div className="text-sm text-primary-600">{member.role}</div>}
                          {member.sequence > 0 && <div className="text-sm text-gray-500">(#{member.sequence})</div>}
                        </div>
                      </div>
                      <button
                        onClick={() => removeMemberMutation.mutate(member.id)}
                        disabled={isRemovingMember}
                        className="text-red-500 hover:text-red-700 p-2"
                      >
                        <UserMinus className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
                {(!groupData?.members || groupData.members.length === 0) && (
                  <div className="text-center py-4 text-gray-500">
                    <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No members in this group</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
            {isPending ? (isEditMode ? 'Saving...' : 'Creating...') : (isEditMode ? 'Save Changes' : 'Create Group')}
          </button>
        </div>
      </form>
    </div>
  );
}