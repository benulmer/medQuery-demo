# MedQuery AI for VitaSense Health Solutions (Python Version)

🏥 **Intelligent healthcare data assistant with role-based access control**

## Features

✅ **Role-Based Access Control** - Doctor, Researcher, Marketing, Intern roles  
✅ **AI-Powered Queries** - Natural language processing with OpenAI  
✅ **Rule-Based Fallback** - Works without AI when API unavailable  
✅ **Patient Data Security** - Automatic data filtering by user permissions  
✅ **Rich CLI Interface** - Beautiful terminal interface with colors and tables  
✅ **Python Type Safety** - Full type hints with dataclasses and Pydantic  

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure OpenAI (Optional)

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 3. Run the Application

```bash
python main.py
```

## Project Structure

```
📁 MedQuery AI (Python)
├── 📄 main.py                    # Main CLI application
├── 📄 requirements.txt           # Python dependencies
├── 📁 agents/
│   └── 📄 medquery_agent.py     # Main query processing logic
├── 📁 utils/
│   ├── 📄 access_control.py     # Role-based access control
│   ├── 📄 summarizer.py         # Patient data summarization
│   └── 📄 ai_processor.py       # OpenAI integration
├── 📁 data/
│   └── 📄 mock_patient_data.json # Demo patient data
├── 📄 .env.example              # Environment template
└── 📄 README_Python.md          # This file
```

## User Roles & Permissions

| Role | Individual Records | Identifying Info | Aggregate Stats | Notes |
|------|-------------------|------------------|----------------|-------|
| **Doctor** | ✅ Full Access | ✅ Names, Addresses | ✅ All Statistics | Complete patient access |
| **Researcher** | ✅ De-identified | ❌ [REDACTED] | ✅ All Statistics | Research-focused access |
| **Marketing** | ❌ Denied | ❌ [REDACTED] | ✅ Aggregate Only | Population-level insights |
| **Intern** | ❌ Denied | ❌ [REDACTED] | ❌ Denied | Requires supervision |

## Example Queries by Role

### Doctor Queries
- "Summarize Jane Smith's health history"
- "What is the medication history of patient ID P001?"
- "Find patients with Type 2 Diabetes"

### Researcher Queries
- "Find all patients aged 60+ with Type 2 Diabetes"
- "What's the average age of patients with Hypertension?"
- "Show demographics of patients taking Lisinopril"

### Marketing Queries
- "What percentage of patients under 40 are on Metformin?"
- "What's the average age of patients with mild hypertension?"
- "Show patient age distribution"

### Intern Queries
- "What can I do with this system?"
- "How does access control work?"
- "What are the different user roles?"

## AI Integration

The system supports two modes:

### 🤖 AI Mode (with OpenAI API)
- Natural language query processing
- Intelligent response generation
- Context-aware role-based filtering
- Requires OpenAI API key

### 📋 Rule-Based Mode (without AI)
- Pattern-matching query processing
- Pre-defined response templates
- Works offline
- No API key required

## Technology Stack

- **Python 3.8+** - Modern Python with async/await
- **Rich** - Beautiful terminal interface
- **Colorama** - Cross-platform colored output
- **OpenAI** - AI integration (optional)
- **Pydantic** - Data validation and typing
- **Python-dotenv** - Environment variable management

## Security Features

- **Access Control Lists** - Granular permission system
- **Data Redaction** - Automatic PII filtering
- **Role Verification** - All queries checked against user permissions
- **Audit Trail** - All access attempts logged with user context
- **Graceful Degradation** - System works even when AI is unavailable

## Development

### Type Checking
```bash
pip install mypy
mypy main.py utils/ agents/
```

### Code Formatting
```bash
pip install black
black main.py utils/ agents/
```

### Testing
```bash
pip install pytest
pytest tests/
```

## Future Enhancements

- **Trust3 Integration** - Enhanced security and audit trails
- **Web Interface** - React/FastAPI web application
- **Database Integration** - PostgreSQL/MongoDB support
- **Advanced Analytics** - ML-powered insights
- **FHIR Compliance** - Healthcare interoperability standards

## License

MIT License - VitaSense Health Solutions