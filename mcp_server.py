"""
nutri_ai/mcp_server.py
───────────────────────
MCP (Model Context Protocol) Nutrition Server.

Exposes 4 tools over stdio transport:
  • get_nutrition_info          — single dish lookup
  • get_daily_nutrition_summary — multi-meal daily total vs ICMR RDA
  • list_available_dishes       — full dish catalogue
  • get_dishes_by_type          — filter by protein type

Run standalone:
    python mcp_server.py

The ADK agents connect to this via McpToolset + StdioConnectionParams.
"""

import json
import asyncio
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Import shared data (works when run as __main__ from nutri_ai/ directory)
from nutrition_data import DISHES, DAILY_RDA, fuzzy_lookup

# ── MCP server instance ───────────────────────────────────────────────────────
app = Server("nutriai-nutrition-mcp")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_nutrition_info",
            description=(
                "Get nutritional info for one Indian non-veg dish. "
                "Returns calories, protein, carbs, fat, fiber, iron, calcium, sodium."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dish_name": {
                        "type": "string",
                        "description": "Dish name e.g. 'butter chicken', 'mutton biryani'",
                    }
                },
                "required": ["dish_name"],
            },
        ),
        types.Tool(
            name="get_daily_nutrition_summary",
            description=(
                "Given a list of dishes eaten in a day, compute total nutrition "
                "and compare against ICMR 2020 recommended daily allowances."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dish":     {"type": "string"},
                                "servings": {"type": "number"},
                            },
                        },
                        "description": "List of {dish, servings} eaten today",
                    }
                },
                "required": ["meals"],
            },
        ),
        types.Tool(
            name="list_available_dishes",
            description="List all Indian non-veg dishes in the nutrition database.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_dishes_by_type",
            description="Filter dishes by protein type: chicken, mutton, fish, egg, seafood.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["chicken", "mutton", "fish", "egg", "seafood", "carb", "side"],
                    }
                },
                "required": ["type"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # ── get_nutrition_info ────────────────────────────────────────────────────
    if name == "get_nutrition_info":
        data = fuzzy_lookup(arguments.get("dish_name", ""))
        if not data:
            result = {
                "error": f"'{arguments.get('dish_name')}' not found.",
                "tip": "Try: " + ", ".join(list(DISHES.keys())[:6]),
            }
        else:
            pct = {
                k: round((data[k] / DAILY_RDA[k]) * 100, 1)
                for k in DAILY_RDA
                if k in data
            }
            result = {**data, "percent_of_daily_rda": pct}
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── get_daily_nutrition_summary ───────────────────────────────────────────
    elif name == "get_daily_nutrition_summary":
        meals    = arguments.get("meals", [])
        totals   = {k: 0.0 for k in DAILY_RDA}
        totals["calories"] = 0.0
        logged   = []

        for meal in meals:
            data = fuzzy_lookup(meal.get("dish", ""))
            if not data:
                continue
            servings = float(meal.get("servings", 1))
            for key in DAILY_RDA:
                if key in data:
                    totals[key] += data[key] * servings
            logged.append(f"{data['name']} × {servings}")

        totals = {k: round(v, 1) for k, v in totals.items()}
        pct    = {k: round((totals[k] / DAILY_RDA[k]) * 100, 1) for k in DAILY_RDA}

        # Simple rating
        cal_ok  = 80 <= pct.get("calories", 0) <= 115
        prot_ok = pct.get("protein_g", 0) >= 80
        if cal_ok and prot_ok:
            rating = "✅ Well-balanced day"
        elif pct.get("calories", 0) > 130:
            rating = "⚠️ High-calorie day"
        elif pct.get("protein_g", 0) < 60:
            rating = "⚠️ Low-protein day"
        else:
            rating = "ℹ️ Acceptable"

        return [types.TextContent(type="text", text=json.dumps({
            "meals_included":    logged,
            "total_nutrition":   totals,
            "percent_daily_rda": pct,
            "health_rating":     rating,
            "standard":          "ICMR 2020 (adult Indian)",
        }, indent=2))]

    # ── list_available_dishes ─────────────────────────────────────────────────
    elif name == "list_available_dishes":
        dishes = [
            {"key": k, "name": v["name"], "type": v["type"], "region": v["region"]}
            for k, v in DISHES.items()
        ]
        return [types.TextContent(type="text", text=json.dumps(
            {"total": len(dishes), "dishes": dishes}, indent=2
        ))]

    # ── get_dishes_by_type ────────────────────────────────────────────────────
    elif name == "get_dishes_by_type":
        t = arguments.get("type", "").lower()
        filtered = [
            {"key": k, "name": v["name"],
             "calories": v["calories"], "protein_g": v["protein_g"]}
            for k, v in DISHES.items() if v.get("type") == t
        ]
        return [types.TextContent(type="text", text=json.dumps(
            {"type": t, "count": len(filtered), "dishes": filtered}, indent=2
        ))]

    else:
        return [types.TextContent(type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    print("🥗 NutriAI MCP Nutrition Server started (stdio)", file=sys.stderr)
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
