# ThinkLink — Student Team Composition

ThinkLink is a Django-rendered student collaboration MVP with optional Groq-powered requirement analysis, public GitHub evidence inspection, persistent student profiles, account registration, and per-user access controls.

## Run locally (Windows / VS Code)

    python -m pip install -r requirements.txt
    Copy-Item .env.example .env
    python manage.py migrate
    python manage.py seed_demo_students
    python manage.py runserver

Open http://127.0.0.1:8000. Create an account at `/accounts/signup/`; the dashboard and saved analyses require sign-in. Edit your own skills and interests at `/profile/`.

### Start FastAPI in a second VS Code terminal

    python -m uvicorn api.main:app --reload --port 8001

- API health: http://127.0.0.1:8001/health
- API docs: http://127.0.0.1:8001/docs
- Student profiles: http://127.0.0.1:8001/v1/students
- Team analysis: POST http://127.0.0.1:8001/v1/team-analysis
- Saved analysis summaries: http://127.0.0.1:8001/v1/analyses

The FastAPI health endpoint is public. Its student, analysis, and saved-analysis endpoints require `Authorization: Bearer <INTERNAL_API_TOKEN>`. Configure that token only if you run the separate service; do not put it in browser JavaScript. The first Vercel deployment should use the Django application and its session-authenticated endpoints, not expose this internal service.

Example request body for /v1/team-analysis:

    {
      "title": "Campus Opportunity AI",
      "problem_statement": "Build a secure AI-powered campus opportunity platform with recommendations and a web dashboard.",
      "student_slugs": ["maya", "arjun", "isha"]
    }

## Groq AI setup

1. Create a Groq API key at the official Groq Console: https://console.groq.com/keys
2. Open the local .env file and set GROQ_API_KEY=your_key_here.
3. The default model is openai/gpt-oss-20b; change GROQ_MODEL only to a model supported by your Groq account.
4. Restart Django after changing .env.

The key must stay server-side in .env or a secrets manager. Never paste it into source code, browser JavaScript, GitHub, or a chat. Groq usage is subject to its current account limits and model-specific rate limits. If no key is configured or the request fails, ThinkLink falls back to transparent rule-based analysis.

## GitHub evidence

- Enter a GitHub username in the dashboard to inspect public repositories.
- The integration shows repository names and links only, plus separately labelled technology/skill signals.
- A bounded sample of public source files and repository metadata is inspected; repository code is never executed.
- You can associate findings only with your own signed-in student profile. Findings for other public profiles are not saved to their records. Detected skills are stored separately from self-reported skills.
- Public GitHub access works without a token, but unauthenticated API limits are low. An optional fine-grained token with public read access can be set as GITHUB_TOKEN in .env. No write scopes are needed.
- Repository activity is not proof of authorship, contribution, or proficiency. Forks are excluded from the repository list; no GitHub account is required for a student to be considered.

## Database and persistence

- Student profiles and team-analysis snapshots use Django ORM models and migrations; private profiles and saved analyses are scoped to their owner.
- SQLite remains the default for local development until DATABASE_URL is configured.
- Selected hosted PostgreSQL provider: Neon Free ($0/month within published quotas). Create a project on the official Neon Console: https://console.neon.tech/ and copy its pooled or direct PostgreSQL connection string into DATABASE_URL in .env. Do not share the connection string in chat or commit it to Git.
- Use the PostgreSQL connection string format provided by Neon; ensure SSL is enabled. Then run:

    python manage.py migrate
    python manage.py seed_demo_students

- Neon Free has quotas and may suspend compute after monthly limits are exhausted; verify the current limits before relying on it for a demo. Free tiers and limits can change.
- The Django web app and FastAPI service share the same ORM models and configured database. The current code is local-development oriented. Production-mode Django settings now fail closed on the built-in development secret and enable secure cookies, HSTS, content-type protection, and HTTPS redirect by default when `DJANGO_DEBUG=False`. Set exact `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` values for the deployed host. HTTPS proxy configuration depends on the selected host; verify it before deployment.

**Public deployment remains blocked** until authentication/authorization, record-level access control, privacy/consent and data deletion flows, API rate limiting, request-size limits, and production hosting configuration are implemented and tested. See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for release blockers and verification steps, and [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for the planned Vercel + GitHub deployment.

## Implemented in this prototype

- Problem-aware team composition with Groq-assisted or rule-based requirements analysis.
- Skill coverage, gaps, rationale, and teammate suggestions.
- Persisted profiles and saved team-analysis snapshots.
- GitHub public repository inspection and separately stored inferred skill evidence.
- Django admin for profile/analysis management.
- Django JSON endpoints and a FastAPI service with OpenAPI docs.
- Responsive dashboard and print-friendly report.

## Authentication and access control

- The dashboard, GitHub inspection form, student JSON endpoint, and saved-analysis endpoint require a signed-in Django session.
- Sign-up creates a Django user and a linked private student profile. Passwords are hashed by Django and password validation is enabled.
- Users can see public demo profiles plus their own profile; another user's private profile is excluded.
- Team-analysis snapshots are owned by the signed-in user. The saved-analysis endpoint returns only that user's records.
- GitHub evidence can only be associated with the current user's own profile.
- The separate FastAPI service protects data endpoints with `Authorization: Bearer <INTERNAL_API_TOKEN>` and fails closed when the token is not configured. Its health endpoint remains public.
- Production launch still requires rate limiting, privacy/consent and deletion flows, production environment configuration, and deployment verification. Do not treat the current build as fully production-ready.

## Known limitations

- Six student profiles are illustrative sample data, not real users.
- Skills in demo profiles are self-reported and unverified.
- GitHub skill inference is a bounded heuristic sample, not a contribution graph or a definitive skill test.
- Collaboration-style, availability-overlap, and interest matching are not yet part of the numeric coverage score.
- No ChromaDB is used: semantic/vector retrieval is not currently needed.
- Email verification, password reset, account deletion, consent and privacy workflows, and abuse/rate limiting are not yet implemented. Complete these before inviting real students.
