import json
import networkx as nx
from networkx.readwrite import json_graph
from grass.control_primitives_context import load_control_primitives_context
from grass.graph_tools.primitive_knowledge import load_primitive_knowledge


# def load_graph_json(filepath):
#
# def get_resume_graph(filepath):
#     return load_graph_json(filepath)
# def get_primitive_graph():
#     return load_graph_json("grass/graph_tools/primitive_graph.json")
def save_graph(graph, filepath):
    print("saving graph to file: " + filepath)
    with open(filepath, 'w') as file:
        json.dump(json_graph.node_link_data(graph), file, indent=4)

def create_primitive_graph():
    graph = nx.DiGraph()
    context, context_names = load_control_primitives_context()
    knowledge_files, primitive_paths = load_primitive_knowledge()

    for name in context_names:
        weight = {'depth': 0, 'successors': 0, 'failures': 0}
        knowledge = knowledge_files[name]
        requirements = {}
        file_path = primitive_paths[name]
        graph.add_node(name, name=name, weight=weight,
                       knowledge=knowledge, requirements=requirements,
                       file_path=file_path)

    save_graph(graph, "grass/graph_tools/primitive_graph.json")
