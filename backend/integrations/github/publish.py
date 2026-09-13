from django.db import transaction
from urllib.parse import quote
from coding_tasks.models import CodingTask,PullRequestPublication
from coding_tasks.lifecycle import transition
from .client import AppClient,GitHubError

def publish(task_id):
    with transaction.atomic():
        task=CodingTask.objects.select_for_update().select_related('repository').get(pk=task_id)
        if task.status!='PUBLISHING':return
        if not task.owner.is_active or not task.owner.is_staff:raise GitHubError('Operator access is required.')
        patch=task.patches.order_by('-created_at').first()
        if not patch or patch.base_sha!=task.base_sha:raise GitHubError('Patch base mismatch.')
        if not task.tests.filter(phase='final',patch_digest=patch.digest,status='passed',exit_code=0).exists():raise GitHubError('Passing final verification is required.')
        if not task.reviews.filter(patch=patch,decision='APPROVED').exists():raise GitHubError('Exact patch approval missing.')
        publication,_=PullRequestPublication.objects.get_or_create(task=task,defaults={'patch':patch,'branch':'repopilot/'+str(task.id)[:8]+'-'+patch.digest[:8]})
        if publication.patch_id!=patch.id:raise GitHubError('Publication approval mismatch.')
    client=AppClient()
    try:
        root='/repos/'+task.repository.full_name
        default=quote(task.repository.default_branch,safe='')
        head=client.call('GET',root+'/git/ref/heads/'+default)['object']['sha']
        if head!=patch.base_sha:raise GitHubError('Target branch moved. New verification and approval are required.')
        existing=client.call('GET',root+'/pulls',params={'head':task.repository.full_name.split('/')[0]+':'+publication.branch,'state':'all'})
        if existing:
            pr=existing[0]
            if publication.commit_sha and pr['head']['sha']!=publication.commit_sha:raise GitHubError('Existing PR was modified.')
            publication.pr_url=pr['html_url']
        else:
            if not publication.commit_sha:
                base=client.call('GET',root+'/git/commits/'+patch.base_sha)
                base_tree=client.call('GET',root+'/git/trees/'+base['tree']['sha'],params={'recursive':'1'})
                if base_tree.get('truncated'):raise GitHubError('Repository tree is too large to publish safely.')
                modes={x['path']:x['mode'] for x in base_tree['tree']}
                tree=[]
                for path,content in patch.contents.items():
                    from agent_engine.tools import safe_path
                    safe_path(path)
                    blob=client.call('POST',root+'/git/blobs',json={'content':content,'encoding':'utf-8'})
                    mode=modes.get(path,'100644')
                    if mode not in {'100644','100755'}:raise GitHubError('Unsupported target file mode.')
                    tree.append({'path':path,'mode':mode,'type':'blob','sha':blob['sha']})
                new_tree=client.call('POST',root+'/git/trees',json={'base_tree':base['tree']['sha'],'tree':tree})
                commit=client.call('POST',root+'/git/commits',json={'message':task.title,'tree':new_tree['sha'],'parents':[patch.base_sha]})
                publication.commit_sha=commit['sha'];publication.save(update_fields=['commit_sha'])
            ref_path=root+'/git/ref/heads/'+publication.branch
            response=client.client.get(ref_path)
            if response.status_code==404:
                client.call('POST',root+'/git/refs',json={'ref':'refs/heads/'+publication.branch,'sha':publication.commit_sha})
            elif response.status_code!=200 or response.json()['object']['sha']!=publication.commit_sha:
                raise GitHubError('Existing branch differs; refusing to overwrite it.')
            pr=client.call('POST',root+'/pulls',json={'title':task.title,'head':publication.branch,'base':task.repository.default_branch,'draft':True,'body':task.summary+'\n\nVerification: final pytest preset passed.\n\nLimitations: '+task.limitation+'\n\nApproved patch: '+patch.digest})
            publication.pr_url=pr['html_url']
        publication.status='CREATED';publication.error='';publication.save()
        transition(task.id,'PR_CREATED','Draft pull request created after human approval.')
    finally:client.close()
