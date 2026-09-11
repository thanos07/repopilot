import time
from decimal import Decimal
from django.conf import settings
from openai import OpenAI
from coding_tasks.models import UsageRecord

class BudgetExceeded(RuntimeError):pass
class ProviderError(RuntimeError):pass

def calculate_cost(input_tokens,cached_tokens,output_tokens,rates):
    cached=min(input_tokens,max(0,cached_tokens or 0))
    return ((Decimal(input_tokens-cached)*Decimal(rates['input']))+(Decimal(cached)*Decimal(rates['cached']))+(Decimal(output_tokens)*Decimal(rates['output'])))/Decimal(1_000_000)

class Provider:
    def __init__(self):
        if not settings.AI_API_KEY:raise ProviderError('AI_API_KEY is not configured.')
        self.client=OpenAI(api_key=settings.AI_API_KEY,base_url=settings.AI_BASE_URL,timeout=60,max_retries=0)
        # Configured ceiling rates, intentionally conservative during off-peak hours.
        self.rates={'input':settings.AI_PRICE_INPUT,'cached':settings.AI_PRICE_CACHED,'output':settings.AI_PRICE_OUTPUT,'basis':'configured ceiling estimate'}
    def turn(self,messages,tools,run):
        used=sum(UsageRecord.objects.filter(run__task=run.task).values_list('estimated_cost',flat=True),Decimal(0))
        # Conservative byte bound plus schema overhead; reject before a call can overspend.
        import json
        size=len(json.dumps(messages,ensure_ascii=False).encode())+len(json.dumps(tools).encode())+4096
        reserve=calculate_cost(size,0,settings.AI_MAX_OUTPUT_TOKENS,self.rates)
        if used+reserve>Decimal(run.task.max_cost):raise BudgetExceeded('Not enough remaining budget for the next model call.')
        account_used=sum(UsageRecord.objects.filter(run__task__owner=run.task.owner).values_list('estimated_cost',flat=True),Decimal(0))
        if account_used+reserve>Decimal(settings.AI_ACCOUNT_BUDGET):raise BudgetExceeded('Account API estimate limit reached. Review recorded usage and your provider balance before increasing AI_ACCOUNT_BUDGET.')
        started=time.monotonic()
        try:
            kwargs={'model':settings.AI_MODEL,'messages':messages,'tools':tools,'max_tokens':settings.AI_MAX_OUTPUT_TOKENS}
            # V1 explicitly disables thinking; no private reasoning is stored or shown.
            if 'deepseek.com' in settings.AI_BASE_URL:kwargs['extra_body']={'thinking':{'type':'disabled'}}
            r=self.client.chat.completions.create(**kwargs)
        except Exception as exc:raise ProviderError('Model request failed ('+type(exc).__name__+'). No fallback patch was generated.') from exc
        if r.usage is None:raise ProviderError('Provider omitted usage metadata; stopping because cost cannot be accounted for.')
        usage=r.usage.model_dump();input_tokens=usage['prompt_tokens'];output_tokens=usage['completion_tokens']
        cached=usage.get('prompt_cache_hit_tokens')
        if cached is None:cached=(usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        cost=calculate_cost(input_tokens,cached,output_tokens,self.rates)
        UsageRecord.objects.create(run=run,requested_model=settings.AI_MODEL,returned_model=r.model,input_tokens=input_tokens,cached_tokens=cached,output_tokens=output_tokens,rates=self.rates,estimated_cost=cost,latency_ms=int((time.monotonic()-started)*1000))
        if used+cost>Decimal(run.task.max_cost):raise BudgetExceeded('Reported usage reached the task budget.')
        m=r.choices[0].message
        return m.model_dump(exclude_none=True,include={'role','content','tool_calls'})
