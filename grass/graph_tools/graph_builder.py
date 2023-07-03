import json
import networkx as nx
from networkx.readwrite import json_graph
from langchain.chat_models import ChatOpenAI
from langchain.prompts import SystemMessagePromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from grass.control_primitives_context import load_control_primitives_context
from grass.graph_tools.primitive_knowledge import load_primitive_knowledge
from grass.agents.skill import  SkillManager


class GraphBuilder:
    def __init__(self,
                 model_name="gpt-3.5-turbo",
                 temperature=0,
                 request_timout=120,
                 ):
        self.model_name = model_name
        self.temperature = temperature
        self.request_timeout = request_timout
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timout,
        )

    def load_graph_json(self, filepath):
        with open(filepath) as f:
            js_graph = json.load(f)
        graph = json_graph.node_link_graph(js_graph)
        return graph

    def get_primitive_graph(self):
        return self.load_graph_json("grass/graph_tools/primitive_graph.json")

    def save_graph(self, graph, filepath):
        print("saving graph to file: " + filepath)
        with open(filepath, 'w') as file:
            json.dump(json_graph.node_link_data(graph), file, indent=4)

    def success_node(self, graph, info):
        file_name = SkillManager.add_graph_skill(graph, info)
        graph[info["node_name"]]["filepath"] = file_name
        successor_list = graph.successors(graph[info["node_name"]])
        for x in successor_list:
            graph[info[x]]["weight"]["successors"] = graph[info[x]]["weight"]["successors"] + 1

    def fail_node(self, graph, info):
        # four was chosen here because it has to be larger than two because of the increase in successors and trials
        # every iteration,we chose 4 over three because of the rapid increase in trials means that fails should make
        # more of a landmark
        graph[info["node_name"]]["weight"]["failures"] = graph[info["node_name"]]["weight"]["failures"] + 4
        successor_list = graph.successors(graph[info["node_name"]])
        for x in successor_list:
            graph[info[x]]["weight"]["failures"] = graph[info[x]]["weight"]["failures"] + 4
            graph[info[x]]["weight"]["successors"] = graph[info[x]]["weight"]["failures"] + 1

    def create_primitive_graph(self):
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

        self.save_graph(graph, "grass/graph_tools/primitive_graph.json")

    def calc_weight(self, node, trials):
        weight_vals = node['weight']
        depth = weight_vals['depth']
        if depth == 0:
            return 0
        successors = weight_vals['successors']
        failures = weight_vals['failures']
        weight = (successors + trials) / (depth + failures)
        return weight

    def get_new_node(self):
        # Get top 5 skills

        # Get new node from GPT

        # Add node to graph

        # Update successor count of predecessors to new node

        # return new_node