"""
LLM-based dependency analysis.
Sends batches of tools to GPT-4o-mini via OpenRouter to identify:
1. What entity IDs each tool PRODUCES in its output
2. Whether each required parameter is user-provided or must come from another tool
3. Semantic dependencies (e.g. send email to person → need contact lookup first)
"""

import json
import os
import time
import requests
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

# Load .env
env = {}
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

OPENROUTER_KEY = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o-mini"
BATCH_SIZE = 15
SLEEP_BETWEEN = 0.5  # seconds between calls

# ─── Load tools ───────────────────────────────────────────────────────────────

root = Path(__file__).parent.parent

with open(root / "googlesuper_tools.json") as f:
    gs_tools = json.load(f)
with open(root / "github_tools.json") as f:
    gh_tools = json.load(f)

all_tools = gs_tools + gh_tools
tool_by_slug = {t["slug"]: t for t in all_tools}

print(f"Loaded {len(gs_tools)} GoogleSuper + {len(gh_tools)} GitHub tools = {len(all_tools)} total")

# ─── Service group helper ─────────────────────────────────────────────────────

def get_service(slug):
    s = slug.upper()
    if any(x in s for x in ["GMAIL","EMAIL","MAIL","THREAD","DRAFT","LABEL","FILTER","MESSAGE"]):
        return "gmail"
    if any(x in s for x in ["CALENDAR","EVENT","ACL","FREEBUSY"]):
        return "calendar"
    if any(x in s for x in ["DRIVE","GDRIVE","FILE","FOLDER","SHARED","PERMISSION"]):
        return "drive"
    if any(x in s for x in ["SHEET","SPREADSHEET","VALUES","RANGE"]):
        return "sheets"
    if any(x in s for x in ["DOC","DOCUMENT"]):
        return "docs"
    if any(x in s for x in ["PRESENTATION","SLIDE"]):
        return "slides"
    if any(x in s for x in ["MAPS","GEOCODE","PLACE","DISTANCE","NEARBY","TILES"]):
        return "maps"
    if any(x in s for x in ["CONTACT","PEOPLE","PERSON"]):
        return "contacts"
    if any(x in s for x in ["ISSUE","MILESTONE"]):
        return "gh_issues"
    if any(x in s for x in ["PULL","REVIEW","MERGE"]):
        return "gh_prs"
    if any(x in s for x in ["RELEASE","DEPLOY","COMMIT","BRANCH","TAG","CONTENT"]):
        return "gh_repos"
    if any(x in s for x in ["WORKFLOW","ACTION","ARTIFACT","RUNNER","SECRET","ENVIRONMENT","CACHE"]):
        return "gh_actions"
    if any(x in s for x in ["TEAM","ORG","ORGANIZATION","MEMBER"]):
        return "gh_orgs"
    if any(x in s for x in ["USER","FOLLOWER","GIST","SSH","GPG"]):
        return "gh_users"
    if any(x in s for x in ["CHECK","STATUS"]):
        return "gh_checks"
    if any(x in s for x in ["HOOK","WEBHOOK"]):
        return "gh_webhooks"
    if any(x in s for x in ["PROJECT"]):
        return "gh_projects"
    return "other"

# Group tools by service
from collections import defaultdict
service_groups = defaultdict(list)
for t in all_tools:
    service_groups[get_service(t["slug"])].append(t)

print("Service groups:")
for svc, tools in sorted(service_groups.items(), key=lambda x: -len(x[1])):
    print(f"  {svc}: {len(tools)} tools")

# ─── LLM call ─────────────────────────────────────────────────────────────────

