# TODO: rewrite all of that to database requests

# TODO: think about other parameters, that might be useful
# Things to consider
# PLAYER:
# - what do you value most on the game (kinda similar to about in general)
# MASTER:
# -

# TEST DATA
# {"title": "name_master", "status": "Глеб"},
#         {"title": "username_master", "status": "@zerr0l"},
#         {"title": "age_master", "status": "19"},
#         {"title": "city_master", "status": "Moscow"},
#         {"title": "system_master", "status": "D&D"},
#         {"title": "edition_master", "status": "5e"},
#         {"title": "balance_master", "status": "13200"},

# in player/master there are only ids of games
user = {
    "general": {"name": "", "age": "", "city": "", "time_zone": "", "role": "", "format": "", "about_info": ""},
    "player": {"experience": "", "payment": "", "systems": [], "games": [{"id": "id_000000", "status": ""}], "archive": [], },
    "master": {"experience": "", "cost": "", "place": "", "platform": "", "requirements": "", "games": ["id_000000"], "archive": []},
}

users = {
    "id_000000": user
}

# in player/master there are only ids of users
game = {
    "status": "",
    "master": "",
    "players": [],
    "title": "",
    "place": "",
    "platform": "",
    "time": "",
    "cost": "",
    "format": "",
    "type": "",
    "system": "",
    "edition": "",
    "setting": "",
    "number_of_players": "",
    "requirements": "",
    "age": "",
    "description": "",
    "picture": "",
}

games = {
    "id_000000": game
}


# Passing arguments to dialog (GETTERS)
async def get_user_general(**kwargs):
    return user["general"]


async def get_user_player(**kwargs):
    return user["player"]


async def get_user_master(**kwargs):
    return user["master"]
