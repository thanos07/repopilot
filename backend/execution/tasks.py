from celery import shared_task
from django.db import transaction
from django.utils import timezone
from coding_tasks.models import CodingTask, AgentRun
from coding_tasks.lifecycle import transition
from agent_engine.loop import execute_run

@shared_task
def run_coding_task(task_id):
    with transaction.atomic():
        task=CodingTask.objects.select_for_update().select_related('repository').get(pk=task_id)
        # Duplicate delivery never starts a second execution.
        if task.status!='QUEUED':return
        if task.cancel_requested:
            transition(task.id,'CANCELLED');return
        transition(task.id,'PREPARING','Preparing an isolated verification environment.')
        run=AgentRun.objects.create(task=task)
    try:
        execute_run(task,run)
        run.state='COMPLETED'
    except InterruptedError as exc:
        transition(task.id,'CANCELLED',str(exc));run.state='CANCELLED';run.stop_reason=str(exc)
    except Exception as exc:
        # Only our known domain errors are safe to return to the UI.
        from agent_engine.provider import BudgetExceeded,ProviderError
        from execution.sandbox import SandboxError
        from integrations.github.client import GitHubError
        message=str(exc) if isinstance(exc,(BudgetExceeded,ProviderError,SandboxError,GitHubError)) else 'Execution failed. Check the worker logs and saved patch.'
        transition(task.id,'FAILED',message)
        run.state='FAILED';run.stop_reason=message
        if not isinstance(exc,(BudgetExceeded,ProviderError,SandboxError,GitHubError)):
            import logging
            logging.getLogger(__name__).exception('Coding task failed')
    finally:
        run.tools.filter(status='STARTED').update(status='FAILED',result={'error':'Execution interrupted before a result was recorded.'})
        run.finished_at=timezone.now();run.save()

@shared_task
def publish_task(task_id):
    from integrations.github.publish import publish
    from django.db import connection
    import uuid
    if connection.vendor!='postgresql':
        transition(task_id,'APPROVED','Publishing requires PostgreSQL for a cross-worker publication lock.')
        return
    key=(uuid.UUID(str(task_id)).int >> 64) & ((1<<63)-1)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)',[key])
        locked=cursor.fetchone()[0]
    if not locked:return
    try:publish(task_id)
    except Exception:
        from coding_tasks.models import PullRequestPublication
        PullRequestPublication.objects.filter(task_id=task_id).update(status='FAILED',error='Publication failed. Inspect GitHub state before retrying.')
        transition(task_id,'APPROVED','Publication interrupted. The approved patch is retained; retry reconciles remote state.')
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(%s)',[key])
