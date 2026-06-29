"""
nutri_ai/tools.py
──────────────────
Python FunctionTools for the ADK agents.

These are lightweight wrappers around nutrition_data.py so agents
can call them without spinning up a subprocess MCP server.

Three tools:
  • lookup_nutrition       — single dish → nutrition JSON
  • calc_weekly_calories   — list of days → calorie breakdown JSON
  • build_grocery_list     — meal plan text → categorised grocery JSON
"""

import json
from nutrition_data import DISHES, DAILY_RDA, fuzzy_lookup
from google.adk.tools import FunctionTool


# ── Tool 1: lookup_nutrition ──────────────────────────────────────────────────
def lookup_nutrition(dish_name: str) -> str:
    """
    Return nutritional information for an Indian non-veg dish.

    Args:
        dish_name: Name of the dish, e.g. 'butter chicken', 'mutton biryani'.

    Returns:
        JSON string with calories, protein, carbs, fat, fiber, iron, calcium,
        sodium, and percentage of ICMR daily recommended values.
    """
    data = fuzzy_lookup(dish_name)
    if not data:
        return json.dumps({
            "error": f"'{dish_name}' not found in database.",
            "available_examples": list(DISHES.keys())[:8],
        })

    pct = {
        k: round((data[k] / DAILY_RDA[k]) * 100, 1)
        for k in DAILY_RDA if k in data
    }
    return json.dumps({**data, "percent_of_daily_rda": pct}, indent=2)