def call_llm(tools_batch):
    """Call GPT-4o-mini with a batch of tools, returns parsed JSON."""

    # Build compact tool descriptions for the prompt
    tool_descriptions = []
    for t in tools_batch:
        inp = t.get("inputParameters", {})
        required = inp.get("required", [])
        props = inp.get("properties", {})

        # Compact param list
        param_list = []
        for p, v in props.items():
            desc = v.get("description", "")[:60] if isinstance(v, dict) else ""
            param_list.append(f"  {p}{'*' if p in required else ''}: {desc}")

        tool_descriptions.append(
            f"TOOL: {t['slug']}\n"
            f"DESC: {t.get('description','')[:120]}\n"
            f"PARAMS (* = required):\n" + "\n".join(param_list[:12])
        )

    tools_text = "\n\n---\n\n".join(tool_descriptions)

    prompt = f"""Analyze these API tools and return a JSON object.

For each tool identify:
1. "produces": Entity ID types this tool returns that OTHER tools need as inputs.
   Only include system-assigned IDs/references (like event_id, issue_number, file_id, thread_id).
   Do NOT include: counts, booleans, user content, pagination tokens.
   Use snake_case names that match how other tools reference them as parameters.

2. "param_types": For each required param (*), classify as:
   - "user": User provides this (text, dates, email addresses, repo/org names, content)
   - "tool": Must come from another tool's output (system IDs, numbers assigned by the API)
   - "semantic": Semantically needs another tool first even if user could guess it

3. "semantic_deps": Array of tool slugs that should logically run before this one
   (beyond what param_types captures). Empty array if none.

Return ONLY valid JSON, no explanation:
{{
  "TOOL_SLUG": {{
    "produces": ["entity_type"],
    "param_types": {{"param": "user|tool|semantic"}},
    "semantic_deps": ["OTHER_TOOL_SLUG"]
  }}
}}

TOOLS TO ANALYZE:

{tools_text}"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)

# ─── Process all service groups ───────────────────────────────────────────────

output_path = root / "llm_analysis.json"

# Load existing results if resuming
if output_path.exists():
    with open(output_path) as f:
        results = json.load(f)
    print(f"Resuming — {len(results)} tools already analyzed")
else:
    results = {}

total_tools = len(all_tools)
processed = 0
errors = 0

# Process each service group in batches
for service, tools in sorted(service_groups.items(), key=lambda x: -len(x[1])):
    # Skip tools already processed
    remaining = [t for t in tools if t["slug"] not in results]
    if not remaining:
        print(f"  {service}: already done ({len(tools)} tools)")
        processed += len(tools)
        continue

    print(f"\n  {service}: {len(tools)} tools ({len(remaining)} remaining)...")

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        slugs = [t["slug"] for t in batch]
        print(f"    Batch {i//BATCH_SIZE + 1}: {slugs[0]} .. {slugs[-1]}", end=" ", flush=True)

        try:
            batch_results = call_llm(batch)
            # Merge results
            for slug, data in batch_results.items():
                if slug in tool_by_slug:  # only keep valid slugs
                    results[slug] = data
            print(f"✓ ({len(batch_results)} parsed)")
        except Exception as e:
            print(f"✗ ERROR: {e}")
            errors += 1
            # On error, add empty entries so we don't retry
            for t in batch:
                if t["slug"] not in results:
                    results[t["slug"]] = {"produces": [], "param_types": {}, "semantic_deps": []}

        processed += len(batch)

        # Save progress after every batch
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        time.sleep(SLEEP_BETWEEN)

print(f"\nDone. {len(results)} tools analyzed, {errors} errors.")
print(f"Saved to {output_path}")

# ─── Summary stats ────────────────────────────────────────────────────────────

total_produces = sum(len(v.get("produces", [])) for v in results.values())
total_semantic = sum(len(v.get("semantic_deps", [])) for v in results.values())
tool_deps = sum(
    1 for v in results.values()
    for ptype in v.get("param_types", {}).values()
    if ptype == "tool"
)

print(f"\nSummary:")
print(f"  Tools that produce entities: {sum(1 for v in results.values() if v.get('produces'))}")
print(f"  Total entity types produced: {total_produces}")
print(f"  Required params needing tool output: {tool_deps}")
print(f"  Semantic dependencies found: {total_semantic}")

# Show top producers
print("\nTop entity producers:")
producers = defaultdict(list)
for slug, data in results.items():
    for entity in data.get("produces", []):
        producers[entity].append(slug)
for entity, slugs in sorted(producers.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {entity}: produced by {len(slugs)} tools")
