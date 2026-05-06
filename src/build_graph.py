"""
Enhanced dependency graph builder — combines heuristic + LLM analysis.

Improvements:
1. LLM-derived producer mappings (from llm_analysis.json)
2. Richer entity types (Gmail drafts/labels, Slides, Docs, Contacts, etc.)
3. Dependency type classification: required / optional / semantic
4. Entry point + terminal node tagging
5. BFS depth computation for hierarchical layout
"""

import json
from collections import defaultdict, deque
from pathlib import Path

root = Path(__file__).parent.parent

# ─── Load tools ───────────────────────────────────────────────────────────────

with open(root / "googlesuper_tools.json") as f:
    gs_tools = json.load(f)
with open(root / "github_tools.json") as f:
    gh_tools = json.load(f)

for t in gs_tools: t["_toolkit"] = "googlesuper"
for t in gh_tools: t["_toolkit"] = "github"

all_tools = gs_tools + gh_tools
tool_by_slug = {t["slug"]: t for t in all_tools}
valid_slugs = set(tool_by_slug.keys())

# ─── Load LLM analysis ────────────────────────────────────────────────────────

llm_path = root / "llm_analysis.json"
llm_data = {}
if llm_path.exists():
    with open(llm_path) as f:
        llm_data = json.load(f)
    print(f"LLM analysis: {len(llm_data)} tools")
else:
    print("No LLM analysis found — using heuristics only")

# Build LLM-derived producer map: entity_type → [tool_slugs]
llm_producers = defaultdict(list)
for slug, data in llm_data.items():
    if slug not in valid_slugs:
        continue
    for entity in data.get("produces", []):
        entity = entity.lower().strip()
        if entity:
            llm_producers[entity].append(slug)

print(f"LLM producer mappings: {len(llm_producers)} entity types")

# ─── Heuristic entity → producer mapping ─────────────────────────────────────

