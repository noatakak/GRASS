import json
import networkx as nx
from networkx.readwrite import json_graph
from langchain.chat_models import ChatOpenAI
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
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
        graph.nodes[info["task"]]["filepath"] = file_name
        successor_list = graph.successors(info["task"])
        for x in successor_list:
            graph.nodes[x["node_name"]]["weight"]["successors"] = graph.nodes[x["node_name"]]["weight"]["successors"] + 1
        for basic in info["basic_list"]:
            graph.nodes[info["task"]]["predecessors"].append(basic)
            graph.nodes[basic]["successors"].append(info["task"])
            graph.add_edge(basic, info["task"])


    def fail_node(self, graph, info):
        # four was chosen here because it has to be larger than two because of the increase in successors and trials
        # every iteration,we chose 4 over three because of the rapid increase in trials means that fails should make
        # more of a landmark
        graph.nodes[info["task"]]["weight"]["failures"] = graph.nodes[info["task"]]["weight"]["failures"] + 4
        successor_list = graph.successors(info["task"])
        for x in successor_list:
            graph.nodes[x["node_name"]]["weight"]["failures"] = graph.nodes[x["node_name"]]["weight"]["failures"] + 4
            graph.nodes[x["node_name"]]["weight"]["successors"] = graph.nodes[x["node_name"]]["weight"]["failures"] + 1

    def create_primitive_graph(self):
        graph = nx.DiGraph()
        context, context_names = load_control_primitives_context()
        knowledge_files, primitive_paths = load_primitive_knowledge()

        for name in context_names:
            weight = {'depth': 0, 'successors': 0, 'failures': 0}
            knowledge = knowledge_files[name]
            predecessors = {}
            successors = {}
            file_path = primitive_paths[name]
            graph.add_node(name, name=name, weight=weight,
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=file_path)

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

    def loadText(self, textFile):
        # Loads text file
        with open('grass/' + textFile, 'r') as file:
            content = file.read()
        return content

    def get_new_node(self, graph, trials):
        revisit_node = False
        best_nodes = []

        for n in graph.nodes:
            if len(best_nodes) < 5 and graph.nodes[n]['weight']['depth'] != 0:
                best_nodes.append(n)
            else:
                for count, element in best_nodes:
                    if self.calc_weight(graph.nodes[n], trials) > self.calc_weight(graph.nodes[best_nodes[count]], trials) and graph.nodes[n]['weight']['depth'] != 0:
                        best_nodes[count] = n

        for count, element in enumerate(best_nodes):
            if graph.nodes[element]['file_path'] == "" and graph.nodes[element]['weight']['depth'] != 0:
                revisit_node = True
                new_node = graph.nodes[element]
            best_nodes[count] = str(graph.nodes[element])

        if not revisit_node:
            system_message = SystemMessage(content=self.loadText("prompts/genTask-System-Message.txt"))
            human_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/genTask-Human-Message.txt"))
            human_message = human_prompt.format(
                top_five=best_nodes,
            )
            assert isinstance(human_message, HumanMessage)
            GRAPH_message = [system_message, human_message]
            ai_message = self.llm(GRAPH_message)
            stringContent = ai_message.content
            jTextNode = json.loads(stringContent)
            name = jTextNode['name']
            knowledge = jTextNode['knowledge']
            successors = {}
            predecessors = jTextNode['predecessors']
            filepath = ""
            weight_depth = -1
            for p in predecessors:
                if graph.nodes[p]['weight']['depth'] > weight_depth:
                    weight_depth = graph.nodes[p]['weight']['depth']
            weight_depth = weight_depth + 1
            weight = {'depth': weight_depth, 'successors': 0, 'failures': 0}
            graph.add_node(name, node_name=name, weight=weight,
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=filepath)

            for p in predecessors:
                graph.nodes[p]['weight']['successors'] = graph.nodes[p]['weight']['successors'] + 1
                graph.add_edge(p, name)

            new_node = graph.nodes[name]

        return new_node