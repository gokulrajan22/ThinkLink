# ThinkLink — Complete Project Handoff for Codex

**Prepared:** 2026-10-26  
**Purpose:** Carry the available AIMORA project discussions, decisions, requirements, and next steps to Codex on another device.

> **Important scope limitation:** This is a consolidated handoff based on the project-chat history available in this session, including summaries of earlier conversations. It is not a verbatim export of every message. Unknown details are explicitly marked rather than invented.

---

## 1. Project identity and working context

- **Current application name:** ThinkLink
- **Workspace/project context:** AIMORA
- **Intended audience:** Students
- **Hosting target:** Vercel
- **Source control target:** A GitHub repository owned by the user
- **AI provider:** Groq
- **Database choice:** PostgreSQL, option B
- **Documentation approach:** Repository documentation and a project handoff document; Obsidian may be used alongside them.
- **Project organization preference:** Use separate chats for each development phase within the AIMORA project. Keep a folder of concise phase notes so key decisions and progress can be recovered later.
- **User workflow preference:** The user wants to see the application while development continues, not only receive descriptions of it.

## 2. Confirmed decisions

### 2.1 Naming
The project should be called **ThinkLink**. Earlier workspace/context references use AIMORA; do not confuse the workspace name with the current application name.

### 2.2 AI integration
- Use **Groq** as the AI API provider.
- Keep API keys on the server and in environment-variable/secret configuration.
- Never commit keys, expose them in browser code, or copy real secret values into documentation.
- The exact model, prompts, AI features, usage limits, and fallback behavior have not been specified in the available context.

### 2.3 Database
- PostgreSQL **option B** was selected.
- The user confirmed that both requested configuration items were configured/saved.
- The exact provider, connection URL, schema, migrations, and current connection status are not present in this handoff. Inspect the repository and environment configuration; do not assume they work solely because they were previously marked saved.

### 2.4 ChromaDB
Use ChromaDB **if and only if** the product is going to include AI functionality that requires it. This is conditional, not a blanket instruction to install it now. Confirm whether the planned AI features require embeddings, semantic retrieval, or RAG before adding ChromaDB.

### 2.5 Deployment and repository
- Hosting target: **Vercel**.
- Source repository: a GitHub repository under the user's account.
- The user asked to make the application ready for public deployment.
- The user explicitly requested that work start with **authentication and access control**.
- The user asked to complete every task required for the application.
- The available chat context does not prove that a repository was connected, a deployment occurred, or authentication was implemented. Verify actual state before claiming completion.

## 3. Available conversation history

### Chat: “Application Development Capabilities”
**Date in project history:** 2026-10-24

The available summary records these points:
1. ChromaDB should be chosen if and only if AI functionality is planned.
2. Obsidian can be used alongside the project control center, repository documentation, and project handoff documentation.
3. Create a separate chat inside the AIMORA project for each development phase.
4. Create a folder inside the project folder to keep crisp notes and preserve key points from each phase.
5. The application will be used by students.
6. The user asked whether they could explain the application in the project discovery chat.

The full product explanation and requirements are not included in the available summary. Do not invent product functionality based on the name ThinkLink alone.

### Chat: “Product Discovery Planning”
**Date in project history:** 2026-10-25

The available summary records this sequence:
1. Change the AI API provider to Groq.
2. Choose PostgreSQL option B.
3. The user confirmed both configuration items were configured/saved.
4. The user asked to see the application on the side while development continued.
5. The user confirmed that the application was visible and asked to continue.
6. Rename the project to ThinkLink.
7. Prepare the project for public deployment.
8. Start with authentication and access control.
9. Use Vercel for hosting and a GitHub repository owned by the user.
10. The user asked to complete every task.

### Current chat: “Codex handoff”
**Date:** 2026-10-26

The user requested a Markdown file containing the available chats to give Codex access to the project context on another device. This document is that consolidated handoff; it is not a full raw transcript of every historical message.

## 4. Development priorities

The latest explicit priority is authentication and access control, followed by the work needed for safe public deployment.

### Phase 0 — Inspect and establish the baseline
- Inspect repository files, framework, package manager, scripts, existing architecture, and git status.
- Identify implemented features and unfinished work.
- Locate environment-variable documentation without printing or exposing secret values.
- Check whether Groq and PostgreSQL integration already exist.
- Run available checks before changing code and record the baseline.
- Preserve working features; avoid replacing the architecture without a clear reason.

### Phase 1 — Authentication and access control
- Choose or use a maintained authentication solution appropriate to the actual stack.
- Implement sign-in/sign-up flows required by the product.
- Add server-side session and identity validation.
- Protect routes, server actions, API handlers, and database operations.
- Define roles and permissions only after checking product requirements; do not invent roles.
- Enforce ownership checks so one user cannot access or modify another user's records by changing an ID or request body.
- Add suitable logout, session expiry, password reset, email verification, and account recovery flows where required by the selected authentication method.
- Test unauthenticated access, forbidden access, and cross-user data access.
- Do not treat hiding a button or page in the UI as authorization.

### Phase 2 — PostgreSQL
- Verify the actual database provider and connection configuration.
- Keep connection credentials in environment variables.
- Review schema, migrations, indexes, constraints, and data ownership.
- Use safe parameterized queries or a suitable ORM.
- Document migrations, backup expectations, and recovery procedures.
- Verify that database operations enforce authorization.

