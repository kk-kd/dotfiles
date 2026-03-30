#!/usr/bin/env bash
# Jira Cloud REST API wrapper for Claude Code skills.
# Usage: jira.sh <command> [args...]
#
# Config is loaded from ~/.config/jira/.env (KEY=VALUE, one per line).
# Required: JIRA_EMAIL, JIRA_API_TOKEN, CLOUD_ID
# Optional: JIRA_PROJECT (default project key), JIRA_SITE (for browse URLs)
set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────

JIRA_ENV="${HOME}/.config/jira/.env"

die() { echo "error: $*" >&2; exit 1; }

# Load config from dotenv file
if [[ -f "$JIRA_ENV" ]]; then
    while IFS='=' read -r key value; do
        # Skip comments and blank lines
        [[ -z "$key" || "$key" == \#* ]] && continue
        # Strip surrounding quotes from value
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        export "$key=$value"
    done < "$JIRA_ENV"
fi

require_env() {
    local var="$1"
    if [[ -z "${!var:-}" ]]; then
        die "$var is not set. Add it to ${JIRA_ENV}"
    fi
}

require_env JIRA_EMAIL
require_env JIRA_API_TOKEN
require_env CLOUD_ID

JIRA_BASE="https://api.atlassian.com/ex/jira/${CLOUD_ID}"
AUTH_HEADER="Authorization: Basic $(printf '%s' "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64)"
PROJECT="${JIRA_PROJECT:-}"
SITE="${JIRA_SITE:-}"

jira_api() {
    local method="$1" path="$2"
    shift 2
    curl -sf -X "$method" \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        "${JIRA_BASE}${path}" \
        "$@"
}

# ── commands ─────────────────────────────────────────────────────────────────

cmd_create() {
    # Usage: jira.sh create --summary "..." --type Task [--description "..."]
    #   [--project ENG] [--parent ENG-123] [--priority High]
    #   [--labels "l1,l2"] [--points 3] [--assignee email@...]
    local summary="" description="" issue_type="Task" project="${PROJECT}"
    local parent="" priority="" labels="" points="" assignee=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --summary)    summary="$2"; shift 2 ;;
            --description) description="$2"; shift 2 ;;
            --type)       issue_type="$2"; shift 2 ;;
            --project)    project="$2"; shift 2 ;;
            --parent)     parent="$2"; shift 2 ;;
            --priority)   priority="$2"; shift 2 ;;
            --labels)     labels="$2"; shift 2 ;;
            --points)     points="$2"; shift 2 ;;
            --assignee)   assignee="$2"; shift 2 ;;
            *) die "unknown flag: $1" ;;
        esac
    done

    [[ -n "$summary" ]] || die "missing --summary"
    [[ -n "$project" ]] || die "missing --project (set JIRA_PROJECT or pass --project)"

    # Build base payload
    local payload
    payload=$(jq -n \
        --arg summary "$summary" \
        --arg desc "${description:-}" \
        --arg type "$issue_type" \
        --arg project "$project" \
        '{
            fields: {
                project: { key: $project },
                summary: $summary,
                issuetype: { name: $type }
            }
        } | if $desc != "" then .fields.description = {
                type: "doc",
                version: 1,
                content: [{ type: "paragraph", content: [{ type: "text", text: $desc }] }]
            } else . end')

    # Add optional fields
    if [[ -n "$parent" ]]; then
        payload=$(echo "$payload" | jq --arg key "$parent" '.fields.parent = { key: $key }')
    fi
    if [[ -n "$priority" ]]; then
        payload=$(echo "$payload" | jq --arg p "$priority" '.fields.priority = { name: $p }')
    fi
    if [[ -n "$labels" ]]; then
        payload=$(echo "$payload" | jq --arg l "$labels" '.fields.labels = ($l | split(","))')
    fi
    if [[ -n "$points" ]]; then
        payload=$(echo "$payload" | jq --argjson p "$points" '.fields.customfield_10016 = $p')
    fi
    if [[ -n "$assignee" ]]; then
        local account_id
        account_id=$(jira_api GET "/rest/api/3/user/search?query=${assignee}" | jq -r '.[0].accountId // empty')
        if [[ -z "$account_id" ]]; then
            echo "warning: could not find assignee '${assignee}', skipping assignment" >&2
        else
            payload=$(echo "$payload" | jq --arg id "$account_id" '.fields.assignee = { accountId: $id }')
        fi
    fi

    local response
    response=$(jira_api POST "/rest/api/3/issue" -d "$payload")

    local ticket_key
    ticket_key=$(echo "$response" | jq -r '.key')

    echo "Created: ${ticket_key}"
    if [[ -n "$SITE" ]]; then
        echo "Link:    https://${SITE}/browse/${ticket_key}"
    fi
    echo "$ticket_key"
}

