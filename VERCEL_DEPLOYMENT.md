# ThinkLink deployment on Vercel

**Do not deploy to production until every release blocker in DEPLOYMENT_CHECKLIST.md is resolved.** The repository is being prepared for deployment; no GitHub repository has been pushed and no Vercel project has been created yet.

## Intended deployment shape

- Django is the primary web application and serves HTML templates, session authentication, and Django JSON endpoints.
- PostgreSQL is the persistent database. Use the existing Neon PostgreSQL provider or a PostgreSQL integration from the Vercel Marketplace.
- Groq and GitHub credentials remain server-side environment variables.
- The separate FastAPI service is not required for the first Vercel deployment. If deployed separately, keep it private and configure INTERNAL_API_TOKEN; never expose this token in browser code.

Vercel's current Python runtime supports Django and can detect Django projects from the project structure. Keep manage.py, requirements.txt, and the Django project package at the repository root. See the official Vercel Python runtime documentation and Django support announcement:
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/changelog/zero-configuration-django-support

## Vercel project configuration

After the repository is reviewed and pushed to the user's GitHub account:

1. Sign in to Vercel and import the ThinkLink GitHub repository.
2. Keep the project root at the repository root (the directory containing manage.py).
3. Let Vercel detect the Django/Python project; do not add a custom build command unless the deployment build requires it.
4. Configure these environment variables in Vercel Production, Preview, and Development scopes as appropriate:
   - DJANGO_DEBUG=False
   - DJANGO_SECRET_KEY: unique high-entropy value generated for deployment; do not reuse the local development key.
   - DJANGO_ALLOWED_HOSTS: exact production hostname(s), including the assigned .vercel.app hostname; no wildcard.
   - DJANGO_CSRF_TRUSTED_ORIGINS: exact HTTPS origin(s), for example https://your-project.vercel.app (replace with the actual hostname).
   - DJANGO_SECURE_SSL_REDIRECT=True
   - DATABASE_URL: persistent PostgreSQL connection string suitable for serverless functions, with TLS.
   - EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL: a verified SMTP sender for account verification and password recovery. Production startup fails closed if these are missing.
   - GROQ_API_KEY and GROQ_MODEL only if AI-assisted analysis is enabled.
   - GITHUB_TOKEN only if needed for public GitHub API rate limits.
5. Do not set INTERNAL_API_TOKEN unless the separate FastAPI service is actually deployed and needs to be protected.
6. Configure a persistent PostgreSQL database. Do not rely on SQLite or local filesystem writes for production data on serverless functions.
7. Run migrations against the intended production database as a controlled release step; do not automatically seed demo data into production.
8. Verify static assets, sign-up, sign-in, sign-out, CSRF, private analysis isolation, database writes, logs, and the deployment health check.
9. Keep preview deployments on a separate database or isolated schema so test data and migrations cannot affect production.
10. Run `python manage.py cleanup_rate_limits` on a regular maintenance schedule (e.g. daily/weekly) to delete rate-limit records inactive for 30 days. Do not schedule this until the database and deployment secrets are available to the scheduler.
11. Confirm the email provider's domain authentication (SPF/DKIM/DMARC), delivery and bounce handling before opening registration.

## Important operational notes

- SECURE_PROXY_SSL_HEADER is configured for Vercel's forwarded HTTPS protocol. Verify HTTPS redirect and CSRF behavior on a preview deployment before production.
- DB_CONN_MAX_AGE defaults to 0 when the VERCEL environment variable is present to avoid stale database connections in request-scoped functions.
- collectstatic and static asset delivery must be verified against the deployed Vercel build; do not assume local static behavior guarantees production behavior.
- Vercel plans, runtime behavior, build limits, and Marketplace provider pricing can change. Confirm the current plan and database limits before launching.
- Do not commit .env, database files, user exports, logs, or any credentials. .env.example contains placeholders only.