HEURISTIC_PRODUCERS = {
    # Google Calendar
    "calendar_id":       ["GOOGLESUPER_LIST_CALENDARS", "GOOGLESUPER_CALENDAR_LIST_INSERT"],
    "calendarId":        ["GOOGLESUPER_LIST_CALENDARS", "GOOGLESUPER_CALENDAR_LIST_INSERT"],
    "event_id":          ["GOOGLESUPER_EVENTS_LIST", "GOOGLESUPER_EVENTS_INSERT",
                          "GOOGLESUPER_EVENTS_LIST_ALL_CALENDARS"],
    "eventId":           ["GOOGLESUPER_EVENTS_LIST", "GOOGLESUPER_EVENTS_INSERT"],
    "rule_id":           ["GOOGLESUPER_ACL_LIST"],
    "ruleId":            ["GOOGLESUPER_ACL_LIST"],
    # Gmail
    "message_id":        ["GOOGLESUPER_FETCH_EMAILS", "GOOGLESUPER_CREATE_EMAIL_DRAFT"],
    "messageId":         ["GOOGLESUPER_FETCH_EMAILS", "GOOGLESUPER_CREATE_EMAIL_DRAFT"],
    "thread_id":         ["GOOGLESUPER_FETCH_EMAILS"],
    "threadId":          ["GOOGLESUPER_FETCH_EMAILS"],
    "label_id":          ["GOOGLESUPER_LIST_LABELS", "GOOGLESUPER_CREATE_LABEL"],
    "labelId":           ["GOOGLESUPER_LIST_LABELS", "GOOGLESUPER_CREATE_LABEL"],
    "draft_id":          ["GOOGLESUPER_LIST_DRAFTS", "GOOGLESUPER_CREATE_EMAIL_DRAFT"],
    "draftId":           ["GOOGLESUPER_LIST_DRAFTS", "GOOGLESUPER_CREATE_EMAIL_DRAFT"],
    "filter_id":         ["GOOGLESUPER_LIST_FILTERS", "GOOGLESUPER_CREATE_GMAIL_FILTER"],
    "filterId":          ["GOOGLESUPER_LIST_FILTERS", "GOOGLESUPER_CREATE_GMAIL_FILTER"],
    # Drive
    "file_id":           ["GOOGLESUPER_LIST_FILES_IN_FOLDER", "GOOGLESUPER_LIST_SHARED_FILES"],
    "fileId":            ["GOOGLESUPER_LIST_FILES_IN_FOLDER", "GOOGLESUPER_LIST_SHARED_FILES"],
    "folder_id":         ["GOOGLESUPER_LIST_FILES_IN_FOLDER"],
    "permission_id":     ["GOOGLESUPER_GET_PERMISSION_ID_FOR_EMAIL"],
    "permissionId":      ["GOOGLESUPER_GET_PERMISSION_ID_FOR_EMAIL"],
    # Sheets
    "spreadsheet_id":    ["GOOGLESUPER_LIST_SPREADSHEETS", "GOOGLESUPER_SPREADSHEETS_CREATE"],
    "spreadsheetId":     ["GOOGLESUPER_LIST_SPREADSHEETS", "GOOGLESUPER_SPREADSHEETS_CREATE"],
    "sheet_id":          ["GOOGLESUPER_SPREADSHEETS_GET"],
    "sheetId":           ["GOOGLESUPER_SPREADSHEETS_GET"],
    # Docs
    "document_id":       ["GOOGLESUPER_LIST_DOCS", "GOOGLESUPER_CREATE_NEW_DOC"],
    "documentId":        ["GOOGLESUPER_LIST_DOCS", "GOOGLESUPER_CREATE_NEW_DOC"],
    # Slides
    "presentation_id":   ["GOOGLESUPER_PRESENTATIONS_LIST", "GOOGLESUPER_PRESENTATIONS_CREATE"],
    "presentationId":    ["GOOGLESUPER_PRESENTATIONS_LIST", "GOOGLESUPER_PRESENTATIONS_CREATE"],
    "slide_id":          ["GOOGLESUPER_PRESENTATIONS_GET"],
    "slideId":           ["GOOGLESUPER_PRESENTATIONS_GET"],
    "page_object_id":    ["GOOGLESUPER_PRESENTATIONS_GET"],
    # Maps
    "place_id":          ["GOOGLESUPER_PLACE_SEARCH_NEARBY", "GOOGLESUPER_GEOCODE_ADDRESS"],
    "placeId":           ["GOOGLESUPER_PLACE_SEARCH_NEARBY", "GOOGLESUPER_GEOCODE_ADDRESS"],
    # Albums (Photos)
    "albumId":           ["GOOGLESUPER_LIST_ALBUMS", "GOOGLESUPER_LIST_SHARED_ALBUMS",
                          "GOOGLESUPER_GET_ALBUM"],
    "album_id":          ["GOOGLESUPER_LIST_ALBUMS", "GOOGLESUPER_LIST_SHARED_ALBUMS"],
    "mediaItemId":       ["GOOGLESUPER_LIST_MEDIA_ITEMS", "GOOGLESUPER_SEARCH_MEDIA_ITEMS"],
    # GitHub
    "issue_number":      ["GITHUB_LIST_REPOSITORY_ISSUES", "GITHUB_CREATE_AN_ISSUE"],
    "pull_number":       ["GITHUB_LIST_PULL_REQUESTS", "GITHUB_CREATE_A_PULL_REQUEST"],
    "comment_id":        ["GITHUB_LIST_ISSUE_COMMENTS",
                          "GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST",
                          "GITHUB_CREATE_AN_ISSUE_COMMENT"],
    "release_id":        ["GITHUB_LIST_RELEASES", "GITHUB_CREATE_A_RELEASE"],
    "team_slug":         ["GITHUB_LIST_TEAMS", "GITHUB_CREATE_A_TEAM"],
    "milestone_number":  ["GITHUB_LIST_MILESTONES", "GITHUB_CREATE_A_MILESTONE"],
    "review_id":         ["GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST"],
    "deployment_id":     ["GITHUB_LIST_DEPLOYMENTS", "GITHUB_CREATE_A_DEPLOYMENT"],
    "environment_name":  ["GITHUB_GET_ALL_ENVIRONMENTS",
                          "GITHUB_CREATE_OR_UPDATE_AN_ENVIRONMENT"],
    "secret_name":       ["GITHUB_LIST_REPOSITORY_SECRETS"],
    "workflow_id":       ["GITHUB_LIST_REPOSITORY_WORKFLOWS"],
    "run_id":            ["GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY",
                          "GITHUB_LIST_WORKFLOW_RUNS_FOR_A_WORKFLOW"],
    "check_run_id":      ["GITHUB_LIST_CHECK_RUNS_FOR_A_GIT_REFERENCE",
                          "GITHUB_CREATE_A_CHECK_RUN"],
    "check_suite_id":    ["GITHUB_LIST_CHECK_SUITES_FOR_A_GIT_REFERENCE"],
    "project_id":        ["GITHUB_LIST_REPOSITORY_PROJECTS",
                          "GITHUB_CREATE_A_REPOSITORY_PROJECT"],
    "hook_id":           ["GITHUB_LIST_REPOSITORY_WEBHOOKS",
                          "GITHUB_CREATE_A_REPOSITORY_WEBHOOK"],
    "key_id":            ["GITHUB_LIST_DEPLOY_KEYS", "GITHUB_CREATE_A_DEPLOY_KEY"],
    "asset_id":          ["GITHUB_LIST_RELEASE_ASSETS"],
    "artifact_id":       ["GITHUB_LIST_ARTIFACTS_FOR_A_REPOSITORY"],
    "job_id":            ["GITHUB_LIST_JOBS_FOR_A_WORKFLOW_RUN"],
    "runner_id":         ["GITHUB_LIST_SELF_HOSTED_RUNNERS_FOR_A_REPOSITORY"],
    "gist_id":           ["GITHUB_LIST_GISTS_FOR_THE_AUTHENTICATED_USER",
                          "GITHUB_CREATE_A_GIST"],
    "invitation_id":     ["GITHUB_LIST_REPOSITORY_INVITATIONS"],
    "migration_id":      ["GITHUB_GET_A_REPOSITORY_MIGRATION_STATUS"],
}

