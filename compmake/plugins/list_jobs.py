''' The actual interface of some commands in commands.py '''
from ..jobs import get_job_cache, all_jobs, up_to_date, parse_job_list
from ..structures import Cache
from ..ui import ui_command, VISUALIZATION
from ..utils import duration_human, colored
from time import time
import string


@ui_command(section=VISUALIZATION, alias='ls')
def list(args):  # @ReservedAssignment
    '''Lists the status of the selected targets (or all targets \
if not specified).
    
    If only one job is specified, then it is listed in more detail.  '''
    if not args:
        job_list = all_jobs()
    else:
        job_list = parse_job_list(args)

    list_jobs(job_list)
    return 0


state2color = {
        # The ones commented out are not possible
        # (Cache.NOT_STARTED, True): None,
        (Cache.NOT_STARTED, False): {}, #'attrs': ['dark']},
        # (Cache.IN_PROGRESS, True): None,
        (Cache.IN_PROGRESS, False): {'color': 'yellow'},
        (Cache.MORE_REQUESTED, True): {'color': 'blue'},
        (Cache.MORE_REQUESTED, False): {'color': 'green',
                                        'on_color': 'on_red'},
        #(Cache.FAILED, True): None,
        (Cache.FAILED, False): {'color': 'red'},
        (Cache.BLOCKED, True): {'color': 'yellow'},
        (Cache.BLOCKED, False): {'color': 'yellow'}, # XXX
        (Cache.DONE, True): {'color': 'green'},
        (Cache.DONE, False): {'color': 'magenta'},
}


def list_jobs(job_list):
    job_list = [x for x in job_list]
    #print('%s jobs in total' % len(job_list))
    if not job_list:
        print('No jobs found.')
        return

    jlen = max(len(x) for x in job_list)

    cpu_total = 0
    for job_id in job_list:
        # TODO: only ask up_to_date if necessary
        up, reason = up_to_date(job_id)

        Mmin = 4
        M = 40
        if jlen < M:
            indent = M - jlen
        else:
            indent = Mmin
        s = " " * indent + string.ljust(job_id, jlen) + '    '
        cache = get_job_cache(job_id)

        tag = Cache.state2desc[cache.state]

        #if not up:
        #    tag += ' (needs update)' 

        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % str(k)

        s += colored(tag, **state2color[k])

#        if cache.state == Cache.DONE and cache.done_iterations > 1:
#            s += ' %s iterations completed ' % cache.done_iterations

        if cache.state == Cache.IN_PROGRESS:
#            s += ' (%s/%s iterations in progress) ' % \
#                (cache.iterations_in_progress, cache.iterations_goal)
#                
            s += ' (in progress)'
        if up:
            cpu = cache.cputime_used
            cpu_total += cpu
            s += ' %5.1f min.  ' % (cpu / 60.0)
            when = duration_human(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE, Cache.MORE_REQUESTED]:
                s += " (needs update: %s)" % reason
        print(s)
    print('Total computation time: %s' % duration_human(cpu_total))

