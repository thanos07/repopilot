from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import CodingTask, TaskEvent, ReviewDecision

TRANSITIONS = {
 'DRAFT':{'QUEUED'},'QUEUED':{'PREPARING','FAILED','CANCELLED'},
 'PREPARING':{'ANALYZING','FAILED','CANCELLED'},'ANALYZING':{'PLANNING','FAILED','CANCELLED'},
 'PLANNING':{'IMPLEMENTING','FAILED','CANCELLED'},'IMPLEMENTING':{'TESTING','REVIEWING','FAILED','CANCELLED'},
 'TESTING':{'IMPLEMENTING','REVIEWING','FAILED','CANCELLED'},'REVIEWING':{'AWAITING_APPROVAL','FAILED','CANCELLED'},
 'AWAITING_APPROVAL':{'APPROVED','CANCELLED'},'APPROVED':{'PUBLISHING','CANCELLED'},
 'PUBLISHING':{'PR_CREATED','APPROVED','FAILED'},'FAILED':{'QUEUED'},'CANCELLED':set(),'PR_CREATED':set()
}
@transaction.atomic
def transition(task_id, state, message=''):
    t=CodingTask.objects.select_for_update().get(pk=task_id)
    if t.status==state:return t
    if state not in TRANSITIONS.get(t.status,set()):raise ValidationError(f'Cannot move from {t.status} to {state}.')
    t.status=state;t.save(update_fields=['status','updated_at'])
    TaskEvent.objects.create(task=t,kind=state.lower(),message=message or state.replace('_',' ').capitalize())
    return t

@transaction.atomic
def approve(task_id, user, digest):
    t=CodingTask.objects.select_for_update().get(pk=task_id,owner=user)
    p=t.patches.order_by('-created_at').first()
    if not p or p.digest!=digest or p.base_sha!=t.base_sha:raise ValidationError('The patch changed. Refresh and review it again.')
    if t.status!='AWAITING_APPROVAL':raise ValidationError('This task is not awaiting approval.')
    if not t.tests.filter(phase='final',patch_digest=p.digest,status='passed').exists():raise ValidationError('Passing final verification is required for this exact patch.')
    ReviewDecision.objects.create(task=t,patch=p,reviewer=user)
    return transition(t.id,'APPROVED','Human approved the exact patch.')
