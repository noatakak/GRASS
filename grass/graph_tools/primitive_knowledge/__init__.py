import pkg_resources
import os
import grass.utils as U


def load_primitive_knowledge(primitive_names=None):
    package_path = pkg_resources.resource_filename("grass", "")
    if primitive_names is None:
        primitive_names = [
            primitive[:-4]
            for primitive in os.listdir(f"{package_path}/graph_tools/primitive_knowledge")
            if primitive.endswith(".txt")
        ]
    paths = {}
    primitives = [
        U.load_text(f"{package_path}/graph_tools/primitive_knowledge/{primitive_name}.txt")
        for primitive_name in primitive_names
    ]
    for primitive_name in primitive_names:
        paths[primitive_name] = U.load_text(f"{package_path}/control_primitives/{primitive_name}.js")

    return primitives, paths
