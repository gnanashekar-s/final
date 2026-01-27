from langfuse import Langfuse
import inspect
import sys
try:
    print(inspect.getfile(Langfuse))
except:
    print("Failed")
