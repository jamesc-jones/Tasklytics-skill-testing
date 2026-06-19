# Claude Global Context — Tasklytics

## Project Overview

Tasklytics is a full-stack smart task management application designed to go beyond a traditional to-do list.

It enables users to:

* Manage tasks (CRUD operations)
* Track productivity via analytics dashboards
* Receive AI-powered productivity insights based on task data

The system emphasizes clean architecture, real-time interactivity, and practical AI integration.

---

## Tech Stack

### Backend

* Python (FastAPI)
* PostgreSQL
* JWT Authentication
* RESTful APIs

### Frontend

* React
* State-driven UI with real-time updates
* Chart.js for analytics visualization

### DevOps / Infrastructure

* Docker (containerized services)
* Nginx (reverse proxy)
* VPS deployment
* HTTPS via Let’s Encrypt

---

## AI System Design

* AI is used to generate structured productivity insights
* Input is based on task data (often JSON)
* Output should be:

  * Structured
  * Clear
  * Actionable
  * Preferably formatted in markdown

Avoid vague or generic advice — prioritize useful, user-specific insights.

---

## General Development Principles

* Follow clean architecture principles
* Separate concerns (API, business logic, UI, AI prompts)
* Prefer clarity over cleverness
* Keep functions small and focused
* Avoid unnecessary abstraction

---

## API & Backend Guidelines

* Follow REST conventions
* Use clear and consistent route naming
* Validate inputs properly
* Handle errors explicitly
* Ensure authentication is enforced where required

---

## Frontend Guidelines

* Keep components modular and reusable
* Maintain clear state management
* Ensure UI reflects real-time data accurately
* Prioritize responsiveness and usability

---

## AI & Prompt Engineering Guidelines

* Prefer structured outputs over freeform text
* Be deterministic when possible
* Avoid hallucinating missing data
* Ask for clarification if required inputs are missing

---

## Git & Pull Request Standards

* Use structured pull request descriptions

* Clearly summarize:

  * What changed
  * Why it changed
  * Key implementation details
  * Risks or edge cases

* Highlight:

  * Breaking changes
  * Database migrations
  * Auth-related updates

---

## Behavior Rules

* Be concise and structured in responses
* Prefer bullet points over long paragraphs
* Do not assume missing technical details
* Ask for clarification when necessary
* Prioritize actionable outputs over explanations

---

## Context Awareness

When working within this project:

* Assume a full-stack environment
* Consider both frontend and backend impact of changes
* Be aware of deployment implications (Docker, Nginx, VPS)

Always think in terms of **real-world production impact**, not just code correctness.
