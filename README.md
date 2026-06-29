# 🍛 NutriAI — Indian Non-Veg Meal Planner

## what needs to be done

Need a fresh Gemini api key, and to be added in a new ".env" file and saved in same folder as the rest.

---

## What it does

NutriAI is a multi-agent AI system that generates personalised 7-day Indian
non-vegetarian meal plans complete with authentic recipes (via Google Search),
nutritional analysis (ICMR 2020 standards), a categorised grocery list, and
an INR budget estimate — all through a clean Gradio web interface.

---

## Multi-Agent Architecture

```
User Input
    │
    ▼
NutriAIOrchestrator  (Google ADK SequentialAgent)
    │
    ├─ 1. MealPlannerAgent       FunctionTool: lookup_nutrition
    │       7-day meal plan with calorie estimates
    │
    ├─ 2. RecipeFinderAgent      Tool: google_search (live grounding)
    │       Authentic recipes from real web sources
    │
    ├─ 3. NutritionTrackerAgent  FunctionTools: lookup_nutrition, calc_weekly_calories
    │       Weekly macro table vs ICMR 2020 RDA
    │
    └─ 4. SummaryAgent           FunctionTool: build_grocery_list
            Grocery list + INR budget + meal prep tips

QuickQueryAgent  (standalone LlmAgent)
    Tools: lookup_nutrition, google_search

MCP Nutrition Server  (stdio, mcp_server.py)
    4 tools: get_nutrition_info · get_daily_nutrition_summary
             list_available_dishes · get_dishes_by_type
    Database: 17 Indian non-veg dishes, ICMR 2020 values
```

---

## Quickstart

### 1. Get your API key
Free from [Google AI Studio](https://aistudio.google.com/app/apikey) — the same
key used in the Kaggle course codelabs.

### 2. Clone and configure
```bash
git clone <your-repo>
cd nutri_ai
cp .env.example .env
# Open .env and paste your key:
#   GOOGLE_API_KEY=AIzaSy...
```

### 3. Install and run
```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:7860** in your browser.

---

## File Structure

```
nutri_ai/
├── app.py               Gradio UI (5 tabs)
├── agents.py            All 5 ADK agents
├── runner.py            Async runner + session management
├── tools.py             FunctionTools (nutrition, calories, grocery)
├── nutrition_data.py    17-dish Indian non-veg nutrition database
├── mcp_server.py        MCP server (stdio transport)
├── config.py            Centralised config + .env loading
├── requirements.txt
├── .env.example         API key template
├── .gitignore           Keeps .env out of git
└── README.md
```

---

## Tabs

| Tab | Agent(s) | What you get |
|-----|----------|--------------|
| 🗓️ 7-Day Meal Plan | All 4 via Orchestrator | Full plan + recipes + nutrition + grocery list |
| 🔍 Recipe Finder | RecipeFinderAgent | Step-by-step recipe from Google Search |
| 🥗 Nutrition Checker | NutritionTrackerAgent | Macros/micros vs ICMR RDA |
| 💬 Quick Ask | QuickQueryAgent | Free-form nutrition & cooking Q&A |
| ℹ️ About | — | Architecture diagram and tech stack |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent framework | Google ADK 2.3 |
| LLM | Gemini 2.0 Flash |
| Recipe discovery | Google Search grounding |
| Nutrition data | MCP server (stdio) + FunctionTools |
| Web UI | Gradio 4+ |
| API key security | python-dotenv |

---

## Cuisine Coverage

North Indian (Butter Chicken, Tandoori, Keema Matar, Korma) ·
Mughlai (Rogan Josh) · Kashmiri · South Indian (Chettinad) ·
Coastal (Goan Fish, Prawn Masala) · Hyderabadi (Biryani) · Pan-Indian (Egg dishes)

---

## Nutrition Standard

All analysis uses **ICMR 2020** recommendations for sedentary adult Indians:
2000 kcal · 60 g protein · 270 g carbs · 67 g fat · 30 g fiber · 17 mg iron · 1000 mg calcium

---

*MIT License · Made for the Kaggle 5-Day AI Agents Intensive · 2026*
