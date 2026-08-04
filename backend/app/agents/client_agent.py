from pydantic_ai import Agent
from pydantic_ai.providers.gateway import gateway_provider

from app.core.config import settings
from app.agents.deps import ClientAgentDeps
from app.agents.tools.client_tools import get_my_accounts, get_transaction_history, explain_faq

provider = gateway_provider(
    "openai",
    api_key=settings.pydantic_ai_gateway_api_key,
    route="builtin-openai",
)

client_agent = Agent(
     "gateway/openai:gpt-5.2",
    deps_type=ClientAgentDeps,
    system_prompt=(
        "You are a helpful banking assistant for a client of this bank. "
        "You can look up their accounts and transaction history, and answer "
        "general banking questions. Be concise and friendly. Never make up "
        "account numbers, balances, or transaction data - only use what the "
        "tools return. If you don't have access to something, say so clearly."
    ),
)