# Merge LLM producers into heuristic map (LLM adds new ones, doesn't override)
merged_producers = defaultdict(list)
for entity, slugs in HEURISTIC_PRODUCERS.items():
    for s in slugs:
        if s in valid_slugs and s not in merged_producers[entity]:
            merged_producers[entity].append(s)

for entity, slugs in llm_producers.items():
    # Normalize to match heuristic keys
    for variant in [entity, entity.replace("_", ""), entity.replace("_id","Id")]:
        if variant in merged_producers:
            for s in slugs:
                if s in valid_slugs and s not in merged_producers[variant]:
                    merged_producers[variant].append(s)
            break
    else:
        for s in slugs:
            if s in valid_slugs and s not in merged_producers[entity]:
                merged_producers[entity].append(s)

# ─── Service group classifier ─────────────────────────────────────────────────

def get_group(slug, toolkit):
    s = slug.upper()
    if toolkit == "googlesuper":
        if any(x in s for x in ["GMAIL","EMAIL","MAIL","THREAD","DRAFT","LABEL","FILTER"]):
            return "gmail"
        if any(x in s for x in ["CALENDAR","EVENT","ACL","FREEBUSY"]):
            return "calendar"
        if any(x in s for x in ["DRIVE","FILE","FOLDER","SHARED","PERMISSION"]):
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
        if any(x in s for x in ["ALBUM","PHOTO","MEDIA"]):
            return "photos"
        return "googlesuper_other"
    else:
        if any(x in s for x in ["ISSUE","MILESTONE","ASSIGNEE"]):
            return "github_issues"
        if any(x in s for x in ["PULL","REVIEW","MERGE"]):
            return "github_prs"
        if any(x in s for x in ["RELEASE","DEPLOY","COMMIT","BRANCH","TAG","CONTENT","REPO","REPOSITOR"]):
            return "github_repos"
        if any(x in s for x in ["ACTION","WORKFLOW","RUN","ARTIFACT","RUNNER","SECRET","CACHE","ENVIRONMENT"]):
            return "github_actions"
        if any(x in s for x in ["ORG","ORGANIZATION","TEAM","MEMBER"]):
            return "github_orgs"
        if any(x in s for x in ["USER","FOLLOWER","GIST","SSH","GPG"]):
            return "github_users"
        if any(x in s for x in ["CHECK","STATUS"]):
            return "github_checks"
        if any(x in s for x in ["HOOK","WEBHOOK"]):
            return "github_webhooks"
        if any(x in s for x in ["PROJECT","COLUMN","CARD"]):
            return "github_projects"
        if any(x in s for x in ["PACKAGE"]):
            return "github_packages"
        return "github_other"

