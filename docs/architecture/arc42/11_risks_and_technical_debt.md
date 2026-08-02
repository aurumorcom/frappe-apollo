# 11. Risks and Technical Debt

## 🎯 Current Technical Debt

### Architectural Decisions / Won't Fix
- **Stagnant Document Status on Job Failure:** When API calls fail, parent CRM documents (e.g., `CRM Lead`, `Multi Channel Cadence`, `Communication`) intentionally remain in a `"Scheduled"` state. This is **by design**, as the Apollo integration state is strictly decoupled from the internal CRM document state.