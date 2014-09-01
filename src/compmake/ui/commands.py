''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
'''
from .. import CompmakeConstants, get_compmake_status
from ..jobs import all_jobs, clean_target
from ..structures import JobFailed, MakeFailed, ShellExitRequested, UserError
from ..utils import safe_pickle_dump
from .console import ask_question
from .helpers import ACTIONS, COMMANDS_ADVANCED, GENERAL, ui_command, ui_section
from .visualization import error, info


ui_section(GENERAL)

__all__ = [
    'make_single',
    'exit',
    '_raise_if_failed',
    'ask_if_sure_remake',
]

@ui_command(alias='quit')
def exit(context):  # @ReservedAssignment
    '''Exits Compmake's console.'''
    raise ShellExitRequested()

def _raise_if_failed(manager):
    if manager.failed:
        raise MakeFailed(failed=manager.failed,
                         blocked=manager.blocked)
#         if manager.blocked:
#             msg = ('%d job(s) failed, %d job(s) blocked.' % 
#                     (len(manager.failed), len(manager.blocked)))
#         else:
#             msg =  ('%d job(s) failed.' % len(manager.failed))
# 
#         if len(manager.failed) < 5:
#             for f in manager.failed:
#                 msg += '\n- %s' % f
#         raise CommandFailed(msg)


@ui_command(section=COMMANDS_ADVANCED,  dbchange=True)
def delete(job_list, context):
    """ Remove completely the job from the DB. Useful for generated jobs ("delete not root"). """
    from compmake.jobs.storage import delete_all_job_data
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    for job_id in job_list:
        delete_all_job_data(job_id=job_id, db=db)

 

@ui_command(section=ACTIONS, dbchange=True)
def clean(job_list, context):
    ''' Cleans the result of the selected computation (or everything \
        if nothing specified). '''
    db = context.get_compmake_db()

    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    if not job_list:
        job_list = list(all_jobs(db=db))

    if not job_list:
        return

    # Use context
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = "Should I clean %d jobs? [y/n] " % len(job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return

    for job_id in job_list:
        clean_target(job_id, db=db)


# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def make_single(job_list, context, out_result):
    ''' Makes a single job -- not for users, but for slave mode. '''
    if len(job_list) > 1:
        raise UserError("I want only one job")

    from compmake.jobs import actions
    try:
        job_id = job_list[0]
        #info('making job %s' % job_id)
        res = actions.make(job_id=job_id, context=context)
        #info('Writing to %r' % out_result)
        safe_pickle_dump(res, out_result)
        return 0
    except JobFailed as e:
        #info('Writing to %r' % out_result)
        safe_pickle_dump(e.get_result_dict(), out_result)
        raise MakeFailed(failed=[job_id])
    except BaseException as e:
        error('warning: %s' % e)
        raise


def ask_if_sure_remake(non_empty_job_list):
    """ If interactive, ask the user yes or no. Otherwise returns True. """
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = ("Should I clean and remake %d jobs? [y/n] " % 
            len(non_empty_job_list))
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return False
        else:
            return True
    return True

