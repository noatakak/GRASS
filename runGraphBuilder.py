import os
from grass.Outdated.graphBuilder import graphBuilder

# Remove key when pushing
os.environ['OPENAI_API_KEY'] = ''

graphBuilder.main()