### Phase 3 — Groq and AI
- Inspect the actual AI feature requirements before implementation.
- Use Groq from server-side code only.
- Add request validation, error handling, timeouts, and appropriate abuse/usage limits.
- Avoid logging private prompts, sensitive user content, or credentials unnecessarily.
- Add ChromaDB only if an implemented AI feature needs vector search/retrieval.
- Document the selected model and configuration once verified from the code or user requirements.

### Phase 4 — Public-deployment preparation
- Configure Vercel for the detected framework and build commands.
- Configure environment variables separately for local development, preview, and production.
- Configure the GitHub repository and any CI checks after confirming the target repository.
- Check production URLs, authentication callback URLs, cookie settings, HTTPS, CORS, and security headers.
- Ensure `.env` and other secret-bearing files are ignored by Git.
- Provide a safe `.env.example` with variable names and placeholder values only.
- Add a clear README with setup, development, testing, migrations, and deployment instructions.
- Document rollback and troubleshooting steps.
- Do not claim public readiness until the checks actually pass.

### Phase 5 — Verification and handoff
- Run the actual scripts defined in the repository for linting, type-checking, tests, and production build.
- Add or update tests for authentication and authorization.
- Report which checks passed, failed, or could not be run.
- Update project notes and documentation with decisions and current status.
- Keep the application viewable during development where the current environment supports it.

These phases are recommended execution guidance derived from the confirmed priorities. They are not a claim that the work has already been completed.

## 5. Public-launch security checklist

- [ ] Secrets are stored in environment variables or an appropriate secret store.
- [ ] Real `.env` files are ignored by Git and are not committed.
- [ ] `.env.example` contains no real secrets.
- [ ] AI provider keys are never exposed to the browser.
- [ ] Server-side authentication checks protect all private operations.
- [ ] Server-side authorization checks protect all private records and actions.
- [ ] Cross-user data access has been tested.
- [ ] Database queries are safely parameterized or managed through a suitable ORM.
- [ ] Input is validated at trust boundaries.
- [ ] Authentication and expensive AI endpoints have suitable abuse controls.
- [ ] Error responses do not reveal secrets, tokens, SQL details, or internal stack traces.
- [ ] Production cookie, HTTPS, redirect, CORS, and security-header settings are reviewed.
- [ ] Database migrations and backup/recovery expectations are documented.
- [ ] Lint, type-check, test, and build results are recorded accurately.
- [ ] Vercel environment variables and deployment settings are verified.
- [ ] Deployment and rollback steps are documented.

## 6. Suggested documentation layout

Adapt this structure to the repository rather than creating duplicate or conflicting documentation:

```text
ThinkLink/
├── README.md
├── AGENTS.md
├── docs/
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── AUTH_AND_ACCESS_CONTROL.md
│   ├── DATABASE.md
│   ├── AI_INTEGRATION.md
│   ├── DEPLOYMENT_VERCEL.md
│   ├── SECURITY_CHECKLIST.md
│   └── HANDOFF.md
└── notes/
    ├── 00-project-discovery.md
    ├── 01-architecture.md
    ├── 02-auth-and-access-control.md
    └── 03-deployment.md
```

Obsidian may use the relevant documentation/notes directory as a vault. Prefer a single source of truth for each fact and link to it from other documents.

## 7. Requirements still unknown

Do not silently fill in these gaps. Check the repository, project discovery chat, and existing project files; ask the user if a decision blocks safe implementation.

- Complete product description and core user journeys.
- MVP feature list and scope.
- Roles, permissions, and administrative workflows.
- Registration policy: open registration, invitation, institution-managed access, or another model.
- Authentication methods and any OAuth/SSO providers.
- Exact PostgreSQL service/provider and existing schema.
- Exact Groq model and intended AI workflows.
- Whether embeddings, RAG, or vector search are genuinely needed.
- Privacy, retention, and student-data requirements.
- Branding, production domain, and launch expectations.
- GitHub repository URL and Vercel project/account details.

## 8. Instructions for Codex

1. Read this handoff fully before editing.
2. Inspect the current repository and actual implementation first.
3. Treat the decisions in Section 2 as confirmed; treat unknowns in Section 7 as unresolved.
4. Start with authentication and server-side access control.
5. Make small, reviewable changes and explain which files changed.
6. Preserve existing working functionality.
7. Never invent credentials, URLs, deployment status, test results, or completed work.
8. Never commit secrets or expose them in logs.
9. Add tests for authorization boundaries and cross-user data isolation.
10. Run the repository's real validation commands and report results truthfully.
11. Update the README, phase notes, and handoff when decisions or implementation status change.
12. Ask the user only when a material product/security decision or account authorization is required.

## 9. Handoff status

### Confirmed decisions
- [x] Current application name is ThinkLink.
- [x] Student audience.
- [x] Groq is the chosen AI provider.
- [x] PostgreSQL option B was selected.
- [x] Vercel is the intended hosting platform.
- [x] GitHub repository should belong to the user.
- [x] Authentication and access control are the first implementation priority.
- [x] ChromaDB is conditional on AI functionality requiring it.
- [x] Phase-based notes and documentation are desired.
- [x] Obsidian may be used alongside repository documentation.

### Not verified
- [ ] Repository contents and current git state.
- [ ] Authentication implementation.
- [ ] Authorization coverage and tests.
- [ ] PostgreSQL connectivity and migrations.
- [ ] Groq integration and selected model.
- [ ] ChromaDB need or configuration.
- [ ] GitHub and Vercel account/repository connections.
- [ ] Production build and deployment.
- [ ] Public-launch security checks.

**Next action:** Open the ThinkLink repository in Codex, inspect the existing code and scripts, then implement and test authentication and server-side access control before proceeding to public deployment.
