# TODO: rewrite all of that to database requests

# TODO: implement database
# TODO: think about other parameters, that might be useful
# Things to consider
# PLAYER:
# - what do you value most on the game (kinda similar to about in general)
# MASTER:
# -
user = {
    "general": {"name": "", "age": "", "city": "", "time_zone": "", "role": "", "format": "", "about_info": ""},
    "player": {"experience": "", "payment": "", "systems": []},
    "master": {"experience": "", "cost": "", "place": "", "platform": "", "requirements": ""},
}


# Passing arguments to dialog (GETTERS)
async def get_user_general(**kwargs):
    return user["general"]


async def get_user_player(**kwargs):
    return user["player"]


async def get_user_master(**kwargs):
    return user["master"]
