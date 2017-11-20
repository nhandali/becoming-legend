import json

with open("./cards_collectible.json") as cards_file:
    card_data = json.load(cards_file)
with open("./tracked_decks.json") as json_file:
    json_data = json.load(json_file)

for class_name in json_data["series"]["data"]:
    print("Class name is " + class_name)

print(json_data["series"]["data"]["WARLOCK"][0])
print(json_data["series"]["data"]["WARLOCK"][0]["deck_list"])

card_id = 42743

def decode_deck_list(raw_decklist):
    return [(card[0], card[1]) for card in json.loads(raw_decklist)]

print("Cards found in deck [WARLOCK,0]:")
print(json_data["series"]["data"]["WARLOCK"][0]["deck_list"])
#for card in json.loads(json_data["series"]["data"]["WARLOCK"][0]["deck_list"]):
for card in decode_deck_list(json_data["series"]["data"]["WARLOCK"][0]["deck_list"]):
    card_id = card[0]
    print(card)
