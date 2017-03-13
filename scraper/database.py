import os
import subprocess
import shlex
from pdb import set_trace

class MongoWrapper(object):

    def __init__(self):
        self.set_up()

    def run_command_no_shell(self, cmd, l=None):
        process = subprocess.Popen(shlex.split(cmd), shell=False, stderr=l, stdout=l)
        return process.pid

    def set_up(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        proj_dir = dir_path[:dir_path.rfind('/')]
        mongod = os.path.join(proj_dir, 'mongodb/bin/mongod')
        db_dir = os.path.join(proj_dir, 'data')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        cmd = '{} --dbpath {}'.format(mongod, db_dir)
        self.db_pid = self.run_command_no_shell(cmd)


def main():
    db = MongoWrapper()

if __name__=='__main__':
    main()
