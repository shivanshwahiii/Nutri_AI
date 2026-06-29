"""
nutri_ai/app.py
────────────────
NutriAI Gradio Web Interface — 5 tabs:

  Tab 1 🗓️  7-Day Meal Plan    — full orchestrator pipeline
  Tab 2 🔍  Recipe Finder      — single dish via Google Search
  Tab 3 🥗  Nutrition Checker  — macro/micro lookup
  Tab 4 💬  Quick Ask          — free-form Q&A
  Tab 5 ℹ️  About              — architecture and tech stack

Run:
    python app.py
"""

import asyncio
import threading

import gradio as gr

from config import APP_NAME, GEMINI_MODEL, GRADIO_PORT, GRADIO_SHARE
from runner import (
    run_pipeline,
    run_recipe_search,
    run_nutrition_check,
    run_quick_query,
)


# ── Run an async coroutine safely from a sync Gradio handler ──────────────────
def _sync(coro, timeout: int = 240) -> str:
    result: dict = {}

    def worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["ok"] = loop.run_until_complete(coro)
        except Exception as exc:
            result["err"] = str(exc)
        finally:
            loop.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if "err" in result:
        return f"❌ Error: {result['err']}"
    if "ok" not in result:
        return "⏳ Timed out — the agents took too long. Please try again."
    return result["ok"] or "⚠️ No response received. Check your API key."


# ── Gradio event handlers ─────────────────────────────────────────────────────
def on_generate_plan(preferences, calorie_goal, restrictions, num_people, progress=gr.Progress()):
    progress(0.05, desc="🚀 Starting NutriAI orchestrator…")
    progress(0.15, desc="📋 MealPlannerAgent: designing your 7-day plan…")
    out = _sync(run_pipeline(preferences, int(calorie_goal), restrictions, int(num_people)))
    progress(1.0,  desc="✅ Done!")
    return out


def on_find_recipe(dish, progress=gr.Progress()):
    if not dish.strip():
        return "⚠️ Please enter a dish name."
    progress(0.2, desc=f"🔍 Searching for '{dish}' recipe…")
    out = _sync(run_recipe_search(dish))
    progress(1.0, desc="✅ Recipe found!")
    return out


def on_check_nutrition(dish, progress=gr.Progress()):
    if not dish.strip():
        return "⚠️ Please enter a dish name."
    progress(0.3, desc=f"🔬 Analysing nutrition for '{dish}'…")
    out = _sync(run_nutrition_check(dish))
    progress(1.0, desc="✅ Done!")
    return out


def on_quick_ask(question, progress=gr.Progress()):
    if not question.strip():
        return "⚠️ Please type a question."
    progress(0.3, desc="💬 Thinking…")
    out = _sync(run_quick_query(question))
    progress(1.0, desc="✅ Done!")
    return out


# ── About content ─────────────────────────────────────────────────────────────
ABOUT_MD = f"""
## 🍛 NutriAI — Indian Non-Veg Meal Planner

Built with **Google ADK {GEMINI_MODEL}** for the Kaggle 5-Day AI Agents Intensive Capstone.

---

### 🏗️ Multi-Agent Architecture

```
User Request
     │
     ▼
NutriAIOrchestrator  (SequentialAgent)
     │
     ├─ 1. MealPlannerAgent      → 7-day Indian non-veg plan
     │       tools: lookup_nutrition (FunctionTool)
     │
     ├─ 2. RecipeFinderAgent     → Authentic recipes
     │       tools: google_search (Google Search grounding)
     │
     ├─ 3. NutritionTrackerAgent → Macro / micro analysis
     │       tools: lookup_nutrition, calc_weekly_calories
     │
     └─ 4. SummaryAgent          → Grocery list + budget
             tools: build_grocery_list (FunctionTool)

QuickQueryAgent  (standalone LlmAgent)
     tools: lookup_nutrition, google_search
     
MCP Nutrition Server  (stdio transport)
     • get_nutrition_info
     • get_daily_nutrition_summary
     • list_available_dishes
     • get_dishes_by_type
```

---

### 🤖 Agents

| Agent | Role | Tools |
|-------|------|-------|
| **OrchestratorAgent** | Coordinates all sub-agents | SequentialAgent |
| **MealPlannerAgent** | 7-day meal schedule | lookup_nutrition |
| **RecipeFinderAgent** | Live recipe search | google_search |
| **NutritionTrackerAgent** | Macro/micro analysis | lookup_nutrition, calc_weekly_calories |
| **SummaryAgent** | Final report + grocery list | build_grocery_list |
| **QuickQueryAgent** | Single-turn Q&A | lookup_nutrition, google_search |

---

### 🔧 Tech Stack
- **Google ADK 2.3** — LlmAgent, SequentialAgent, FunctionTool
- **Gemini 2.0 Flash** — LLM for all agents
- **Google Search grounding** — live recipe discovery
- **MCP (Model Context Protocol)** — nutrition data server
- **Gradio 4+** — web UI
- **python-dotenv** — secure API key handling

### 🌶️ Cuisine Coverage
North Indian · Mughlai · Kashmiri · South Indian · Coastal · Hyderabadi

### 📊 Nutrition Standard
**ICMR 2020** — 2000 kcal · 60 g protein · 17 mg iron · 1000 mg calcium
"""


