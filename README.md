# 🏥 MedQuery AI for VitaSense Health Solutions

An intelligent healthcare data assistant with comprehensive role-based access control, designed to help healthcare teams extract insights from patient data safely and efficiently.

## 🚀 Features

### 🔐 Role-Based Access Control
- **Doctor**: Full access to all patient fields including identifying information
- **Researcher**: De-identified patient records (no names/addresses) for population studies  
- **Marketing**: Aggregated statistics only, no individual patient data
- **Intern**: No direct patient access, requires supervision

### 🧠 Intelligent Query Processing
- Natural language patient queries
- Individual patient summaries with field filtering
- Population statistics and trends
- Criteria-based patient search
- Medication and condition analysis

### 🛡️ Security & Compliance
- Automatic field redaction based on user role
- Audit trail of all queries and access levels
- Data sanitization for different permission levels
- Comprehensive access denied messaging

## 📁 Project Structure

```
Demo 1/
├── Agents/
│   └── MedQueryAgent.ts      # Main AI agent with query processing
├── Data/
│   └── mock_patient_data.json # Sample patient records
├── Utils/
│   ├── accessControl.ts      # Role-based permissions system
│   └── summarizer.ts         # Patient data summarization
├── main.ts                   # Interactive CLI application
├── package.json              # Dependencies and scripts
└── tsconfig.json            # TypeScript configuration
```

## 🏃‍♂️ Quick Start

### Prerequisites
- Node.js 18.0.0 or higher
- npm or yarn

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd "Demo 1"
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build the project:**
   ```bash
   npm run build
   ```

4. **Start the application:**
   ```bash
   npm start
   ```

### Development Mode
```bash
# Watch for changes and rebuild automatically
npm run watch

# Run in development mode
npm run dev
```

## 🎯 Usage Examples

### Doctor Queries
```
"Summarize Jane Smith's health history"
"What is the medication history of patient ID P001?"
"Find patients with Type 2 Diabetes"
"Show me all patients taking Metformin"
```

### Researcher Queries  
```
"Find all patients aged 60+ with Type 2 Diabetes"
"How many patients with Asthma are currently prescribed Albuterol?"
"Show population statistics for hypertension patients"
"What's the average age of patients with diabetes?"
```

### Marketing Queries
```
"What percentage of patients under 40 are on Metformin?"
"What's the average age of patients with mild hypertension?"
"How many patients are prescribed Lisinopril?"
"Show me population statistics"
```

### Intern Queries
```
"What can I do with this system?" 
"How does access control work?"
# Most patient queries will be denied with supervision message
```

## 🔒 Access Control Matrix

| Role | Individual Records | Identifying Info | Aggregated Stats | Fields Available |
|------|-------------------|------------------|------------------|------------------|
| **Doctor** | ✅ Full Access | ✅ Names, Addresses | ✅ All Statistics | All fields |
| **Researcher** | ✅ Anonymized | ❌ No Names/Addresses | ✅ All Statistics | ID*, age, gender, conditions, medications, notes, visits |
| **Marketing** | ❌ Denied | ❌ Denied | ✅ Aggregated Only | age, gender, conditions, medications (stats only) |
| **Intern** | ❌ Denied | ❌ Denied | ❌ Denied | None - requires supervision |

*Researcher IDs are anonymized (e.g., P001 → ANON_P001)

## 🏗️ Architecture

### Core Components

1. **AccessControlManager** (`Utils/accessControl.ts`)
   - Defines user roles and permissions
   - Filters patient data based on role
   - Provides access denied messaging

2. **PatientSummarizer** (`Utils/summarizer.ts`)
   - Generates role-appropriate patient summaries
   - Calculates population statistics
   - Handles criteria-based patient search

3. **MedQueryAgent** (`Agents/MedQueryAgent.ts`)
   - Processes natural language queries
   - Routes queries to appropriate handlers
   - Formats responses based on user permissions

4. **Main Application** (`main.ts`)
   - Interactive CLI interface
   - User selection and authentication
   - Query processing loop

### Data Flow

```
User Query → MedQueryAgent → AccessControlManager → PatientSummarizer → Filtered Response
```

## 🔧 Configuration

### Adding New User Roles

1. Add role to `UserRole` enum in `accessControl.ts`
2. Define permissions in `rolePermissions` object
3. Add role-specific examples in `MedQueryAgent.ts`
4. Update demo users in `main.ts`

### Extending Patient Data Fields

1. Update `PatientData` interface in `accessControl.ts`
2. Modify field filtering logic in `AccessControlManager`
3. Update summarization logic in `PatientSummarizer`
4. Add sample data to `mock_patient_data.json`

## 🚧 Future Enhancements (Trust3 Integration)

When integrated with Trust3, MedQuery AI will include:

- **Enhanced Security**: Prompt injection prevention and output validation
- **Audit Trail**: Complete lineage tracking of all AI interactions  
- **Response Validation**: Automatic accuracy checking and sanitization
- **Compliance Reporting**: HIPAA and healthcare regulation compliance
- **Advanced Redaction**: ML-powered sensitive data detection

## 🧪 Testing

```bash
# Run tests (when implemented)
npm test

# Lint code
npm run lint
```

## 📝 Sample Data

The system includes 3 sample patients:
- **Jane Smith** (67F): Type 2 Diabetes, Hypertension
- **David Chen** (42M): Asthma  
- **Maria Lopez** (58F): High Cholesterol

## 🤝 Contributing

1. Follow TypeScript best practices
2. Maintain role-based access control integrity
3. Add comprehensive error handling
4. Update documentation for new features

## 📄 License

MIT License - See LICENSE file for details

---

**VitaSense Health Solutions** - Making patient data more actionable while ensuring the highest levels of privacy and security.