import sys
from time import time
import re

from compmake.structures import Computation, ParsimException, UserError, Cache

#from compmake.storage import reset_cache, delete_cache
from compmake.process import make_targets, mark_more, mark_remake,\
    top_targets, parmake_targets, make_sure_cache_is_sane, \
    up_to_date, clean_target

from compmake.process_storage import get_job_cache

from compmake.visualization import duration_human

def make_sure_pickable(obj):
    # TODO
    pass


def collect_dependencies(iterable):
    depends = []
    for i in iterable:
        if isinstance(i, Computation):
            depends.append(i)
        if isinstance(i, list):
            depends.extend(collect_dependencies(i))
        if isinstance(i, dict):
            depends.extend(collect_dependencies(i.values()))
    return list(set(depends))

def comp(command, *args, **kwargs):
    args = list(args) # args is a non iterable tuple
    # Get job id from arguments
    job_id_key = 'job_id'
    if job_id_key in kwargs:
        job_id = kwargs[job_id_key]
        del kwargs[job_id_key]
        if job_id in Computation.id2computations:
            raise UserError('Computation %s already defined.' % job_id)
    else:
        # make our own
        for i in xrange(1000000):
            job_id = str(command)+'-%d'%i
            if not job_id in Computation.id2computations:
                break

    assert(job_id not in Computation.id2computations )

    depends = collect_dependencies([args, kwargs])
    # make sure we do not have two Computation with the same id
    depends = [ Computation.id2computations[x.job_id] for x in depends ]
    
    c = Computation(job_id=job_id,depends=depends,
                    command=command, args=args, kwargs=kwargs)
    Computation.id2computations[job_id] = c
        # TODO: check for loops     
            
    for x in depends:
        if not c in x.needed_by:
            x.needed_by.append(c)
        
    return c

def add_computation(depends, parsim_job_id, command, *args, **kwargs):
    job_id = parsim_job_id
    
    if job_id in Computation.id2computations:
        raise ParsimException('Computation %s already defined.' % job_id)
    
    if not isinstance(depends, list):
        depends = [depends]
        
    for i, d in enumerate(depends):
        if isinstance(d, str):
            depends[i] = Computation.id2computations[d]
        elif isinstance(d, Computation):
            pass
        
    c = Computation(job_id=job_id,depends=depends,
                    command=command, args=args, kwargs=kwargs)
    Computation.id2computations[job_id] = c
        # TODO: check for loops     
    for x in depends:
        x.needed_by.append(c)
        
    return c



def reg_from_shell_wildcard(arg):
    """ Returns a regular expression from a shell wildcard expression """
    return re.compile('\A' + arg.replace('*', '.*') + '\Z')
                      
def parse_job_list(argv): 
    jobs = []
    for arg in argv:
        if arg.find('*') > -1:
            reg = reg_from_shell_wildcard(arg)
            matches = [x for x in Computation.id2computations.keys() 
                       if reg.match(x) ]
            jobs.extend(matches)
        else:
            if not arg in Computation.id2computations:
                raise ParsimException('Job %s not found ' % arg) 
            jobs.append(arg)
    return jobs

def interpret_commands():
    
    commands = sys.argv[1:]
    if len(commands) == 0:
        make_targets(top_targets())
        sys.exit(0)

    elif commands[0] == 'check':
        make_sure_cache_is_sane()

    elif commands[0] == 'clean':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            job_list = Computation.id2computations.keys()
        
        for job_id in job_list:
            # print "Cleaning %s" % job_id
            clean_target(job_id)
            

    elif commands[0] == 'list':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            job_list = Computation.id2computations.keys()
        job_list.sort()
        list_jobs(job_list)
         

    elif commands[0] == 'make':
        job_list = parse_job_list(commands[1:])
        if not job_list:
            job_list = top_targets()
        make_targets(job_list)
    
    elif commands[0] == 'parmake':
        job_list = parse_job_list(commands[1:])
        if not job_list:
            job_list = top_targets()
        
        parmake_targets(job_list)
        
    elif commands[0] == 'remake':
        job_list = parse_job_list(commands[1:])
        if not job_list:
            print "remake: specify which ones "
            sys.exit(2)
            
        for job in job_list:
           mark_remake(job)
            
        make_targets(job_list)
                    
    elif commands[0] == 'parremake':
        job_list = parse_job_list(commands[1:])
        if not job_list:
            print "parremake: specify which ones "
            sys.exit(2)
            
        parmake_targets(job_list)
            
    elif commands[0] == 'parmore':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "parmore: specify which ones "
            sys.exit(2)
        parmake_targets(job_list, more=True)

    elif commands[0] == 'more':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "more: specify which ones "
            sys.exit(2)
        
        for job in job_list:
           mark_more(job)
            
        make_targets(job_list, more=True)

    else:
        print "Uknown command %s" % commands[0]
        sys.exit(-1)    
    

def list_jobs(job_list):
   for job_id in job_list:
        up, reason = up_to_date(job_id)
        s = job_id
        s += " " * (50-len(s))
        cache = get_job_cache(job_id)
        s += Cache.state2desc[cache.state]
        if up:
            when = duration_human(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE, Cache.MORE_REQUESTED]:
                s += " (needs update: %s)" % reason 
        print s
        
        if cache.state == Cache.FAILED:
            print cache.exception
            print cache.backtrace
            
    
    