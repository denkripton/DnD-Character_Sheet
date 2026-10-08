# AGENTS.md

## Project Overview

This repository contains a D&D character management application.

The application allows users to:

* create D&D characters;
* manually configure character parameters;
* generate character parameters;
* manage and edit characters;
* generate character backstories using AI;
* select an available AI provider and model;
* use the application through a Telegram Bot / Telegram Mini App interface.

The current architecture consists of:

* `backend/` — FastAPI modular monolith containing application, domain, and infrastructure logic;
* `bot/` — Telegram interface built with aiogram;
* PostgreSQL — primary persistent storage;
* Redis — caching, rate limiting, and supporting infrastructure;
* RabbitMQ — communication transport between Bot and Backend;
* AI providers — external AI integrations, currently Gemini;
* GitHub Actions — CI/CD automation.

The architecture must remain extensible for future interfaces, AI providers, and infrastructure changes.

---

# Core Engineering Principles

All changes MUST follow these principles:

1. SOLID
2. Domain-Driven Design (DDD)
3. Separation of concerns
4. High cohesion and low coupling
5. Explicit dependency direction
6. Scalability
7. Maintainability
8. Reliability
9. Testability
10. Backward compatibility with existing functionality

Do not introduce architectural complexity without a concrete reason.

Do not introduce microservices unless explicitly requested.

The backend should remain a modular monolith unless a future requirement explicitly justifies splitting it.

---

# Repository Structure

The main structure is:

```text
/
├── backend/
├── bot/
├── compose.yml
├── compose.dev.yml
├── pyproject.toml
├── uv.lock
├── AGENTS.md
└── .github/
    └── workflows/
```

`backend/` and `bot/` are separate application boundaries.

They must not become tightly coupled through direct imports.

---

# Backend Architecture

The backend is a modular monolith.

The backend contains:

```text
backend/
└── src/
    ├── api.py
    ├── config.py
    ├── databases/
    ├── infrastructure/
    ├── messaging/
    ├── modules/
    ├── repositories/
    └── utils/
```

Existing bounded contexts include:

* authentication;
* characters;
* character stats;
* skills;
* saving throws;
* proficiencies;
* combat;
* features;
* personality;
* backstory;
* AI.

Respect the existing module boundaries.

Do not move domain logic into unrelated modules simply because it is convenient.

---

# Domain Rules

The domain is the source of truth for D&D character rules.

The following MUST remain in the backend/domain/application layer where appropriate:

* character validation;
* character ownership;
* character calculations;
* stat modifiers;
* hit points;
* character generation;
* progression rules;
* character state transitions;
* business invariants.

The Telegram Bot MUST NOT implement these rules.

Do not duplicate existing character logic inside the bot.

If a required capability already exists in the backend, reuse it.

Do not create a second implementation.

---

# Bot Architecture

`bot/` is the presentation/application interface for Telegram.

The bot is responsible for:

* Telegram updates;
* commands;
* callback queries;
* FSM/conversational state;
* presentation;
* user interaction;
* Telegram-specific validation;
* sending commands through RabbitMQ;
* receiving backend responses/events;
* translating backend results into Telegram UI.

The bot MUST NOT:

* access PostgreSQL directly;
* import SQLAlchemy models from backend;
* import backend domain entities;
* execute character business rules;
* calculate D&D statistics;
* generate characters independently;
* call AI providers directly;
* contain backend repositories;
* contain backend Unit of Work;
* bypass RabbitMQ for Bot ↔ Backend communication.

The bot must remain replaceable.

A future web client or another interface should be able to communicate with the same backend application layer without requiring domain changes.

---

# Bot State Management

FSM state in the bot represents conversational state only.

FSM MUST NOT become the authoritative source of character state.

The backend remains authoritative for persistent character data.

The bot may store temporary interaction information required to continue a conversation, but persistent business state must belong to the backend.

The character creation flow should be sequential and user-friendly.

Users should be able to:

