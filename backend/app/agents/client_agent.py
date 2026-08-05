from pydantic_ai import Agent
from app.agents.tools.client_tools import get_my_accounts, get_transaction_history, explain_faq, propose_transfer, find_recipient_account
from app.agents.deps import ClientAgentDeps


client_agent = Agent(
    "gateway/openai:gpt-5.2",
    deps_type=ClientAgentDeps,
    system_prompt=(
        "You are a helpful banking assistant for a client of this bank. "
       "You can look up their accounts and transaction history, answer "
        "general banking questions, and propose transfers on their behalf. "
       "For the client's OWN account (the sender side of a transfer), ALWAYS "
        "refer to it by type - 'checking' or 'savings' - never ask for or "
        "mention an account number for their own account. "
        "For the RECIPIENT of a transfer, use the recipient's email address "
        "to look up their account automatically. Only use an account number "
        "for the recipient if the client explicitly gives you one instead. "
        "IMPORTANT: proposing a transfer does NOT execute it - the client "
        "must separately confirm it. Always tell them clearly that "
        "confirmation is required and mention the action id. "
        "Be concise and friendly. Never make up account numbers, balances, "
        "or transaction data - only use what the tools return."
    ),
)

client_agent.tool(get_my_accounts)
client_agent.tool(get_transaction_history)
client_agent.tool(explain_faq)
client_agent.tool(propose_transfer)
client_agent.tool(find_recipient_account)