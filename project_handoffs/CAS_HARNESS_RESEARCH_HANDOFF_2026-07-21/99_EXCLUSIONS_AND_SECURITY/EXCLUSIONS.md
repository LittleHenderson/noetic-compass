# Exclusions and Scope

The handoff intentionally excludes:

- `.env` files and provider credentials
- SSH private keys, API tokens, browser profiles, session cookies, and MFA material
- Hugging Face model caches and downloaded model weights
- Python virtual environments, `node_modules`, `.git` worktree pointers, `.pytest_cache`, `__pycache__`, and `.pyc`
- the complete 243–251 MB temporary Git worktrees, because the exact frozen ZIP and curated source snapshots are included instead
- unrelated dirty-worktree changes, especially CAS Forex work
- any claim that a copied file is independently escrowed or WORM anchored

The original files were copied, not moved. The `C:\tmp` sources remain temporary by nature; this OneDrive-backed handoff is the durable local consolidation. Independent object-store durability remains `OPEN`.

