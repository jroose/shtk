import os
import sys

if __name__ == "__main__":
    sys.stdout.write(os.getenv(sys.argv[1]))
