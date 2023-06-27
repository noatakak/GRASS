import json
import pandas as pd
import networkx as nx
from networkx.readwrite import json_graph

from queue import PriorityQueue

from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

import openai
import pkg_resources

import fandom
from fandom.error import PageError


def loadText(textFile):
    # Loads text file
    with open('graphBuilder/' + textFile, 'r') as file:
        content = file.read()
    return content


def countPrev(graph, node):
    # Recursive score calculator
    score = 1
    prevs = graph.predecessors(node)
    for p in prevs:
        score += countPrev(graph, p)
    return score


def genScore(graph):
    # Calls recrusive method to generate scores for nodes
    print("Generating scores for nodes")
    iter = graph.__iter__()
    for node in iter:
        graph.nodes._nodes[node]["score"] = countPrev(graph, node)
    print("scores generated")


def listNodesByScore(graph):
    # Returns priority queue of nodes by their score
    print("creating skill queue organized by score")
    q = PriorityQueue()
    iter = graph.__iter__()
    for node in iter:
        q.put((graph.nodes._nodes[node]["score"], graph.nodes._nodes[node]))

    print("queue filled")
    return q


def saveStoredGraph(graphObject, fileName):
    # Save completed graph object to json
    print("saving graph to file: " + fileName)
    with open('graphBuilder/' + fileName, 'w') as file:
        json.dump(json_graph.node_link_data(graphObject), file, indent=4)


def cleanList(itemFile):
    # cleans up the copy and pasted list of items from GITM
    print("cleaning up names text file")
    read_file = pd.read_csv('graphBuilder/' + itemFile)
    df = []
    for i in range(65):
        listOfWordsNums = read_file.iloc[i][0].split()
        k = ""
        for x in listOfWordsNums:
            if (not isinstance(x, str)) or '.' in x:
                df.append(k)
                k = ""
            else:
                if k != "":
                    k += "_"
                k += x

    return df


def getGPTJSONnode(name, desc, llm, system_message, human_prompt):
    print("generating json node for item: " + name + ", and description: " + desc)
    human_message = human_prompt.format(
        target=name,
        knowledge=desc
    )
    assert isinstance(human_message, HumanMessage)
    GRAPH_message = [system_message, human_message]
    ai_message = llm(GRAPH_message)
    stringContent = ai_message.content
    return stringContent

def getGPTItemDesc(name, llm, system_message, human_prompt):
    # Generates item description from gpt
    human_message = human_prompt.format(
        item=name
    )
    assert isinstance(human_message, HumanMessage)
    DESCRIPTION_message = [system_message, human_message]
    ai_description = llm(DESCRIPTION_message)
    desc = ai_description.content
    return desc

def generateNode(stringContent, graph):
    jTextNode = json.loads(stringContent)
    print("graph node:"
          "\n" + stringContent)

    obj = jTextNode['object']
    minimum_count = jTextNode['minimum_count']
    material = jTextNode['material']
    tool = jTextNode['tool']
    modifier = jTextNode['modifier']
    info = jTextNode['info']

    # Add node to the graph
    graph.add_node(obj, object_name=obj, minimum_count=minimum_count, minimum_materials=material,
                   required_tool=tool, required_modifier=modifier, info=info, score=-1)

    # Add edges for the material dependencies
    if not isinstance(material, str):
        for item, quantity in material.items():
            graph.add_edge(item, obj, quantity=quantity)

    # Add edge for the tool dependency
    if tool != '':
        graph.add_edge(tool, obj)

    # Add edge for the modifier dependency
    if modifier != '':
        graph.add_edge(modifier, obj)

    return obj



def graphFromNames(itemFile, graphFile):
    # Initialize llm, wiki, names list, graph list, and graph
    print("Starting graph generation")
    llm = ChatOpenAI(
        model_name="gpt-4",
        request_timeout=60
    )
    fandom.set_wiki("minecraft")
    graph = nx.DiGraph()
    names = cleanList(itemFile)

    # Initialize system_message and human_prompt for GRAPH and DESCRIPTION
    GRAPH_system_message = SystemMessage(content=loadText("nodeGenSYSTEM-MESSAGE.txt"))
    GRAPH_human_prompt = HumanMessagePromptTemplate.from_template(loadText("nodeGenUSER-MESSAGE.txt"))
    DESCRIPTION_system_message = SystemMessage(content=loadText("descGenSYSTEM-MESSAGE.txt"))
    DESCRIPTION_human_prompt = HumanMessagePromptTemplate.from_template(loadText("descGenUSER-MESSAGE.txt"))

    # Iterating through names list
    done = 0
    for name in names:
        total = len(names)
        # Try pulling description from wiki, if failure then generate description with gpt
        try:
            page = fandom.page(title=name)
            desc = page.summary
        except PageError as e:
            print("Bad name found, generating description")
            desc = getGPTItemDesc(name, llm, DESCRIPTION_system_message, DESCRIPTION_human_prompt)

        # Generate gpt call to get node in json format
        stringContent = getGPTJSONnode(name, desc, llm, GRAPH_system_message, GRAPH_human_prompt)

        # Check if node is actually JSON format, if not then add it's name to the end of the names list to try again later
        try:
            item_name = generateNode(stringContent, graph)

            # Check if predecessors are in item list, if not then add to list
            pred = graph.predecessors(item_name)
            for p in pred:
                if p not in names:
                    names.append(p)

        except ValueError as e:
            names.append(name)
            print("item: " + name + " was not in json format, adding to the end of the list to try again")
        done += 1
        print("viewed names: " + str(done) + "/" + str(total))

    # Fill out score fields in graph, and save graph to json file
    print("graph fully generated")
    genScore(graph)
    saveStoredGraph(graph, graphFile)


def main():
    items = "items.txt"
    graphJSON = "graph.json"
    graphFromNames(items, graphJSON)
    print("finished")


def queueWithoutJS(graph):
    # Returns priority queue of nodes by their score
    print("creating skill queue organized by score")
    q = PriorityQueue()
    iter = graph.__iter__()
    for node in iter:
        try:
            graph.nodes[node]["script_path"]
        except KeyError as e:
            q.put((graph.nodes._nodes[node]["score"], graph.nodes._nodes[node]['object_name']))

    print("queue filled")
    return q


def returnGraphAndQueue(filePath):
    with open(filePath) as f:
        js_graph = json.load(f)
    graph = json_graph.node_link_graph(js_graph)
    queue = queueWithoutJS(graph)
    return graph, queue


if __name__ == "__main__":
    main()
