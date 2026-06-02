"""CAS Harness public-production-readiness scaffolding (design-stage).

This subpackage holds *import-isolated* interface scaffolds (typing.Protocol / ABC
definitions and clearly-labeled in-memory stubs) for the nine production-readiness
workstreams. Nothing here is wired into the live FastAPI app or the fleet executor;
it exists so the design blueprints in ``docs/working/production_readiness/`` have
concrete seams the team can build against.

Honesty rule for everything in this package: a stub is a stub. No module here may
produce a ``*_VERIFIED`` / ``*_METERED`` / ``*_WORM_COMMITTED`` status from a stub
backend -- those statuses are only honest when a real backend has actually done the
work. See ``docs/working/production_readiness/00_index.md``.
"""
