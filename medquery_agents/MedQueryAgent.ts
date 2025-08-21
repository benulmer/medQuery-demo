import { PatientData, User, UserRole } from '../Utils/accessControl.js';
import { PatientSummarizer, PopulationStats, SummaryOptions } from '../Utils/summarizer.js';
import { AIProcessor } from '../Utils/aiProcessor.js';

export interface QueryResult {
  success: boolean;
  data?: any;
  message: string;
  accessLevel: string;
  redactedFields?: string[];
}

export interface QueryContext {
  user: User;
  patients: PatientData[];
}

export class MedQueryAgent {
  private context: QueryContext;
  private aiProcessor?: AIProcessor;
  private useAI: boolean = false;

  constructor(context: QueryContext) {
    this.context = context;
    this.initializeAI();
  }

  private initializeAI(): void {
    // Check if OpenAI is configured
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (apiKey && apiKey !== 'your_openai_api_key_here' && apiKey.trim() !== '') {
      try {
        this.aiProcessor = new AIProcessor({
          apiKey,
          model: process.env.OPENAI_MODEL || 'gpt-4',
          maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '1000'),
          temperature: parseFloat(process.env.OPENAI_TEMPERATURE || '0.1')
        });
        this.useAI = true;
        console.log('🤖 AI Mode: OpenAI integration enabled');
      } catch (error) {
        console.log('⚠️  AI Mode: OpenAI setup failed, falling back to rule-based system');
        this.useAI = false;
      }
    } else {
      console.log('📋 Rule-Based Mode: OpenAI API key not configured');
      this.useAI = false;
    }
  }

  async processQuery(query: string): Promise<QueryResult> {
    try {
      // Use AI if configured, otherwise fall back to rule-based system
      if (this.useAI && this.aiProcessor) {
        return await this.aiProcessor.processQuery(query, this.context.user, this.context.patients);
      } else {
        return await this.processQueryRuleBased(query);
      }
    } catch (error) {
      return {
        success: false,
        message: `Error processing query: ${error instanceof Error ? error.message : 'Unknown error'}`,
        accessLevel: this.context.user.role
      };
    }
  }

  private async processQueryRuleBased(query: string): Promise<QueryResult> {
    try {
      // Parse and categorize the query
      const queryType = this.categorizeQuery(query);
      
      switch (queryType) {
        case 'individual_summary':
          return await this.handleIndividualSummary(query);
        case 'patient_lookup':
          return await this.handlePatientLookup(query);
        case 'population_stats':
          return await this.handlePopulationStats(query);
        case 'criteria_search':
          return await this.handleCriteriaSearch(query);
        case 'medication_query':
          return await this.handleMedicationQuery(query);
        case 'condition_query':
          return await this.handleConditionQuery(query);
        default:
          return await this.handleGeneralQuery(query);
      }
    } catch (error) {
      return {
        success: false,
        message: `Error processing query: ${error instanceof Error ? error.message : 'Unknown error'}`,
        accessLevel: this.context.user.role
      };
    }
  }

  private categorizeQuery(query: string): string {
    const lowerQuery = query.toLowerCase();
    
    // Individual patient queries
    if (lowerQuery.includes('summarize') && (lowerQuery.includes('patient') || lowerQuery.includes('history'))) {
      return 'individual_summary';
    }
    
    if (lowerQuery.includes('patient id') || lowerQuery.includes('medication history')) {
      return 'patient_lookup';
    }
    
    // Population statistics
    if (lowerQuery.includes('percentage') || lowerQuery.includes('average') || 
        lowerQuery.includes('how many') || lowerQuery.includes('statistics')) {
      return 'population_stats';
    }
    
    // Search queries
    if (lowerQuery.includes('find') && lowerQuery.includes('patients')) {
      return 'criteria_search';
    }
    
    // Medication queries
    if (lowerQuery.includes('medication') || lowerQuery.includes('drug') || 
        lowerQuery.includes('prescribed') || lowerQuery.includes('taking')) {
      return 'medication_query';
    }
    
    // Condition queries
    if (lowerQuery.includes('condition') || lowerQuery.includes('diabetes') || 
        lowerQuery.includes('hypertension') || lowerQuery.includes('asthma')) {
      return 'condition_query';
    }
    
    return 'general';
  }

  private async handleIndividualSummary(query: string): Promise<QueryResult> {
    // Extract patient identifier from query
    const patientId = this.extractPatientId(query);
    const patientName = this.extractPatientName(query);
    
    let patient: PatientData | undefined;
    
    if (patientId) {
      patient = this.context.patients.find(p => p.id === patientId);
    } else if (patientName) {
      patient = this.context.patients.find(p => 
        p.name.toLowerCase().includes(patientName.toLowerCase())
      );
    }
    
    if (!patient) {
      return {
        success: false,
        message: "Patient not found. Please check the patient ID or name.",
        accessLevel: this.context.user.role
      };
    }
    
    const summary = PatientSummarizer.summarizeIndividualPatient(
      this.context.user, 
      patient, 
      { includeStatistics: true }
    );
    
    return {
      success: summary.accessLevel !== 'denied',
      data: summary,
      message: summary.summary,
      accessLevel: summary.accessLevel,
      redactedFields: summary.redactedFields
    };
  }

  private async handlePatientLookup(query: string): Promise<QueryResult> {
    const patientId = this.extractPatientId(query);
    
    if (!patientId) {
      return {
        success: false,
        message: "Please specify a patient ID for lookup.",
        accessLevel: this.context.user.role
      };
    }
    
    const patient = this.context.patients.find(p => p.id === patientId);
    
    if (!patient) {
      return {
        success: false,
        message: `Patient with ID ${patientId} not found.`,
        accessLevel: this.context.user.role
      };
    }
    
    return await this.handleIndividualSummary(`Summarize patient ${patient.name}`);
  }

  private async handlePopulationStats(query: string): Promise<QueryResult> {
    const stats = PatientSummarizer.generatePopulationStats(this.context.user, this.context.patients);
    
    if ('error' in stats) {
      return {
        success: false,
        message: stats.error,
        accessLevel: this.context.user.role
      };
    }
    
    let message = this.formatPopulationStats(stats, query);
    
    return {
      success: true,
      data: stats,
      message,
      accessLevel: this.context.user.role
    };
  }

  private async handleCriteriaSearch(query: string): Promise<QueryResult> {
    const criteria = this.extractSearchCriteria(query);
    const results = PatientSummarizer.findPatientsByCriteria(
      this.context.user, 
      this.context.patients, 
      criteria
    );
    
    if ('error' in results) {
      return {
        success: false,
        message: results.error,
        accessLevel: this.context.user.role
      };
    }
    
    let message = `Found ${results.length} patients matching criteria:\n\n`;
    
    if (this.context.user.role === UserRole.MARKETING) {
      // Marketing only gets aggregate info
      message += `Total matches: ${results.length}\n`;
      if (criteria.minAge || criteria.maxAge) {
        message += `Age range: ${criteria.minAge || 0}-${criteria.maxAge || 'any'}\n`;
      }
    } else {
      // Other roles can see individual results
      results.slice(0, 10).forEach((patient, index) => {
        if (patient.name) {
          message += `${index + 1}. ${patient.name} (ID: ${patient.id})\n`;
        } else {
          message += `${index + 1}. Patient ID: ${patient.id}\n`;
        }
      });
      
      if (results.length > 10) {
        message += `... and ${results.length - 10} more patients\n`;
      }
    }
    
    return {
      success: true,
      data: results,
      message,
      accessLevel: this.context.user.role
    };
  }

  private async handleMedicationQuery(query: string): Promise<QueryResult> {
    const medication = this.extractMedication(query);
    
    if (!medication) {
      return {
        success: false,
        message: "Please specify a medication name in your query.",
        accessLevel: this.context.user.role
      };
    }
    
    const patientsOnMedication = this.context.patients.filter(patient =>
      patient.medications.some(med => 
        med.toLowerCase().includes(medication.toLowerCase())
      )
    );
    
    if (this.context.user.role === UserRole.MARKETING) {
      const percentage = Math.round((patientsOnMedication.length / this.context.patients.length) * 100 * 100) / 100;
      return {
        success: true,
        data: { count: patientsOnMedication.length, percentage },
        message: `${percentage}% of patients (${patientsOnMedication.length} out of ${this.context.patients.length}) are prescribed ${medication}.`,
        accessLevel: this.context.user.role
      };
    }
    
    return await this.handleCriteriaSearch(`Find patients taking ${medication}`);
  }

  private async handleConditionQuery(query: string): Promise<QueryResult> {
    const condition = this.extractCondition(query);
    
    if (!condition) {
      return {
        success: false,
        message: "Please specify a medical condition in your query.",
        accessLevel: this.context.user.role
      };
    }
    
    return await this.handleCriteriaSearch(`Find patients with ${condition}`);
  }

  private async handleGeneralQuery(query: string): Promise<QueryResult> {
    // For general queries, provide helpful suggestions based on user role
    const suggestions = this.getRoleSuggestions();
    
    return {
      success: true,
      message: `I can help you with medical queries. Here are some examples of what you can ask:\n\n${suggestions.join('\n')}`,
      accessLevel: this.context.user.role
    };
  }

  private extractPatientId(query: string): string | null {
    const idMatch = query.match(/(?:patient\s+id\s+|id\s+)([A-Z]\d+)/i);
    return idMatch ? idMatch[1] : null;
  }

  private extractPatientName(query: string): string | null {
    // Look for quoted names or common name patterns
    const quotedMatch = query.match(/["'](.*?)["']/);
    if (quotedMatch) return quotedMatch[1];
    
    const nameMatch = query.match(/(?:patient\s+|summarize\s+)([A-Z][a-z]+\s+[A-Z][a-z]+)/i);
    return nameMatch ? nameMatch[1] : null;
  }

  private extractSearchCriteria(query: string): any {
    const criteria: any = {};
    
    // Age extraction
    const ageMatch = query.match(/(\d+)\+|over (\d+)|aged (\d+)/i);
    if (ageMatch) {
      criteria.minAge = parseInt(ageMatch[1] || ageMatch[2] || ageMatch[3]);
    }
    
    const ageRangeMatch = query.match(/(\d+)-(\d+)|between (\d+) and (\d+)/i);
    if (ageRangeMatch) {
      criteria.minAge = parseInt(ageRangeMatch[1] || ageRangeMatch[3]);
      criteria.maxAge = parseInt(ageRangeMatch[2] || ageRangeMatch[4]);
    }
    
    // Condition extraction
    const conditions = ['diabetes', 'hypertension', 'asthma', 'cholesterol'];
    const foundConditions = conditions.filter(condition => 
      query.toLowerCase().includes(condition.toLowerCase())
    );
    if (foundConditions.length > 0) {
      criteria.conditions = foundConditions;
    }
    
    // Medication extraction
    const medications = ['metformin', 'lisinopril', 'albuterol', 'atorvastatin'];
    const foundMedications = medications.filter(medication => 
      query.toLowerCase().includes(medication.toLowerCase())
    );
    if (foundMedications.length > 0) {
      criteria.medications = foundMedications;
    }
    
    return criteria;
  }

  private extractMedication(query: string): string | null {
    const medications = ['metformin', 'lisinopril', 'albuterol', 'atorvastatin'];
    const found = medications.find(med => 
      query.toLowerCase().includes(med.toLowerCase())
    );
    return found || null;
  }

  private extractCondition(query: string): string | null {
    const conditions = ['diabetes', 'hypertension', 'asthma', 'cholesterol'];
    const found = conditions.find(condition => 
      query.toLowerCase().includes(condition.toLowerCase())
    );
    return found || null;
  }

  private formatPopulationStats(stats: PopulationStats, query: string): string {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('average age')) {
      return `The average age of patients is ${stats.averageAge} years.`;
    }
    
    if (lowerQuery.includes('percentage') && lowerQuery.includes('under')) {
      const ageMatch = query.match(/under (\d+)/i);
      if (ageMatch) {
        const ageLimit = parseInt(ageMatch[1]);
        // This would require calculating from the actual data
        return `Population statistics available. Please specify the exact metric you'd like to know.`;
      }
    }
    
    // Default comprehensive stats
    let message = `Population Statistics:\n\n`;
    message += `Total Patients: ${stats.totalPatients}\n`;
    message += `Average Age: ${stats.averageAge} years\n\n`;
    
    message += `Gender Distribution:\n`;
    Object.entries(stats.genderDistribution).forEach(([gender, count]) => {
      const percentage = Math.round((count / stats.totalPatients) * 100);
      message += `- ${gender}: ${count} (${percentage}%)\n`;
    });
    
    message += `\nMost Common Conditions:\n`;
    stats.commonConditions.slice(0, 5).forEach(({ condition, count, percentage }) => {
      message += `- ${condition}: ${count} patients (${percentage}%)\n`;
    });
    
    message += `\nMost Common Medications:\n`;
    stats.commonMedications.slice(0, 5).forEach(({ medication, count, percentage }) => {
      message += `- ${medication}: ${count} patients (${percentage}%)\n`;
    });
    
    return message;
  }

  private getRoleSuggestions(): string[] {
    switch (this.context.user.role) {
      case UserRole.DOCTOR:
        return [
          "• 'Summarize Jane Smith's health history'",
          "• 'What is the medication history of patient ID P001?'",
          "• 'Find patients with Type 2 Diabetes'",
          "• 'Show me all patients taking Metformin'"
        ];
      case UserRole.RESEARCHER:
        return [
          "• 'Find all patients aged 60+ with Type 2 Diabetes'",
          "• 'How many patients with Asthma are currently prescribed Albuterol?'",
          "• 'Show population statistics for hypertension patients'",
          "• 'What's the average age of patients with diabetes?'"
        ];
      case UserRole.MARKETING:
        return [
          "• 'What percentage of patients under 40 are on Metformin?'",
          "• 'What's the average age of patients with mild hypertension?'",
          "• 'How many patients are prescribed Lisinopril?'",
          "• 'Show me population statistics'"
        ];
      case UserRole.INTERN:
        return [
          "• Access to patient data requires supervision",
          "• Please contact your supervisor for assistance",
          "• You can ask general questions about the system"
        ];
      default:
        return ["• Please specify what information you're looking for"];
    }
  }
}
