import json
from collections import defaultdict

with open("./cards_collectible.json") as cards_file:
    card_data = json.load(cards_file)
with open("./tracked_decks.json") as hsreplay_file:
    hsreplay_data = json.load(hsreplay_file)

"""
This function prints some extremely basic info to the console
Call this if you are interested in seeing how the HSReplay JSON data
stores each deck.
"""
def raw_info():
    for class_name in hsreplay_data["series"]["data"]:
        print("Class name is " + class_name)

    print(hsreplay_data["series"]["data"]["WARLOCK"][0])
    print(hsreplay_data["series"]["data"]["WARLOCK"][0]["deck_list"])

"""
IMPORTANT!!!
Convenience functions - don't go through the trouble of parsing
all the cards/card data yourself, use these instead
decode_deck_list accepts a string that looks like this:
        "[[42743,2],[40465,1],[38452,2],[39740,2],[48,2],[974,2],[680,2],[631,2],[1090,2],[45340,1],[42790,2],[42773,2],[43415,1],[41323,2],[42395,2],[1092,1],[997,2]]"
and returns that horrible string as a list of tuples
get_card_info accepts an integer, like the first integer of all the lists in the string decode_deck_list accepts
and returns a dictionary of information regarding that card (or None if the ID is not valid)
"""
def decode_deck_list(raw_decklist):
    # expects a deck string from the HSReplay JSON data
    return [(card[0], card[1]) for card in json.loads(raw_decklist)]
_card_info_cache = {}
def get_card_info(card_id):
    if card_id in _card_info_cache:
        return _card_info_cache[card_id]
    # expects a card id from the deck list of the HSReplay JSON data for a specific deck
    # returns a map of info for the card (print card["name"] to see which card it is)
    for card in card_data:
        if card["dbfId"] == card_id:
            _card_info_cache[card_id] = card
            return card

"""
This method prints the card info for a single deck
(useful to know how this works for later uses)
"""
def printSingleHardcodedDeckCards():
    print("Cards found in deck [WARLOCK,0]:")
    for card in decode_deck_list(hsreplay_data["series"]["data"]["WARLOCK"][0]["deck_list"]):
        card_info = get_card_info(card[0])
        if card_info["rarity"] == "LEGENDARY":
            print("- ", card_info["name"], "x1 (legendary)")
        else:
            print("- ", card_info["name"], "x", card[1])


"""
The following code loops through all the warlock decks in the HSReplay data file
It then creates a frequency table of the cards as they appear across all Warlock decks in that file
and outputs a sorted list by frequency of all the cards in the current meta Walock decks
(which is why we have to create the card_tuples and sort it)
It currently doesn't take into account relative frequency between decks but that would be easy
to fix: just change frequencyTable[card_info["name"]] += card[1]
                 to frequencyTable[card_info["name"]] += card[1] * deck["total_games"]
"""
def printWarlockCardFreqs():
    frequencyTable = defaultdict(int)
    for deck in hsreplay_data["series"]["data"]["WARLOCK"]:
        for card in decode_deck_list(deck["deck_list"]):
            card_info = get_card_info(card[0])
            frequencyTable[card_info["name"]] += card[1]

    card_tuples = []
    for card_name in frequencyTable:
        card_tuples.append((frequencyTable[card_name], card_name))

    for item in reversed(sorted(card_tuples)):
        print(item[1], " has frequency ", item[0])

def buildWarlockCardMatchings():
    """
    Want to have e.g. key = "Flame Imp", value = {"cardname": relativeFreq}
    """
    matchings = defaultdict(lambda: defaultdict(int))
    for deck in hsreplay_data["series"]["data"]["WARLOCK"]:
        for first_card in decode_deck_list(deck["deck_list"]):
            first_card_info = get_card_info(first_card[0])
            for second_card in decode_deck_list(deck["deck_list"]):
                if first_card == second_card: # don't add proximity data for itself
                    continue
                else:
                    second_card_info = get_card_info(second_card[0])
                    matchings[first_card_info["name"]][second_card_info["name"]] += second_card[1] * deck["total_games"]

    return matchings

def getCardsThatAppearAlongside(card_names):
    matchings = defaultdict(int)
    for deck in hsreplay_data["series"]["data"]["WARLOCK"]:
        deck_cards = {}
        for card in decode_deck_list(deck["deck_list"]):
            card_info = get_card_info(card[0])
            deck_cards[card_info["name"]] = card[1]

        for required_card in card_names:
            if required_card not in deck_cards:
                break
        else:
            # All required cards are here!
            for card in deck_cards:
                #if card not in card_names: # do we actually want this?
                matchings[card] += deck_cards[card] * deck["total_games"]
    return matchings

if __name__ == "__main__":
    #print(get_card_info(42743)) # prints info for Despicable Dreadlord
    """
    matchings = buildWarlockCardMatchings()
    for card in matchings["Flame Imp"]:
        print(card, " has relative frequency with Flame Imp of ", matchings["Flame Imp"][card])
    """
    matchings = getCardsThatAppearAlongside(["Flame Imp", "Despicable Dreadlord", "Patches the Pirate"])

    del(matchings["Flame Imp"])
    for thing in matchings:
        print(thing + ",", matchings[thing])
