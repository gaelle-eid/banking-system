import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from decimal import Decimal

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.models.models import SavingsGoal, Account, User, ContributionMode
from app.schemas.goal import SavingsGoalOut, SavingsGoalCreate

router = APIRouter(prefix="/goals", tags=["goals"])


class SetContributionRequest(BaseModel):
    contribution_mode: ContributionMode
    fixed_monthly_amount: Decimal | None = None


def _mask_and_generate_account_number() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))


async def _attach_currency(db: AsyncSession, goal: SavingsGoal) -> SavingsGoal:
    """Goals are denominated in whatever currency their goal account uses -
    look it up so the frontend can display amounts correctly."""
    currency = "USD"
    if goal.goal_account_id:
        acc_result = await db.execute(select(Account).where(Account.id == goal.goal_account_id))
        account = acc_result.scalar_one_or_none()
        if account:
            currency = account.currency
    goal.currency = currency
    return goal


@router.post("", response_model=SavingsGoalOut, status_code=201)
async def create_goal(
    payload: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a savings goal directly (not via the AI assistant). Creates
    the goal immediately, with no separate confirmation step needed - this
    just opens a new dedicated savings account, no money moves yet."""
    source_result = await db.execute(select(Account).where(Account.id == payload.source_account_id))
    source_account = source_result.scalar_one_or_none()
    if not source_account:
        raise HTTPException(status_code=404, detail="Source account not found")
    if source_account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your account")
    if source_account.status.value != "active":
        raise HTTPException(status_code=400, detail="This account isn't active")

    goal_account = Account(
        owner_id=current_user.id,
        account_number=_mask_and_generate_account_number(),
        nickname=payload.name,
        type="savings",
        currency=source_account.currency,
        balance=0,
    )
    db.add(goal_account)
    await db.flush()

    goal = SavingsGoal(
        client_id=current_user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        goal_account_id=goal_account.id,
        source_account_id=source_account.id,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    await log_action(
        db, current_user.id, "created", "savings_goal", goal.id,
        details={"name": payload.name, "target_amount": str(payload.target_amount)},
    )
    await db.commit()

    goal.currency = goal_account.currency
    return goal


@router.get("/me", response_model=list[SavingsGoalOut])
async def list_my_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SavingsGoal).where(SavingsGoal.client_id == current_user.id))
    goals = result.scalars().all()
    for goal in goals:
        await _attach_currency(db, goal)
    return goals


@router.get("/{goal_id}/progress")
async def get_goal_progress(
    goal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SavingsGoal).where(SavingsGoal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your goal")

    current_balance = 0
    currency = "USD"
    if goal.goal_account_id:
        acc_result = await db.execute(select(Account).where(Account.id == goal.goal_account_id))
        account = acc_result.scalar_one_or_none()
        if account:
            current_balance = float(account.balance)
            currency = account.currency

    percent = min(100, round((current_balance / float(goal.target_amount)) * 100, 1)) if goal.target_amount else 0

    return {
        "goal_id": goal.id,
        "name": goal.name,
        "target_amount": float(goal.target_amount),
        "current_amount": current_balance,
        "percent_complete": percent,
        "currency": currency,
    }


@router.patch("/{goal_id}/contribution", response_model=SavingsGoalOut)
async def set_contribution_mode(
    goal_id: str,
    payload: SetContributionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SavingsGoal).where(SavingsGoal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your goal")

    if payload.contribution_mode == ContributionMode.fixed and not payload.fixed_monthly_amount:
        raise HTTPException(status_code=400, detail="fixed_monthly_amount is required for fixed contribution mode")

    goal.contribution_mode = payload.contribution_mode
    goal.fixed_monthly_amount = payload.fixed_monthly_amount

    await db.commit()
    await db.refresh(goal)
    await _attach_currency(db, goal)
    return goal