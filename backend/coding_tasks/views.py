from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError,PermissionDenied
from repositories.models import Repository
from integrations.github.client import repo_name,metadata,GitHubError
from .models import CodingTask,TaskEvent
from .serializers import TaskSerializer,RepositorySerializer
from .lifecycle import transition,approve

def task_for(user,pk):return get_object_or_404(CodingTask.objects.select_related('repository'),pk=pk,owner=user)
def operator(user):
    if not user.is_staff:raise PermissionDenied('Live execution and publishing are restricted to the workspace operator in v1.')

class RepositoryList(APIView):
    def get(self,r):return Response(RepositorySerializer(Repository.objects.filter(owner=r.user),many=True).data)
    def post(self,r):
        operator(r.user)
        try:name=repo_name(r.data.get('url',''));data=metadata(name)
        except GitHubError as e:raise ValidationError({'detail':str(e)})
        repo,_=Repository.objects.get_or_create(owner=r.user,github_id=data['id'],defaults={'full_name':data['full_name'],'default_branch':data['default_branch']})
        return Response(RepositorySerializer(repo).data,status=201)

class TaskList(APIView):
    def get(self,r):return Response(TaskSerializer(CodingTask.objects.filter(owner=r.user).select_related('repository')[:50],many=True).data)
    def post(self,r):
        operator(r.user)
        repo=get_object_or_404(Repository,pk=r.data.get('repository_id'),owner=r.user)
        title=str(r.data.get('title','')).strip();description=str(r.data.get('description','')).strip()
        if not title or len(title)>240 or not description or len(description)>12000:raise ValidationError({'detail':'Provide a title (up to 240 characters) and description (up to 12,000 characters).'})
        t=CodingTask.objects.create(owner=r.user,repository=repo,title=title,description=description)
        TaskEvent.objects.create(task=t,kind='draft',message='Task created. No execution has started.')
        return Response(TaskSerializer(t).data,status=201)

class TaskDetail(APIView):
    def get(self,r,pk):return Response(TaskSerializer(task_for(r.user,pk)).data)

class TaskAction(APIView):
    def post(self,r,pk,action):
        t=task_for(r.user,pk)
        operator(r.user)
        if action=='approve':t=approve(t.id,r.user,r.data.get('digest',''))
        elif action=='cancel':
            with transaction.atomic():
                t=CodingTask.objects.select_for_update().get(pk=t.id)
                if t.status in {'PUBLISHING','PR_CREATED','CANCELLED','FAILED'}:raise ValidationError({'detail':'This task cannot be cancelled in its current state.'})
                t.cancel_requested=True;t.save(update_fields=['cancel_requested'])
                if t.status in {'DRAFT','QUEUED','AWAITING_APPROVAL','APPROVED'}:
                    if t.status=='DRAFT':t.status='CANCELLED';t.save(update_fields=['status'])
                    else:t=transition(t.id,'CANCELLED')
        elif action=='start':
            operator(r.user)
            if not settings.LIVE_EXECUTION_ENABLED or not all([settings.AI_API_KEY,settings.E2B_API_KEY,settings.E2B_TEMPLATE]):raise ValidationError({'detail':'Live execution is disabled or model/sandbox configuration is incomplete.'})
            with transaction.atomic():
                # Serialize operator starts to enforce one running task per account.
                get_user_model().objects.select_for_update().get(pk=r.user.pk)
                if CodingTask.objects.filter(owner=r.user,status__in=['QUEUED','PREPARING','ANALYZING','PLANNING','IMPLEMENTING','TESTING','REVIEWING']).exists():raise ValidationError({'detail':'A task is already running in this workspace.'})
                t=transition(t.id,'QUEUED','Task queued for background execution.')
            try:
                from execution.tasks import run_coding_task
                run_coding_task.delay(str(t.id))
            except Exception:
                transition(t.id,'FAILED','Queue unavailable. No execution started.')
                raise ValidationError({'detail':'Background queue unavailable. Start Redis and the worker, then retry.'})
        elif action=='publish':
            operator(r.user)
            if not settings.PUBLISH_ENABLED:raise ValidationError({'detail':'GitHub publishing is disabled in server settings.'})
            with transaction.atomic():
                t=CodingTask.objects.select_for_update().get(pk=t.id)
                if t.status!='APPROVED':raise ValidationError({'detail':'Approve the patch before publishing.'})
                t=transition(t.id,'PUBLISHING','Publishing the approved patch as a draft pull request.')
            try:
                from execution.tasks import publish_task
                publish_task.delay(str(t.id))
            except Exception:
                transition(t.id,'APPROVED','Queue unavailable; approval retained.')
                raise ValidationError({'detail':'Background queue unavailable.'})
        else:raise ValidationError({'detail':'Unknown action.'})
        t.refresh_from_db();return Response(TaskSerializer(t).data)

class ToolDetail(APIView):
    def get(self,r,pk,tool_id):
        from .models import ToolExecution
        t=task_for(r.user,pk)
        x=get_object_or_404(ToolExecution,pk=tool_id,run__task=t)
        return Response({'name':x.name,'arguments':x.arguments,'result':x.result,'status':x.status,'duration_ms':x.duration_ms})
