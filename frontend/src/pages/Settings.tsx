import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { useAuthStore } from '../stores/authStore';
import {
  User,
  Building,
  Bell,
  Shield,
  Key,
  Users,
  Trash2,
  Plus,
  Copy,
  Eye,
  EyeOff,
  History,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Edit3,
} from 'lucide-react';
import {
  updateUser,
  changePassword,
  createApiKey,
  getApiKeys,
  revokeApiKey,
  getUsers,
  getAuditLogs,
} from '../lib/api';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';

type SettingsTab = 'profile' | 'organization' | 'notifications' | 'security' | 'users' | 'user-groups' | 'audit';

interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  entity_name: string | null;
  action: string;
  user_id: number | null;
  user_email: string | null;
  user_name: string | null;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  changes: Record<string, { old: unknown; new: unknown }> | null;
  description: string | null;
  created_at: string;
}

interface UserData {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  username: string;
  phone?: string;
  job_title?: string;
  hourly_rate?: number;
  is_active: boolean;
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const queryClient = useQueryClient();
  const isAdmin = user?.is_superuser || user?.role === 'admin';

  // Profile form state
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    username: user?.username || '',
  });

  // Password form state
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [showPasswords, setShowPasswords] = useState(false);

  // API Key form state
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [apiKeyName, setApiKeyName] = useState('');
  const [apiKeyExpiry, setApiKeyExpiry] = useState<number | undefined>(undefined);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);

  // Notification preferences state
  const [notifications, setNotifications] = useState({
    workOrderAssignments: true,
    pmDueReminders: true,
    lowStockAlerts: true,
    statusChanges: true,
    comments: true,
  });

  // Audit log state
  const [auditFilters, setAuditFilters] = useState({
    entity_type: '',
    action: '',
    search: '',
    page: 1,
  });

  // User edit state
  const [showUserEditModal, setShowUserEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserData | null>(null);
  const [userEditForm, setUserEditForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    job_title: '',
    hourly_rate: '',
    is_active: true,
  });

  const baseTabs = [
    { id: 'profile' as SettingsTab, label: 'Profile', icon: User },
    { id: 'organization' as SettingsTab, label: 'Organization', icon: Building },
    { id: 'notifications' as SettingsTab, label: 'Notifications', icon: Bell },
    { id: 'security' as SettingsTab, label: 'Security', icon: Shield },
    { id: 'users' as SettingsTab, label: 'Users', icon: Users },
    { id: 'user-groups' as SettingsTab, label: 'User Groups', icon: Users },
  ];

  const tabs = isAdmin
    ? [...baseTabs, { id: 'audit' as SettingsTab, label: 'Audit Logs', icon: History }]
    : baseTabs;

  // Fetch API keys
  const { data: apiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: getApiKeys,
    enabled: activeTab === 'security',
  });

  // Fetch users for user management tab
  const { data: usersData } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => getUsers({ page_size: 100 }),
    enabled: activeTab === 'users',
  });

  // Fetch audit logs
  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['audit-logs', auditFilters],
    queryFn: () => getAuditLogs({
      entity_type: auditFilters.entity_type || undefined,
      action: auditFilters.action || undefined,
      search: auditFilters.search || undefined,
      page: auditFilters.page,
      page_size: 25,
    }),
    enabled: activeTab === 'audit' && isAdmin,
  });

  // Profile update mutation
  const profileMutation = useMutation({
    mutationFn: () => updateUser(user?.id || 0, profileData),
    onSuccess: (data) => {
      setUser(data);
      toast.success('Profile updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update profile');
    },
  });

  // Password change mutation
  const passwordMutation = useMutation({
    mutationFn: () => changePassword(passwordData.currentPassword, passwordData.newPassword),
    onSuccess: () => {
      toast.success('Password changed successfully');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to change password');
    },
  });

  // API key create mutation
  const createApiKeyMutation = useMutation({
    mutationFn: () => createApiKey(apiKeyName, apiKeyExpiry),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewApiKey(data.key);
      setApiKeyName('');
      setApiKeyExpiry(undefined);
      toast.success('API key created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create API key');
    },
  });

  // API key revoke mutation
  const revokeApiKeyMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      toast.success('API key revoked');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to revoke API key');
    },
  });

  // User update mutation
  const userUpdateMutation = useMutation({
    mutationFn: (data: { userId: number; userData: Record<string, unknown> }) =>
      updateUser(data.userId, data.userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-list'] });
      setShowUserEditModal(false);
      setEditingUser(null);
      toast.success('User updated successfully');
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || (error as Error).message || 'Failed to update user';
      toast.error(message);
    },
  });

  const handleEditUser = (userData: UserData) => {
    setEditingUser(userData);
    setUserEditForm({
      first_name: userData.first_name || '',
      last_name: userData.last_name || '',
      email: userData.email || '',
      phone: userData.phone || '',
      job_title: userData.job_title || '',
      hourly_rate: userData.hourly_rate?.toString() || '',
      is_active: userData.is_active,
    });
    setShowUserEditModal(true);
  };

  const handleSaveUser = () => {
    if (!editingUser) return;
    const updateData: Record<string, unknown> = {
      first_name: userEditForm.first_name,
      last_name: userEditForm.last_name,
      email: userEditForm.email,
      is_active: userEditForm.is_active,
    };
    if (userEditForm.phone) updateData.phone = userEditForm.phone;
    if (userEditForm.job_title) updateData.job_title = userEditForm.job_title;
    if (userEditForm.hourly_rate) updateData.hourly_rate = parseFloat(userEditForm.hourly_rate);

    userUpdateMutation.mutate({ userId: editingUser.id, userData: updateData });
  };

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    profileMutation.mutate();
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    passwordMutation.mutate();
  };

  const handleCreateApiKey = () => {
    if (!apiKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }
    createApiKeyMutation.mutate();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="card p-2 space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left ${
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          {activeTab === 'profile' && (
            <form onSubmit={handleProfileSubmit} className="card space-y-6">
              <h2 className="text-lg font-semibold">Profile Settings</h2>

              <div className="flex items-center gap-4">
                <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center">
                  <User className="w-10 h-10 text-primary-600" />
                </div>
                <div>
                  <p className="font-medium text-lg">{user?.first_name} {user?.last_name}</p>
                  <p className="text-gray-500">{user?.email}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">First Name</label>
                  <input
                    type="text"
                    className="input"
                    value={profileData.first_name}
                    onChange={(e) => setProfileData({ ...profileData, first_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Last Name</label>
                  <input
                    type="text"
                    className="input"
                    value={profileData.last_name}
                    onChange={(e) => setProfileData({ ...profileData, last_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input
                    type="email"
                    className="input"
                    value={profileData.email}
                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Username</label>
                  <input
                    type="text"
                    className="input"
                    value={profileData.username}
                    onChange={(e) => setProfileData({ ...profileData, username: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={profileMutation.isPending}
                  className="btn-primary"
                >
                  {profileMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}

          {activeTab === 'organization' && (
            <div className="card space-y-6">
              <h2 className="text-lg font-semibold">Organization Settings</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">Organization Name</label>
                  <input type="text" className="input" placeholder="Company Name" />
                </div>
                <div>
                  <label className="label">Organization Code</label>
                  <input type="text" className="input" placeholder="ORG-001" disabled />
                </div>
                <div>
                  <label className="label">Timezone</label>
                  <select className="input">
                    <option>America/New_York</option>
                    <option>America/Chicago</option>
                    <option>America/Denver</option>
                    <option>America/Los_Angeles</option>
                    <option>UTC</option>
                  </select>
                </div>
                <div>
                  <label className="label">Currency</label>
                  <select className="input">
                    <option>USD - US Dollar</option>
                    <option>EUR - Euro</option>
                    <option>GBP - British Pound</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end">
                <button className="btn-primary">Save Changes</button>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="card space-y-6">
              <h2 className="text-lg font-semibold">Notification Preferences</h2>

              <div className="space-y-4">
                {[
                  { key: 'workOrderAssignments', label: 'Work Order Assignments', description: 'Get notified when a work order is assigned to you' },
                  { key: 'pmDueReminders', label: 'PM Due Reminders', description: 'Receive reminders for upcoming preventive maintenance' },
                  { key: 'lowStockAlerts', label: 'Low Stock Alerts', description: 'Get alerted when parts fall below reorder point' },
                  { key: 'statusChanges', label: 'Work Order Status Changes', description: 'Notifications when work order status changes' },
                  { key: 'comments', label: 'Comments & Mentions', description: 'When someone comments or mentions you' },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium">{item.label}</p>
                      <p className="text-sm text-gray-500">{item.description}</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={notifications[item.key as keyof typeof notifications]}
                        onChange={(e) => setNotifications({ ...notifications, [item.key]: e.target.checked })}
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                ))}
              </div>

              <div className="flex justify-end">
                <button className="btn-primary" onClick={() => toast.success('Preferences saved')}>
                  Save Preferences
                </button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              {/* Change Password Card */}
              <form onSubmit={handlePasswordSubmit} className="card space-y-4">
                <h2 className="text-lg font-semibold">Change Password</h2>
                <div className="space-y-3 max-w-md">
                  <div className="relative">
                    <input
                      type={showPasswords ? 'text' : 'password'}
                      className="input pr-10"
                      placeholder="Current Password"
                      value={passwordData.currentPassword}
                      onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords(!showPasswords)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    className="input"
                    placeholder="New Password"
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                  />
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    className="input"
                    placeholder="Confirm New Password"
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                  />
                  <button
                    type="submit"
                    disabled={passwordMutation.isPending}
                    className="btn-primary"
                  >
                    {passwordMutation.isPending ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </form>

              {/* API Keys Card */}
              <div className="card space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                      <Key className="w-5 h-5" />
                      API Keys
                    </h2>
                    <p className="text-sm text-gray-500">
                      Manage API keys for programmatic access to the CMMS
                    </p>
                  </div>
                  <button
                    onClick={() => setShowApiKeyModal(true)}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Generate New Key
                  </button>
                </div>

                {apiKeys && apiKeys.length > 0 ? (
                  <div className="space-y-3">
                    {apiKeys.map((key: ApiKey) => (
                      <div key={key.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{key.name}</p>
                          <p className="text-sm text-gray-500">
                            {key.key_prefix}... | Created: {new Date(key.created_at).toLocaleDateString()}
                            {key.expires_at && ` | Expires: ${new Date(key.expires_at).toLocaleDateString()}`}
                          </p>
                        </div>
                        <button
                          onClick={() => revokeApiKeyMutation.mutate(key.id)}
                          disabled={revokeApiKeyMutation.isPending}
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No API keys created yet</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="card space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">User Management</h2>
                <button className="btn-primary flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  Add User
                </button>
              </div>

              {usersData?.items && usersData.items.length > 0 ? (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Job Title</th>
                        <th>Rate</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersData.items.map((u: UserData) => (
                        <tr key={u.id}>
                          <td className="font-medium">{u.first_name} {u.last_name}</td>
                          <td>{u.email}</td>
                          <td>{u.job_title || '-'}</td>
                          <td>{u.hourly_rate ? `$${u.hourly_rate.toFixed(2)}/hr` : '-'}</td>
                          <td>
                            <span className={`badge ${u.is_active ? 'badge-green' : 'badge-red'}`}>
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td>
                            <button
                              onClick={() => handleEditUser(u)}
                              className="text-primary-600 hover:underline text-sm flex items-center gap-1"
                            >
                              <Edit3 className="w-3 h-3" />
                              Edit
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Users className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p>No users found</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'user-groups' && (
            <div className="card space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    User Groups
                  </h2>
                  <p className="text-sm text-gray-500">
                    Manage user groups for work assignment and team organization
                  </p>
                </div>
                <Link to="/settings/user-groups/new" className="btn-primary flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  New Group
                </Link>
              </div>
              
              <div className="text-center py-12">
                <Users className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p className="text-gray-500 mb-4">Manage user groups from the dedicated section</p>
                <Link to="/settings/user-groups" className="btn-primary">
                  Go to User Groups
                </Link>
              </div>
            </div>
          )}

          {activeTab === 'audit' && isAdmin && (
            <div className="space-y-6">
              {/* Filters */}
              <div className="card">
                <div className="flex flex-wrap gap-4">
                  <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search by name or description..."
                        className="input pl-10"
                        value={auditFilters.search}
                        onChange={(e) => setAuditFilters({ ...auditFilters, search: e.target.value, page: 1 })}
                      />
                    </div>
                  </div>
                  <div className="w-48">
                    <select
                      className="input"
                      value={auditFilters.entity_type}
                      onChange={(e) => setAuditFilters({ ...auditFilters, entity_type: e.target.value, page: 1 })}
                    >
                      <option value="">All Entities</option>
                      <option value="Asset">Assets</option>
                      <option value="User">Users</option>
                      <option value="WorkOrder">Work Orders</option>
                      <option value="Part">Parts</option>
                      <option value="PM">PM Schedules</option>
                    </select>
                  </div>
                  <div className="w-48">
                    <select
                      className="input"
                      value={auditFilters.action}
                      onChange={(e) => setAuditFilters({ ...auditFilters, action: e.target.value, page: 1 })}
                    >
                      <option value="">All Actions</option>
                      <option value="CREATE">Created</option>
                      <option value="UPDATE">Updated</option>
                      <option value="DELETE">Deleted</option>
                      <option value="STATUS_CHANGE">Status Change</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Audit Log Table */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <History className="w-5 h-5" />
                    Audit Logs
                  </h2>
                  {auditData?.total > 0 && (
                    <span className="text-sm text-gray-500">
                      {auditData.total} entries found
                    </span>
                  )}
                </div>

                {auditLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : auditData?.items?.length > 0 ? (
                  <>
                    <div className="space-y-3">
                      {auditData.items.map((log: AuditLogEntry) => (
                        <div key={log.id} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={`badge ${
                                  log.action === 'CREATE' ? 'badge-green' :
                                  log.action === 'UPDATE' ? 'badge-blue' :
                                  log.action === 'DELETE' ? 'badge-red' :
                                  'badge-yellow'
                                }`}>
                                  {log.action}
                                </span>
                                <span className="font-medium text-gray-700">
                                  {log.entity_type}
                                </span>
                                {log.entity_name && (
                                  <span className="text-gray-500">
                                    - {log.entity_name}
                                  </span>
                                )}
                              </div>
                              {log.description && (
                                <p className="mt-1 text-sm text-gray-600">{log.description}</p>
                              )}
                              {log.changes && Object.keys(log.changes).length > 0 && (
                                <div className="mt-2 text-xs space-y-1">
                                  {Object.entries(log.changes).map(([field, change]) => (
                                    <div key={field} className="flex gap-2">
                                      <span className="font-medium text-gray-500">{field}:</span>
                                      <span className="text-red-600 line-through">{String(change.old ?? 'null')}</span>
                                      <span className="text-gray-400">-&gt;</span>
                                      <span className="text-green-600">{String(change.new ?? 'null')}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                              <div className="mt-2 text-xs text-gray-400">
                                By {log.user_name || 'System'} | {format(new Date(log.created_at), 'MMM d, yyyy h:mm a')}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Pagination */}
                    {auditData.pages > 1 && (
                      <div className="flex items-center justify-between mt-6">
                        <p className="text-sm text-gray-600">
                          Page {auditData.page} of {auditData.pages}
                        </p>
                        <div className="flex gap-2">
                          <button
                            className="btn-secondary flex items-center gap-1"
                            disabled={auditFilters.page === 1}
                            onClick={() => setAuditFilters({ ...auditFilters, page: auditFilters.page - 1 })}
                          >
                            <ChevronLeft className="w-4 h-4" />
                            Previous
                          </button>
                          <button
                            className="btn-secondary flex items-center gap-1"
                            disabled={auditFilters.page === auditData.pages}
                            onClick={() => setAuditFilters({ ...auditFilters, page: auditFilters.page + 1 })}
                          >
                            Next
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <History className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <p>No audit log entries found</p>
                    <p className="text-sm mt-1">Changes to assets and users will appear here</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* API Key Modal */}
      {showApiKeyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Generate API Key</h2>

            {newApiKey ? (
              <div className="space-y-4">
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800 mb-2">
                    Copy this key now. You won't be able to see it again!
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-white rounded border text-sm break-all">
                      {newApiKey}
                    </code>
                    <button
                      onClick={() => copyToClipboard(newApiKey)}
                      className="p-2 hover:bg-gray-100 rounded"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowApiKeyModal(false);
                    setNewApiKey(null);
                  }}
                  className="btn-primary w-full"
                >
                  Done
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="label">Key Name</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g., Production API"
                    value={apiKeyName}
                    onChange={(e) => setApiKeyName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="label">Expiration (optional)</label>
                  <select
                    className="input"
                    value={apiKeyExpiry || ''}
                    onChange={(e) => setApiKeyExpiry(e.target.value ? Number(e.target.value) : undefined)}
                  >
                    <option value="">Never expires</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                    <option value="365">1 year</option>
                  </select>
                </div>
                <div className="flex justify-end gap-4">
                  <button
                    onClick={() => {
                      setShowApiKeyModal(false);
                      setApiKeyName('');
                      setApiKeyExpiry(undefined);
                    }}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateApiKey}
                    disabled={createApiKeyMutation.isPending}
                    className="btn-primary"
                  >
                    {createApiKeyMutation.isPending ? 'Creating...' : 'Generate Key'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Edit Modal */}
      {showUserEditModal && editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Edit User</h2>
              <button
                onClick={() => {
                  setShowUserEditModal(false);
                  setEditingUser(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">First Name *</label>
                  <input
                    type="text"
                    className="input"
                    value={userEditForm.first_name}
                    onChange={(e) => setUserEditForm({ ...userEditForm, first_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Last Name *</label>
                  <input
                    type="text"
                    className="input"
                    value={userEditForm.last_name}
                    onChange={(e) => setUserEditForm({ ...userEditForm, last_name: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label className="label">Email *</label>
                <input
                  type="email"
                  className="input"
                  value={userEditForm.email}
                  onChange={(e) => setUserEditForm({ ...userEditForm, email: e.target.value })}
                />
              </div>

              <div>
                <label className="label">Phone</label>
                <input
                  type="text"
                  className="input"
                  value={userEditForm.phone}
                  onChange={(e) => setUserEditForm({ ...userEditForm, phone: e.target.value })}
                  placeholder="(555) 123-4567"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Job Title / Craft</label>
                  <input
                    type="text"
                    className="input"
                    value={userEditForm.job_title}
                    onChange={(e) => setUserEditForm({ ...userEditForm, job_title: e.target.value })}
                    placeholder="e.g., Electrician, Mechanic"
                  />
                </div>
                <div>
                  <label className="label">Hourly Rate ($)</label>
                  <input
                    type="number"
                    className="input"
                    step="0.01"
                    min="0"
                    value={userEditForm.hourly_rate}
                    onChange={(e) => setUserEditForm({ ...userEditForm, hourly_rate: e.target.value })}
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={userEditForm.is_active}
                  onChange={(e) => setUserEditForm({ ...userEditForm, is_active: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">
                  Active User
                </label>
              </div>

              <div className="flex justify-end gap-4 pt-4">
                <button
                  onClick={() => {
                    setShowUserEditModal(false);
                    setEditingUser(null);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveUser}
                  disabled={userUpdateMutation.isPending || !userEditForm.first_name || !userEditForm.last_name || !userEditForm.email}
                  className="btn-primary"
                >
                  {userUpdateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
