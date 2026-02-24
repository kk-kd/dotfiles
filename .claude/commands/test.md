Generate or fix tests for the code I've selected or the current file.

Rules:

- Use `pytest`. Prefer fixtures and `@pytest.mark.parametrize` over copy-paste tests.
- Each test function tests ONE behavior. Name it `test_<function>_<scenario>`.
- Include edge cases: empty input, None, boundary values, error paths.
- Mock external dependencies (DB, HTTP, filesystem) — never hit real services.
- If tests already exist and are failing, diagnose the failure and fix them.
- After writing tests, run `pytest` on the file to confirm they pass.
- If any fail, fix them until green.

Output the test file and the pytest results.
