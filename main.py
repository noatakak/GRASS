from grass import Grass

# You can also use mc_port instead of azure_login, but azure_login is highly recommended
azure_login = {
    "client_id": "513c64b8-702a-42e6-9d46-21316dcaa1cf",
    "redirect_url": "https://127.0.0.1/auth-response",
    "secret_value": "rIE8Q~PQLsdM0EA_Fb8Aw.w_GFUKMHQ-CC8JBcfN",
    "version": "fabric-loader-0.14.21-1.19.4", # the version Grass is tested on
}
openai_api_key = ""

grass = Grass(
    mc_port=59279,
    openai_api_key=openai_api_key,
)

# start lifelong learning
grass.learn()