* proceed step by step;
* go back;
* edit previous values;
* regenerate supported values;
* cancel the process;
* review the character;
* confirm creation.

Do not create a single huge Telegram form.

---

# RabbitMQ

RabbitMQ is the transport between Bot and Backend.

The intended communication flow is:

```text
Telegram
    ↓
Bot
    ↓
RabbitMQ
    ↓
Backend
    ↓
Application Layer
    ↓
Domain
    ↓
Repositories / Unit of Work
    ↓
PostgreSQL
```

Responses/events flow back through RabbitMQ.

The Bot must not bypass RabbitMQ by directly calling backend internals.

RabbitMQ infrastructure must support, where appropriate:

* connection lifecycle;
* reconnect handling;
* acknowledgements;
* retries;
* dead-letter queues;
* deterministic serialization;
* message metadata;
* correlation IDs;
* request/response correlation;
* safe error handling;
* graceful shutdown.

Message contracts must be explicit and versionable.

Do not pass ORM entities through RabbitMQ.

Use transport DTOs/contracts.

---

# Messaging Contracts

Messaging contracts should be independent of:

* SQLAlchemy;
* Telegram objects;
* FastAPI request objects;
* Redis clients;
* AI SDK objects.

Messages should contain only the data necessary for communication.

Prefer explicit commands and events.

Examples:

```text
CreateCharacterCommand
UpdateCharacterCommand
GenerateCharacterCommand
GenerateBackstoryCommand
GetCharacterCommand
CharacterCreatedEvent
CharacterUpdatedEvent
CharacterGenerationResult
BackstoryGenerationResult
```

Use the existing messaging architecture where possible.

Do not introduce a second messaging abstraction.

---

# Authentication and Authorization

Authentication must be implemented through the existing backend authentication architecture.

Telegram is an external identity/interface.

Telegram user identity must be mapped to an application user.

Use Telegram user ID as the stable external identity.

Do not use Telegram username as the primary identity because usernames can change.

Authentication logic must not live inside individual Telegram handlers.

Authorization must be enforced in the backend.

Every character operation must verify ownership.

A user must never be able to access or modify another user's character.

Do not trust user IDs supplied by arbitrary client payloads when the authenticated identity is already available.

---

# Character Creation

Character creation must reuse the existing character domain.

Do not rewrite the character system to support Telegram.

The bot should orchestrate the interaction while the backend executes business operations.

Preferred conceptual flow:

```text
Start
 ↓
Name
 ↓
Race / Species
 ↓
Class
 ↓
Level
 ↓
Background
 ↓
Stats
 ↓
Personality
 ↓
Proficiencies
 ↓
Saving Throws
 ↓
Combat
 ↓
Features
 ↓
Backstory
 ↓
Review
 ↓
Save
```

This is only a conceptual example.

The actual order MUST be derived from existing domain dependencies and invariants.

Do not blindly implement the example order if the existing domain requires another sequence.

Every step should use existing backend capabilities.

Where generation exists, users should be able to choose between manual input and generation.

---

# Character Generation

Character generation must be performed by the backend.

The bot only collects preferences and displays results.

The general flow is:

```text
Telegram User
    ↓
Bot
    ↓
Authentication
    ↓
Rate Limit
    ↓
RabbitMQ
    ↓
Backend Application Service
    ↓
Character Domain
    ↓
Persistence
    ↓
RabbitMQ
    ↓
Bot
    ↓
Telegram User
```

The bot must not duplicate generation algorithms.

---

# Rate Limiting

Character generation must have a configurable daily limit.

The limit must be configurable through application configuration/environment variables.

Example:

```text
CHARACTER_GENERATION_DAILY_LIMIT
```

The limiter should be generic and reusable.

It must not contain Telegram-specific logic.

The rate limit must be enforced before expensive character generation.

The limiter should be concurrency-safe.

Redis should be used for distributed rate limiting.

Character generation operations should count toward the limit.

Opening a character creation wizard or editing an existing character should not automatically count as a generation operation unless explicitly required.

