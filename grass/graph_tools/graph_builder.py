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
        #successor_list = graph.successors(info["task"])
        for basic in info["basic_list"]:
            if graph.has_node(basic):
                graph.nodes[basic]["weight"]["successors"] = graph.nodes[basic]["weight"]["successors"] + 1
            if basic not in graph.nodes[info["task"]]["predecessors"]:
                graph.nodes[info["task"]]["predecessors"].append(basic)
                graph.add_edge(basic, info["task"])
            if info['task'] not in graph.nodes[basic]["successors"]:
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
        for pred in graph.predecessors(info["program_name"]):
            if info["task"] in graph.nodes[pred]["successors"]:
                graph.nodes[pred]["successors"].remove(info['task'])
            if info["program_name"] not in graph.nodes[pred]["successors"]:
                graph.nodes[pred]["successors"].append(info['program_name'])
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
        appearances = weight_vals['appearances']
        weight = (successors + trials + depth) / (appearances + failures + 1)
        return weight

    def loadText(self, textFile):
        # Loads text file
        with open('grass/' + textFile, 'r') as file:
            content = file.read()
        return content

    def get_new_node(self, graph, trials, fail_nodes, iterations):
        revisit_node = False
        best_nodes = []
        dont_use = fail_nodes.copy()
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
            random.shuffle(best_nodes)
            for node in best_nodes:
                graph.nodes[node['node_name']]['weight']['appearances'] += 1
                input_string += "{\n\"name\": \""
                input_string += node['node_name'] + "\",\n\"knowledge\": \""
                input_string += node['knowledge'] + "\",\n}"
                #   input_string += "\"prerequisites\":" +str(node['predecessors']) + "\n}"
                for suc in node['successors']:
                    if suc not in dont_use:
                        dont_use.append(suc)
                # for pred in node['predecessors']:
                #     if pred not in dont_use and pred not in [x['node_name'] for x in best_nodes]:
                #         dont_use.append(pred)
            for node in best_nodes:
                if node['node_name'] in dont_use:
                    dont_use.remove(node['node_name'])
            system_message = SystemMessage(content=self.loadText("prompts/genTask-System-Message.txt"))
            human_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/genTask-Human-Message.txt"))
            human_message = human_prompt.format(
                top_five=input_string,
                failures=dont_use
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
            weight = {'depth': weight_depth, 'successors': 0, 'failures': 0, "appearances": 0}
            graph.add_node(name, node_name=name, weight=weight,
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=filepath)

            for p in predecessors:
                graph.nodes[p]["successors"].append(name)
                graph.nodes[p]['weight']['successors'] = graph.nodes[p]['weight']['successors'] + 1
                graph.add_edge(p, name)

            new_node = graph.nodes[name]

        return new_node

    def get_new_node_in_three(self, graph, trials, fail_nodes):
        revisit_node = False
        best_nodes = []
        dont_use = fail_nodes.copy()
        count = 0
        for n in graph.nodes:
            if graph.nodes[n]["file_path"] != "":
                count = count + 1
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
                    if self.calc_weight(n, trials, graph) > self.calc_weight(best_nodes[count], trials, graph) and \
                            graph.nodes[n]['weight']['depth'] != 0:
                        best_nodes[4] = n
                        break
                sorted(best_nodes, key=lambda x: self.calc_weight(x, trials, graph))

        for count, element in enumerate(best_nodes):
            if graph.nodes[element]['file_path'] == "" and graph.nodes[element]['weight']['depth'] != 0:
                revisit_node = True
                new_node = graph.nodes[element]
            best_nodes[count] = graph.nodes[element]

        if not revisit_node:
            best_nodes_string = ""
            random.shuffle(best_nodes)
            for node in best_nodes:
                graph.nodes[node['node_name']]['weight']['appearances'] += 1
                best_nodes_string += "{\n\"name\": \""
                best_nodes_string += node['node_name'] + "\",\n\"knowledge\": \""
                best_nodes_string += node['knowledge'] + "\",\n}"

            jText_skillList = {}
            if best_nodes_string != "":
                skill_sm = SystemMessage(content=self.loadText("prompts/newTaskGeneration/skill-selection-SM.txt"))
                skill_hm_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/newTaskGeneration/skill-selection-HM.txt"))
                skill_hm = skill_hm_prompt.format(
                    top_five=best_nodes_string
                )
                assert isinstance(skill_hm, HumanMessage)
                skill_message = [skill_sm, skill_hm]
                print(
                    f"\033[32m****Skill Selection human message****\n{skill_hm.content}\033[0m"
                )
                ai_skill_message = self.llm(skill_message)
                skill_string = ai_skill_message.content
                print(f"\033[34m****Skill Selection ai message****\n{skill_string}\033[0m")
                jText_skillList = json.loads(skill_string)

            mand_skills = "[\n"
            #TODO jtext is string and needs to be list, same for other jtext instances
            if not bool(jText_skillList):
                selected_list = []
            else:
                selected_list = jText_skillList['skill_list']
            for s in selected_list:
                mand_skills += "{\n\"name\": \""
                mand_skills += s + "\",\n\"guide\": \""
                mand_skills += graph.nodes[s]['knowledge'] + "\",\n}"
            mand_skills += "\n]"
            prev_desc = "[\n"
            for s in selected_list:
                prev_desc += graph.nodes[s]['knowledge'] + ",\n"
            for f in fail_nodes:
                prev_desc += graph.nodes[f]['knowledge'] + ",\n"
            prev_desc += "\n]"
            guide_sm = SystemMessage(content=self.loadText("prompts/newTaskGeneration/knowledge-SM.txt"))
            guide_hm_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/newTaskGeneration/knowledge-HM.txt"))
            guide_hm = guide_hm_prompt.format(
                mand_skills=mand_skills,
                prev_descriptions=prev_desc
            )
            assert isinstance(guide_hm, HumanMessage)
            guide_message = [guide_sm, guide_hm]
            print(
                f"\033[32m****Guide Creation human message****\n{guide_hm.content}\033[0m"
            )
            ai_guide__message = self.llm(guide_message)
            guide_string = ai_guide__message.content
            print(f"\033[34m****Guide Creation ai message****\n{guide_string}\033[0m")
            jText_guide = json.loads(guide_string)

            title_sm = SystemMessage(content=self.loadText("prompts/newTaskGeneration/skill-title-SM.txt"))
            title_hm_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/newTaskGeneration/skill-title-HM.txt"))
            title_hm = title_hm_prompt.format(
                guide=jText_guide
            )
            assert isinstance(title_hm, HumanMessage)
            name_message = [title_sm, title_hm]
            print(
                f"\033[32m****Skill Naming human message****\n{title_hm.content}\033[0m"
            )
            ai_name_message = self.llm(name_message)
            name_string = ai_name_message.content
            print(f"\033[34m****Skill Naming ai message****\n{name_string}\033[0m")
            jText_name = json.loads(name_string)

            name = jText_name['name']
            knowledge = jText_guide['guide']
            successors = []
            predecessors = selected_list
            filepath = ""
            weight_depth = -1
            for p in predecessors:
                if graph.nodes[p]['weight']['depth'] > weight_depth:
                    weight_depth = graph.nodes[p]['weight']['depth']
            weight_depth = weight_depth + 1
            weight = {'depth': weight_depth, 'successors': 0, 'failures': 0, "appearances": 0}
            graph.add_node(name, node_name=name, weight=weight,
                           knowledge=knowledge, predecessors=predecessors,
                           successors=successors, file_path=filepath)

            for p in predecessors:
                graph.nodes[p]["successors"].append(name)
                graph.nodes[p]['weight']['successors'] = graph.nodes[p]['weight']['successors'] + 1
                graph.add_edge(p, name)

            new_node = graph.nodes[name]
        else:
            regen_sm = SystemMessage(content=self.loadText("prompts/newTaskGeneration/failReGen-SM.txt"))
            regen_hm_prompt = HumanMessagePromptTemplate.from_template(self.loadText("prompts/newTaskGeneration/failReGen-HM.txt"))
            regen_hm = regen_hm_prompt.format(
                skill_name=new_node['node_name'],
                mand_skills=new_node['prerequisites'],
            )
            assert isinstance(regen_hm, HumanMessage)
            regen_message = [regen_sm, regen_hm]
            print(
                f"\033[32m****Guide Regen human message****\n{regen_message.content}\033[0m"
            )
            ai_regen_message = self.llm(regen_message)
            regen_string = ai_regen_message.content
            print(f"\033[34m****Guide Regen ai message****\n{regen_string}\033[0m")
            jText_regen = json.loads(regen_string)
            graph.nodes[new_node['node_name']]['knowledge'] = jText_regen['guide']


        return new_node
