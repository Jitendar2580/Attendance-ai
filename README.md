# AI Attendance & Performance Insights SaaS

FastAPI + Jinja2 + PostgreSQL SaaS app for attendance tracking with AI-generated insight summaries.

## Features
- Session-based authentication with RBAC (`admin`, `manager`, `player`)
- Team and user management
- Attendance tracking with duplicate prevention (`user_id + date`)
- Dashboard metrics and Chart.js visualization
- AI insight generation from recent attendance records
- **🤖 AI Attendance Assistant** - Conversational chatbot for personalized attendance insights
- CSV export and attendance filters
- Alembic migration included

## AI Attendance Assistant

The AI-powered assistant provides personalized attendance insights through natural conversation:

### Key Capabilities:
- **Personal Attendance Analysis** - "Show me my attendance trends"
- **Absence Pattern Recognition** - "Why have I been absent more this month?"
- **Predictive Insights** - "Am I at risk of disciplinary action?"
- **Leave Management** - "Should I request leave for next week?"
- **Policy Guidance** - Answer attendance policy questions
- **Actionable Recommendations** - Suggest improvements and next steps

### Example Conversations:
```
User: "Why was I marked absent last week?"
AI: "Looking at your records from April 8-12...
    - April 8: Marked LEAVE (official leave approved)
    - April 10: ABSENT with no excuse (HIGH RISK)

Action: File an excuse note or review policy."
```

### Technical Implementation:
- **Context-Aware Responses** - Uses user's actual attendance data
- **Conversation History** - Remembers recent exchanges
- **Multi-Provider Support** - Groq (recommended) or OpenAI
- **Fallback Mode** - Works even without AI keys configured
- **Rate Limiting** - Built-in abuse prevention

## Project Structure
```
app/
  main.py
  core/
  models/
  schemas/
  routes/
  services/
  templates/
  static/
```

## Setup
1. Create and activate virtual env.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy environment file:
   `copy .env.example .env`
4. **Configure AI (Optional but Recommended):**
   - Get Groq API key from [groq.com](https://groq.com) (recommended)
   - Or OpenAI API key from [platform.openai.com](https://platform.openai.com)
   - Set `GROQ_API_KEY` or `OPENAI_API_KEY` in `.env`
   - Set `AI_PROVIDER=groq` or `AI_PROVIDER=openai`
5. Run migration:
   `alembic upgrade head`
6. Start app:
   `uvicorn app.main:app --reload`

Open `http://127.0.0.1:8000`.

## Default Admin
- Email: `admin@example.com`
- Password: `Admin@12345`

Change immediately in production.

## AI Configuration

The AI assistant works with or without API keys:

### With AI Keys (Recommended):
- **Groq**: Faster, cheaper, good for conversational AI
- **OpenAI**: More accurate, but slower and more expensive

### Without AI Keys:
- Fallback mode provides basic responses
- Still functional but less personalized

### Environment Variables:
```bash
# AI Provider Configuration
AI_PROVIDER=groq  # or openai
GROQ_API_KEY=your_groq_key_here
OPENAI_API_KEY=your_openai_key_here
AI_MODEL=llama-3.3-70b-versatile  # or gpt-4o-mini
```
