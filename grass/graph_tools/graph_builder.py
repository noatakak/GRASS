import json
import networkx as nx
from networkx.readwrite import json_graph
from langchain.chat_models import ChatOpenAI
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from grass.control_primitives_context import load_control_primitives_context
from grass.graph_tools.primitive_knowledge import load_primitive_knowledge
import grass.utils as U

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

    def success_node(self, graph, info, ckpt_dir):
        #successor_list = graph.successors(info["task"])
        for basic in info["basic_list"]:
            if graph.has_node(basic):
                graph.nodes[basic]["weight"]["successors"] = graph.nodes[basic]["weight"]["successors"] + 1
            if basic not in graph.nodes[info["task"]]["predecessors"]:
                graph.nodes[info["task"]]["predecessors"].append(basic)
                graph.add_edge(basic, info["task"])
            graph.nodes[basic]["successors"].append(info["program_name"])
        max = -1
        for pred in graph.predecessors(info["task"]):
            if graph.nodes[pred]["weight"]["depth"] > max:
                max = graph.nodes[pred]["weight"]["depth"]
        max = max + 1
        file_name = self.add_graph_skill(graph, info, ckpt_dir)
        nx.relabel_nodes(graph, {info["task"]: info["program_name"]}, False)
        graph.nodes[info["program_name"]]["node_name"] = info["program_name"]
        graph.nodes[info["program_name"]]["weight"]["depth"] = max
        graph.nodes[info["program_name"]]["file_path"] = file_name
        # graph.add_node(info["program_name"], node_name=info["program_name"],
        #                weight=graph.nodes[info["task"]]["weight"],
        #                knowledge=graph.nodes[info["task"]]["knowledge"],
        #                predecessors=graph.nodes[info["task"]]["predecessors"],
        #                successors=graph.nodes[info["task"]]["successors"],
        #                file_path=graph.nodes[info["task"]]["file_path"])
        # graph.remove_node(info["task"])

    def add_graph_skill(self, graph,  info, ckpt_dir):
        program_name = info["program_name"]
        program_code = info["program_code"]
        U.dump_text(
            program_code, f"{ckpt_dir}/skill_code/{program_name}.js"
        )
        task_name = info['task']
        graph.nodes[task_name]['file_path'] = program_name
        with open(f"{ckpt_dir}/graph.json", 'w') as file:
            json.dump(json_graph.node_link_data(graph), file, indent=4)
        return f"{ckpt_dir}/skill_code/{program_name}.js"

    def fail_node(self, graph, info, ckpt_dir):
        # four was chosen here because it has to be larger than two because of the increase in successors and trials
        # every iteration,we chose 4 over three because of the rapid increase in trials means that fails should make
        # more of a landmark
        graph.nodes[info["task"]]["weight"]["failures"] = graph.nodes[info["task"]]["weight"]["failures"] + 4
        #successor_list = graph.successors(info["task"])
        # for x in successor_list:
        #     graph.nodes[x["node_name"]]["weight"]["failures"] = graph.nodes[x["node_name"]]["weight"]["failures"] + 4
        #     graph.nodes[x["node_name"]]["weight"]["successors"] = graph.nodes[x["node_name"]]["weight"]["failures"] + 1
        max = -1
        for pred in graph.predecessors(info["task"]):
            graph.nodes[pred]
            if info["task"] not in graph.nodes[pred]["successors"]:
                graph.nodes[pred]["successors"].append(info["task"])
                graph.nodes[pred]["weight"]["successors"] = graph.nodes[pred]["weight"]["successors"] + 1
            graph.nodes[pred]["weight"]["failures"] = graph.nodes[pred]["weight"]["failures"] + 3
        for pred in graph.predecessors(info["task"]):
            if graph.nodes[pred]["weight"]["depth"] > max:
                max = graph.nodes[pred]["weight"]["depth"]
        max = max + 1
        graph.nodes[info["task"]]["weight"]["depth"] = max
        with open(f"{ckpt_dir}/graph.json", 'w') as file:
            json.dump(json_graph.node_link_data(graph), file, indent=4)

    def create_primitive_graph(self):
        graph = nx.DiGraph()
        context, context_names = load_control_primitives_context()
        knowledge_files, primitive_paths = load_primitive_knowledge()

        for name in context_names:
            weight = {'depth': 0, 'successors': 0, 'failures': 0}
            knowledge = knowledge_files[name]
            predecessors = []
            successors = []
            file_path = primitive_paths[name]
            graph.add_node(name, name=name, weight=weight,
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=file_path)

        self.save_graph(graph, "grass/graph_tools/primitive_graph.json")

    def calc_weight(self, node, trials, graph):
        weight_vals = graph.nodes[node]['weight']
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

    def get_new_node(self, graph, trials, past_nodes, iterations):
        revisit_node = False
        best_nodes = []
        count = 0
        for n in graph.nodes:
            if graph.nodes[n]["file_path"] != "":
                count = count +1
                if count >= 13:
                    break
        for n in graph.nodes:
            if len(best_nodes) < 5 and graph.nodes[n]['weight']['depth'] != 0:
                if count < 13 and graph.nodes[n]["file_path"] != "":
                    best_nodes.append(n)
                elif count >= 13:
                    best_nodes.append(n)
            else:
                for count, element in enumerate(best_nodes):
                    if self.calc_weight(n, trials, graph) > self.calc_weight(best_nodes[count], trials, graph) and graph.nodes[n]['weight']['depth'] != 0:
                        best_nodes[4] = n
                        break
                sorted(best_nodes, key = lambda x: self.calc_weight(x, trials, graph))

        for count, element in enumerate(best_nodes):
            if graph.nodes[element]['file_path'] == "" and graph.nodes[element]['weight']['depth'] != 0:
                revisit_node = True
                new_node = graph.nodes[element]
            best_nodes[count] = graph.nodes[element]

        if not revisit_node:
            # if iterations > 2:
            input_string = ""
            for node in best_nodes:
                input_string += "{\n\"name\": \""
                input_string += node['node_name'] + "\",\n\"knowledge\": \""
                input_string += node['knowledge'] + "\",\n\"prerequisites\": "
                input_string += str(node['predecessors']) + "\n}"
                for suc in node['successors']:
                    if suc not in past_nodes:
                        past_nodes.append(suc)
            for node in best_nodes:
                if node['node_name'] in past_nodes:
                    past_nodes.remove(node['node_name'])
            system_message = SystemMessage(content=self.loadText("prompts/genTask-System-Message.txt"))
            human_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/genTask-Human-Message.txt"))
            human_message = human_prompt.format(
                top_five=input_string,
                failures=past_nodes
            )
            assert isinstance(human_message, HumanMessage)
            GRAPH_message = [system_message, human_message]
            print(
                f"\033[32m****Graph Agent human message****\n{human_message.content}\033[0m"
            )
            ai_message = self.llm(GRAPH_message)
            stringContent = ai_message.content
            print(f"\033[34m****Graph Agent ai message****\n{stringContent}\033[0m")
            jTextNode = json.loads(stringContent)
            name = jTextNode['name']
            knowledge = jTextNode['knowledge']
            successors = []
            predecessors = jTextNode['prerequisites']
            # elif iterations == 0:
            #     name = "gatherWood"
            #     knowledge = "Look for a tree of any type. When found, mine the logs of the tree and collect dropped items."
            #     successors = []
            #     predecessors = []
            # elif iterations == 1:
            #     name = "craftPlanks"
            #     knowledge = "Call gatherWood predecessor to acquire logs. Open inventory and craft planks without a crafting table for any type of log."
            #     successors = []
            #     predecessors = ["gatherWood"]
            # elif iterations == 2:
            #     name = "getCraftingTable"
            #     knowledge = "Call craftPlanks predecessor, to acquire planks. Open inventory and craft crafting_table item without crafting table using planks."
            #     successors = []
            #     predecessors = ["craftPlanks"]
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