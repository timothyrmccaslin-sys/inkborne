import os; P=os.environ.get('RUSTY_WORK','/tmp/rusty-ib-work')+'/core/src/lib.rs'
open(P,'a').write(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'p6_tests.rs')).read())