# ─── Build graph ──────────────────────────────────────────────────────────────

nodes = {}      # slug → node dict
edges = []      # list of edge dicts
edge_set = set()

USER_PARAMS = {
    "name", "title", "body", "description", "type", "sort", "direction",
    "page", "per_page", "pageToken", "pageSize", "fields", "state", "labels",
    "key", "ref", "user_id", "email", "query", "owner", "repo", "org",
    "username", "branch", "parent", "color", "private", "auto_init",
    "default_branch", "visibility", "content", "message", "path",
    "accept", "subject_type", "permission", "role",
}

def add_node(slug):
    if slug in nodes or slug not in valid_slugs:
        return
    t = tool_by_slug[slug]
    toolkit = t.get("_toolkit", "unknown")
    nodes[slug] = {
        "id": slug,
        "label": t["name"],
        "description": t.get("description", "")[:250],
        "group": get_group(slug, toolkit),
        "toolkit": toolkit,
    }

def add_edge(from_slug, to_slug, param, dep_type="required"):
    if from_slug == to_slug:
        return
    if from_slug not in valid_slugs or to_slug not in valid_slugs:
        return
    key = (from_slug, to_slug)
    if key in edge_set:
        return
    edge_set.add(key)
    edges.append({
        "from": from_slug,
        "to": to_slug,
        "param": param,
        "type": dep_type,  # required / optional / semantic
    })

# ─── Pass 1: Parameter-matching (heuristic + LLM producers) ──────────────────

for tool in all_tools:
    slug = tool["slug"]
    inp = tool.get("inputParameters", {})
    all_params = set(inp.get("properties", {}).keys())
    required_params = set(inp.get("required", []))
    llm_info = llm_data.get(slug, {})
    llm_param_types = llm_info.get("param_types", {})

    id_params = {p for p in all_params
                 if p in merged_producers and p not in USER_PARAMS}

    for param in id_params:
        producers = merged_producers.get(param, [])
        # Determine dependency type
        if param in required_params:
            # Check LLM classification
            ltype = llm_param_types.get(param, "tool")
            dep_type = "optional" if ltype == "semantic" else "required"
        else:
            dep_type = "optional"

        for producer_slug in producers:
            if producer_slug != slug:
                add_node(producer_slug)
                add_node(slug)
                add_edge(producer_slug, slug, param, dep_type)

# ─── Pass 2: LLM semantic dependencies ───────────────────────────────────────

for slug, data in llm_data.items():
    if slug not in valid_slugs:
        continue
    for dep_slug in data.get("semantic_deps", []):
        if dep_slug in valid_slugs and dep_slug != slug:
            add_node(dep_slug)
            add_node(slug)
            add_edge(dep_slug, slug, "semantic", "semantic")

# ─── Pass 3: Explicit high-quality chains ────────────────────────────────────

