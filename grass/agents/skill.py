import json
import os
import networkx as nx
from networkx.readwrite import json_graph

import grass.utils as U
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import Chroma

from grass.prompts import load_prompt
from grass.control_primitives import load_control_primitives


class SkillManager:
    def __init__(
        self,
        ckpt_dir="ckpt",
        resume=False,
    ):
        U.f_mkdir(f"{ckpt_dir}/skill_code")
        # programs for env execution
        self.control_primitives = load_control_primitives()
        if resume:
            print(f"\033[33mLoading Skill Manager from {ckpt_dir}/skill\033[0m")
            self.coded_skills = U.load_json(f"{ckpt_dir}/skill/skills.json")
        else:
            self.coded_skills = {}
        self.ckpt_dir = ckpt_dir


    @property
    def programs(self):
        programs = ""
        for skill_name, entry in self.coded_skills.items():
            programs += f"{entry['code']}\n\n"
        for primitives in self.control_primitives[0]:
            programs += f"{primitives}\n\n"
        return programs

    def add_to_skills(self, info, graph):
        program_name = info["program_name"]
        program_code = info["program_code"]
        self.coded_skills[program_name] = {
            "code": program_code,
            "description": graph.nodes[info["program_name"]]["knowledge"],
        }
