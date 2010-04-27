import sys
from time import time
import re

from compmake.structures import Computation, ParsimException, UserError, Cache
 
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
        # make sure that command does not have itself a job_id key
        available = command.func_code.co_varnames
        if job_id_key in available:
            raise UserError('You cannot define the job_id in this way' + 
                'because job_id is already a parameter of this function')    
        
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


from collections import namedtuple
def find_commands():
    Command = namedtuple('Command', 'function name doc ')
    commands = {}
    import compmake.ui_commands as ui_commands
    keys = ui_commands.__dict__.keys()
    keys.sort() # XXX does not work?
    for k in keys: 
        v = ui_commands.__dict__[k]
        if type(v) == type(ui_commands.make) and v.__module__ == 'compmake.ui_commands' and v.__doc__:
            commands[k] = Command(function=v,name=k,doc=v.__doc__)
    return commands

def list_commands(commands):
    for cmd in commands.values():
        function, name, doc = cmd
        print padleft(15, name), doc

def padleft(n, s):
    return " " * (n - len(s)) + s

def interpret_commands(commands):

    ui_commands = find_commands()
    
    if (len(commands) == 0) or commands[0]=='help':
        list_commands(ui_commands)
        sys.exit(0)

    command = commands[0]
    if not command in ui_commands.keys():
        print "Uknown command '%s' " % command
        list_commands(ui_commands)
        sys.exit(-2)
        
    function, name, doc = ui_commands[commands[0]]
    args = commands[1:]
    
    function_args = command.func_code.co_varnames
    if 'non_empty_job_list' in function_args:
        if not args:
            print "Command %s requires arguments" % command


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
    elif commands[0] == 'parmorecont':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "parmorecont: specify which ones "
            sys.exit(2)
            
        for i in range(100000):
            print "------- parmorecont: iteration %d" % i 
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
    