---

# Redis

Redis is infrastructure.

Domain code must not depend directly on redis-py.

Use abstractions/interfaces where appropriate.

Redis may be used for:

* rate limiting;
* caching;
* temporary infrastructure state;
* other explicitly justified use cases.

Redis failure must be handled deliberately.

Caching must never become the primary source of truth for persistent character data.

PostgreSQL remains the source of truth.

Cache invalidation must be considered whenever mutable data is cached.

Do not cache sensitive data unnecessarily.

---

# Database

PostgreSQL is the persistent source of truth.

Use:

* SQLAlchemy;
* Alembic;
* asyncpg;
* existing Unit of Work/repository abstractions.

Do not access the database from the Telegram Bot.

Do not create database access outside the backend.

Database schema changes must use Alembic migrations.

Never modify an existing migration that has already been applied in shared environments unless explicitly requested.

Create a new migration instead.

---

# AI Architecture

AI functionality must use a provider abstraction.

The domain/application layer must not depend on Gemini.

The intended architecture is:

```text
Application Service
        ↓
AI Provider Interface
        ↓
Provider Implementation
        ↓
External AI API
```

Current provider:

```text
Gemini
```

Future providers may include other AI services.

Provider-specific code must remain isolated.

Do not add provider-specific types to domain models.

AI model selection should be explicit and configurable.

Do not hardcode API keys.

Secrets must come from environment/configuration.

---

# AI Backstory Generation

Backstory generation belongs to the backend.

The Bot must not call Gemini or another AI provider directly.

Flow:

```text
Bot
 ↓
RabbitMQ
 ↓
Backend
 ↓
Backstory Application Service
 ↓
AI Provider Abstraction
 ↓
Selected Provider + Model
 ↓
AI Provider
 ↓
Backend
 ↓
Persistence
 ↓
RabbitMQ
 ↓
Bot
```

The backend should construct the final AI prompt using character data and the existing prompt architecture.

Users should be able to:

* generate;
* regenerate;
* accept;
* manually edit where supported;
* cancel.

Provider failures must be translated into appropriate application-level errors.

---

# Logging

Use structured logging.

The preferred logging stack is:

```text
structlog
```

Logs should be machine-readable JSON in production.

Where applicable, logs should include:

* timestamp;
* log level;
* service;
* environment;
* event;
* correlation ID;
* request ID;
* safe user identifier;
* exception information.

Never log:

* passwords;
* JWTs;
* access tokens;
* refresh tokens;
* API keys;
* Telegram bot tokens;
* authorization headers;
* database passwords;
* connection strings containing credentials;
* unnecessary sensitive personal data.

Do not create multiple competing logging systems.

Reuse and improve the existing logging infrastructure where possible.

---

# Correlation IDs

Correlation IDs should propagate through:

```text
Bot
 ↓
RabbitMQ
 ↓
Backend
 ↓
Database / Redis / AI
```

This is required for tracing distributed interactions.

Do not generate unrelated correlation IDs at every layer unless there is a clear reason.

Message metadata should preserve correlation information.

---

# Health Checks

Implement separate concepts for:

### Liveness

Answers:

> Is the application process alive?

Liveness should not require every external dependency to be available.

### Readiness

Answers:

> Is the application ready to serve requests/messages?

Readiness may verify required dependencies such as:

* PostgreSQL;
* Redis;
* RabbitMQ.

Health responses must not expose:

* credentials;
* connection strings;
* secrets;
* internal sensitive information.

Health checks should be lightweight and asynchronous.

---

# Docker

Docker Compose should provide the required local infrastructure.

Expected services include:

```text
backend
bot
postgres
redis
rabbitmq
```

Do not use `localhost` for communication between Docker services.

Use Docker Compose service names.

Example:

```text
postgres
redis
rabbitmq
```

Environment-specific configuration must come from environment variables.

Do not hardcode secrets.

Use health checks and appropriate service dependencies.

Do not add infrastructure that is not required.

