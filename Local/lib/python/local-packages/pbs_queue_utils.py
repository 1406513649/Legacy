from subprocess import check_output
from getpass import getuser

def check_queue(user=None):
    """Checks qstat and returns dictionary of jobs being run by the user"""
    jobs = {}
    user = user or getuser()
    command = 'qstat -u {0}'.format(user)
    out = check_output(command.split()).decode('utf-8')
    for line in out.split('\n'):
        if user in line:
            jobid, user, _, _, _, _, _, _, _, stat, _ = line.split() 
            assert user == user
            jobs[jobid.split('.')[0].strip()] = stat.strip()
    n = len([1 for (k,v) in jobs.items() if v in 'QR'])
    return n, jobs


def delete_from_queue(job):
    n, jobs = check_queue()
    if job not in jobs:
        return
    p = Popen('qdel {0}'.format(job))
    p.wait()
    return 0
