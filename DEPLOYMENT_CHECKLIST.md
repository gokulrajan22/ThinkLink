# ThinkLink Deployment Readiness Checklist

**Current status: pre-production. Do not expose publicly until every blocker below is resolved.**

## Identity and access control

- [x] Django session login/logout and account creation.
- [x] Password hashing through Django; password strength validation.
- [x] Dashboard, GitHub inspection, and private Django JSON endpoints require authentication.
- [x] Student profiles are scoped to demo profiles plus the signed-in user's own profile.
- [x] Saved team analyses have an owner and are only returned to that owner.
- [x] GitHub skill evidence can only be associated with the signed-in user's own profile.
- [x] Separate FastAPI data endpoints fail closed without a configured bearer token.
- [ ] Add login/signup rate limiting and abuse monitoring.
- [ ] Add email verification, password reset, and account deletion.
- [x] Add profile editing for the signed-in user's own skills/interests and availability.
- [ ] Add user-facing data export/correction.

## Environment and Django security

- [x] Production mode rejects placeholder/development secrets and localhost-only/wildcard hosts.
- [x] Production secure cookies, HTTPS redirect, HSTS, content-type protection, and frame denial configured.
- [x] CSRF trusted origins configurable.
- [x] PostgreSQL connection lifetime defaults to zero on Vercel serverless runtime.
- [ ] Set real production DJANGO_SECRET_KEY in Vercel's secret environment.
- [ ] Set exact DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS values after the Vercel hostname exists.
- [ ] Verify Vercel forwarded HTTPS behavior and python manage.py check --deploy in the production environment.
- [ ] Verify production static assets and admin pages.
- [ ] Confirm provider-managed PostgreSQL backup and restore procedures.

## Privacy and operational safety — release blockers

- [ ] Add a clear privacy notice and consent before processing personal profile data and public GitHub evidence.
- [ ] Define retention, deletion, and correction workflows for profile data and generated analyses.
- [ ] Add persistent/distributed rate limiting and request-size limits for expensive AI/GitHub routes.
- [ ] Review API payloads for personal-data minimization and verify every endpoint's authorization.
- [ ] Add security/dependency scanning and deployment monitoring.
- [ ] Keep demo seed data out of production unless deliberately approved.
- [ ] Test backup restoration, rollback, and dependency updates before the student pilot.

## Vercel + GitHub release

- [x] Added .python-version (Python 3.12).
- [x] Added Vercel deployment instructions in VERCEL_DEPLOYMENT.md.
- [ ] Review repository for secrets and generated database files.
- [ ] Create/push the GitHub repository named ThinkLink after the user confirms the target repository/account.
- [ ] Import that repository into Vercel and configure production/preview environment variables.
- [ ] Apply migrations to the intended production database through a controlled release step.
- [ ] Complete end-to-end smoke tests on a Vercel preview before production promotion.

## Verification commands

    python -m compileall -q config core api
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test -v 1
    python manage.py check --deploy
    python manage.py collectstatic --noinput

Run production checks with the actual deployment environment, not local development defaults. Resolve relevant warnings instead of suppressing them without review.
