# ThinkLink Frontend Files

This directory contains a separated working copy of the existing ThinkLink interface files.

## Structure

- `templates/core/dashboard.html` — signed-in dashboard, team builder, skill analysis and GitHub evidence UI.
- `templates/registration/` — login, signup, profile, privacy, account deletion, verification and password-reset templates.
- `static/core/app.css` — shared dashboard styling.

## Important: this is a Django-template frontend, not a standalone SPA

These HTML files contain Django template tags such as `{% csrf_token %}`, `{% url ... %}`, `{% static ... %}` and context variables such as `{{ request.user }}`. They require the Django backend and template context to render correctly. They are not directly runnable by opening the HTML files in a browser and are not a React/Vite application.

## Integration

The original working files remain in the project's root `templates/` and `static/` directories. This `frontend/` directory is a copied workspace for organizing frontend work; it does not automatically replace the original templates or change Django's template/static settings. After making changes here, copy the relevant files back to the matching root directories or deliberately update Django settings and deployment configuration.

## Start the current app

From the project root, follow the project's README and run the Django application. The current website is served by Django, while FastAPI is a separate API service.
