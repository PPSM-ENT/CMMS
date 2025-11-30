import { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Edit,
  UserPlus,
  UserMinus,
  Users,
} from 'lucide-react';
import { 
  getUserGroup, 
  getUsers, 
  addGroupMember, 
  removeGroupMember 
} from '../lib/api';
import { AddGroupMemberData } from '../lib/userGroups';

interface MemberFormData {
  user_id: number | '';
  role: string;
}

export default function UserGroupDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [memberForm, setMemberForm] = useState<MemberFormData>({
    user_id: '',
    role: '',
  });

  // Fetch user group data
  const { data: groupData, isLoading: groupLoading } = useQuery({
    queryKey: ['user-group', id],
    queryFn: () => getUserGroup(Number(id)),
    enabled: !!id,
  });

  // Fetch all users for dropdown
  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
  });

  const addMemberMutation = useMutation({
    mutationFn: (data: AddGroupMemberData) => addGroupMember(Number(id), data),
    onSuccess: (data) => {
      queryClient.setQueryData(['user-group', id], data);
      toast.success('Member added to group');
      setMemberForm({ user_id: '', role: '' });
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

  const handleAddMember = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!memberForm.user_id) {
      toast.error('Please select a user');
      return;
    }

    addMemberMutation.mutate({
      user_id: Number(memberForm.user_id),
      role: memberForm.role || undefined
    });
  };

  const isAddingMember = addMemberMutation.isPending;
  const isRemovingMember = removeMemberMutation.isPending;

  const handleMemberChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setMemberForm(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  if (groupLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{groupData?.name}</h1>
            <p className="text-gray-600">View and manage group members</p>
          </div>
        </div>
        <Link 
          to={`/settings/user-groups/${id}/edit`} 
          className="btn-primary flex items-center gap-2"
        >
          <Edit className="w-4 h-4" />
          Edit Group
        </Link>
      </div>

      {/* Group Info */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Users className="w-5 h-5" />
            Group Information
          </h2>
          {groupData?.is_active ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Active
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
              Inactive
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Name</label>
            <p className="font-medium">{groupData?.name}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Members</label>
            <p className="font-medium">{groupData?.member_count || 0} members</p>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-500 mb-1">Description</label>
            <p>{groupData?.description || 'No description provided'}</p>
          </div>
        </div>
      </div>

      {/* Members */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <UserPlus className="w-5 h-5" />
          Group Members ({groupData?.members?.length || 0})
        </h2>

        <div className="space-y-4">
          {/* Add Member Form */}
          <form onSubmit={handleAddMember} className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
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
            <div className="flex-1">
              <input
                type="text"
                name="role"
                value={memberForm.role}
                onChange={handleMemberChange}
                className="input"
                placeholder="Role (e.g., Lead, Technician)"
                disabled={isAddingMember}
              />
            </div>
            <button
              type="submit"
              disabled={isAddingMember}
              className="btn-primary flex items-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              {isAddingMember ? 'Adding...' : 'Add Member'}
            </button>
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
                    {member.role && <div className="text-sm text-primary-600">{member.role}</div>}
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
    </div>
  );
}