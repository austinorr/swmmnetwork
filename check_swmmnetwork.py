import sys

import swmmnetwork
status = swmmnetwork.test(*sys.argv[1:])
sys.exit(status)
