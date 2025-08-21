# 🤖 AI Integration Setup Guide

## Overview
MedQuery AI now supports both **Rule-Based** and **AI-Powered** modes:

- **📋 Rule-Based Mode**: Pattern matching and keyword detection (no API key required)
- **🤖 AI-Powered Mode**: OpenAI GPT-4 integration with intelligent responses

## 🚀 Quick Setup

### Step 1: Get OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-...`)

### Step 2: Configure Environment
Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file with your API key
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.1
```

### Step 3: Test the Integration
```bash
npm start
```

Look for this message when starting:
- ✅ `🤖 AI Mode: OpenAI integration enabled` - AI is working!
- ⚠️ `📋 Rule-Based Mode: OpenAI API key not configured` - Fallback mode

## 🔍 How It Works

### AI Mode Features
- **Natural Language Understanding**: Understands complex medical queries
- **Role-Aware Responses**: AI respects access control automatically
- **Intelligent Summarization**: GPT-4 provides detailed patient insights
- **Context-Aware**: Understands medical terminology and healthcare workflows

### Security & Access Control
The AI system maintains all security features:

| Role | AI Access |
|------|-----------|
| **Doctor** | Full patient data + AI insights |
| **Researcher** | De-identified data + AI analysis |
| **Marketing** | Aggregate stats + AI summaries |
| **Intern** | Access denied + AI explanation |

### Example AI vs Rule-Based Responses

**Query**: "What medications might help patients with diabetes?"

**Rule-Based Response**: "I can help you with medical queries. Here are some examples..."

**AI Response**: "Based on the patient data available, I can see that Metformin is currently prescribed for patients with Type 2 Diabetes in our system. For patients with diabetes, common medication categories include..."

## 🛠️ Configuration Options

### Environment Variables
```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (with defaults)
OPENAI_MODEL=gpt-4                 # or gpt-3.5-turbo for faster/cheaper
OPENAI_MAX_TOKENS=1000            # Response length limit
OPENAI_TEMPERATURE=0.1            # Creativity (0.0-1.0, lower = more focused)
```

### Model Recommendations
- **gpt-4**: Best accuracy, slower, more expensive
- **gpt-3.5-turbo**: Faster, cheaper, good for basic queries
- **gpt-4-turbo**: Balance of speed and accuracy

## 💰 Cost Estimation

Approximate costs per query:
- **GPT-4**: ~$0.03 per query
- **GPT-3.5-Turbo**: ~$0.001 per query

For a demo with 100 queries:
- **GPT-4**: ~$3.00
- **GPT-3.5-Turbo**: ~$0.10

## 🔧 Troubleshooting

### "AI service temporarily unavailable"
- Check your OpenAI API key is correct
- Verify you have OpenAI credits/billing setup
- Check internet connection

### "Rule-Based Mode" when you expect AI
- Verify `.env` file exists and has correct API key
- Make sure API key starts with `sk-`
- Restart the application after changing `.env`

### API Rate Limits
- OpenAI has rate limits per minute/day
- The system will show specific error messages
- Consider upgrading your OpenAI plan if needed

## 🎯 Testing Different Modes

### Test Rule-Based Mode
1. Remove or rename `.env` file
2. Start application
3. Should see "📋 Rule-Based Mode" message

### Test AI Mode
1. Add valid `.env` file with API key
2. Start application  
3. Should see "🤖 AI Mode: OpenAI integration enabled"

## 🔐 Security Notes

- **Never commit** `.env` files to version control
- API keys are **automatically filtered** from logs
- AI responses respect **role-based access control**
- Patient data is **filtered before** sending to OpenAI API
- All API calls are **logged for audit purposes**

## 🚀 Next Steps

1. **Set up your API key** following Step 1-2 above
2. **Test with different user roles** to see access control in action
3. **Try complex queries** to see AI intelligence vs rule-based responses
4. **Monitor costs** on your OpenAI dashboard

The system works great in both modes - AI just makes it smarter! 🧠