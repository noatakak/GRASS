import os
from grass.graphBuilder import graphBuilder

# Remove key when pushing
os.environ['OPENAI_API_KEY'] = ''

graphBuilder.main()