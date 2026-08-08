from pydantic_ai import Agent
from app.agents.deps import EmployeeAgentDeps
from app.agents.tools.employee_tools import (
    list_pending_approvals, summarize_client_activity, get_bank_summary, propose_approval_decision, search_knowledge_base,
)

employee_agent = Agent(
    "gateway/openai:gpt-5.2",
    deps_type=EmployeeAgentDeps,
    system_prompt=(
        "You are an internal assistant for a bank employee. You can list "
        "pending approval requests (loans, cards), summarize a client's "
        "account activity by email, give a live bank-wide summary, and "
        "propose approving or rejecting a pending request, and search internal "
        "policy documents to answer questions about bank procedures and rules. "
        "IMPORTANT: proposing an approval decision does NOT apply it - the "
        "employee must separately confirm it. You MUST include the exact "
        "action id returned by the tool, verbatim, in your reply every time "
        "you propose a decision - never omit it or paraphrase it away. "
        "Be concise and professional. Never make up numbers, client data, "
        "or approval details - only use what the tools return."
    ),
)

employee_agent.tool(list_pending_approvals)
employee_agent.tool(summarize_client_activity)
employee_agent.tool(get_bank_summary)
employee_agent.tool(propose_approval_decision)
employee_agent.tool(search_knowledge_base)