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

# Load config from dotenv file (allowlisted keys only)
ALLOWED_KEYS="JIRA_EMAIL JIRA_API_TOKEN CLOUD_ID JIRA_PROJECT JIRA_SITE"
if [[ -f "$JIRA_ENV" ]]; then
    # Warn if the env file is readable by others
    local_perms=$(stat -f '%Lp' "$JIRA_ENV" 2>/dev/null || stat -c '%a' "$JIRA_ENV" 2>/dev/null)
    if [[ "$local_perms" != "600" ]]; then
        echo "warning: ${JIRA_ENV} is mode ${local_perms}, should be 600 (chmod 600 ${JIRA_ENV})" >&2
    fi

    while IFS='=' read -r key value; do
        # Skip comments and blank lines
        [[ -z "$key" || "$key" == \#* ]] && continue
        # Only export known keys
        [[ " $ALLOWED_KEYS " == *" $key "* ]] || continue
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
PROJECT="${JIRA_PROJECT:-}"
SITE="${JIRA_SITE:-}"

# Write auth header to a temp file so it doesn't appear in `ps` output
AUTH_FILE=$(mktemp)
trap 'rm -f "$AUTH_FILE"' EXIT
printf 'Authorization: Basic %s' "$(printf '%s' "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64)" > "$AUTH_FILE"

jira_api() {
    local method="$1" path="$2"
    shift 2
    curl -s --fail-with-body -X "$method" \
        -H @"$AUTH_FILE" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        "${JIRA_BASE}${path}" \
        "$@"
}

# ── input validation ────────────────────────────────────────────────────────

validate_issue_key() {
    [[ "$1" =~ ^[A-Z][A-Z0-9]+-[0-9]+$ ]] || die "invalid issue key: $1"
}

validate_project_key() {
    [[ "$1" =~ ^[A-Z][A-Z0-9_]+$ ]] || die "invalid project key: $1"
}

validate_integer() {
    [[ "$1" =~ ^[0-9]+$ ]] || die "expected integer, got: $1"
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
    validate_project_key "$project"
    [[ -z "$parent" ]] || validate_issue_key "$parent"
    [[ -z "$points" ]] || validate_integer "$points"

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

    validate_integer "$board_id"
    [[ "$state" =~ ^[a-z,]+$ ]] || die "invalid state: $state"

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
    validate_integer "$sprint_id"
    validate_issue_key "$issue"

    local payload
    payload=$(jq -n --arg issue "$issue" '{issues: [$issue]}')
    jira_api POST "/rest/agile/1.0/sprint/${sprint_id}/issue" -d "$payload"

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
    validate_issue_key "$1"
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
    validate_integer "$max_results"

    local payload
    payload=$(jq -n --arg jql "$jql" --argjson max "$max_results" '{jql: $jql, maxResults: $max, fields: ["summary", "status", "assignee", "priority", "issuetype"]}')

    jira_api POST "/rest/api/3/search" -d "$payload" \
        | jq '.issues[] | {key: .key, summary: .fields.summary, status: .fields.status.name, assignee: .fields.assignee.displayName, priority: .fields.priority.name, type: .fields.issuetype.name}'
}

cmd_update() {
    # Usage: jira.sh update <issue-key> --parent ENG-123 [--summary "..."]
    #   [--priority High] [--labels "l1,l2"] [--assignee email@...]
    #   [--status "In Progress"] [--type Bug]
    [[ $# -ge 1 ]] || die "usage: jira.sh update <issue-key> [--field value ...]"
    local issue_key="$1"; shift
    validate_issue_key "$issue_key"

    local parent="" summary="" priority="" labels="" assignee="" status="" issue_type=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --parent)   parent="$2"; shift 2 ;;
            --summary)  summary="$2"; shift 2 ;;
            --priority) priority="$2"; shift 2 ;;
            --labels)   labels="$2"; shift 2 ;;
            --assignee) assignee="$2"; shift 2 ;;
            --status)   status="$2"; shift 2 ;;
            --type)     issue_type="$2"; shift 2 ;;
            *) die "unknown flag: $1" ;;
        esac
    done

    [[ -z "$parent" ]] || validate_issue_key "$parent"

    local payload='{"fields":{}}'

    if [[ -n "$parent" ]]; then
        payload=$(echo "$payload" | jq --arg key "$parent" '.fields.parent = { key: $key }')
    fi
    if [[ -n "$summary" ]]; then
        payload=$(echo "$payload" | jq --arg s "$summary" '.fields.summary = $s')
    fi
    if [[ -n "$priority" ]]; then
        payload=$(echo "$payload" | jq --arg p "$priority" '.fields.priority = { name: $p }')
    fi
    if [[ -n "$labels" ]]; then
        payload=$(echo "$payload" | jq --arg l "$labels" '.fields.labels = ($l | split(","))')
    fi
    if [[ -n "$issue_type" ]]; then
        payload=$(echo "$payload" | jq --arg t "$issue_type" '.fields.issuetype = { name: $t }')
    fi
    if [[ -n "$assignee" ]]; then
        local account_id
        account_id=$(jira_api GET "/rest/api/3/user/search?query=${assignee}" | jq -r '.[0].accountId // empty')
        if [[ -z "$account_id" ]]; then
            echo "warning: could not find assignee '${assignee}', skipping" >&2
        else
            payload=$(echo "$payload" | jq --arg id "$account_id" '.fields.assignee = { accountId: $id }')
        fi
    fi

    jira_api PUT "/rest/api/3/issue/${issue_key}" -d "$payload"

    # Transition (status change) requires a separate call
    if [[ -n "$status" ]]; then
        local transitions
        transitions=$(jira_api GET "/rest/api/3/issue/${issue_key}/transitions")
        local transition_id
        transition_id=$(echo "$transitions" | jq -r --arg name "$status" '.transitions[] | select(.name == $name) | .id' | head -1)
        if [[ -z "$transition_id" ]]; then
            echo "warning: no transition found to status '${status}'" >&2
        else
            local t_payload
            t_payload=$(jq -n --arg id "$transition_id" '{transition: {id: $id}}')
            jira_api POST "/rest/api/3/issue/${issue_key}/transitions" -d "$t_payload"
        fi
    fi

    echo "Updated: ${issue_key}"
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
    update)         cmd_update "$@" ;;
    help|--help|-h)
        echo "Usage: jira.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  create          Create a Jira issue"
        echo "  update          Update an existing issue"
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
