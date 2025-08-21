import OpenAI from 'openai';
import { PatientData, User, UserRole } from './accessControl.js';
import { QueryResult } from '../Agents/MedQueryAgent.js';

export interface AIConfig {
  apiKey: string;
  model?: string;
  maxTokens?: number;
  temperature?: number;
}

export class AIProcessor {
  private openai: OpenAI;
  private config: AIConfig;

  constructor(config: AIConfig) {
    this.config = {
      model: 'gpt-4',
      maxTokens: 1000,
      temperature: 0.1,
      ...config
    };

    this.openai = new OpenAI({
      apiKey: this.config.apiKey,
    });
  }

  async processQuery(
    query: string, 
    user: User, 
    patients: PatientData[]
  ): Promise<QueryResult> {
    try {
      const systemPrompt = this.buildSystemPrompt(user, patients);
      const userPrompt = this.buildUserPrompt(query, user);

      const response = await this.openai.chat.completions.create({
        model: this.config.model!,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        max_tokens: this.config.maxTokens,
        temperature: this.config.temperature,
      });

      const aiResponse = response.choices[0]?.message?.content || "I couldn't process your request.";
      
      return {
        success: true,
        message: aiResponse,
        accessLevel: user.role,
        data: null
      };

    } catch (error) {
      console.error('OpenAI API Error:', error);
      
      // Fallback to rule-based system if AI fails
      return {
        success: false,
        message: `AI service temporarily unavailable. Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        accessLevel: user.role
      };
    }
  }

  private buildSystemPrompt(user: User, patients: PatientData[]): string {
    const rolePermissions = this.getRolePermissions(user.role);
    const filteredPatients = this.filterPatientsForRole(patients, user);

    return `You are MedQuery AI, an intelligent healthcare assistant for VitaSense Health Solutions.

CRITICAL SECURITY RULES:
- You are responding to a ${user.role} named ${user.name}
- NEVER provide data that exceeds the user's role permissions
- ALWAYS respect the access control restrictions
- If asked for unauthorized data, politely deny and explain the restriction

USER ROLE: ${user.role}
PERMISSIONS: ${rolePermissions}

AVAILABLE PATIENT DATA:
${JSON.stringify(filteredPatients, null, 2)}

RESPONSE GUIDELINES:
1. Be professional and healthcare-focused
2. Provide accurate information based on available data
3. Use clear, medical terminology appropriate for the user's role
4. If data is filtered/redacted, explain what information is hidden and why
5. For population queries, provide statistics and insights
6. For individual queries, provide comprehensive summaries within permission limits

REMEMBER: You can only work with the patient data provided above. Do not make up or assume information not present in the data.`;
  }

  private buildUserPrompt(query: string, user: User): string {
    return `User Query: "${query}"

Please provide a helpful response based on the available patient data and my role permissions as a ${user.role}.`;
  }

  private getRolePermissions(role: UserRole): string {
    switch (role) {
      case UserRole.DOCTOR:
        return "FULL ACCESS - Can view all patient fields including names, addresses, and complete medical records";
      case UserRole.RESEARCHER:
        return "DE-IDENTIFIED ACCESS - Can view medical data but NOT names or addresses (anonymized patient IDs only)";
      case UserRole.MARKETING:
        return "AGGREGATE DATA ONLY - Can only view population statistics, percentages, and aggregate metrics. NO individual patient records";
      case UserRole.INTERN:
        return "NO DIRECT ACCESS - Requires supervision for any patient data queries. Can only get general information about the system";
      default:
        return "NO ACCESS";
    }
  }

  private filterPatientsForRole(patients: PatientData[], user: User): any[] {
    switch (user.role) {
      case UserRole.DOCTOR:
        // Doctors get full access
        return patients;
        
      case UserRole.RESEARCHER:
        // Researchers get de-identified data
        return patients.map(patient => ({
          id: `ANON_${patient.id}`,
          age: patient.age,
          gender: patient.gender,
          conditions: patient.conditions,
          medications: patient.medications,
          notes: patient.notes,
          visit_dates: patient.visit_dates
        }));
        
      case UserRole.MARKETING:
        // Marketing gets only aggregate stats structure (AI will generate stats)
        return [{
          summary: `${patients.length} total patients`,
          note: "Only aggregate statistics available for marketing role"
        }];
        
      case UserRole.INTERN:
        // Interns get no patient data
        return [{
          message: "No patient data available - requires supervision"
        }];
        
      default:
        return [];
    }
  }

  static isConfigured(): boolean {
    return process.env.OPENAI_API_KEY !== undefined && 
           process.env.OPENAI_API_KEY !== '' &&
           process.env.OPENAI_API_KEY !== 'your_openai_api_key_here';
  }
}