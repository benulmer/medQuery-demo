import { PatientData, User, AccessControlManager, UserRole } from './accessControl.js';

export interface SummaryOptions {
  includeStatistics?: boolean;
  includeTrends?: boolean;
  maxLength?: number;
}

export interface PatientSummary {
  summary: string;
  accessLevel: string;
  redactedFields?: string[];
}

export interface PopulationStats {
  totalPatients: number;
  averageAge: number;
  genderDistribution: Record<string, number>;
  commonConditions: Array<{ condition: string; count: number; percentage: number }>;
  commonMedications: Array<{ medication: string; count: number; percentage: number }>;
}

export class PatientSummarizer {
  
  static summarizeIndividualPatient(
    user: User, 
    patientData: PatientData, 
    options: SummaryOptions = {}
  ): PatientSummary {
    
    // Check if user can access individual records
    if (!AccessControlManager.checkAccess(user, 'individual')) {
      return {
        summary: AccessControlManager.getAccessDeniedMessage(user),
        accessLevel: 'denied',
        redactedFields: Object.keys(patientData)
      };
    }

    const filteredData = AccessControlManager.filterPatientData(user, patientData);
    
    if (!filteredData) {
      return {
        summary: AccessControlManager.getAccessDeniedMessage(user),
        accessLevel: 'denied',
        redactedFields: Object.keys(patientData)
      };
    }

    const permissions = AccessControlManager.getUserPermissions(user);
    const redactedFields = Object.keys(patientData).filter(
      field => !permissions.allowedFields.includes(field)
    );

    let summary = this.generateIndividualSummary(filteredData, user.role);
    
    if (options.maxLength && summary.length > options.maxLength) {
      summary = summary.substring(0, options.maxLength) + '...';
    }

    return {
      summary,
      accessLevel: user.role,
      redactedFields: redactedFields.length > 0 ? redactedFields : undefined
    };
  }

  private static generateIndividualSummary(patientData: Partial<PatientData>, role: UserRole): string {
    const parts: string[] = [];

    // Patient identification (role-dependent)
    if (patientData.name) {
      parts.push(`Patient: ${patientData.name}`);
    } else if (patientData.id) {
      parts.push(`Patient ID: ${patientData.id}`);
    }

    // Demographics
    const demographics: string[] = [];
    if (patientData.age !== undefined) demographics.push(`${patientData.age} years old`);
    if (patientData.gender) demographics.push(patientData.gender);
    if (demographics.length > 0) {
      parts.push(`Demographics: ${demographics.join(', ')}`);
    }

    // Medical conditions
    if (patientData.conditions && patientData.conditions.length > 0) {
      parts.push(`Conditions: ${patientData.conditions.join(', ')}`);
    }

    // Current medications
    if (patientData.medications && patientData.medications.length > 0) {
      parts.push(`Current Medications: ${patientData.medications.join(', ')}`);
    }

    // Clinical notes
    if (patientData.notes) {
      parts.push(`Clinical Notes: ${patientData.notes}`);
    }

    // Visit history
    if (patientData.visit_dates && patientData.visit_dates.length > 0) {
      const visitCount = patientData.visit_dates.length;
      const lastVisit = patientData.visit_dates[patientData.visit_dates.length - 1];
      parts.push(`Visit History: ${visitCount} visits, most recent on ${lastVisit}`);
    }

    // Contact information (doctors only)
    if (patientData.address && role === UserRole.DOCTOR) {
      parts.push(`Address: ${patientData.address}`);
    }

    return parts.join('\n\n');
  }

  static generatePopulationStats(
    user: User, 
    patients: PatientData[]
  ): PopulationStats | { error: string } {
    
    if (!AccessControlManager.checkAccess(user, 'aggregated')) {
      return { error: AccessControlManager.getAccessDeniedMessage(user) };
    }

    const totalPatients = patients.length;
    
    // Calculate average age
    const ages = patients.map(p => p.age).filter(age => age !== undefined);
    const averageAge = ages.length > 0 ? ages.reduce((sum, age) => sum + age, 0) / ages.length : 0;

    // Gender distribution
    const genderDistribution: Record<string, number> = {};
    patients.forEach(patient => {
      if (patient.gender) {
        genderDistribution[patient.gender] = (genderDistribution[patient.gender] || 0) + 1;
      }
    });

    // Common conditions
    const conditionCounts: Record<string, number> = {};
    patients.forEach(patient => {
      patient.conditions?.forEach(condition => {
        conditionCounts[condition] = (conditionCounts[condition] || 0) + 1;
      });
    });

    const commonConditions = Object.entries(conditionCounts)
      .map(([condition, count]) => ({
        condition,
        count,
        percentage: Math.round((count / totalPatients) * 100 * 100) / 100
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Common medications
    const medicationCounts: Record<string, number> = {};
    patients.forEach(patient => {
      patient.medications?.forEach(medication => {
        medicationCounts[medication] = (medicationCounts[medication] || 0) + 1;
      });
    });

    const commonMedications = Object.entries(medicationCounts)
      .map(([medication, count]) => ({
        medication,
        count,
        percentage: Math.round((count / totalPatients) * 100 * 100) / 100
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    return {
      totalPatients,
      averageAge: Math.round(averageAge * 100) / 100,
      genderDistribution,
      commonConditions,
      commonMedications
    };
  }

  static findPatientsByCriteria(
    user: User,
    patients: PatientData[],
    criteria: {
      minAge?: number;
      maxAge?: number;
      gender?: string;
      conditions?: string[];
      medications?: string[];
    }
  ): PatientData[] | { error: string } {
    
    if (!AccessControlManager.checkAccess(user, 'aggregated') && 
        !AccessControlManager.checkAccess(user, 'individual')) {
      return { error: AccessControlManager.getAccessDeniedMessage(user) };
    }

    let filteredPatients = patients.filter(patient => {
      // Age filter
      if (criteria.minAge !== undefined && patient.age < criteria.minAge) return false;
      if (criteria.maxAge !== undefined && patient.age > criteria.maxAge) return false;
      
      // Gender filter
      if (criteria.gender && patient.gender.toLowerCase() !== criteria.gender.toLowerCase()) return false;
      
      // Conditions filter
      if (criteria.conditions && criteria.conditions.length > 0) {
        const hasAllConditions = criteria.conditions.every(condition =>
          patient.conditions.some(pc => pc.toLowerCase().includes(condition.toLowerCase()))
        );
        if (!hasAllConditions) return false;
      }
      
      // Medications filter
      if (criteria.medications && criteria.medications.length > 0) {
        const hasAllMedications = criteria.medications.every(medication =>
          patient.medications.some(pm => pm.toLowerCase().includes(medication.toLowerCase()))
        );
        if (!hasAllMedications) return false;
      }
      
      return true;
    });

    // Apply access control filtering to each patient
    if (AccessControlManager.checkAccess(user, 'individual')) {
      filteredPatients = filteredPatients
        .map(patient => AccessControlManager.filterPatientData(user, patient))
        .filter(patient => patient !== null) as PatientData[];
    }

    return filteredPatients;
  }
}
