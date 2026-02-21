# Neuro-Fabric 🧠

Neuro-Fabric is a local-first, interactive **Data Dictionary and Analytics Dashboard**. It connects directly to your SQL databases (like PostgreSQL, Supabase) or local DuckDB files, dynamically inspects your schema, and surfaces analytics, real-time data quality monitoring, and an AI-powered data assistant.

The project features a sleek, Shadcn-inspired UI built with React and Tailwind CSS, backed by a robust and extensible FastAPI Python application.

## 🚀 Features
- **Dynamic Dashboard:** Instantly tracks table row counts, storage size, delivery stats, and revenue metrics.
- **Intelligent Schema Browser:** Visually explore tables, columns, constraints, foreign keys, and sample data.
- **AI Data Quality Matrix:** Real-time computation of table completeness and column-by-column null rates.
- **AI-Powered Documentation:** One-click automated data dictionary generation with business insights and query suggestions using Gemini.
- **SQL Editor:** Run raw SQL queries against your database right from the UI with robust error handling.
- **Conversational Chat:** A persistent, threaded natural-language Chat AI (LLM) that understands your schema and writes data-extraction SQL for you.

---

## 🏗️ Project Structure
```text
Neuro-Fabric/
├── neuro-fabric/             # ⚛️ The Modern Frontend
│   ├── src/
│   │   ├── App.jsx           # Main React component (Dashboard, Quality, chat, etc.)
│   │   └── index.css         # Styling system (Shadcn-inspired CSS variables, Layout Grids)
│   ├── package.json          # Vite / React dependencies
│   └── vite.config.js        # Vite bundler configuration
│
├── server.py                 # 🐍 The FastAPI Backend
│                             # Serves the /api endpoints for SQL parsing, DB inspection, and LLM orchestration
│
├── core/                     # Backend core modules
│   ├── db_connectors.py      # SQLAlchemy/DuckDB abstraction layer for query execution
│   └── ai_agents.py          # Definitions for the Gemini LLM interactions
│
├── tools/                    # Tool definitions provided to the AI Agents
│   ├── schema_tools.py       # Let the AI inspect tables and keys
│   └── sql_tools.py          # Let the AI execute raw queries securely
│
├── scripts/                  # Helpful automation scripts (e.g., loading Supabase tables)
├── .env                      # Connection strings and API keys (ignored by git)
└── app.py                    # (Deprecated) Legacy Streamlit frontend version
```

---

## 🛠️ Setup Instructions

To get the application up and running locally, you need to start **both** the Python backend and the React frontend.

### 1. Configure your Environment Variables
In the root directory of the project, create or modify the `.env` file with your database URI and API keys:

```env
# Example .env file
DATABASE_URL=postgresql://user:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
GOOGLE_API_KEY=AIzaSy...your...gemini...key
```

### 2. Start the Backend (FastAPI)
The Python backend handles the database connections and powers the AI Chat. **You must activate your virtual environment first.**

```bash
# 1. Activate the Python virtual environment
source .venv/bin/activate

# 2. Install the required backend dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary google-generativeai

# 3. Start the server on http://localhost:8000
uvicorn server:app --reload
```

### 3. Start the Frontend (Vite + React)
Open a new terminal window to start the frontend interface.
```bash
# Navigate to the frontend directory
cd neuro-fabric

# Install Node dependencies (React, Lucide-React, Radix UI, etc.)
npm install

# Start the Vite development server
npm run dev
```

The application will now be running at `http://localhost:5173` (or `5174`). Click on the "Settings" tab in the app to visually verify your database connection string and model pipeline status!