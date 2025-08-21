#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import chalk from 'chalk';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();
import { MedQueryAgent, QueryContext } from './Agents/MedQueryAgent.js';
import { PatientData, User, UserRole } from './Utils/accessControl.js';

// Demo users for different roles
const DEMO_USERS: User[] = [
  { id: 'doc1', name: 'Dr. Sarah Johnson', role: UserRole.DOCTOR },
  { id: 'res1', name: 'Dr. Michael Chen', role: UserRole.RESEARCHER },
  { id: 'mar1', name: 'Alice Thompson', role: UserRole.MARKETING },
  { id: 'int1', name: 'David Wilson', role: UserRole.INTERN }
];

class MedQueryApp {
  private patients: PatientData[] = [];
  private currentUser: User | null = null;
  private agent: MedQueryAgent | null = null;
  private rl = createInterface({
    input: process.stdin,
    output: process.stdout
  });

  constructor() {
    this.loadPatientData();
  }

  private loadPatientData(): void {
    try {
      // Get the directory of the current module (dist/main.js)
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = dirname(__filename);
      // Go up one level from dist to project root, then into Data folder
      const dataPath = join(__dirname, '..', 'Data', 'mock_patient_data.json');
      
      const data = readFileSync(dataPath, 'utf-8');
      this.patients = JSON.parse(data);
      console.log(chalk.green(`✅ Loaded ${this.patients.length} patient records`));
    } catch (error) {
      console.error(chalk.red('❌ Error loading patient data:'), error);
      process.exit(1);
    }
  }

  private displayWelcome(): void {
    console.clear();
    console.log(chalk.blue.bold('\n🏥 Welcome to MedQuery AI'));
    console.log(chalk.blue('   VitaSense Health Solutions\n'));
    console.log(chalk.gray('An intelligent healthcare data assistant with role-based access control\n'));
  }

  private displayUserMenu(): void {
    console.log(chalk.yellow.bold('Available Users (Demo):'));
    DEMO_USERS.forEach((user, index) => {
      const roleColor = this.getRoleColor(user.role);
      console.log(chalk.white(`${index + 1}. ${user.name} `) + roleColor(`(${user.role})`));
    });
    console.log(chalk.white('5. Exit\n'));
  }

  private getRoleColor(role: UserRole): (text: string) => string {
    switch (role) {
      case UserRole.DOCTOR: return chalk.green;
      case UserRole.RESEARCHER: return chalk.blue;
      case UserRole.MARKETING: return chalk.magenta;
      case UserRole.INTERN: return chalk.red;
      default: return chalk.gray;
    }
  }

  private async selectUser(): Promise<User | null> {
    return new Promise((resolve) => {
      this.rl.question(chalk.cyan('Select a user (1-5): '), (answer: string) => {
        const choice = parseInt(answer);
        if (choice >= 1 && choice <= 4) {
          resolve(DEMO_USERS[choice - 1]);
        } else if (choice === 5) {
          resolve(null);
        } else {
          console.log(chalk.red('Invalid choice. Please try again.\n'));
          resolve(this.selectUser());
        }
      });
    });
  }

  private displayUserInfo(user: User): void {
    const roleColor = this.getRoleColor(user.role);
    console.log(chalk.white('\n👤 Current User: ') + chalk.bold(user.name));
    console.log(chalk.white('🔒 Role: ') + roleColor(user.role));
    console.log(chalk.gray('━'.repeat(50)));
  }

  private displayPermissions(user: User): void {
    console.log(chalk.yellow('\n📋 Your Permissions:'));
    
    switch (user.role) {
      case UserRole.DOCTOR:
        console.log(chalk.green('✅ Full access to all patient fields'));
        console.log(chalk.green('✅ Can view individual patient records'));
        console.log(chalk.green('✅ Can view identifying information'));
        console.log(chalk.green('✅ Can access aggregated statistics'));
        break;
      case UserRole.RESEARCHER:
        console.log(chalk.green('✅ Access to de-identified patient records'));
        console.log(chalk.red('❌ Cannot view names or addresses'));
        console.log(chalk.green('✅ Can view individual records (anonymized)'));
        console.log(chalk.green('✅ Can access aggregated statistics'));
        break;
      case UserRole.MARKETING:
        console.log(chalk.red('❌ Cannot view individual patient records'));
        console.log(chalk.red('❌ Cannot view identifying information'));
        console.log(chalk.green('✅ Can access aggregated statistics only'));
        break;
      case UserRole.INTERN:
        console.log(chalk.red('❌ No direct patient data access'));
        console.log(chalk.red('❌ Requires supervision for any queries'));
        break;
    }
    console.log(chalk.gray('━'.repeat(50)));
  }

