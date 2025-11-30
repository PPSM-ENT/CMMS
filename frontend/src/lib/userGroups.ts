import api from './api';

export interface UserGroupMember {
  id: number;
  user_id: number;
  role: string | null;
  sequence: number;
  user_name: string;
  user_email: string;
}

export interface UserGroup {
  id: number;
  organization_id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
  members?: UserGroupMember[];
}

export interface UserGroupsResponse {
  items: UserGroup[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface GetUserGroupsParams {
  page?: number;
  page_size?: number;
  search?: string;
  include_inactive?: boolean;
}

export interface CreateUserGroupData {
  name: string;
  description?: string;
  members: Array<{
    user_id: number;
    role?: string;
    sequence?: number;
  }>;
}

export interface UpdateUserGroupData {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface AddGroupMemberData {
  user_id: number;
  role?: string;
  sequence?: number;
}

// User Group API Functions

export const getUserGroups = async (params?: GetUserGroupsParams): Promise<UserGroupsResponse> => {
  const response = await api.get('/user-groups', { params });
  return response.data;
};

export const getUserGroup = async (id: number): Promise<UserGroup> => {
  const response = await api.get(`/user-groups/${id}`);
  return response.data;
};

export const createUserGroup = async (data: CreateUserGroupData): Promise<UserGroup> => {
  const response = await api.post('/user-groups', data);
  return response.data;
};

export const updateUserGroup = async (id: number, data: UpdateUserGroupData): Promise<UserGroup> => {
  const response = await api.put(`/user-groups/${id}`, data);
  return response.data;
};

export const deleteUserGroup = async (id: number): Promise<{ message: string }> => {
  const response = await api.delete(`/user-groups/${id}`);
  return response.data;
};

export const addGroupMember = async (groupId: number, data: AddGroupMemberData): Promise<UserGroup> => {
  const response = await api.post(`/user-groups/${groupId}/members`, data);
  return response.data;
};

export const removeGroupMember = async (groupId: number, memberId: number): Promise<UserGroup> => {
  const response = await api.delete(`/user-groups/${groupId}/members/${memberId}`);
  return response.data;
};