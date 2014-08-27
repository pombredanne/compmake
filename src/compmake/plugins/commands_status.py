from ..events import register_handler
from ..ui import error
from contracts.utils import indent


# TODO: command-succeeded: {'command': '
# command-interrupted: {'reason': 'KeyboardInterrupt', 'command': 'ls todo'}
def command_interrupted(context, event):  # @UnusedVariable
    error('Command %r interrupted.' % event.kwargs['command'])
register_handler('command-interrupted', command_interrupted)


def command_failed(context, event):  # @UnusedVariable
    error('Command %r failed: %s' % (event.kwargs['command'],
                                      event.kwargs['reason']))
register_handler('command-failed', command_failed)


def command_line_interrupted(context, event):  # @UnusedVariable
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error('Command sequence %r interrupted.' % command)
register_handler('command-line-interrupted', command_line_interrupted)


def command_line_failed(context, event):  # @UnusedVariable
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error('Command sequence %r failed.' % command)
register_handler('command-line-failed', command_line_failed)

def job_failed(context, event):  # @UnusedVariable
    error('Job %r failed: %s' % (event.kwargs['job_id'],
                                  event.kwargs['reason']))
    
register_handler('job-failed', job_failed)


def job_interrupted(context, event):  # @UnusedVariable
    error('Job %r interrupted:\n %s' % 
          (event.kwargs['job_id'],
            indent(event.kwargs['bt'], '> ')))
register_handler('job-interrupted', job_interrupted)

def compmake_bug(context, event):  # @UnusedVariable
    error(event.kwargs['user_msg'])
    error(event.kwargs['dev_msg'])

register_handler('compmake-bug', compmake_bug)


# We ignore some other events; otherwise they will be catched 
# by the default handler
def ignore(context, event):
    pass

register_handler('command-starting', ignore)
register_handler('command-line-starting', ignore)
register_handler('command-line-failed', ignore)
register_handler('command-line-succeeded', ignore)
register_handler('command-line-interrupted', ignore)
register_handler('manager-phase', ignore)

register_handler('parmake-status', ignore)

register_handler('job-succeeded', ignore)
register_handler('job-interrupted', ignore)

if True:  # debugging
    register_handler('worker-status', ignore)
    register_handler('manager-job-succeeded', ignore)
    register_handler('manager-job-failed', ignore)
    register_handler('manager-job-starting', ignore)

register_handler('manager-succeeded', ignore)  # TODO: maybe write sth


