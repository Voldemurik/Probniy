from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
 
 
class PeriodType(str, Enum):
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    YTD = "ytd"
    ALL = "all"
 
 
class ExpenseCategory(str, Enum):
    """Полная классификация расходов пользователя."""
    SUBSCRIPTION = "subscription"
    RECURRING_PAYMENT = "recurring_payment"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    HOUSEHOLD_FOOD = "household_food"
    HOUSEHOLD_TRANSPORT = "household_transport"
    HOUSEHOLD_CAFE = "household_cafe"
    HOUSEHOLD_PHARMACY = "household_pharmacy"
    MARKETPLACE = "marketplace"
    CASH_WITHDRAWAL = "cash_withdrawal"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"
 
 
class Transaction(BaseModel):
    date: str
    amount: float
    raw_description: str
    category: Optional[str] = None
 
 
class Subscription(BaseModel):
    service_name: str
    monthly_cost: float
    yearly_cost: float
    frequency: str
    confidence: str
    alerts: List[str]
    transactions: List[Transaction]
    subscription_type: str = "subscription"
    actual_spent_in_period: float = 0.0
    mir_compatible: bool = True
    cancellation_guide: Optional[str] = None
    # --- добавлено 06.09: поля для карточки подписки в чате ---
    charge_amount: Optional[float] = None      # цена одного списания (последнего)
    charges_count: int = 0                     # сколько списаний в периоде
    last_charge: Optional[str] = None          # дата последнего списания, YYYY-MM-DD
    next_charge: Optional[str] = None          # ожидаемая дата следующего списания
    yearly_savings: Optional[float] = None     # экономия за год вперёд при отказе
 
 
class ExpenseCluster(BaseModel):
    """Кластер транзакций одного типа для общей картины расходов."""
    category: ExpenseCategory
    canonical_name: str
    total_amount: float
    transaction_count: int
    transactions: List[Transaction]
    is_subscription: bool = False
    mir_compatible: bool = True
    cancellation_guide: Optional[str] = None
    confidence: str = "medium"
    reason: str = ""
 
 
class SpendingOverview(BaseModel):
    """Сводка по всем категориям расходов."""
    total_spent: float
    total_income: float
    total_subscriptions: float
    total_recurring: float
    total_household: float
    total_transfers_out: float
    subscriptions_count: int
    categories: List[ExpenseCluster]
 
 
class AnalyzeResponse(BaseModel):
    subscriptions: List[Subscription]
    total_monthly_savings_potential: float
    total_actual_spent: float = 0.0
    period_analyzed: str = "all"
    spending_overview: Optional[SpendingOverview] = None