import uuid
from django.conf import settings
from django.db import models

class CodingTask(models.Model):
    class State(models.TextChoices):
        DRAFT='DRAFT'; QUEUED='QUEUED'; PREPARING='PREPARING'; ANALYZING='ANALYZING'; PLANNING='PLANNING'; IMPLEMENTING='IMPLEMENTING'; TESTING='TESTING'; REVIEWING='REVIEWING'; AWAITING_APPROVAL='AWAITING_APPROVAL'; APPROVED='APPROVED'; PUBLISHING='PUBLISHING'; PR_CREATED='PR_CREATED'; FAILED='FAILED'; CANCELLED='CANCELLED'
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    repository=models.ForeignKey('repositories.Repository',on_delete=models.PROTECT)
    title=models.CharField(max_length=240)
    description=models.TextField()
    status=models.CharField(max_length=24,choices=State.choices,default=State.DRAFT,db_index=True)
    base_sha=models.CharField(max_length=40,blank=True)
    plan=models.JSONField(default=list)
    summary=models.TextField(blank=True)
    limitation=models.TextField(blank=True)
    max_iterations=models.PositiveIntegerField(default=12)
    max_tools=models.PositiveIntegerField(default=24)
    max_test_runs=models.PositiveIntegerField(default=4)
    max_seconds=models.PositiveIntegerField(default=900)
    max_cost=models.DecimalField(max_digits=10,decimal_places=6,default='0.05')
    cancel_requested=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-created_at']

class AgentRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey(CodingTask,on_delete=models.CASCADE,related_name='runs')
    state=models.CharField(max_length=20,default='RUNNING')
    sandbox_id=models.CharField(max_length=180,blank=True)
    iteration=models.PositiveIntegerField(default=0)
    tool_count=models.PositiveIntegerField(default=0)
    stop_reason=models.TextField(blank=True)
    started_at=models.DateTimeField(auto_now_add=True)
    heartbeat_at=models.DateTimeField(auto_now=True)
    finished_at=models.DateTimeField(null=True)

class AgentStep(models.Model):
    run=models.ForeignKey(AgentRun,on_delete=models.CASCADE,related_name='steps')
    sequence=models.PositiveIntegerField()
    summary=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','sequence'],name='unique_run_step')]

class ToolExecution(models.Model):
    run=models.ForeignKey(AgentRun,on_delete=models.CASCADE,related_name='tools')
    sequence=models.PositiveIntegerField()
    name=models.CharField(max_length=60)
    arguments=models.JSONField(default=dict)
    result=models.JSONField(default=dict)
    status=models.CharField(max_length=20,default='STARTED')
    duration_ms=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','sequence'],name='unique_run_tool')]

class PatchSet(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey(CodingTask,on_delete=models.CASCADE,related_name='patches')
    base_sha=models.CharField(max_length=40)
    digest=models.CharField(max_length=64)
    diff=models.TextField()
    files=models.JSONField(default=list)
    # Snapshot supports publishing without executing repository code again.
    contents=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)

class TestRun(models.Model):
    task=models.ForeignKey(CodingTask,on_delete=models.CASCADE,related_name='tests')
    run=models.ForeignKey(AgentRun,on_delete=models.CASCADE)
    patch_digest=models.CharField(max_length=64,blank=True)
    phase=models.CharField(max_length=20)
    status=models.CharField(max_length=20)
    exit_code=models.IntegerField(null=True)
    stdout=models.TextField(blank=True)
    stderr=models.TextField(blank=True)
    duration_ms=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)

class UsageRecord(models.Model):
    run=models.ForeignKey(AgentRun,on_delete=models.CASCADE,related_name='usage')
    requested_model=models.CharField(max_length=120)
    returned_model=models.CharField(max_length=120)
    input_tokens=models.PositiveIntegerField()
    cached_tokens=models.PositiveIntegerField(null=True)
    output_tokens=models.PositiveIntegerField()
    rates=models.JSONField(default=dict)
    estimated_cost=models.DecimalField(max_digits=14,decimal_places=8)
    latency_ms=models.PositiveIntegerField()
    created_at=models.DateTimeField(auto_now_add=True)

class ReviewDecision(models.Model):
    task=models.ForeignKey(CodingTask,on_delete=models.CASCADE,related_name='reviews')
    patch=models.ForeignKey(PatchSet,on_delete=models.PROTECT)
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    decision=models.CharField(max_length=20,default='APPROVED')
    created_at=models.DateTimeField(auto_now_add=True)

class PullRequestPublication(models.Model):
    task=models.OneToOneField(CodingTask,on_delete=models.CASCADE,related_name='publication')
    patch=models.ForeignKey(PatchSet,on_delete=models.PROTECT)
    branch=models.CharField(max_length=200)
    commit_sha=models.CharField(max_length=40,blank=True)
    pr_url=models.URLField(blank=True)
    status=models.CharField(max_length=20,default='PENDING')
    error=models.TextField(blank=True)

class TaskEvent(models.Model):
    task=models.ForeignKey(CodingTask,on_delete=models.CASCADE,related_name='events')
    kind=models.CharField(max_length=60)
    message=models.CharField(max_length=1000)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['id']
