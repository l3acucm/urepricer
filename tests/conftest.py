import sys
import os

current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)
