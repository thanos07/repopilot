from decimal import Decimal
from rest_framework import serializers
from repositories.models import Repository
from .models import CodingTask, TaskEvent, TestRun, PatchSet, UsageRecord

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:model=Repository;fields=['id','full_name','default_branch']
class EventSerializer(serializers.ModelSerializer):
    class Meta:model=TaskEvent;fields=['id','kind','message','created_at']
class TestSerializer(serializers.ModelSerializer):
    class Meta:model=TestRun;fields=['id','phase','status','exit_code','stdout','stderr','duration_ms','patch_digest']
class PatchSerializer(serializers.ModelSerializer):
    class Meta:model=PatchSet;fields=['id','digest','diff','files']
class TaskSerializer(serializers.ModelSerializer):
    repository=RepositorySerializer(read_only=True)
    events=EventSerializer(many=True,read_only=True)
    tests=TestSerializer(many=True,read_only=True)
    patch=serializers.SerializerMethodField()
    cost=serializers.SerializerMethodField()
    model=serializers.SerializerMethodField()
    tool_count=serializers.SerializerMethodField()
    pr_url=serializers.SerializerMethodField()
    usage=serializers.SerializerMethodField()
    tools=serializers.SerializerMethodField()
    def get_usage(self,obj):
        records=list(UsageRecord.objects.filter(run__task=obj))
        input_tokens=sum(x.input_tokens for x in records)
        cached=None if any(x.cached_tokens is None for x in records) else sum(x.cached_tokens for x in records)
        return {'input_tokens':input_tokens,'output_tokens':sum(x.output_tokens for x in records),'cached_tokens':cached,'cache_hit_percent':round(100*cached/input_tokens,1) if cached is not None and input_tokens else None,'calls':len(records),'cost_basis':'Configured ceiling rates; sandbox charges excluded.'}
    def get_tools(self,obj):
        from .models import ToolExecution
        return list(ToolExecution.objects.filter(run__task=obj).order_by('id').values('id','name','status','duration_ms'))
    def get_patch(self,obj):
        p=obj.patches.order_by('-created_at').first()
        return PatchSerializer(p).data if p else None
    def get_cost(self,obj):return str(sum(UsageRecord.objects.filter(run__task=obj).values_list('estimated_cost',flat=True),Decimal(0)))
    def get_model(self,obj):
        u=UsageRecord.objects.filter(run__task=obj).order_by('-created_at').first()
        return u.returned_model if u else ''
    def get_tool_count(self,obj):return sum(obj.runs.values_list('tool_count',flat=True))
    def get_pr_url(self,obj):return getattr(getattr(obj,'publication',None),'pr_url','')
    class Meta:
        model=CodingTask
        fields=['id','title','description','status','repository','base_sha','plan','summary','limitation','events','tests','patch','cost','model','tool_count','pr_url','created_at','usage','tools','max_cost','max_iterations','max_tools','max_test_runs']