EXPLICIT_CHAINS = [
    # Calendar
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_EVENTS_LIST",             "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_EVENTS_LIST_ALL_CALENDARS","calendar_id",   "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_GET_CALENDAR",            "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_PATCH_CALENDAR",          "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_CALENDARS_UPDATE",        "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_CALENDARS_DELETE",        "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_CLEAR_CALENDAR",          "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_ACL_LIST",                "calendar_id",    "required"),
    ("GOOGLESUPER_LIST_CALENDARS",      "GOOGLESUPER_EVENTS_INSERT",           "calendar_id",    "required"),
    ("GOOGLESUPER_EVENTS_LIST",         "GOOGLESUPER_EVENTS_GET",              "event_id",       "required"),
    ("GOOGLESUPER_EVENTS_LIST",         "GOOGLESUPER_EVENTS_UPDATE",           "event_id",       "required"),
    ("GOOGLESUPER_EVENTS_LIST",         "GOOGLESUPER_EVENTS_DELETE",           "event_id",       "required"),
    ("GOOGLESUPER_EVENTS_LIST",         "GOOGLESUPER_EVENTS_PATCH",            "event_id",       "required"),
    ("GOOGLESUPER_EVENTS_LIST",         "GOOGLESUPER_EVENTS_INSTANCES",        "event_id",       "required"),
    ("GOOGLESUPER_ACL_LIST",            "GOOGLESUPER_ACL_GET",                 "rule_id",        "required"),
    ("GOOGLESUPER_ACL_LIST",            "GOOGLESUPER_ACL_DELETE",              "rule_id",        "required"),
    ("GOOGLESUPER_ACL_LIST",            "GOOGLESUPER_ACL_PATCH",               "rule_id",        "required"),
    ("GOOGLESUPER_ACL_LIST",            "GOOGLESUPER_ACL_UPDATE",              "rule_id",        "required"),
    # Gmail
    ("GOOGLESUPER_FETCH_EMAILS",        "GOOGLESUPER_ADD_LABEL_TO_EMAIL",      "message_id",     "required"),
    ("GOOGLESUPER_FETCH_EMAILS",        "GOOGLESUPER_FORWARD_EMAIL",           "message_id",     "required"),
    ("GOOGLESUPER_FETCH_EMAILS",        "GOOGLESUPER_DELETE_THREAD",           "thread_id",      "required"),
    ("GOOGLESUPER_FETCH_EMAILS",        "GOOGLESUPER_SEND_EMAIL",              "thread_id",      "optional"),
    ("GOOGLESUPER_LIST_LABELS",         "GOOGLESUPER_PATCH_LABEL",             "label_id",       "required"),
    ("GOOGLESUPER_LIST_LABELS",         "GOOGLESUPER_UPDATE_LABEL",            "label_id",       "required"),
    ("GOOGLESUPER_LIST_LABELS",         "GOOGLESUPER_DELETE_LABEL",            "label_id",       "required"),
    ("GOOGLESUPER_LIST_LABELS",         "GOOGLESUPER_ADD_LABEL_TO_EMAIL",      "label_id",       "required"),
    ("GOOGLESUPER_LIST_DRAFTS",         "GOOGLESUPER_SEND_EMAIL_DRAFT",        "draft_id",       "required"),
    ("GOOGLESUPER_LIST_DRAFTS",         "GOOGLESUPER_DELETE_DRAFT",            "draft_id",       "required"),
    ("GOOGLESUPER_LIST_FILTERS",        "GOOGLESUPER_DELETE_GMAIL_FILTER",     "filter_id",      "required"),
    ("GOOGLESUPER_SEND_EMAIL",          "GOOGLESUPER_FETCH_EMAILS",            "semantic",       "semantic"),
    # Drive
    ("GOOGLESUPER_LIST_FILES_IN_FOLDER","GOOGLESUPER_DOWNLOAD_FILE",           "file_id",        "required"),
    ("GOOGLESUPER_LIST_FILES_IN_FOLDER","GOOGLESUPER_ADD_FILE_SHARING_PREFERENCE","file_id",     "required"),
    ("GOOGLESUPER_LIST_FILES_IN_FOLDER","GOOGLESUPER_GET_PERMISSION_ID_FOR_EMAIL","file_id",     "required"),
    ("GOOGLESUPER_GET_PERMISSION_ID_FOR_EMAIL","GOOGLESUPER_ADD_FILE_SHARING_PREFERENCE","permission_id","required"),
    ("GOOGLESUPER_LIST_SHARED_FILES",   "GOOGLESUPER_DOWNLOAD_FILE",           "file_id",        "required"),
    ("GOOGLESUPER_LIST_SHARED_FILES",   "GOOGLESUPER_ADD_FILE_SHARING_PREFERENCE","file_id",     "required"),
    # Sheets
    ("GOOGLESUPER_LIST_SPREADSHEETS",   "GOOGLESUPER_SPREADSHEETS_GET",        "spreadsheet_id", "required"),
    ("GOOGLESUPER_SPREADSHEETS_GET",    "GOOGLESUPER_SPREADSHEETS_VALUES_GET", "spreadsheetId",  "required"),
    ("GOOGLESUPER_SPREADSHEETS_GET",    "GOOGLESUPER_SPREADSHEETS_VALUES_UPDATE","spreadsheetId","required"),
    ("GOOGLESUPER_SPREADSHEETS_GET",    "GOOGLESUPER_SPREADSHEETS_VALUES_CLEAR","spreadsheetId", "required"),
    ("GOOGLESUPER_SPREADSHEETS_GET",    "GOOGLESUPER_SPREADSHEETS_VALUES_APPEND","spreadsheetId","required"),
    ("GOOGLESUPER_SPREADSHEETS_GET",    "GOOGLESUPER_SPREADSHEETS_BATCH_UPDATE","spreadsheetId", "required"),
    ("GOOGLESUPER_SPREADSHEETS_CREATE", "GOOGLESUPER_SPREADSHEETS_GET",        "spreadsheetId",  "required"),
    # Docs
    ("GOOGLESUPER_LIST_DOCS",           "GOOGLESUPER_CREATE_NEW_DOC",          "semantic",       "semantic"),
    # GitHub Issues
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_GET_AN_ISSUE",                 "issue_number",   "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_UPDATE_AN_ISSUE",              "issue_number",   "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_LOCK_AN_ISSUE",                "issue_number",   "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_ADD_ASSIGNEES_TO_AN_ISSUE",    "issue_number",   "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_REMOVE_ASSIGNEES_FROM_AN_ISSUE","issue_number",  "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_LIST_ISSUE_COMMENTS",          "issue_number",   "required"),
    ("GITHUB_LIST_REPOSITORY_ISSUES",   "GITHUB_CREATE_AN_ISSUE_COMMENT",      "issue_number",   "required"),
    ("GITHUB_CREATE_AN_ISSUE",          "GITHUB_ADD_ASSIGNEES_TO_AN_ISSUE",    "issue_number",   "required"),
    ("GITHUB_LIST_ISSUE_COMMENTS",      "GITHUB_UPDATE_AN_ISSUE_COMMENT",      "comment_id",     "required"),
    ("GITHUB_LIST_ISSUE_COMMENTS",      "GITHUB_DELETE_AN_ISSUE_COMMENT",      "comment_id",     "required"),
    ("GITHUB_LIST_MILESTONES",          "GITHUB_GET_A_MILESTONE",              "milestone_number","required"),
    ("GITHUB_LIST_MILESTONES",          "GITHUB_UPDATE_A_MILESTONE",           "milestone_number","required"),
    ("GITHUB_LIST_MILESTONES",          "GITHUB_DELETE_A_MILESTONE",           "milestone_number","required"),
    # GitHub PRs
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_GET_A_PULL_REQUEST",           "pull_number",    "required"),
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_UPDATE_A_PULL_REQUEST",        "pull_number",    "required"),
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_MERGE_A_PULL_REQUEST",         "pull_number",    "required"),
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST","pull_number",  "required"),
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_CREATE_A_REVIEW_FOR_A_PULL_REQUEST","pull_number","required"),
    ("GITHUB_LIST_PULL_REQUESTS",       "GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST","pull_number","required"),
    ("GITHUB_CREATE_A_PULL_REQUEST",    "GITHUB_MERGE_A_PULL_REQUEST",         "pull_number",    "required"),
    ("GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST","GITHUB_DISMISS_A_PULL_REQUEST_REVIEW","review_id","required"),
    ("GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST","GITHUB_SUBMIT_A_REVIEW_FOR_A_PULL_REQUEST","review_id","required"),
    ("GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST","GITHUB_UPDATE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST","comment_id","required"),
    ("GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST","GITHUB_DELETE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST","comment_id","required"),
    # GitHub Repos
    ("GITHUB_LIST_RELEASES",            "GITHUB_GET_A_RELEASE",                "release_id",     "required"),
    ("GITHUB_LIST_RELEASES",            "GITHUB_UPDATE_A_RELEASE",             "release_id",     "required"),
    ("GITHUB_LIST_RELEASES",            "GITHUB_DELETE_A_RELEASE",             "release_id",     "required"),
    ("GITHUB_LIST_RELEASES",            "GITHUB_LIST_RELEASE_ASSETS",          "release_id",     "required"),
    ("GITHUB_CREATE_A_RELEASE",         "GITHUB_UPDATE_A_RELEASE",             "release_id",     "required"),
    ("GITHUB_LIST_DEPLOY_KEYS",         "GITHUB_GET_A_DEPLOY_KEY",             "key_id",         "required"),
    ("GITHUB_LIST_DEPLOY_KEYS",         "GITHUB_DELETE_A_DEPLOY_KEY",          "key_id",         "required"),
    ("GITHUB_LIST_DEPLOYMENTS",         "GITHUB_CREATE_A_DEPLOYMENT_STATUS",   "deployment_id",  "required"),
    ("GITHUB_LIST_DEPLOYMENTS",         "GITHUB_LIST_DEPLOYMENT_STATUSES",     "deployment_id",  "required"),
    ("GITHUB_LIST_RELEASE_ASSETS",      "GITHUB_UPDATE_A_RELEASE_ASSET",       "asset_id",       "required"),
    ("GITHUB_LIST_RELEASE_ASSETS",      "GITHUB_DELETE_A_RELEASE_ASSET",       "asset_id",       "required"),
    # GitHub Actions
    ("GITHUB_LIST_REPOSITORY_WORKFLOWS","GITHUB_GET_A_WORKFLOW",               "workflow_id",    "required"),
    ("GITHUB_LIST_REPOSITORY_WORKFLOWS","GITHUB_LIST_WORKFLOW_RUNS_FOR_A_WORKFLOW","workflow_id","required"),
    ("GITHUB_LIST_WORKFLOW_RUNS_FOR_A_WORKFLOW","GITHUB_GET_A_WORKFLOW_RUN",   "run_id",         "required"),
    ("GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY","GITHUB_GET_A_WORKFLOW_RUN", "run_id",         "required"),
    ("GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY","GITHUB_DELETE_A_WORKFLOW_RUN","run_id",       "required"),
    ("GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY","GITHUB_CANCEL_A_WORKFLOW_RUN","run_id",       "required"),
    ("GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY","GITHUB_RE_RUN_A_WORKFLOW",  "run_id",         "required"),
    ("GITHUB_LIST_JOBS_FOR_A_WORKFLOW_RUN","GITHUB_RE_RUN_A_JOB_FROM_A_WORKFLOW_RUN","job_id",  "required"),
    ("GITHUB_LIST_REPOSITORY_SECRETS",  "GITHUB_CREATE_OR_UPDATE_A_REPOSITORY_SECRET","secret_name","required"),
    ("GITHUB_LIST_REPOSITORY_SECRETS",  "GITHUB_DELETE_A_REPOSITORY_SECRET",  "secret_name",    "required"),
    ("GITHUB_GET_ALL_ENVIRONMENTS",     "GITHUB_GET_AN_ENVIRONMENT",           "environment_name","required"),
    ("GITHUB_GET_ALL_ENVIRONMENTS",     "GITHUB_DELETE_AN_ENVIRONMENT",        "environment_name","required"),
    ("GITHUB_LIST_ARTIFACTS_FOR_A_REPOSITORY","GITHUB_DOWNLOAD_AN_ARTIFACT",   "artifact_id",    "required"),
    ("GITHUB_LIST_ARTIFACTS_FOR_A_REPOSITORY","GITHUB_DELETE_AN_ARTIFACT",     "artifact_id",    "required"),
    ("GITHUB_LIST_SELF_HOSTED_RUNNERS_FOR_A_REPOSITORY","GITHUB_DELETE_A_SELF_HOSTED_RUNNER_FROM_A_REPOSITORY","runner_id","required"),
    # GitHub Orgs
    ("GITHUB_LIST_TEAMS",               "GITHUB_GET_A_TEAM_BY_NAME",           "team_slug",      "required"),
    ("GITHUB_LIST_TEAMS",               "GITHUB_UPDATE_A_TEAM",                "team_slug",      "required"),
    ("GITHUB_LIST_TEAMS",               "GITHUB_DELETE_A_TEAM",                "team_slug",      "required"),
    ("GITHUB_LIST_TEAMS",               "GITHUB_LIST_TEAM_MEMBERS",            "team_slug",      "required"),
    ("GITHUB_LIST_TEAMS",               "GITHUB_LIST_TEAM_REPOSITORIES",       "team_slug",      "required"),
    # GitHub Webhooks
    ("GITHUB_LIST_REPOSITORY_WEBHOOKS", "GITHUB_GET_A_REPOSITORY_WEBHOOK",     "hook_id",        "required"),
    ("GITHUB_LIST_REPOSITORY_WEBHOOKS", "GITHUB_UPDATE_A_REPOSITORY_WEBHOOK",  "hook_id",        "required"),
    ("GITHUB_LIST_REPOSITORY_WEBHOOKS", "GITHUB_DELETE_A_REPOSITORY_WEBHOOK",  "hook_id",        "required"),
    ("GITHUB_LIST_REPOSITORY_WEBHOOKS", "GITHUB_PING_A_REPOSITORY_WEBHOOK",    "hook_id",        "required"),
    # GitHub Checks
    ("GITHUB_LIST_CHECK_RUNS_FOR_A_GIT_REFERENCE","GITHUB_UPDATE_A_CHECK_RUN", "check_run_id",   "required"),
    ("GITHUB_LIST_CHECK_SUITES_FOR_A_GIT_REFERENCE","GITHUB_REREQUEST_A_CHECK_SUITE","check_suite_id","required"),
]