# ── Tool 2: calc_weekly_calories ──────────────────────────────────────────────
def calc_weekly_calories(meal_plan_json: str) -> str:
    """
    Calculate estimated weekly calorie totals from a 7-day meal plan.

    Args:
        meal_plan_json: JSON array of objects like:
            [{"day": "Monday", "dishes": ["butter chicken", "roti", "raita"]}, ...]

    Returns:
        JSON string with per-day calorie estimates and weekly total.
    """
    try:
        plan = json.loads(meal_plan_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON. Expected array of {day, dishes}."})

    daily_rows = []
    weekly_total = 0

    for entry in plan:
        day       = entry.get("day", "?")
        dishes    = entry.get("dishes", [])
        day_cals  = 0
        found     = []
        for dish in dishes:
            data = fuzzy_lookup(dish)
            if data:
                day_cals += data["calories"]
                found.append(data["name"])
        weekly_total += day_cals
        daily_rows.append({"day": day, "calories": day_cals, "dishes_matched": found})

    days = len(daily_rows) or 1
    return json.dumps({
        "daily_breakdown":    daily_rows,
        "weekly_total_kcal":  weekly_total,
        "daily_average_kcal": round(weekly_total / days),
        "icmr_target_daily":  2000,
        "icmr_target_weekly": 14000,
        "vs_target_pct":      round((weekly_total / 14000) * 100, 1),
    }, indent=2)


# ── Tool 3: build_grocery_list ────────────────────────────────────────────────

# Ingredient map: dish keyword → ingredients by category
_DISH_INGREDIENTS: dict[str, dict[str, list[str]]] = {
    "butter chicken": {
        "protein":  ["Chicken breast 500g"],
        "dairy":    ["Butter 50g", "Fresh cream 100ml"],
        "pantry":   ["Kasuri methi", "Butter chicken masala"],
    },
    "biryani": {
        "protein":  ["Chicken/Mutton 600g"],
        "grains":   ["Basmati rice 500g"],
        "dairy":    ["Yogurt 200g", "Ghee 3 tbsp"],
        "pantry":   ["Biryani masala", "Saffron pinch", "Fried onions"],
    },
    "fish curry": {
        "protein":  ["Fish fillets 400g (rohu/catfish/pomfret)"],
        "pantry":   ["Tamarind paste", "Coconut milk 200ml", "Curry leaves"],
    },
    "goan fish": {
        "protein":  ["Fish 400g"],
        "pantry":   ["Coconut milk 200ml", "Goan masala", "Kokum 4 pieces"],
    },
    "egg bhurji": {
        "protein":  ["Eggs 6"],
        "pantry":   ["Green chillies 3", "Cumin seeds"],
    },
    "egg curry": {
        "protein":  ["Eggs 8"],
        "pantry":   ["Coriander powder", "Garam masala"],
    },
    "keema": {
        "protein":  ["Minced mutton/chicken 400g"],
        "vegs":     ["Green peas 100g (frozen OK)"],
    },
    "tandoori": {
        "protein":  ["Whole chicken 1 (cut into pieces)"],
        "dairy":    ["Hung yogurt 200g"],
        "pantry":   ["Tandoori masala 3 tbsp", "Lemons 2"],
    },
    "rogan josh": {
        "protein":  ["Mutton on bone 500g"],
        "pantry":   ["Kashmiri red chilli powder 2 tbsp", "Fennel powder 1 tsp", "Asafoetida pinch"],
    },
    "prawn masala": {
        "protein":  ["Prawns 400g (cleaned)"],
        "pantry":   ["Coconut milk 100ml", "Curry leaves", "Mustard seeds"],
    },
    "korma": {
        "protein":  ["Chicken 500g"],
        "dairy":    ["Fresh cream 100ml", "Yogurt 200g"],
        "pantry":   ["Cashews 50g", "Cardamom 4", "Rose water 1 tsp"],
    },
    "chettinad": {
        "protein":  ["Chicken 500g"],
        "pantry":   ["Kalpasi (stone flower)", "Marathi mokku", "Chettinad masala"],
    },
}

def build_grocery_list(meal_plan_text: str) -> str:
    """
    Generate a categorised weekly grocery list from a 7-day meal plan description.

    Args:
        meal_plan_text: Free-text description of the week's meals (can be the
                        full meal plan output from MealPlannerAgent).

    Returns:
        JSON string with categorised grocery items and a rough INR budget estimate
        for Delhi NCR (2 people, 1 week).
    """
    text = meal_plan_text.lower()

    # Start with the always-needed base ingredients
    grocery: dict[str, list[str]] = {
        "🥩 Proteins":              [],
        "🧅 Vegetables & Aromatics": [
            "Onions 1 kg", "Tomatoes 500g", "Ginger piece 100g",
            "Garlic 2 bulbs", "Green chillies 50g", "Fresh coriander 2 bunches",
            "Lemon 4",
        ],
        "🌾 Grains & Staples": [
            "Basmati rice 1 kg", "Whole wheat atta 1 kg",
        ],
        "🫙 Spices & Pantry": [
            "Cumin seeds", "Mustard seeds", "Turmeric powder",
            "Red chilli powder", "Coriander powder", "Garam masala",
            "Salt", "Bay leaves",
        ],
        "🥛 Dairy": [
            "Yogurt 500g", "Milk 1 L",
        ],
        "🛢️ Oils & Condiments": [
            "Cooking oil 500ml", "Ghee 200g",
        ],
    }

    proteins_added: set[str] = set()

    for keyword, ing_map in _DISH_INGREDIENTS.items():
        # Check if this dish appears in the plan
        if not any(word in text for word in keyword.split()):
            continue

        for category, items in ing_map.items():
            target = {
                "protein": "🥩 Proteins",
                "dairy":   "🥛 Dairy",
                "grains":  "🌾 Grains & Staples",
                "vegs":    "🧅 Vegetables & Aromatics",
                "pantry":  "🫙 Spices & Pantry",
            }.get(category, "🫙 Spices & Pantry")

            for item in items:
                if target == "🥩 Proteins":
                    if item not in proteins_added:
                        grocery[target].append(item)
                        proteins_added.add(item)
                else:
                    if item not in grocery[target]:
                        grocery[target].append(item)

    # Deduplicate all lists
    grocery = {k: list(dict.fromkeys(v)) for k, v in grocery.items()}

    # Rough Delhi NCR budget estimate (INR, 2 people, 1 week, 2025 prices)
    budget = {
        "🥩 Proteins (chicken/mutton/fish/eggs)": "₹800 – ₹1,200",
        "🧅 Vegetables & Aromatics":               "₹150 – ₹250",
        "🌾 Grains & Staples":                     "₹120 – ₹180",
        "🫙 Spices & Pantry":                      "₹100 – ₹150",
        "🥛 Dairy":                                "₹100 – ₹150",
        "🛢️ Oils & Condiments":                   "₹80 – ₹120",
        "💰 Total estimate":                        "₹1,350 – ₹2,050",
    }

    return json.dumps({
        "grocery_list":    grocery,
        "budget_inr_2ppl": budget,
        "note": "Prices based on Delhi NCR retail markets. Buy proteins fresh 2-3×/week.",
    }, indent=2, ensure_ascii=False)


# ── Wrap as ADK FunctionTools (import these in agents.py) ────────────────────
nutrition_tool = FunctionTool(func=lookup_nutrition)
calories_tool  = FunctionTool(func=calc_weekly_calories)
grocery_tool   = FunctionTool(func=build_grocery_list)