---

# Testing

Every meaningful change should include appropriate tests.

Use the existing test structure.

Current categories include:

```text
tests/
├── unit/
└── integration/
```

Prefer:

* unit tests for domain/application logic;
* integration tests for infrastructure and database behavior;
* messaging tests for RabbitMQ contracts;
* Redis tests for rate limiting/cache behavior;
* end-to-end style tests only when justified.

Do not remove existing tests merely to make the suite pass.

If behavior intentionally changes, update affected tests.

Test failure handling, not only happy paths.

Important failure scenarios include:

* database unavailable;
* Redis unavailable;
* RabbitMQ unavailable;
* message retry;
* invalid message;
* duplicate message;
* timeout;
* provider failure;
* authorization failure;
* rate limit exceeded.

---

# Async Code

The project uses asynchronous infrastructure.

Do not introduce blocking operations into async request/message handlers.

Avoid:

* synchronous network calls;
* blocking file operations in hot paths;
* synchronous database access;
* unnecessary thread usage.

Use async-compatible clients and APIs.

Resources must be closed correctly.

Connections, channels, sessions, and clients must have explicit lifecycle management.

---

# Error Handling

Use the existing exception architecture.

Do not expose internal implementation errors directly to users.

Separate:

* domain errors;
* application errors;
* infrastructure errors;
* transport errors;
* presentation/Telegram errors.

Map errors at the appropriate boundary.

Do not catch broad exceptions unless there is a deliberate recovery/logging strategy.

Avoid silently swallowing exceptions.

---

# Configuration

Configuration must be centralized.

Use environment variables for environment-specific values and secrets.

Do not hardcode:

* API keys;
* passwords;
* tokens;
* service credentials;
* environment-specific URLs.

Configuration must be validated at startup where appropriate.

Do not scatter `os.getenv()` throughout business logic.

---

# Dependencies

Maintain clear dependency direction.

Preferred direction:

```text
Presentation
     ↓
Application
     ↓
Domain
     ↑
Infrastructure
```

Infrastructure implementations may depend on domain/application abstractions.

Domain must not depend on:

* FastAPI;
* aiogram;
* SQLAlchemy;
* Redis client;
* RabbitMQ client;
* Gemini SDK;
* Telegram SDK.

Avoid circular dependencies.

Do not solve dependency problems by adding imports across bounded contexts.

---

# Existing Code

Before modifying a feature:

1. Inspect the existing implementation.
2. Identify existing abstractions.
3. Identify existing tests.
4. Reuse existing services/repositories/interfaces.
5. Determine whether the requested behavior already exists.
6. Change only what is necessary.

Do not rewrite working functionality without a concrete architectural reason.

Do not introduce duplicate implementations.

Do not create parallel abstractions that solve the same problem.

---

# Atomic Changes

Development is intentionally performed as Atomic commits.

Each task/prompt should represent one coherent change.

A task should:

* have one clear responsibility;
* minimize unrelated modifications;
* preserve existing behavior;
* include relevant tests;
* avoid opportunistic refactoring.

Do not combine unrelated features into one task.

Do not modify unrelated files merely for stylistic consistency.

The developer, not the agent, is responsible for creating Git commits.

---

# Git Rules

The agent MUST NOT create commits.

The agent MUST NOT run:

```text
git commit
git push
```

unless explicitly instructed otherwise.

The agent may inspect Git state and history when necessary.

At the end of a task, report:

* files changed;
* behavior implemented;
* tests added/updated;
* tests executed;
* remaining issues;
* any architectural concerns.

---

# Comments

Do not add comments to code.

Prefer self-explanatory:

* names;
* functions;
* classes;
* modules;
* types;
* abstractions.

Do not add comments explaining obvious code.

Do not add comments as a substitute for proper architecture.

Existing useful comments may remain unless they become incorrect.

---

# Code Style

Follow the existing project style.

Before introducing a new pattern:

