export enum UserRole {
  DOCTOR = 'doctor',
  RESEARCHER = 'researcher',
  MARKETING = 'marketing',
  INTERN = 'intern'
}

export interface User {
  id: string;
  name: string;
  role: UserRole;
}

export interface PatientData {
  id: string;
  name: string;
  age: number;
  gender: string;
  conditions: string[];
  medications: string[];
  notes: string;
  address: string;
  visit_dates: string[];
}

export interface AccessControlConfig {
  allowedFields: string[];
  canViewIndividualRecords: boolean;
  canViewIdentifyingInfo: boolean;
  canViewAggregatedData: boolean;
}

const rolePermissions: Record<UserRole, AccessControlConfig> = {
  [UserRole.DOCTOR]: {
    allowedFields: ['id', 'name', 'age', 'gender', 'conditions', 'medications', 'notes', 'address', 'visit_dates'],
    canViewIndividualRecords: true,
    canViewIdentifyingInfo: true,
    canViewAggregatedData: true
  },
  [UserRole.RESEARCHER]: {
    allowedFields: ['id', 'age', 'gender', 'conditions', 'medications', 'notes', 'visit_dates'],
    canViewIndividualRecords: true,
    canViewIdentifyingInfo: false,
    canViewAggregatedData: true
  },
  [UserRole.MARKETING]: {
    allowedFields: ['age', 'gender', 'conditions', 'medications'],
    canViewIndividualRecords: false,
    canViewIdentifyingInfo: false,
    canViewAggregatedData: true
  },
  [UserRole.INTERN]: {
    allowedFields: [],
    canViewIndividualRecords: false,
    canViewIdentifyingInfo: false,
    canViewAggregatedData: false
  }
};

export class AccessControlManager {
  static checkAccess(user: User, requestType: 'individual' | 'aggregated'): boolean {
    const permissions = rolePermissions[user.role];
    
    if (requestType === 'individual') {
      return permissions.canViewIndividualRecords;
    }
    
    if (requestType === 'aggregated') {
      return permissions.canViewAggregatedData;
    }
    
    return false;
  }

  static filterPatientData(user: User, patientData: PatientData): Partial<PatientData> | null {
    const permissions = rolePermissions[user.role];
    
    if (!permissions.canViewIndividualRecords) {
      return null;
    }

    const filteredData: Partial<PatientData> = {};
    
    for (const field of permissions.allowedFields) {
      if (field in patientData) {
        (filteredData as any)[field] = (patientData as any)[field];
      }
    }

    // Additional filtering for identifying information
    if (!permissions.canViewIdentifyingInfo) {
      delete filteredData.name;
      delete filteredData.address;
      // Replace patient ID with anonymized version for researchers
      if (filteredData.id) {
        filteredData.id = `ANON_${filteredData.id}`;
      }
    }

    return filteredData;
  }

  static getAccessDeniedMessage(user: User): string {
    switch (user.role) {
      case UserRole.INTERN:
        return "Access Denied: Interns require supervision for patient data access. Please contact your supervisor.";
      case UserRole.MARKETING:
        return "Access Denied: Marketing personnel can only access aggregated, de-identified statistics.";
      default:
        return "Access Denied: Insufficient permissions for this operation.";
    }
  }

  static getUserPermissions(user: User): AccessControlConfig {
    return rolePermissions[user.role];
  }
}
