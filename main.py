import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from agent.agent import run

if __name__ == "__main__":
    run()
