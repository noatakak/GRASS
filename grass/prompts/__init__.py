import pkg_resources
import grass.utils as U


def load_prompt(prompt):
    package_path = pkg_resources.resource_filename("grass", "")
    return U.load_text(f"{package_path}/prompts/{prompt}.txt")
