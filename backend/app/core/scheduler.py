from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


async def run_monthly_fixed_contributions():
    """Run on the 1st of each month: move each goal's fixed_monthly_amount
    from its source account to its goal account, for goals in 'fixed' mode."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import SavingsGoal, ContributionMode, Account, Transaction, TransactionType, TransactionStatus, User
    from app.core.email import send_email
    import uuid

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SavingsGoal).where(
                SavingsGoal.active == True,
                SavingsGoal.contribution_mode == ContributionMode.fixed,
                SavingsGoal.fixed_monthly_amount.isnot(None),
            )
        )
        goals = result.scalars().all()

        for goal in goals:
            source_result = await db.execute(select(Account).where(Account.id == goal.source_account_id))
            source_account = source_result.scalar_one_or_none()
            goal_result = await db.execute(select(Account).where(Account.id == goal.goal_account_id))
            goal_account = goal_result.scalar_one_or_none()

            if not source_account or not goal_account:
                continue
            if source_account.balance < goal.fixed_monthly_amount:
                continue  # skip silently if insufficient funds this month

            group_id = str(uuid.uuid4())
            source_account.balance -= goal.fixed_monthly_amount
            goal_account.balance += goal.fixed_monthly_amount

            db.add(Transaction(
                account_id=source_account.id, type=TransactionType.transfer_debit,
                amount=goal.fixed_monthly_amount, transfer_group_id=group_id,
                status=TransactionStatus.completed, initiated_by=goal.client_id,
            ))
            db.add(Transaction(
                account_id=goal_account.id, type=TransactionType.transfer_credit,
                amount=goal.fixed_monthly_amount, transfer_group_id=group_id,
                status=TransactionStatus.completed, initiated_by=goal.client_id,
            ))

            user_result = await db.execute(select(User).where(User.id == goal.client_id))
            user = user_result.scalar_one_or_none()
            if user:
                try:
                    send_email(
                        user.email, f"Monthly savings contribution: {goal.name}",
                        f"<p>Hi {user.full_name},</p>"
                        f"<p>We moved <strong>{goal.fixed_monthly_amount} {goal_account.currency}</strong> "
                        f"from your {source_account.nickname or source_account.type.value} account into "
                        f"your <strong>{goal.name}</strong> savings goal, as scheduled.</p>"
                        f"<p>New {goal.name} balance: {goal_account.balance} {goal_account.currency}</p>",
                    )
                except Exception:
                    pass

        await db.commit()


async def run_monthly_loan_repayments():
    """Run on the 1st of each month: auto-debit each active loan's monthly
    payment from its disbursement account, same pattern as the fixed
    savings goal contributions. Marks a loan 'closed' (paid off) once its
    remaining balance hits zero."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import Loan, LoanStatus, Account, Transaction, TransactionType, TransactionStatus, User
    from app.core.email import send_email
    from decimal import Decimal
    from datetime import datetime, timedelta

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Loan).where(
                Loan.status == LoanStatus.active,
                Loan.remaining_balance.isnot(None),
                Loan.remaining_balance > 0,
            )
        )
        loans = result.scalars().all()

        for loan in loans:
            account_result = await db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
            account = account_result.scalar_one_or_none()
            if not account:
                continue

            payment = min(loan.monthly_payment, loan.remaining_balance)
            if account.balance < payment:
                continue  # skip silently if insufficient funds this month, matching goal contributions

            account.balance -= payment
            loan.remaining_balance -= payment

            db.add(Transaction(
                account_id=account.id, type=TransactionType.withdrawal,
                amount=payment, status=TransactionStatus.completed,
                initiated_by=loan.client_id, source="Loan Repayment",
            ))

            paid_off = loan.remaining_balance <= 0
            if paid_off:
                loan.remaining_balance = Decimal("0")
                loan.status = LoanStatus.closed
                loan.next_payment_due = None
            else:
                loan.next_payment_due = datetime.utcnow() + timedelta(days=30)

            user_result = await db.execute(select(User).where(User.id == loan.client_id))
            user = user_result.scalar_one_or_none()
            if user:
                try:
                    if paid_off:
                        send_email(
                            user.email, "Loan paid off!",
                            f"<p>Hi {user.full_name},</p>"
                            f"<p>Congratulations - your loan has been fully paid off with your final payment of "
                            f"<strong>{payment} {account.currency}</strong>.</p>",
                        )
                    else:
                        send_email(
                            user.email, "Monthly loan payment processed",
                            f"<p>Hi {user.full_name},</p>"
                            f"<p>We took your scheduled payment of <strong>{payment} {account.currency}</strong> "
                            f"from your {account.nickname or account.type.value} account.</p>"
                            f"<p>Remaining balance: {loan.remaining_balance} {account.currency}</p>",
                        )
                except Exception:
                    pass

        await db.commit()


async def send_variable_goal_reminders():
    """Run on the 1st of each month: email clients with 'variable' mode
    goals, asking them how much they want to contribute this month."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import SavingsGoal, ContributionMode, User
    from app.core.email import send_email

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SavingsGoal).where(
                SavingsGoal.active == True,
                SavingsGoal.contribution_mode == ContributionMode.variable,
            )
        )
        goals = result.scalars().all()

        for goal in goals:
            user_result = await db.execute(select(User).where(User.id == goal.client_id))
            user = user_result.scalar_one_or_none()
            if not user:
                continue
            try:
                send_email(
                    user.email, f"How much would you like to save toward {goal.name} this month?",
                    f"<p>Hi {user.full_name},</p>"
                    f"<p>It's a new month! Open your Assistant and let us know how much you'd like "
                    f"to contribute to your <strong>{goal.name}</strong> goal this month.</p>",
                )
            except Exception:
                pass


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            run_monthly_fixed_contributions,
            trigger=CronTrigger(day=1, hour=6, minute=0),
            id="monthly_fixed_contributions",
            replace_existing=True,
        )
        scheduler.add_job(
            run_monthly_loan_repayments,
            trigger=CronTrigger(day=1, hour=6, minute=2),
            id="monthly_loan_repayments",
            replace_existing=True,
        )
        scheduler.add_job(
            send_variable_goal_reminders,
            trigger=CronTrigger(day=1, hour=6, minute=5),
            id="variable_goal_reminders",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()