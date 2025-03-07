
# Cricket Analytics Multi-Agent System

A sophisticated cricket analytics system that uses multiple AI agents to process natural language queries about cricket statistics and generate detailed insights. The system leverages LangChain, LangSmith, and advanced language models to provide accurate cricket statistics and analysis.  

## 🌟 Features

- Natural language query processing for cricket statistics
- Multi-agent architecture for specialized tasks


## 🏗 Architecture  

![Architecture](./image.png)  


### Setup
backend
cd C:\Users\adith\Documents\Projects\python-projects\csql-agent
.\venv\scripts\activate
uvicorn backend.app.main:app --reload

frontend
cd chatbot
npm run dev


### Agents
1. **Supervisor Agent**
   - Central orchestrator
   - Routes queries between specialized agents
   - Makes intelligent routing decisions using LLM

2. **Search Agent**
   - Entity recognition
   - Player/team/venue identification
   - Context resolution

3. **SQL Agent**
   - SQL query generation
   - Query execution
   - Results formatting
4. **Viz Agent**
- Visualisation generation

5. **Chatbot Agent**
   - Conversation management
   - Query clarification
   - User interaction

## 🛠 Technical Stack

- **Language**: Python 3.12+
- **Framework**: LangChain,Lanagraph
- **Database**: Bigquery-SQL (with custom cricket statistics schema)
- **LLM**: Google Gemini 2.0 Flash
- **Evaluation**: LangSmith
- **Additional Libraries**:
  - langchain_core
  - langgraph
  - pydantic
  - dotenv
  - rich (for console output)

## 📦 Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd cricket-analytics-system
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configurations
```

## 🙏 Acknowledgments  

-Himanish Ganjoo for providing ball by ball dataset (https://x.com/hganjoo_153)



