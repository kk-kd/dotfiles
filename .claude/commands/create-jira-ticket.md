Create a Jira ticket using the jira skill.

Steps:
1. Ask the user for a **summary** (required) and **description** (optional).
2. Ask for **issue type** (Task, Bug, Story, Subtask — default: Task).
3. Only ask about optional fields (parent, sprint, labels, priority, story points, assignee) if the user mentions them or context suggests they're needed.
4. Run `bash ~/.claude/skills/jira/scripts/jira.sh create --summary "..." --type "..." [other flags]`.
5. If the user wants a sprint assignment, first run `bash ~/.claude/skills/jira/scripts/jira.sh list-sprints` to find the sprint ID, then `bash ~/.claude/skills/jira/scripts/jira.sh move-to-sprint --sprint ID --issue TICKET_KEY`.
6. After creation, ask if the user wants a git branch: `git checkout -b TICKET_KEY`.
