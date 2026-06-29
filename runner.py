"""
nutri_ai/runner.py
───────────────────
Async runner and session management for all NutriAI agents.

Public API (all are async coroutines):
  run_pipeline(preferences, calorie_goal, restrictions, num_people)
      → full orchestrator run (all 4 sub-agents)

  run_recipe_search(dish_name)   → RecipeFinderAgent only
  run_nutrition_check(dish_name) → NutritionTrackerAgent only
  run_quick_query(question)      → QuickQueryAgent
"""

import asyncio
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from config import APP_NAME, USER_ID, SESS_PFX

# Single shared session service for the whole app lifetime
_session_svc = InMemorySessionService()


# ── Core: run any agent, return full text response ────────────────────────────
async def _run(agent, prompt: str, session_id: str | None = None) -> str:
    """
    Create a session (if needed), invoke the agent, collect all text output.

    ADK Runner streams Events; we accumulate text from every final-response
    event (sub-agents each emit one) and join them.
    """
    if session_id is None:
        session_id = f"{SESS_PFX}_{uuid.uuid4().hex[:8]}"

    # auto_create_session=True means the Runner creates the session for us
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=_session_svc,
        auto_create_session=True,
    )

    message = Content(role="user", parts=[Part(text=prompt)])

    chunks: list[str] = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        # Collect text from every final response (each sub-agent emits one)
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    chunks.append(part.text.strip())

    return "\n\n".join(filter(None, chunks))


# ── Public coroutines ─────────────────────────────────────────────────────────
async def run_pipeline(
    preferences: str = "",
    calorie_goal: int = 2000,
    restrictions: str = "",
    num_people: int = 2,
) -> str:
    """Run the full 4-agent orchestration pipeline."""
    from agents import orchestrator_agent

    prompt = f"""
Create a complete 7-day Indian non-vegetarian meal plan with the following details:

User Preferences : {preferences or "Balanced Indian non-veg cuisine"}
Daily Calorie Goal: {calorie_goal} kcal
Dietary Restrictions: {restrictions or "None"}
Cooking For: {num_people} people

Steps to follow:
1. MealPlannerAgent     — design the 7-day plan (Mon–Sun, 4 meals/day)
2. RecipeFinderAgent    — find authentic recipes for 5 key dishes
3. NutritionTrackerAgent— analyse macros and weekly calorie total
4. SummaryAgent         — produce grocery list and budget for {num_people} people

Make weekday meals quick (≤40 min). Weekend dishes can be elaborate.
"""
    return await _run(orchestrator_agent, prompt)


async def run_recipe_search(dish_name: str) -> str:
    """Search for a single recipe using RecipeFinderAgent + Google Search."""
    from agents import recipe_finder_agent

    prompt = (
        f"Find the most authentic, detailed recipe for '{dish_name}'. "
        "Use Google Search. Include ingredients (for 4 people), "
        "step-by-step method, and a professional chef tip."
    )
    return await _run(recipe_finder_agent, prompt)


async def run_nutrition_check(dish_name: str) -> str:
    """Nutrition breakdown for a single dish via NutritionTrackerAgent."""
    from agents import nutrition_tracker_agent

    prompt = (
        f"Give a complete nutritional breakdown for '{dish_name}'. "
        "Use lookup_nutrition, then present calories, protein, carbs, fat, "
        "fiber, iron, calcium, sodium, and % of ICMR daily recommended values."
    )
    return await _run(nutrition_tracker_agent, prompt)


async def run_quick_query(question: str) -> str:
    """Single-turn Q&A via QuickQueryAgent."""
    from agents import quick_query_agent
    return await _run(quick_query_agent, question)
