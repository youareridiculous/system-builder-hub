export enum Role {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
}

export const getCurrentRole = (): Role => {
  const role = localStorage.getItem('user_role');
  return (role as Role) || Role.VIEWER;
};

export const hasPermission = (requiredRole: Role): boolean => {
  const currentRole = getCurrentRole();
  const roleHierarchy = {
    [Role.OWNER]: 4,
    [Role.ADMIN]: 3,
    [Role.MEMBER]: 2,
    [Role.VIEWER]: 1,
  };

  return roleHierarchy[currentRole] >= roleHierarchy[requiredRole];
};

export const canCreate = (resource: string): boolean => {
  const currentRole = getCurrentRole();
  return [Role.OWNER, Role.ADMIN, Role.MEMBER].includes(currentRole);
};

export const canUpdate = (resource: string): boolean => {
  const currentRole = getCurrentRole();
  return [Role.OWNER, Role.ADMIN, Role.MEMBER].includes(currentRole);
};

export const canDelete = (resource: string): boolean => {
  const currentRole = getCurrentRole();
  return [Role.OWNER, Role.ADMIN].includes(currentRole);
};

export const canView = (resource: string): boolean => {
  return true; // All roles can view
};

export const canManageUsers = (): boolean => {
  const currentRole = getCurrentRole();
  return [Role.OWNER, Role.ADMIN].includes(currentRole);
};

export const canManageSubscriptions = (): boolean => {
  const currentRole = getCurrentRole();
  return [Role.OWNER, Role.ADMIN].includes(currentRole);
};