for from_slug, to_slug, param, dep_type in EXPLICIT_CHAINS:
    if from_slug in valid_slugs and to_slug in valid_slugs:
        add_node(from_slug)
        add_node(to_slug)
        add_edge(from_slug, to_slug, param, dep_type)

# ─── Compute entry points, terminal nodes, BFS depth ─────────────────────────

# Entry point = no incoming edges (node with in-degree 0)
has_incoming = {e["to"] for e in edges}
has_outgoing = {e["from"] for e in edges}

for slug, node in nodes.items():
    node["is_entry"] = slug not in has_incoming
    node["is_terminal"] = slug not in has_outgoing

# BFS depth from entry points
entry_points = {s for s in nodes if nodes[s]["is_entry"]}
depth = {s: 0 for s in entry_points}
queue = deque(entry_points)
adj = defaultdict(list)
for e in edges:
    adj[e["from"]].append(e["to"])

while queue:
    slug = queue.popleft()
    for child in adj[slug]:
        if child not in depth:
            depth[child] = depth[slug] + 1
            queue.append(child)

for slug, node in nodes.items():
    node["depth"] = depth.get(slug, 0)

max_depth = max((n["depth"] for n in nodes.values()), default=0)
print(f"Max dependency depth: {max_depth}")

# ─── Stats ────────────────────────────────────────────────────────────────────

n_entry = sum(1 for n in nodes.values() if n["is_entry"])
n_terminal = sum(1 for n in nodes.values() if n["is_terminal"])
n_required = sum(1 for e in edges if e["type"] == "required")
n_optional = sum(1 for e in edges if e["type"] == "optional")
n_semantic = sum(1 for e in edges if e["type"] == "semantic")

print(f"\nGraph stats:")
print(f"  Nodes: {len(nodes)}")
print(f"  Edges: {len(edges)} (required={n_required}, optional={n_optional}, semantic={n_semantic})")
print(f"  Entry points: {n_entry}")
print(f"  Terminal nodes: {n_terminal}")

groups = defaultdict(int)
for n in nodes.values():
    groups[n["group"]] += 1
print("\nNodes by group:")
for g, c in sorted(groups.items(), key=lambda x: -x[1]):
    print(f"  {g}: {c}")

# ─── Write output ─────────────────────────────────────────────────────────────

graph = {"nodes": list(nodes.values()), "edges": edges}
with open(root / "dependency_graph.json", "w") as f:
    json.dump(graph, f, indent=2)
print(f"\nWritten dependency_graph.json")
