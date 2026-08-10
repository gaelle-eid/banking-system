from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import SavingsGoal, Account, User
from app.schemas.goal import SavingsGoalOut

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/me", response_model=list[SavingsGoalOut])
async def list_my_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SavingsGoal).where(SavingsGoal.client_id == current_user.id))
    return result.scalars().all()


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
    if goal.goal_account_id:
        acc_result = await db.execute(select(Account).where(Account.id == goal.goal_account_id))
        account = acc_result.scalar_one_or_none()
        if account:
            current_balance = float(account.balance)

    percent = min(100, round((current_balance / float(goal.target_amount)) * 100, 1)) if goal.target_amount else 0

    return {
        "goal_id": goal.id,
        "name": goal.name,
        "target_amount": float(goal.target_amount),
        "current_amount": current_balance,
        "percent_complete": percent,
    }