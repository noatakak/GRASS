import random
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
        for basic in info["basic_list"]:
            if graph.has_node(basic):
                graph.nodes[basic]["weight"]["successors"] = graph.nodes[basic]["weight"]["successors"] + 1
            if basic not in graph.nodes[info["task"]]["predecessors"]:
                graph.nodes[info["task"]]["predecessors"].append(basic)
                graph.add_edge(basic, info["task"])
            if info['task'] not in graph.nodes[basic]["successors"]:
                graph.nodes[basic]["successors"].append(info["program_name"])
        max_depth = -1
        for pred in graph.predecessors(info["task"]):
            if graph.nodes[pred]["weight"]["depth"] > max_depth:
                max_depth = graph.nodes[pred]["weight"]["depth"]
        max_depth = max_depth + 1
        file_name = self.add_graph_skill(graph, info, ckpt_dir)
        nx.relabel_nodes(graph, {info["task"]: info["program_name"]}, False)
        graph.nodes[info["program_name"]]["node_name"] = info["program_name"]
        graph.nodes[info["program_name"]]["weight"]["depth"] = max_depth
        graph.nodes[info["program_name"]]["file_path"] = file_name
        for pred in graph.predecessors(info["program_name"]):
            if info["task"] in graph.nodes[pred]["successors"]:
                graph.nodes[pred]["successors"].remove(info['task'])
            if info["program_name"] not in graph.nodes[pred]["successors"]:
                graph.nodes[pred]["successors"].append(info['program_name'])

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
        try:
            for basic in info["basic_list"]:
                if graph.has_node(basic):
                    graph.nodes[basic]["weight"]["successors"] = graph.nodes[basic]["weight"]["successors"] + 1
                if basic not in graph.nodes[info["task"]]["predecessors"]:
                    graph.nodes[info["task"]]["predecessors"].append(basic)
                    graph.add_edge(basic, info["task"])
                if info['task'] not in graph.nodes[basic]["successors"]:
                    graph.nodes[basic]["successors"].append(info["task"])
            graph.nodes[info["task"]]["weight"]["failures"] = graph.nodes[info["task"]]["weight"]["failures"] + 8
            for pred in graph.predecessors(info["task"]):
                if info["task"] not in graph.nodes[pred]["successors"]:
                    graph.nodes[pred]["successors"].append(info["task"])
                    graph.nodes[pred]["weight"]["successors"] = graph.nodes[pred]["weight"]["successors"] + 1
                graph.nodes[pred]["weight"]["failures"] = graph.nodes[pred]["weight"]["failures"] + 3
            max_depth = -1
            for pred in graph.predecessors(info["task"]):
                if graph.nodes[pred]["weight"]["depth"] > max_depth:
                    max_depth = graph.nodes[pred]["weight"]["depth"]
            max_depth = max_depth + 1
            graph.nodes[info["task"]]["weight"]["depth"] = max_depth
            with open(f"{ckpt_dir}/graph.json", 'w') as file:
                json.dump(json_graph.node_link_data(graph), file, indent=4)
        except:
            print("Caught an error in the fail node method, so this node has been destroyed.")
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
        appearances = weight_vals['appearances']
        weight = (successors + trials + depth) / (appearances + failures + 1)
        return weight

    def loadText(self, textFile):
        # Loads text file
        with open('grass/' + textFile, 'r') as file:
            content = file.read()
        return content

    def get_new_node(self, graph, trials, fail_nodes):
        revisit_node = False
        all_nodes = []
        best_nodes = []
        dont_use = list(set(fail_nodes.copy()))
        successful_count = 0
        new_node = ""
        for n in graph.nodes:
            if graph.nodes[n]['weight']['depth'] != 0:
                all_nodes.append(n)
                if graph.nodes[n]["file_path"] != "":
                    successful_count += 1
        if successful_count < 5:
            for b in all_nodes:
                if graph.nodes[b]["file_path"] != "":
                    best_nodes.append(b)
        else:
            best_nodes = sorted(all_nodes, key=lambda x: self.calc_weight(x, trials, graph), reverse=True)[:5]
        for count, element in enumerate(best_nodes):
            if graph.nodes[element]['file_path'] == "" and graph.nodes[element]['weight']['depth'] != 0:
                revisit_node = True
                if new_node == "":
                    new_node = graph.nodes[element]
                else:
                    if self.calc_weight(element, trials, graph) > self.calc_weight(new_node['node_name'], trials, graph):
                        new_node = graph.nodes[element]
                        graph.nodes[new_node['node_name']]['weight']['appearances'] -= 1
                graph.nodes[element]['weight']['appearances'] += 1

            best_nodes[count] = graph.nodes[element]

        if not revisit_node:
            # if iterations > 2:
            best_nodes_string = "["
            random.shuffle(best_nodes)
            for node in best_nodes:
                graph.nodes[node['node_name']]['weight']['appearances'] += 1
                best_nodes_string += "{\n\"name\": \""
                best_nodes_string += node['node_name'] + "\",\n\"description\": \""
                best_nodes_string += node['knowledge'] + "\",\n\"internal_skills\": ["
                for p in graph.predecessors(node['node_name']):
                    if graph.nodes[p]['weight']['depth'] > 0:
                        best_nodes_string += p + ","
                best_nodes_string += "]\n}"
                for suc in node['successors']:
                    if suc not in dont_use:
                        dont_use.append(suc)
            for node in best_nodes:
                if node['node_name'] in dont_use:
                    dont_use.remove(node['node_name'])
            best_nodes_string += "]"
            dont_use_string = "["
            for d in dont_use:
                dont_use_string += "{\n\"name\": \""
                dont_use_string += graph.nodes[d]['node_name'] + "\",\n}\n"
                # "
                # dont_use_string += "\n\"description\": \""
                # dont_use_string += graph.nodes[d]['knowledge'] + "\",\n
            dont_use_string += "]"
            system_message = SystemMessage(content=self.loadText("prompts/genTask-System-Message.txt"))
            human_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/genTask-Human-Message.txt"))
            human_message = human_prompt.format(
                top_five=best_nodes_string,
                failures=dont_use_string
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
            knowledge = jTextNode['description']
            successors = []
            predecessors = []
            filepath = ""
            weight_depth = -1
            for p in predecessors:
                if graph.nodes[p]['weight']['depth'] > weight_depth:
                    weight_depth = graph.nodes[p]['weight']['depth']
            weight_depth = weight_depth + 1
            if name in graph:
                print("\nGraph agent is duplicating node: " + name+ "\n")
                if graph.nodes[name]['file_path'] == "":
                    graph.nodes[name]['knowledge'] = knowledge
                new_pred = jTextNode['internal_skills']
                for p in new_pred:
                    if p not in graph.nodes[name]['predecessors']:
                        graph.nodes[name]['predecessors'].append(p)
                new_node = graph.nodes[name]
                graph.nodes[name]['weight']['appearances'] += 1
                return new_node
            weight = {'depth': weight_depth, 'successors': 0, 'failures': 0, "appearances": 0}
            graph.add_node(name, node_name=name, weight=weight, top_five=[x['node_name'] for x in best_nodes],
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=filepath)

            for p in predecessors:
                graph.nodes[p]["successors"].append(name)
                graph.nodes[p]['weight']['successors'] = graph.nodes[p]['weight']['successors'] + 1
                graph.add_edge(p, name)

            new_node = graph.nodes[name]
        else:
            regen_sm = SystemMessage(content=self.loadText("prompts/failReGen-SM.txt"))
            regen_hm_prompt = HumanMessagePromptTemplate.from_template(
                self.loadText("prompts/failReGen-HM.txt"))
            regen_hm = regen_hm_prompt.format(
                skill_name=new_node['node_name'],
                mand_skills=new_node['predecessors'],
            )
            assert isinstance(regen_hm, HumanMessage)
            regen_message = [regen_sm, regen_hm]
            print(
                f"\033[32m****Guide Regen human message****\n{regen_hm.content}\033[0m"
            )
            ai_regen_message = self.llm(regen_message)
            regen_string = ai_regen_message.content
            print(f"\033[34m****Guide Regen ai message****\n{regen_string}\033[0m")
            jText_regen = json.loads(regen_string)
            graph.nodes[new_node['node_name']]['knowledge'] = jText_regen['description']

        return new_node