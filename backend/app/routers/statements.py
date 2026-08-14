import io
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.account_access import user_can_access_account
from app.models.models import Statement, Account, Transaction, TransactionType, TransactionStatus, User
from app.schemas.statement import StatementOut

router = APIRouter(prefix="/statements", tags=["statements"])

CREDIT_TYPES = {TransactionType.deposit, TransactionType.transfer_credit}
DEBIT_TYPES = {TransactionType.withdrawal, TransactionType.transfer_debit}

TYPE_LABELS = {
    "deposit": "Deposit",
    "withdrawal": "Withdrawal",
    "transfer_debit": "Transfer out",
    "transfer_credit": "Transfer in",
}


def _mask_account_number(account_number: str) -> str:
    return f"****{account_number[-4:]}"


def _pdf_safe(text: str) -> str:
    """FPDF's core fonts only support Latin-1. Some of our stored data
    (funding source labels, etc.) contains a bullet character used for
    masking elsewhere in the app - replace it and any other non-Latin-1
    character so PDF generation never crashes on it."""
    text = text.replace("•", "*")
    return text.encode("latin-1", errors="replace").decode("latin-1")


async def _generate_statement_for_account(db: AsyncSession, account: Account) -> Statement:
    """Core statement-generation logic, shared by the REST endpoint and
    the AI assistant's statement tool. Covers the current month to date -
    a frozen SNAPSHOT that won't change even with more activity later,
    exactly like a real bank statement."""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = now

    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.account_id == account.id,
            Transaction.created_at >= period_start,
            Transaction.created_at <= period_end,
            Transaction.status == TransactionStatus.completed,
        )
        .order_by(Transaction.created_at.asc())
    )
    period_transactions = tx_result.scalars().all()

    # The account's CURRENT balance already reflects everything that's
    # happened. Work backward from it to find the opening balance for this
    # period, then walk forward to build a running balance for each line -
    # same method a real statement uses.
    net_change = Decimal("0")
    for tx in period_transactions:
        if tx.type in CREDIT_TYPES:
            net_change += tx.amount
        elif tx.type in DEBIT_TYPES:
            net_change -= tx.amount

    opening_balance = account.balance - net_change
    closing_balance = account.balance

    total_deposits = sum((tx.amount for tx in period_transactions if tx.type in CREDIT_TYPES), Decimal("0"))
    total_withdrawals = sum((tx.amount for tx in period_transactions if tx.type in DEBIT_TYPES), Decimal("0"))

    running = opening_balance
    lines = []
    for tx in period_transactions:
        if tx.type in CREDIT_TYPES:
            running += tx.amount
        elif tx.type in DEBIT_TYPES:
            running -= tx.amount

        description = TYPE_LABELS.get(tx.type.value, tx.type.value)
        if tx.source:
            description = f"{description} - {tx.source}"
        elif tx.method:
            description = f"{description} ({tx.method})"

        lines.append({
            "date": tx.created_at.strftime("%Y-%m-%d"),
            "type": tx.type.value,
            "description": description,
            "amount": str(tx.amount),
            "running_balance": str(running),
        })

    statement = Statement(
        account_id=account.id,
        period_start=period_start,
        period_end=period_end,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        currency=account.currency,
        transactions_snapshot=lines,
    )
    db.add(statement)
    await db.commit()
    await db.refresh(statement)
    return statement


@router.post("/generate/{account_id}", response_model=StatementOut, status_code=201)
async def generate_statement(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not await user_can_access_account(db, current_user.id, account_id):
        raise HTTPException(status_code=403, detail="Not your account")

    return await _generate_statement_for_account(db, account)


@router.get("/{account_id}", response_model=list[StatementOut])
async def list_statements(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not await user_can_access_account(db, current_user.id, account_id):
        raise HTTPException(status_code=403, detail="Not your account")

    result = await db.execute(
        select(Statement).where(Statement.account_id == account_id).order_by(Statement.generated_at.desc())
    )
    return result.scalars().all()


@router.get("/detail/{statement_id}/pdf")
async def download_statement_pdf(
    statement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fpdf import FPDF

    result = await db.execute(select(Statement).where(Statement.id == statement_id))
    statement = result.scalar_one_or_none()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    acc_result = await db.execute(select(Account).where(Account.id == statement.account_id))
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not await user_can_access_account(db, current_user.id, account.id):
        raise HTTPException(status_code=403, detail="Not your account")

    owner_result = await db.execute(select(User).where(User.id == account.owner_id))
    owner = owner_result.scalar_one_or_none()

    currency = statement.currency or "USD"
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Account Statement", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Banking System", ln=True)
    pdf.ln(4)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _pdf_safe(f"Account holder: {owner.full_name if owner else 'N/A'}"), ln=True)
    pdf.cell(0, 6, _pdf_safe(f"Account: {account.nickname or account.type.value} ({_mask_account_number(account.account_number)})"), ln=True)
    pdf.cell(0, 6, f"Statement period: {statement.period_start.strftime('%b %d, %Y')} - {statement.period_end.strftime('%b %d, %Y')}", ln=True)
    pdf.cell(0, 6, f"Generated: {statement.generated_at.strftime('%b %d, %Y')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, f"Opening balance: {statement.opening_balance} {currency}", ln=False)
    pdf.cell(0, 7, f"Closing balance: {statement.closing_balance} {currency}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, f"Total deposits: {statement.total_deposits} {currency}", ln=False)
    pdf.cell(0, 6, f"Total withdrawals: {statement.total_withdrawals} {currency}", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(28, 8, "Date", border=1, fill=True)
    pdf.cell(82, 8, "Description", border=1, fill=True)
    pdf.cell(35, 8, "Amount", border=1, fill=True, align="R")
    pdf.cell(35, 8, "Balance", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    lines = statement.transactions_snapshot or []
    if not lines:
        pdf.cell(180, 8, "No transactions in this period.", border=1)
        pdf.ln()
    else:
        for line in lines:
            is_credit = line["type"] in ("deposit", "transfer_credit")
            sign = "+" if is_credit else "-"
            pdf.cell(28, 7, line["date"], border=1)
            pdf.cell(82, 7, _pdf_safe(line["description"])[:48], border=1)
            pdf.cell(35, 7, f"{sign}{line['amount']}", border=1, align="R")
            pdf.cell(35, 7, line["running_balance"], border=1, align="R")
            pdf.ln()

    pdf_bytes = bytes(pdf.output())
    filename = f"statement_{account.account_number[-4:]}_{statement.period_start.strftime('%Y%m')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )