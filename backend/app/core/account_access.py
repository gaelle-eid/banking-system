from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Account, AccountOwner, JointOwnerStatus


async def get_accessible_account_ids(db: AsyncSession, user_id: str) -> list[str]:
    """Return all account IDs a user can view/transact on: accounts they
    primarily own, plus any accounts where they're an ACCEPTED joint owner.
    Pending or declined invitations grant no access."""
    result = await db.execute(
        select(Account.id).where(Account.owner_id == user_id)
    )
    owned_ids = list(result.scalars().all())

    joint_result = await db.execute(
        select(AccountOwner.account_id).where(
            AccountOwner.user_id == user_id,
            AccountOwner.status == JointOwnerStatus.accepted,
        )
    )
    joint_ids = list(joint_result.scalars().all())

    return list(set(owned_ids + joint_ids))


async def get_accessible_accounts(db: AsyncSession, user_id: str):
    """Return full Account rows a user can view/transact on: primarily owned
    accounts plus any accounts where they're an ACCEPTED joint owner."""
    result = await db.execute(
        select(Account)
        .outerjoin(
            AccountOwner,
            (AccountOwner.account_id == Account.id) & (AccountOwner.status == JointOwnerStatus.accepted),
        )
        .where(
            or_(
                Account.owner_id == user_id,
                AccountOwner.user_id == user_id,
            )
        )
        .distinct()
    )
    return result.scalars().all()


async def user_can_access_account(db: AsyncSession, user_id: str, account_id: str) -> bool:
    """Check if a user owns or is an ACCEPTED joint owner on a specific account."""
    result = await db.execute(
        select(Account.id).where(Account.id == account_id, Account.owner_id == user_id)
    )
    if result.scalar_one_or_none():
        return True

    joint_result = await db.execute(
        select(AccountOwner.id).where(
            AccountOwner.account_id == account_id,
            AccountOwner.user_id == user_id,
            AccountOwner.status == JointOwnerStatus.accepted,
        )
    )
    return joint_result.scalar_one_or_none() is not None