import os
import subprocess
import shlex
import time
from pymongo import MongoClient
from pdb import set_trace

class MongoWrapper(object):

    def __init__(self, db_name):
        self.db_name = db_name
        #self.set_up()
        self.client = MongoClient()
        self.db = self.client[self.db_name]

    def run_command_no_shell(self, cmd, l=None):
        process = subprocess.Popen(shlex.split(cmd), shell=False, stderr=l, stdout=l)
        return process.pid

    def run_command(self, cmd):
        process = subprocess.Popen(cmd, shell=True)
        process.communicate()

    def set_up(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        proj_dir = dir_path[:dir_path.rfind('/')]
        mongod = os.path.join(proj_dir, 'mongodb/bin/mongod')
        db_dir = os.path.join(proj_dir, 'data')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        cmd = '{} --dbpath {}'.format(mongod, db_dir)
        #FNULL = open(os.devnull, 'w')
        self.db_pid = self.run_command_no_shell(cmd)
        time.sleep(10)

    def clean_up(self):
        self.client.close()
        cmd = 'kill -9 {}'.format(self.db_pid)
        self.run_command(cmd)

    def add_entry(self, entry):
        posts = self.db.posts
        post_id = posts.insert_one(entry).inserted_id

def main():
    db = MongoWrapper('articles5')
    db.add_entry({"name": "dbthaker"})

if __name__=='__main__':
    main()
