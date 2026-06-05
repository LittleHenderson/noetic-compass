"""FastAPI dependencies -- centralized, reusable request-scoped guards.

Currently houses the authz dependency (``authz``): the ONE place role/tenant/account identity is
read off the SERVER-SET ``request.state`` and turned into an allow/deny. Centralizing it means a
privileged route declares ``Depends(require_role(...))`` instead of re-deriving an ad-hoc check, so
the deny semantics (401 vs 403) are uniform and auditable in one file.
"""
