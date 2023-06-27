from grass import grass

# You can also use mc_port instead of azure_login, but azure_login is highly recommended
azure_login = {
    "client_id": "513c64b8-702a-42e6-9d46-21316dcaa1cf",
    "redirect_url": "https://127.0.0.1/auth-response",
    "secret_value": "rIE8Q~PQLsdM0EA_Fb8Aw.w_GFUKMHQ-CC8JBcfN",
    "version": "fabric-loader-0.14.21-1.19.4", # the version Voyager is tested on
}
openai_api_key = ""

grass = grass(
    mc_port=58124,
    openai_api_key=openai_api_key,
    #resume = True,
    #ckpt_dir="C:/Users/noata/MinecraftVoyager/ckpt",
    #skill_library_dir="./skill_library/trial2",
)

# start lifelong learning
grass.learn()
#voyager.inference(task="craft a diamond sword")
