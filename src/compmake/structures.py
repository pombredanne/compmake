from contracts import contract, describe_value

'''
    A Job represents the computation as passed by the user.
    It contains only the "action" but not the state.
    (The state of the computation is represented by a Cache object.)
    
    A Cache object can be in one of the following states:
    
    *) non-existent / or NOT_STARTED
       (no difference between these states)
       
    *) IN_PROGRESS: The yielding mechanism is taking care of 
       the incremental computation.
       
       computation:  current computation
       user_object:  None / invalid
       timestamp:    None / timestamp
       tmp_result:   set to the temporary result (if any)
       
       In this state, we also publish a progress report. 
       
    *) DONE:  The computation has been completed
    
       computation:  current computation
       user_object: the result of the computation
       timestamp:   when computation was completed 
       timetaken:   time taken by the computation
       tmp_result:  None
        
       
    *) FAILED
       The computation has failed for some reason

       computation:  failed computation

    Note that user_object and tmp_result are stored separately 
    from the Cache element.
    
    DB Layout:
    
        'job_id:computation'       Job object
        'job_id:cache'             Cache object
        'job_id:user_object'       Result of the computation
        'job_id:user_object_tmp'   
    
    
    
    Up-to-date or not?
    =================
    
    Here we have to be careful because of the fact that we have
    the special state MORE_REQUESTED. 
    Is it a computation done if MORE_REQUESTED? Well, we could say 
    no, because when more is completed, the parents will need to be
    redone. However, the use case is that:
    1) you do the all computation
    2) you explicity ask MORE for some targets
    3) you explicitly ask to redo the parents of those targets
    Therefore, a MORE_REQUESTED state is considered as uptodate.
     
    
'''
import os
from compmake.utils.pickle_frustration import pickle_main_context_save

__all__ = [
    'Promise',
    'Job',
    'Cache',
    'execute_with_context'
]


class Promise(object):
    def __init__(self, job_id):
        self.job_id = job_id

    def __repr__(self):
        return 'Promise(%r)' % self.job_id


class Job(object):
    @contract(defined_by='list[>=1](str)', children=set)
    def __init__(self, job_id, children, command_desc,
                 needs_context=False,
                 defined_by=None):
        """
        
            needs_context: new facility for dynamic jobs
            defined_by: name of jobs defining this job dynamically
                        This is the stack of jobs. 'root' is the first.
                        
            children: the direct dependencies
        """
        self.job_id = job_id
        self.children = set(children)
        self.command_desc = command_desc
        self.parents = set()
        self.needs_context = needs_context
        self.defined_by = defined_by
        assert len(defined_by) >= 1, defined_by
        assert defined_by[0] == 'root', defined_by
        # str -> set(str), where the key is one
        # of the direct children 
        self.dynamic_children = {}

        self.pickle_main_context = pickle_main_context_save() 
        
def same_computation(jobargs1, jobargs2):
    """ Returns boolean, string tuple """
    cmd1, args1, kwargs1 = jobargs1
    cmd2, args2, kwargs2 = jobargs2

    equal_command = cmd1 == cmd2
    equal_args = args1 == args2
    equal_kwargs = kwargs1 == kwargs2

    equal = equal_args and equal_kwargs and equal_command
    if not equal:
        reason = ""

        if not equal_command:
            reason += '* function changed \n'
            reason += '  - old: %s \n' % cmd1
            reason += '  - new: %s \n' % cmd2

            # TODO: can we check the actual code?

        warn = ' (or you did not implement proper __eq__)'
        if len(args1) != len(args2):
            reason += '* different number of arguments (%d -> %d)\n' % \
                      (len(args1), len(args2))
        else:
            for i, ob in enumerate(args1):
                if ob != args2[i]:
                    reason += '* arg #%d changed %s \n' % (i, warn)
                    reason += '  - old: %s\n' % describe_value(ob)
                    reason += '  - old: %s\n' % describe_value(args2[i])

        for key, value in kwargs1.items():
            if key not in kwargs2:
                reason += '* kwarg "%s" not found\n' % key
            elif value != kwargs2[key]:
                reason += '* argument "%s" changed %s \n' % (key, warn)
                reason += '  - old: %s \n' % describe_value(value)
                reason += '  - new: %s \n' % describe_value(kwargs2[key])

        # TODO: different lengths

        return False, reason
    else:
        return True, None


class Cache(object):
    # TODO: add blocked

    NOT_STARTED = 0
#     IN_PROGRESS = 1
    FAILED = 3
    BLOCKED = 5
    DONE = 4
    
    TIMESTAMP_TO_REMAKE = 0.0

    allowed_states = [NOT_STARTED, 
#                       IN_PROGRESS, 
                      FAILED, 
                      DONE, 
                      BLOCKED]

    state2desc = {
        NOT_STARTED: 'todo',
#         IN_PROGRESS: 'in prog.',
        BLOCKED: 'blocked',
        FAILED: 'failed',
        DONE: 'done'}

    def __init__(self, state):
        assert (state in Cache.allowed_states)
        self.state = state
        # if DONE:
        self.timestamp = 0.0
        self.cputime_used = None
        self.walltime_used = None

        self.jobs_defined = set()

        # in case of failure
        self.exception = None  # a short string
        self.backtrace = None  # a long string
        # 
        self.captured_stdout = None
        self.captured_stderr = None

        # used for visualization
        self.debug_in_progress = False


    def __repr__(self):
        return ('Cache(%s;%s;cpu:%s;wall:%s)' %
                (Cache.state2desc[self.state],
                 self.timestamp, self.cputime_used,
                 self.walltime_used))


class ProgressStage(object):
    @contract(name=str, iterations='tuple((float|int),(float|int))')
    def __init__(self, name, iterations, iteration_desc):
        self.name = name
        self.iterations = iterations
        self.iteration_desc = iteration_desc
        # We keep track of when to send the event
        self.last_broadcast = None

    def __str__(self):
        return "[%s %s %s]" % (self.name, self.iterations, self.iteration_desc)

    def was_finished(self):
        # allow off-by-one conventions
        if isinstance(self.iterations[1], int):
            return (self.iterations[0] >= self.iterations[1] - 1)
        else:
            return self.iterations[0] >= self.iterations[1]
            



