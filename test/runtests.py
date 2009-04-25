#! /usr/bin/env python
import os
import sys
import unittest

if __name__ == "__main__":
    __file__ = sys.argv[0]

TESTDIR = os.path.dirname(os.path.abspath(__file__))
TOPDIR = os.path.dirname(TESTDIR)

def load_test_files():
    test_files = []
    for f in os.listdir(TESTDIR):
        if f.startswith('test_') and f.endswith('.py'):
            test_files.append(os.path.splitext(f)[0])
    return test_files
    
if __name__ == "__main__":
    if TOPDIR not in sys.path:
        sys.path.insert(0, TOPDIR)
    sys.path.insert(0, TESTDIR)
    suite = unittest.defaultTestLoader.loadTestsFromNames(load_test_files())
    try:
        v = sys.argv[1]
    except:
        v = 1
    runner = unittest.TextTestRunner(verbosity=int(v))
    runner.run(suite)
