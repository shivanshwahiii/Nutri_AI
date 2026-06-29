"""
nutri_ai/agents.py
───────────────────
All NutriAI agents built with Google ADK.

Uses a custom Gemini subclass to pass the AQ. key via
X-goog-api-key header — exactly like the cURL quickstart.
"""

import os
from functools import cached_property

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.genai import Client, types as genai_types

from config import GEMINI_MODEL, CUISINE, GOOGLE_API_KEY
from tools import nutrition_tool, calories_tool, grocery_tool


# ── Custom Gemini client that uses X-goog-api-key header (for AQ. tokens) ────
class _GeminiWithHeader(Gemini):
    """Passes the API key as X-goog-api-key header — supports AQ. format keys."""

    @cached_property
    def api_client(self) -> Client:
        return Client(
            api_key=GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(
                headers={"X-goog-api-key": GOOGLE_API_KEY}
            ),
        )


def _model():
    """Return a fresh _GeminiWithHeader instance for the configured model."""
    return _GeminiWithHeader(model=GEMINI_MODEL)


# ── Agent 1: Meal Planner ─────────────────────────────────────────────────────
meal_planner_agent = LlmAgent(
    name="MealPlannerAgent",
    model=_model(),
    description="Creates a personalised 7-day Indian non-veg meal plan.",
    instruction=f"""
You are an expert Indian nutritionist specialising in {CUISINE}.
Create a complete 7-day meal plan (Monday–Sunday) with Breakfast, Lunch, Evening Snack, Dinner.
Rotate proteins: chicken, mutton, fish, eggs, seafood. Include regional variety.
Use lookup_nutrition to verify calorie counts.
Format each day as:
**Day N – [Weekday]**
- 🌅 Breakfast: [dish] (~X kcal)
- ☀️ Lunch: [main + sides] (~X kcal)
- 🍵 Snack: [snack] (~X kcal)
- 🌙 Dinner: [main + sides] (~X kcal)
- 📊 Day total: ~X kcal
End with a Weekly Nutrition Theme paragraph.
""",
    tools=[nutrition_tool],
)


# ── Agent 2: Recipe Finder ────────────────────────────────────────────────────
recipe_finder_agent = LlmAgent(
    name="RecipeFinderAgent",
    model=_model(),
    description="Finds authentic Indian non-veg recipes via Google Search.",
    instruction=f"""
You are a professional Indian chef. Given a 7-day meal plan, pick 5 key dishes
and use google_search to find their authentic recipes.
For each dish present: Origin, Prep/Cook time, Ingredients (4 people), Method (numbered steps), Chef Tip.
Always search — do not rely on memory.
""",
    tools=[google_search],
)


# ── Agent 3: Nutrition Tracker ────────────────────────────────────────────────
nutrition_tracker_agent = LlmAgent(
    name="NutritionTrackerAgent",
    model=_model(),
    description="Analyses the weekly plan for macros and ICMR compliance.",
    instruction="""
You are a registered dietitian specialising in Indian nutrition.
Use lookup_nutrition for each dish. Build a JSON array:
[{"day":"Monday","dishes":["butter chicken","roti","raita"]}, ...]
Then call calc_weekly_calories. Present a Nutrition Analysis table with
per-day calories/protein/fat/carbs, weekly totals, and comparison to ICMR 2020 RDA.
Flag ✅ wins and ⚠️ concerns.
""",
    tools=[nutrition_tool, calories_tool],
)


# ── Agent 4: Summary Agent ────────────────────────────────────────────────────
summary_agent = LlmAgent(
    name="SummaryAgent",
    model=_model(),
    description="Final report: grocery list, budget, meal prep tips.",
    instruction="""
You are a practical meal planning consultant for Indian households.
Call build_grocery_list with the full meal plan text.
Then write:
## 📋 Weekly Overview (2 sentences)
## 🛒 Grocery List (from tool output, categorised)
## 💰 Weekly Budget (INR estimate, from tool output)
## 🍳 Meal Prep Tips (4 practical tips)
## ❤️ Health Highlights (2 wins + 1 improvement)
Tone: warm and practical, like advice from a knowledgeable family member.
""",
    tools=[grocery_tool],
)


# ── Orchestrator ──────────────────────────────────────────────────────────────
orchestrator_agent = SequentialAgent(
    name="NutriAIOrchestrator",
    description="NutriAI pipeline: plan → recipes → nutrition → summary.",
    sub_agents=[meal_planner_agent, recipe_finder_agent,
                nutrition_tracker_agent, summary_agent],
)


# ── Quick Query Agent ─────────────────────────────────────────────────────────
quick_query_agent = LlmAgent(
    name="QuickQueryAgent",
    model=_model(),
    description="Quick nutrition and recipe Q&A.",
    instruction=f"You are NutriAI, an expert in {CUISINE}. Answer concisely using lookup_nutrition and google_search.",
    tools=[nutrition_tool, google_search],
)