from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from coding_tasks.models import AgentRun,CodingTask
from coding_tasks.lifecycle import transition

class Command(BaseCommand):
    help='Mark interrupted runs failed after a 20-minute stale heartbeat. Saved patches remain available for explicit retry.'
    def handle(self,*args,**kwargs):
        cutoff=timezone.now()-timedelta(minutes=20);count=0
        for pk in AgentRun.objects.filter(state='RUNNING',heartbeat_at__lt=cutoff).values_list('pk',flat=True):
            with transaction.atomic():
                run=AgentRun.objects.select_for_update().get(pk=pk)
                if run.state!='RUNNING' or run.heartbeat_at>=cutoff:continue
                task=CodingTask.objects.select_for_update().get(pk=run.task_id)
                if task.status not in {'PREPARING','ANALYZING','PLANNING','IMPLEMENTING','TESTING','REVIEWING'}:continue
                transition(task.id,'FAILED','Worker heartbeat expired. Saved patch is retained for explicit retry.')
                run.state='FAILED';run.stop_reason='Stale heartbeat';run.finished_at=timezone.now();run.save();count+=1
        self.stdout.write(f'Recovered {count} interrupted runs. No work was replayed automatically.')