cmd_list_sprints() {
    # Usage: jira.sh list-sprints [--board BOARD_ID] [--state active,future]
    local board_id="1" state="active,future"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --board) board_id="$2"; shift 2 ;;
            --state) state="$2"; shift 2 ;;
            *) die "unknown flag: $1" ;;
        esac
    done

    jira_api GET "/rest/agile/1.0/board/${board_id}/sprint?state=${state}" \
        | jq '.values[] | {id, name, state}'
}

cmd_move_to_sprint() {
    # Usage: jira.sh move-to-sprint --sprint SPRINT_ID --issue TICKET_KEY
    local sprint_id="" issue=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sprint) sprint_id="$2"; shift 2 ;;
            --issue)  issue="$2"; shift 2 ;;
            *) die "unknown flag: $1" ;;
        esac
    done

    [[ -n "$sprint_id" ]] || die "missing --sprint"
    [[ -n "$issue" ]]     || die "missing --issue"

    jira_api POST "/rest/agile/1.0/sprint/${sprint_id}/issue" \
        -d "{\"issues\": [\"${issue}\"]}"

    echo "Moved ${issue} to sprint ${sprint_id}"
}

cmd_search_user() {
    # Usage: jira.sh search-user <query>
    [[ $# -ge 1 ]] || die "usage: jira.sh search-user <query>"
    jira_api GET "/rest/api/3/user/search?query=$1" \
        | jq '.[] | {accountId, displayName, emailAddress}'
}

cmd_get() {
    # Usage: jira.sh get <issue-key>
    [[ $# -ge 1 ]] || die "usage: jira.sh get <issue-key>"
    jira_api GET "/rest/api/3/issue/$1" \
        | jq '{key: .key, summary: .fields.summary, status: .fields.status.name, assignee: .fields.assignee.displayName, priority: .fields.priority.name, type: .fields.issuetype.name}'
}

cmd_search() {
    # Usage: jira.sh search --jql "project = ENG AND status = 'In Progress'" [--max 20]
    local jql="" max_results="20"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --jql) jql="$2"; shift 2 ;;
            --max) max_results="$2"; shift 2 ;;
            *) die "unknown flag: $1" ;;
        esac
    done

    [[ -n "$jql" ]] || die "missing --jql"

    local payload
    payload=$(jq -n --arg jql "$jql" --argjson max "$max_results" '{jql: $jql, maxResults: $max, fields: ["summary", "status", "assignee", "priority", "issuetype"]}')

    jira_api POST "/rest/api/3/search" -d "$payload" \
        | jq '.issues[] | {key: .key, summary: .fields.summary, status: .fields.status.name, assignee: .fields.assignee.displayName, priority: .fields.priority.name, type: .fields.issuetype.name}'
}

# ── dispatch ─────────────────────────────────────────────────────────────────

cmd="${1:-help}"
shift || true

case "$cmd" in
    create)         cmd_create "$@" ;;
    list-sprints)   cmd_list_sprints "$@" ;;
    move-to-sprint) cmd_move_to_sprint "$@" ;;
    search-user)    cmd_search_user "$@" ;;
    get)            cmd_get "$@" ;;
    search)         cmd_search "$@" ;;
    help|--help|-h)
        echo "Usage: jira.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  create          Create a Jira issue"
        echo "  get             Get issue details"
        echo "  search          Search issues via JQL"
        echo "  list-sprints    List board sprints"
        echo "  move-to-sprint  Move issue to a sprint"
        echo "  search-user     Search for a Jira user"
        echo ""
        echo "Config: ~/.config/jira/.env"
        echo "Required: JIRA_EMAIL, JIRA_API_TOKEN, CLOUD_ID"
        echo "Optional: JIRA_PROJECT, JIRA_SITE"
        ;;
    *) die "unknown command: $cmd (run with --help)" ;;
esac