  private displayExamples(user: User): void {
    console.log(chalk.yellow('\n💡 Example Queries:'));
    
    const examples = this.getExamplesForRole(user.role);
    examples.forEach(example => {
      console.log(chalk.white('  • ') + chalk.cyan(`"${example}"`));
    });
    console.log(chalk.gray('━'.repeat(50)));
  }

  private getExamplesForRole(role: UserRole): string[] {
    switch (role) {
      case UserRole.DOCTOR:
        return [
          "Summarize Jane Smith's health history",
          "What is the medication history of patient ID P001?",
          "Find patients with Type 2 Diabetes",
          "Show me all patients taking Metformin"
        ];
      case UserRole.RESEARCHER:
        return [
          "Find all patients aged 60+ with Type 2 Diabetes",
          "How many patients with Asthma are currently prescribed Albuterol?",
          "Show population statistics",
          "What's the average age of patients with diabetes?"
        ];
      case UserRole.MARKETING:
        return [
          "What percentage of patients under 40 are on Metformin?",
          "What's the average age of patients with mild hypertension?",
          "How many patients are prescribed Lisinopril?",
          "Show me population statistics"
        ];
      case UserRole.INTERN:
        return [
          "What can I do with this system?",
          "How does access control work?",
          "What are the different user roles?"
        ];
      default:
        return [];
    }
  }

  private async chatWithAgent(user: User): Promise<void> {
    const context: QueryContext = {
      user,
      patients: this.patients
    };
    
    this.agent = new MedQueryAgent(context);
    
    console.log(chalk.green('\n🤖 MedQuery AI is ready! Type your questions below.'));
    console.log(chalk.gray('Type "exit" to return to user selection, "help" for examples\n'));

    return new Promise((resolve) => {
      const askQuestion = () => {
        this.rl.question(chalk.cyan('❓ Your query: '), async (query: string) => {
          if (query.toLowerCase() === 'exit') {
            console.log(chalk.yellow('👋 Returning to user selection...\n'));
            this.currentUser = null;
            this.agent = null;
            resolve();
            return;
          }
          
          if (query.toLowerCase() === 'help') {
            this.displayExamples(user);
            askQuestion();
            return;
          }
          
          if (query.trim() === '') {
            askQuestion();
            return;
          }

          console.log(chalk.gray('\n🔍 Processing your query...\n'));
          
          try {
            const result = await this.agent!.processQuery(query);
            
            if (result.success) {
              console.log(chalk.green('✅ Query Result:\n'));
              console.log(chalk.white(result.message));
              
              if (result.redactedFields && result.redactedFields.length > 0) {
                console.log(chalk.yellow('\n🔒 Redacted fields: ') + 
                           chalk.red(result.redactedFields.join(', ')));
              }
            } else {
              console.log(chalk.red('❌ ') + chalk.white(result.message));
            }
            
            console.log(chalk.gray(`\n🏷️  Access Level: ${result.accessLevel}`));
            console.log(chalk.gray('━'.repeat(50)));
            
          } catch (error) {
            console.log(chalk.red('❌ Error processing query:'), error);
          }
          
          console.log(); // Add spacing
          askQuestion();
        });
      };

      askQuestion();
    });
  }

  async run(): Promise<void> {
    this.displayWelcome();
    
    while (true) {
      if (!this.currentUser) {
        this.displayUserMenu();
        const selectedUser = await this.selectUser();
        
        if (!selectedUser) {
          console.log(chalk.yellow('\n👋 Thank you for using MedQuery AI!'));
          this.rl.close();
          break;
        }
        
        this.currentUser = selectedUser;
        this.displayUserInfo(this.currentUser);
        this.displayPermissions(this.currentUser);
        this.displayExamples(this.currentUser);
      }
      
      await this.chatWithAgent(this.currentUser);
    }
  }
}

// Error handling
process.on('uncaughtException', (error: Error) => {
  console.error(chalk.red('\n❌ Uncaught Exception:'), error);
  process.exit(1);
});

process.on('unhandledRejection', (reason: any, promise: Promise<any>) => {
  console.error(chalk.red('\n❌ Unhandled Rejection at:'), promise, chalk.red('reason:'), reason);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log(chalk.yellow('\n\n👋 Goodbye! Thank you for using MedQuery AI.'));
  process.exit(0);
});

// Start the application
console.log(chalk.blue('🚀 Starting MedQuery AI...\n'));

const app = new MedQueryApp();
app.run().catch(error => {
  console.error(chalk.red('❌ Application error:'), error);
  process.exit(1);
});
