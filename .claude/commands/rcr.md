Respond to code review comments on the current PR.

Steps:
1. Run `gh pr view --json reviews,comments` to fetch review feedback.
2. For each comment or requested change:
   - Read the reviewer's feedback.
   - If the feedback is valid, make the fix directly — no discussion needed.
   - If you disagree, draft a concise reply explaining why (1-2 sentences).
3. After making all fixes:
   - Run linters/tests to confirm nothing broke.
   - Stage and commit with `fix: address review feedback` (or more specific if warranted).
   - Push the changes.
4. Resolve addressed review threads:
   - List the comment threads you fixed or replied to.
   - Ask the user for permission before resolving any threads.
   - If approved, resolve them using the GraphQL API:
     - First fetch thread IDs: `gh api graphql -f query='{ repository(owner:"OWNER",name:"REPO") { pullRequest(number:NUM) { reviewThreads(first:100) { nodes { id isResolved comments(first:1) { nodes { body } } } } } } }'`
     - Then resolve each: `gh api graphql -f query='mutation { resolveReviewThread(input:{threadId:"THREAD_ID"}) { thread { id } } }'`
   - Only resolve threads where the feedback was accepted and the fix was pushed. Do NOT resolve threads where you pushed back.
5. Summarize what was addressed, what was pushed back on, and which threads were resolved.

Bias toward accepting feedback. Only push back when the reviewer is factually wrong or the suggestion would degrade the code.
