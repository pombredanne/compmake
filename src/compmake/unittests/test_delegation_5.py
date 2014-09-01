from nose.tools import istest

from tempfile import mkdtemp
from compmake.storage.filesystem import StorageFilesystem
from compmake.context import Context
import unittest
from compmake.jobs.storage import get_job


def g():
    return 2

def f(context):
    return context.comp(g)

def e(context):
    return context.comp_dynamic(f)

def h(i):
    assert i==2

    
def define_jobs(root):
    db = StorageFilesystem(root, compress=True)
    cc = Context(db=db)
    cc.comp(h, cc.comp_dynamic(e))
#     cc.batch_command('make;ls')
#     cc.batch_command('make;ls')
#     cc.batch_command('make;ls')
#     cc.batch_command('details e')
#     cc.batch_command('check_consistency raise_if_error=1')
    return db, cc

@istest
class TestDelegation5(unittest.TestCase):
    """ 
        Here's the problem: when the master are overwritten then
        the additional dependencies are lost.
    """

    def test_delegation_5(self):
        root = mkdtemp()
        db, cc = define_jobs(root)
        job0 = get_job('h', db)
        self.assertEqual(job0.children, set(['e']))
        
        cc.batch_command('make;ls')
        
        job = get_job('h', db)
        self.assertEqual(job.children, set(['e', 'g', 'f']))
        print('parents: %s' % job.parents)
        print('children: %s' % job.children)

        cc.batch_command('ls')
        cc.batch_command('check_consistency raise_if_error=1')
        # Now just define h again
        db, cc = define_jobs(root)
        cc.batch_command('check_consistency raise_if_error=1')
        job2 = get_job('h', db)
        self.assertEqual(job2.children, set(['e', 'g', 'f']))
            