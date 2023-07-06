import copy
import os
import time
from typing import Dict

import grass.utils as U
from .env import GrassEnv

from .agents import ActionAgent
from .agents import CriticAgent
from .agents import CurriculumAgent
from .agents import SkillManager
from .graph_tools.graph_builder import GraphBuilder
from datetime import datetime
import traceback


# TODO: remove event memory
class Grass:
    def __init__(
            self,
            mc_port: int = None,
            azure_login: Dict[str, str] = None,
            server_port: int = 3000,
            openai_api_key: str = None,
            env_wait_ticks: int = 20,
            env_request_timeout: int = 600,
            max_iterations: int = 160,
            reset_placed_if_failed: bool = False,
            action_agent_model_name: str = "gpt-4",
            action_agent_temperature: int = 0,
            action_agent_task_max_retries: int = 4,
            action_agent_show_chat_log: bool = True,
            action_agent_show_execution_error: bool = True,
            curriculum_agent_model_name: str = "gpt-4",
            curriculum_agent_temperature: int = 0,
            curriculum_agent_qa_model_name: str = "gpt-3.5-turbo",
            curriculum_agent_qa_temperature: int = 0,
            curriculum_agent_warm_up: Dict[str, int] = None,
            curriculum_agent_core_inventory_items: str = r".*_log|.*_planks|stick|crafting_table|furnace"
                                                         r"|cobblestone|dirt|coal|.*_pickaxe|.*_sword|.*_axe",
            curriculum_agent_mode: str = "auto",
            critic_agent_model_name: str = "gpt-4",
            critic_agent_temperature: int = 0,
            critic_agent_mode: str = "auto",
            skill_manager_model_name: str = "gpt-3.5-turbo",
            skill_manager_temperature: int = 0,
            skill_manager_retrieval_top_k: int = 5,
            openai_api_request_timeout: int = 240,
            ckpt_dir: str = datetime.now().strftime("Tests/Date_%m-%d_Time_%H-%M"),
            skill_library_dir: str = None,
            resume: bool = False,
            graph_agent_model_name: str = "gpt-3.5-turbo",
            graph_agent_temperature: int= 0,
            graph_agent_request_timeout: int = 120
    ):
        """
        The main class for Grass.
        Action agent is the iterative prompting mechanism in paper.
        Curriculum agent is the automatic curriculum in paper.
        Critic agent is the self-verification in paper.
        Skill manager is the skill library in paper.
        :param mc_port: minecraft in-game port
        :param azure_login: minecraft login config
        :param server_port: mineflayer port
        :param openai_api_key: openai api key
        :param env_wait_ticks: how many ticks at the end each step will wait, if you found some chat log missing,
        you should increase this value
        :param env_request_timeout: how many seconds to wait for each step, if the code execution exceeds this time,
        python side will terminate the connection and need to be resumed
        :param reset_placed_if_failed: whether to reset placed blocks if failed, useful for building task
        :param action_agent_model_name: action agent model name
        :param action_agent_temperature: action agent temperature
        :param action_agent_task_max_retries: how many times to retry if failed
        :param curriculum_agent_model_name: curriculum agent model name
        :param curriculum_agent_temperature: curriculum agent temperature
        :param curriculum_agent_qa_model_name: curriculum agent qa model name
        :param curriculum_agent_qa_temperature: curriculum agent qa temperature
        :param curriculum_agent_warm_up: info will show in curriculum human message
        if completed task larger than the value in dict, available keys are:
        {
            "context": int,
            "biome": int,
            "time": int,
            "other_blocks": int,
            "nearby_entities": int,
            "health": int,
            "hunger": int,
            "position": int,
            "equipment": int,
            "chests": int,
            "optional_inventory_items": int,
        }
        :param curriculum_agent_core_inventory_items: only show these items in inventory before optional_inventory_items
        reached in warm up
        :param curriculum_agent_mode: "auto" for automatic curriculum, "manual" for human curriculum
        :param critic_agent_model_name: critic agent model name
        :param critic_agent_temperature: critic agent temperature
        :param critic_agent_mode: "auto" for automatic critic ,"manual" for human critic
        :param skill_manager_model_name: skill manager model name
        :param skill_manager_temperature: skill manager temperature
        :param skill_manager_retrieval_top_k: how many skills to retrieve for each task
        :param openai_api_request_timeout: how many seconds to wait for openai api
        :param ckpt_dir: checkpoint dir
        :param skill_library_dir: skill library dir
        :param resume: whether to resume from checkpoint
        """
        # init env
        self.env = GrassEnv(
            mc_port=mc_port,
            azure_login=azure_login,
            server_port=server_port,
            request_timeout=env_request_timeout,
        )
        self.env_wait_ticks = env_wait_ticks
        self.reset_placed_if_failed = reset_placed_if_failed
        self.max_iterations = max_iterations

        # set openai api key
        os.environ["OPENAI_API_KEY"] = openai_api_key

        # init agents
        self.action_agent = ActionAgent(
            model_name=action_agent_model_name,
            temperature=action_agent_temperature,
            request_timout=openai_api_request_timeout,
            ckpt_dir=ckpt_dir,
            resume=resume,
            chat_log=action_agent_show_chat_log,
            execution_error=action_agent_show_execution_error,
        )
        self.action_agent_task_max_retries = action_agent_task_max_retries
        self.curriculum_agent = CurriculumAgent(
            model_name=curriculum_agent_model_name,
            temperature=curriculum_agent_temperature,
            qa_model_name=curriculum_agent_qa_model_name,
            qa_temperature=curriculum_agent_qa_temperature,
            request_timout=openai_api_request_timeout,
            ckpt_dir=ckpt_dir,
            resume=resume,
            mode=curriculum_agent_mode,
            warm_up=curriculum_agent_warm_up,
            core_inventory_items=curriculum_agent_core_inventory_items,
        )
        self.critic_agent = CriticAgent(
            model_name=critic_agent_model_name,
            temperature=critic_agent_temperature,
            request_timout=openai_api_request_timeout,
            mode=critic_agent_mode,
        )
        self.skill_manager = SkillManager(
            model_name=skill_manager_model_name,
            temperature=skill_manager_temperature,
            retrieval_top_k=skill_manager_retrieval_top_k,
            request_timout=openai_api_request_timeout,
            ckpt_dir=skill_library_dir if skill_library_dir else ckpt_dir,
            resume=True if resume or skill_library_dir else False,
        )
        self.recorder = U.EventRecorder(ckpt_dir=ckpt_dir, resume=resume)
        self.resume = resume

        # init variables for rollout
        self.trial_count = 0
        self.action_agent_rollout_num_iter = -1
        self.task = None
        self.context = ""
        self.messages = None
        self.conversations = []
        self.last_events = None

        # init graph_agent and graph
        self.graph_agent = GraphBuilder(
            model_name=graph_agent_model_name,
            temperature=graph_agent_temperature,
            request_timout=graph_agent_request_timeout
        )
        self.graph = self.graph_agent.load_graph_json(
            (ckpt_dir + "/graph.json") if resume else "grass/graph_tools/primitive_graph.json")

    def reset(self, new_node, reset_env=True):
        self.action_agent_rollout_num_iter = 0
        # self.task = task
        # self.context = context
        if reset_env:
            self.env.reset(
                options={
                    "mode": "soft",
                    "wait_ticks": self.env_wait_ticks,
                }
            )
        difficulty = (
            "easy" if len(self.curriculum_agent.completed_tasks) > 15 else "peaceful"
        )
        # step to peek an observation
        events = self.env.step(
            "bot.chat(`/time set ${getNextTime()}`);\n"
            + f"bot.chat('/difficulty {difficulty}');"
        )
        # skills = []
        # preds = self.graph.predecessors(item_name)
        # for p in preds:
        #     prev_node = self.graph.nodes[p]
        #     with open(self.ckpt_dir + '/skill_code/' + prev_node['script_path'], 'r') as file:
        #         contents = file.read()
        #         skills.append(contents)
        # skills = self.skill_manager.retrieve_skills(query=self.context)
        # print(
        #     f"\033[33mRender Action Agent system message with {len(skills)} control_primitives\033[0m"
        # )
        system_message = self.action_agent.render_system_message(self.graph, new_node)
        human_message = self.action_agent.render_human_message(
            events=events, code="", task=self.task, critique=""#, context=context
        )
        self.messages = [system_message, human_message]
        print(
            f"\033[32m****Action Agent human message****\n{human_message.content}\033[0m"
        )
        assert len(self.messages) == 2
        self.conversations = []
        return self.messages

    def close(self):
        self.env.close()

    def step(self):
        if self.action_agent_rollout_num_iter < 0:
            raise ValueError("Agent must be reset before stepping")
        ai_message = self.action_agent.llm(self.messages)
        print(f"\033[34m****Action Agent ai message****\n{ai_message.content}\033[0m")
        self.conversations.append(
            (self.messages[0].content, self.messages[1].content, ai_message.content)
        )
        parsed_result = self.action_agent.process_new_ai_message(message=ai_message)
        success = False
        if isinstance(parsed_result, dict):
            code = parsed_result["program_code"] + "\n" + parsed_result["exec_code"]
            events = self.env.step(
                code,
                programs=self.skill_manager.programs,
            )
            self.recorder.record(events, self.task)
            self.action_agent.update_chest_memory(events[-1][1]["nearbyChests"])
            success, critique = self.critic_agent.check_task_success(
                events=events,
                task=self.task,
                context=self.context,
                chest_observation=self.action_agent.render_chest_observation(),
                max_retries=5,
            )

            if self.reset_placed_if_failed and not success:
                # revert all the placing event in the last step
                blocks = []
                positions = []
                for event_type, event in events:
                    if event_type == "onSave" and event["onSave"].endswith("_placed"):
                        block = event["onSave"].split("_placed")[0]
                        position = event["status"]["position"]
                        blocks.append(block)
                        positions.append(position)
                new_events = self.env.step(
                    f"await givePlacedItemBack(bot, {U.json_dumps(blocks)}, {U.json_dumps(positions)})",
                    programs=self.skill_manager.programs,
                )
                events[-1][1]["inventory"] = new_events[-1][1]["inventory"]
                events[-1][1]["voxels"] = new_events[-1][1]["voxels"]
            # new_skills = self.skill_manager.retrieve_skills(
            #     query=self.context
            #           + "\n\n"
            #           + self.action_agent.summarize_chatlog(events)
            # )
            # skills = []
            # preds = self.graph.predecessors(self.task)
            # for p in preds:
            #     prev_node = self.graph.nodes[p]
            #     with open(self.ckpt_dir + '/skill_code/' + prev_node['script_path'], 'r') as file:
            #         contents = file.read()
            #         skills.append(contents)
            system_message = self.action_agent.render_system_message(self.graph, self.new_node)
            human_message = self.action_agent.render_human_message(
                events=events, code="", task=self.task, critique=""
            )
            self.last_events = copy.deepcopy(events)
            self.messages = [system_message, human_message]
        else:
            assert isinstance(parsed_result, str)
            self.recorder.record([], self.task)
            print(f"\033[34m{parsed_result} Trying again!\033[0m")
        assert len(self.messages) == 2
        self.action_agent_rollout_num_iter += 1
        done = (
                self.action_agent_rollout_num_iter >= self.action_agent_task_max_retries
                or success
        )
        info = {
            "task": self.task,
            "success": success,
            "conversations": self.conversations,
            "basic_list": parsed_result["basic_list"]
        }
        if success:
            assert (
                    "program_code" in parsed_result and "program_name" in parsed_result
            ), "program and program_name must be returned when success"
            info["program_code"] = parsed_result["program_code"]
            info["program_name"] = parsed_result["program_name"]
        else:
            print(
                f"\033[32m****Action Agent human message****\n{self.messages[-1].content}\033[0m"
            )
        return self.messages, 0, done, info

    def rollout(self, *, new_node, reset_env=True):
        self.reset(new_node=new_node, reset_env=reset_env)
        self.trial_count = self.trial_count + 1
        while True:
            messages, reward, done, info = self.step()
            if done:
                break
        return messages, reward, done, info

    def learn(self, reset_env=True):
        if self.resume:
            # keep the inventory
            self.env.reset(
                options={
                    "mode": "soft",
                    "wait_ticks": self.env_wait_ticks,
                }
            )
        else:
            # clear the inventory
            self.env.reset(
                options={
                    "mode": "hard",
                    "wait_ticks": self.env_wait_ticks,
                }
            )
            self.resume = True
        self.last_events = self.env.step("")


        while True:
            # if len(sub_q) == 0:
            #     print("sub queue is empty")
            #     break
            # parent_task = sub_q.pop()
            # task = parent_task[1]
            # context = self.graph.nodes[task]['info']
            # node_name = task
            # self.item_name = node_name
            # task = "Obtain " + str(self.graph.nodes[task]["minimum_count"]) + " "+ task
            # task, context = self.curriculum_agent.propose_next_task(
            #     events=self.last_events,
            #     chest_observation=self.action_agent.render_chest_observation(),
            #     max_retries=5,
            # )
            if self.recorder.iteration > self.max_iterations:
                print("Iteration limit reached")
                break

            self.new_node = self.graph_agent.get_new_node(graph=self.graph, trials=self.trial_count)
            new_node = self.new_node
            self.task = new_node['node_name']
            task = self.task
            print(
                f"\033[35mStarting task {task} for at most {self.action_agent_task_max_retries} times\033[0m"
            )
            try:
                messages, reward, done, info = self.rollout(
                    new_node=new_node,
                    reset_env=reset_env,
                )
            except Exception as e:
                time.sleep(3)  # wait for mineflayer to exit
                info = {
                    "task": task,
                    "success": False,
                }
                # reset bot status here
                self.last_events = self.env.reset(
                    options={
                        "mode": "hard",
                        "wait_ticks": self.env_wait_ticks,
                        "inventory": self.last_events[-1][1]["inventory"],
                        "equipment": self.last_events[-1][1]["status"]["equipment"],
                        "position": self.last_events[-1][1]["status"]["position"],
                    }
                )
                # use red color background to print the error
                traceback.print_exc()
                print("Your last round rollout terminated due to error:")
                print(f"\033[41m{e}\033[0m")

            if info["success"]:
                self.graph_agent.success_node(self.graph, info)
            else:
                self.graph_agent.fail_node(self.graph, info)

            self.curriculum_agent.update_exploration_progress(info)
            print(
                f"\033[35mCompleted tasks: {', '.join(self.curriculum_agent.completed_tasks)}\033[0m"
            )
            print(
                f"\033[35mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m"
            )

        return {
            "completed_tasks": self.curriculum_agent.completed_tasks,
            "failed_tasks": self.curriculum_agent.failed_tasks,
            "skills": self.skill_manager.skills,
        }

    def decompose_task(self, task):
        if not self.last_events:
            self.last_events = self.env.reset(
                options={
                    "mode": "hard",
                    "wait_ticks": self.env_wait_ticks,
                }
            )
        return self.curriculum_agent.decompose_task(task, self.last_events)

    def inference(self, task=None, sub_goals=[], reset_mode="hard", reset_env=True):
        if not task and not sub_goals:
            raise ValueError("Either task or sub_goals must be provided")
        if not sub_goals:
            sub_goals = self.decompose_task(task)
        self.env.reset(
            options={
                "mode": reset_mode,
                "wait_ticks": self.env_wait_ticks,
            }
        )
        self.curriculum_agent.completed_tasks = []
        self.curriculum_agent.failed_tasks = []
        self.last_events = self.env.step("")
        while self.curriculum_agent.progress < len(sub_goals):
            next_task = sub_goals[self.curriculum_agent.progress]
            context = self.curriculum_agent.get_task_context(next_task)
            print(
                f"\033[35mStarting task {next_task} for at most {self.action_agent_task_max_retries} times\033[0m"
            )
            messages, reward, done, info = self.rollout(
                task=next_task,
                context=context,
                reset_env=reset_env,
            )
            self.curriculum_agent.update_exploration_progress(info)
            print(
                f"\033[35mCompleted tasks: {', '.join(self.curriculum_agent.completed_tasks)}\033[0m"
            )
            print(
                f"\033[35mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m"
            )