# ── Build UI ──────────────────────────────────────────────────────────────────
def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="NutriAI — Indian Non-Veg Meal Planner",
        theme=gr.themes.Soft(primary_hue="orange", secondary_hue="green"),
    ) as demo:

        # Header
        gr.HTML("""
        <div style="background:linear-gradient(135deg,#E07B39,#C75A1C 60%,#2E7D32);
                    border-radius:12px;padding:28px;text-align:center;color:#fff;margin-bottom:8px">
          <h1 style="margin:0;font-size:2.2em;letter-spacing:1px">🍛 NutriAI</h1>
          <p style="margin:8px 0 0;font-size:1.05em;opacity:.9">
            AI-Powered Indian Non-Vegetarian Meal Planner
          </p>
          <p style="margin:6px 0 0;font-size:.8em;opacity:.7">
            Google ADK · Gemini 2.0 Flash · MCP · Google Search
          </p>
        </div>
        """)

        with gr.Tabs():

            # ── Tab 1: 7-Day Meal Plan ─────────────────────────────────────
            with gr.TabItem("🗓️ 7-Day Meal Plan"):
                gr.Markdown(
                    "Generate a personalised 7-day Indian non-veg meal plan — "
                    "with recipes, nutrition analysis, and a grocery list. "
                    "**Runs 4 agents sequentially. Allow 90–150 seconds.**"
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        pref = gr.Textbox(
                            label="Your Preferences",
                            placeholder="e.g. More chicken, love coastal flavours, no pork",
                            value="Balanced mix of chicken, fish, mutton and eggs",
                            lines=2,
                        )
                        kcal = gr.Slider(
                            label="Daily Calorie Target (kcal)",
                            minimum=1500, maximum=3000, step=100, value=2000,
                        )
                        restr = gr.Textbox(
                            label="Restrictions / Allergies",
                            placeholder="e.g. No shellfish, low sodium",
                            lines=1,
                        )
                        people = gr.Slider(
                            label="Cooking For (people)",
                            minimum=1, maximum=8, step=1, value=2,
                        )
                        plan_btn = gr.Button("🚀 Generate My 7-Day Plan", variant="primary", size="lg")
                        gr.Markdown("*Full pipeline · 90–150 sec · be patient!*")

                    with gr.Column(scale=2):
                        plan_out = gr.Markdown("*Your plan will appear here…*")

                plan_btn.click(
                    fn=on_generate_plan,
                    inputs=[pref, kcal, restr, people],
                    outputs=[plan_out],
                    show_progress="full",
                )

                gr.Examples(
                    examples=[
                        ["High protein, Punjabi food lover", 2200, "No shellfish", 2],
                        ["Coastal seafood, mild spices",     1800, "Low sodium",    1],
                        ["Family with kids, not too spicy",  2000, "No very spicy", 4],
                        ["Gym-goer, max protein",            2600, "None",          1],
                    ],
                    inputs=[pref, kcal, restr, people],
                    label="Quick-start presets",
                )

            # ── Tab 2: Recipe Finder ───────────────────────────────────────
            with gr.TabItem("🔍 Recipe Finder"):
                gr.Markdown(
                    "Find authentic step-by-step recipes via **Google Search**. "
                    "Results come from real culinary sources, not the model's memory."
                )
                with gr.Row():
                    dish_in = gr.Textbox(
                        label="Dish Name",
                        placeholder="e.g. Goan Fish Curry, Mutton Rogan Josh, Egg Bhurji",
                        scale=4,
                    )
                    recipe_btn = gr.Button("🔍 Find Recipe", variant="primary", scale=1)

                recipe_out = gr.Markdown("*Recipe will appear here…*")

                recipe_btn.click(
                    fn=on_find_recipe,
                    inputs=[dish_in],
                    outputs=[recipe_out],
                    show_progress="full",
                )
                gr.Examples(
                    examples=[
                        ["Butter Chicken"],
                        ["Mutton Biryani"],
                        ["Chettinad Chicken Curry"],
                        ["Goan Fish Curry"],
                        ["Keema Matar"],
                        ["Tandoori Chicken"],
                        ["Rogan Josh"],
                        ["Prawn Masala"],
                    ],
                    inputs=[dish_in],
                    label="Popular dishes",
                )

            # ── Tab 3: Nutrition Checker ───────────────────────────────────
            with gr.TabItem("🥗 Nutrition Checker"):
                gr.Markdown(
                    "Get a detailed nutritional profile for any Indian non-veg dish "
                    "benchmarked against **ICMR 2020** daily recommended values."
                )
                with gr.Row():
                    nutr_in = gr.Textbox(
                        label="Dish Name",
                        placeholder="e.g. Chicken Biryani, Prawn Masala, Rogan Josh",
                        scale=4,
                    )
                    nutr_btn = gr.Button("🔬 Analyse", variant="primary", scale=1)

                nutr_out = gr.Markdown("*Nutrition info will appear here…*")

                nutr_btn.click(
                    fn=on_check_nutrition,
                    inputs=[nutr_in],
                    outputs=[nutr_out],
                    show_progress="full",
                )
                gr.Examples(
                    examples=[
                        ["Butter Chicken"],
                        ["Mutton Biryani"],
                        ["Tandoori Chicken"],
                        ["Fish Curry"],
                        ["Egg Bhurji"],
                        ["Keema Matar"],
                    ],
                    inputs=[nutr_in],
                    label="Try these",
                )

                gr.Markdown("""
---
### 📊 ICMR 2020 Daily Reference (Adult Indian)
| Nutrient | Target |
|----------|--------|
| Energy | 2000 kcal |
| Protein | 60 g |
| Carbohydrates | 270 g |
| Fat | 67 g |
| Dietary Fiber | 30 g |
| Iron | 17 mg |
| Calcium | 1000 mg |
| Sodium | < 2000 mg |
""")

            # ── Tab 4: Quick Ask ───────────────────────────────────────────
            with gr.TabItem("💬 Quick Ask"):
                gr.Markdown(
                    "Ask NutriAI anything about Indian non-veg nutrition, "
                    "cooking tips, ingredient swaps, or healthy eating."
                )
                q_in = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g. Which is healthier — chicken or mutton? How do I reduce oil in biryani?",
                    lines=2,
                )
                ask_btn = gr.Button("💬 Ask NutriAI", variant="primary")
                q_out = gr.Markdown("*Answer will appear here…*")

                ask_btn.click(
                    fn=on_quick_ask,
                    inputs=[q_in],
                    outputs=[q_out],
                    show_progress="full",
                )
                gr.Examples(
                    examples=[
                        ["Which is higher in protein — chicken breast or mutton?"],
                        ["How many calories in a standard plate of biryani?"],
                        ["What are high-protein Indian snacks I can have post-workout?"],
                        ["How do I make butter chicken less calorie-dense?"],
                        ["Is egg bhurji good for weight loss?"],
                        ["Best fish for curries — rohu, pomfret, or surmai?"],
                        ["Can I use coconut oil instead of mustard oil in fish curry?"],
                        ["How much protein do I need if I gym 5 days a week?"],
                    ],
                    inputs=[q_in],
                    label="Popular questions",
                )

            # ── Tab 5: About ───────────────────────────────────────────────
            with gr.TabItem("ℹ️ About"):
                gr.Markdown(ABOUT_MD)

        # Footer
        gr.HTML("""
        <div style="text-align:center;margin-top:16px;padding:10px;
                    color:#888;font-size:11px;border-top:1px solid #eee">
          NutriAI · Kaggle 5-Day AI Agents Intensive Capstone · Google ADK + Gemini 🇮🇳
        </div>
        """)

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🍛 {APP_NAME} starting…")
    print(f"   Model : {GEMINI_MODEL}")
    print(f"   Port  : {GRADIO_PORT}")
    print(f"   Share : {GRADIO_SHARE}")
    print()
    demo = build_app()
    demo.launch(
        server_port=GRADIO_PORT,
        share=GRADIO_SHARE,
        show_error=True,
    )
