---
id: python-web
title: Web APIs & frameworks
order: 3
summary: FastAPI/Django/Flask, layered APIs, dependency injection, validation, errors, framework internals.
docs: python/python-interview-prep/deep_dive/10_web_frameworks.md, python/python-interview-prep/deep_dive/11_python_framework_development.md
folders: 05_web_apis_fastapi, 12_framework_internals
examples: python/python-interview-prep/05_web_apis_fastapi
keywords: fastapi, django, flask, rest, api, endpoint, pydantic, depends, dependency injection, middleware, uvicorn, wsgi, asgi, router, http, status code, framework, plugin, camel
---
Skill focus for Web APIs & frameworks answers:
- Layering: thin routers, services with business logic, repositories; exception handlers decide status codes.
- Depends() for auth, DB sessions and singletons; dependency_overrides in tests.
- Calling third-party APIs from Python: httpx with timeouts, tenacity retries, circuit breaking, problem-details errors.
