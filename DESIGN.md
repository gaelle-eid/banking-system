# Design Notes

## Approval Workflow

Loans and cards require employee sign-off before becoming active. When a client
requests a loan or card, the backend:

1. Creates the entity (`Loan` or `Card`) with status `pending`
2. Creates a matching row in the generic `approvals` table
   (`entity_type` + `entity_id` pointing back to the loan/card)

Employees (Step 8) will query `approvals` for `status = pending`, and approving
or rejecting there should also update the underlying `Loan.status` /
`Card.status` accordingly (e.g. `approved` -> `active`, `rejected` -> `rejected`).

This same pattern extends to `transactions` and `agent_action` approvals later.

## Gotcha: Postgres enums + Alembic autogenerate

Alembic's `--autogenerate` does **not** detect changes to existing Postgres
enum types (e.g. adding a new value like `pending` to `CardStatus`). It will
generate an empty migration (`pass` in both `upgrade()`/`downgrade()`) with no
error or warning.

**If you add or change an enum value:**
1. Generate the migration as usual (`alembic revision --autogenerate -m "..."`)
2. Manually edit the generated file's `upgrade()`:
```python
   op.execute("ALTER TYPE <enum_name> ADD VALUE IF NOT EXISTS '<new_value>'")
```
3. Postgres does not support removing enum values without recreating the type,
   so `downgrade()` is generally left as `pass` for this project's scope.
4. Always verify with:
```sql
   SELECT unnest(enum_range(NULL::<enum_name>));
```

## Database Sharing Model

One shared PostgreSQL database, one shared FastAPI backend, with role-based
access control (RBAC) distinguishing `client` / `employee` / `admin`. Both
portals read/write the same tables — there is no data duplication between
client and employee views, since both need to see the same live account and
transaction state.

## Transfers: Double-Entry Pattern

A transfer between two accounts creates **two** transaction rows (one debit,
one credit), linked by a shared `transfer_group_id`. This mirrors standard
accounting practice and keeps every transaction row describing exactly one
account's movement, simplifying history queries and audit logging.