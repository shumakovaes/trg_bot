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
    "player": {"experience": "", "payment": "", "systems": [], "games": ["id_000000"], "archive": [], },
    "master": {"experience": "", "cost": "", "place": "", "platform": "", "requirements": "", "games": ["id_000000"], "archive": []},
}

users = {
    "id_000000": user
}

# in player/master there are only ids of users
game = {
    "status": "Набор игроков закрыт",
    "master": "id_000000",
    "players": ["id_000000"],
    "title": "Тестовая игра",
    "place": "Улица Пушкина, дом Колотушкина",
    "platform": "",
    "time": "2222.2.22 22:22:22",
    "cost": "222 рубля",
    "format": "Оффлайн",
    "type": "Ваншот",
    "system": "D&D 5e",
    "min_players_number": 3,
    "max_players_number": 4,
    "requirements": "Дожить",
    "min_age": 80,
    "max_age": 99,
    "description": "Вот бы сейчас, эххх",
    "picture": "",
}

default_game = {
    "status": "Набор игроков открыт",
    "master": "id_000000",
    "players": [""],
    "title": "",
    "place": "",
    "platform": "",
    "time": "",
    "cost": "",
    "format": "",
    "type": "",
    "system": "",
    "min_players_number": 0,
    "max_players_number": 0,
    "requirements": "",
    "min_age": 14,
    "max_age": 99,
    "description": "",
    "picture": "",
}

games = {
    "id_000000": game
}


# These are ttrpgs from top of the list of ORR Roll20 report Q3 | 2021, maybe some other systems should be added:
# Star Wars, Blades in the Dark, Apocalypse World System, Mutants and Masterminds, Shadowrun, Savage Worlds, Vampire: The Masquerade (as separate from World of Darkness category)
popular_systems = [
    {"system": "D&D", "id": "system_dnd"},
    {"system": "Зов Ктулху", "id": "system_call_of_cthulhu"},
    {"system": "Pathfinder", "id": "system_pathfinder"},
    {"system": "Warhammer", "id": "system_warhammer"},
    {"system": "Мир Тьмы", "id": "system_world_of_darkness"},
    {"system": "Starfinder", "id": "system_starfinder"},
    {"system": "FATE", "id": "system_fate"},
    {"system": "Savage Worlds", "id": "system_savage_worlds"},
    {"system": "Cyberpunk", "id": "system_cyberpunk"},
    {"system": "GURPS", "id": "system_gurps"},
]


# CONSTANTS
MIN_AGE = 14
MAX_AGE = 99
MIN_PLAYERS_NUMBER = 1
MAX_PLAYERS_NUMBER = 20


# Passing arguments to dialog (GETTERS)
async def get_user_general(**kwargs):
    return user["general"]


async def get_user_player(**kwargs):
    return user["player"]


async def get_user_master(**kwargs):
    return user["master"]


async def get_player_games(**kwargs):
    player_games = []
    for game_id in user["player"]["games"]:
        game_title_and_status = {"status": games[game_id]["status"], "title": games[game_id]["title"]}
        player_games.append(game_title_and_status)
    return {"games": player_games}


async def get_master_games(**kwargs):
    master_games = []
    for game_id in user["master"]["games"]:
        game_title_and_status = {"status": games[game_id]["status"], "title": games[game_id]["title"]}
        master_games.append(game_title_and_status)
    return {"games": master_games}


async def get_player_archive(**kwargs):
    player_archive = []
    for game_id in user["player"]["archive"]:
        game_title_and_status = {"status": games[game_id]["status"], "title": games[game_id]["title"]}
        player_archive.append(game_title_and_status)
    return {"games": player_archive}


async def get_master_archive(**kwargs):
    master_archive = []
    for game_id in user["master"]["archive"]:
        game_title_and_status = {"status": games[game_id]["status"], "title": games[game_id]["title"]}
        master_archive.append(game_title_and_status)
    return {"games": master_archive}