1. Search for an existing equivalent.
2. Follow the established naming conventions.
3. Follow existing dependency injection patterns.
4. Follow existing schema/model patterns.
5. Follow existing repository/service patterns.
6. Follow existing test conventions.

Do not introduce a new style merely because it is personally preferred.

---

# Refactoring Rules

Refactor only when required for the current task or when the existing implementation prevents correct integration.

Avoid large speculative refactors.

When a refactor is necessary:

* keep the behavior unchanged unless behavior change is the goal;
* preserve public contracts where possible;
* update tests;
* keep the change focused.

Do not mix large refactors with unrelated feature development.

---

# Security

Never commit secrets.

Never expose secrets in:

* logs;
* exceptions;
* API responses;
* RabbitMQ messages;
* Telegram messages;
* tests;
* configuration files.

Validate authorization at the backend boundary.

Do not trust client-provided ownership information.

Sanitize external input where appropriate.

Treat Telegram updates, RabbitMQ messages, AI responses, and external API responses as untrusted input.

---

# Reliability

External dependencies are unreliable.

Design explicitly for:

* timeouts;
* retries;
* connection failures;
* duplicate messages;
* temporary Redis failures;
* RabbitMQ reconnects;
* AI provider failures;
* database failures.

Retries must not create uncontrolled duplicate side effects.

Where operations are not naturally idempotent, introduce an appropriate idempotency strategy rather than blindly retrying.

---

# Performance

Do not optimize prematurely.

Before introducing caching or complex concurrency:

1. identify the actual bottleneck;
2. verify that the optimization is necessary;
3. choose the simplest appropriate solution.

Avoid:

* unnecessary database queries;
* N+1 queries;
* excessive Telegram API calls;
* excessive RabbitMQ messages;
* unnecessary Redis calls;
* loading large datasets into memory.

---

# API and Transport Contracts

REST remains the backend HTTP API style where HTTP APIs are appropriate.

RabbitMQ messages are transport contracts, not domain objects.

Telegram handlers are presentation contracts.

Do not leak internal implementation details through public APIs.

Use explicit schemas/DTOs.

Validate external input at the boundary.

---

# Development Workflow

For every task:

### Step 1 — Inspect

Read the relevant existing code first.

### Step 2 — Understand

Identify:

* existing abstractions;
* dependencies;
* domain rules;
* tests;
* infrastructure constraints.

### Step 3 — Plan

Determine the smallest coherent implementation.

### Step 4 — Implement

Modify only the necessary parts.

### Step 5 — Test

Run relevant tests.

### Step 6 — Verify

Check:

* architecture;
* dependency direction;
* error handling;
* security;
* async behavior;
* backwards compatibility.

### Step 7 — Report

Provide a concise summary of what changed and what was tested.

Do not create a Git commit.

---

# Priority Rules

When requirements conflict, use this priority:

1. Correctness
2. Security
3. Existing domain invariants
4. Architectural boundaries
5. Reliability
6. Testability
7. Maintainability
8. Performance
9. Convenience

Do not sacrifice domain correctness for Telegram UX convenience.

Do not sacrifice security for implementation simplicity.

Do not bypass architectural boundaries simply to make a feature easier to implement.

---

# Important Constraints

Always remember:

* Backend owns business logic.
* PostgreSQL owns persistent state.
* Redis is infrastructure, not the source of truth.
* RabbitMQ is the Bot ↔ Backend transport.
* Bot owns Telegram interaction.
* FSM owns conversational state only.
* Backend owns character state.
* Backend owns authorization.
* AI providers are replaceable.
* Gemini is an implementation, not a domain dependency.
* Character generation must reuse existing domain logic.
* Do not duplicate business logic in the bot.
* Do not access PostgreSQL from the bot.
* Do not import backend domain models into the bot.
* Do not call AI providers from the bot.
* Do not create commits.
* Do not add code comments.
* Do not rewrite working architecture without a concrete reason.
* Prefer small, Atomic changes.
* Always preserve existing tests and behavior unless the current task explicitly changes them.
