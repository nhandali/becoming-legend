import json
from collections import defaultdict
import copy

"""
Note to self on how to get virtual environment started:
With Terminal in the base directory, type
"source hs/bin/activate"
And to deactivate the virtual environment, just type "deactivate" anywhere.

Link to page describing the deck we are using:
https://hsreplay.net/decks/Ius8aeryh7bo0KDV00Koqe/

Wanna use some data from HSReplay? Well have I got something for you!
(All files are in JSON)

List of all decks HSReplay tracks:
https://hsreplay.net/analytics/query/list_decks_by_win_rate/?GameType=RANKED_STANDARD&RankRange=LEGEND_THROUGH_TWENTY

List of mulligan rules for our deck:
https://hsreplay.net/analytics/query/single_deck_mulligan_guide/?GameType=RANKED_STANDARD&RankRange=ALL&Region=ALL&deck_id=Ius8aeryh7bo0KDV00Koqe

List of base winrate by opponent class for our deck:
https://hsreplay.net/analytics/query/single_deck_base_winrate_by_opponent_class/?GameType=RANKED_STANDARD&RankRange=ALL&Region=ALL&deck_id=Ius8aeryh7bo0KDV00Koqe

List of popularity (AND WIN RATE!!!) of all the cards in the game (useful for evaluation functions):
https://hsreplay.net/analytics/query/card_played_popularity_report/?GameType=RANKED_STANDARD&RankRange=ALL&TimeRange=LAST_14_DAYS
"""

with open("./cards_collectible.json") as cards_file:
    card_data = json.load(cards_file)
with open("./tracked_decks.json") as hsreplay_file:
    """
    NOTE: To update this file, redownload from the following link:
    https://hsreplay.net/analytics/query/list_decks_by_win_rate/?GameType=RANKED_STANDARD&RankRange=LEGEND_THROUGH_TWENTY
    """
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
Convenience function for looping over all the classes, since
HSReplay splits deck data by class
"""
def get_all_classes():
    return [class_name for class_name in hsreplay_data["series"]["data"]]

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
It currently takes into account relative frequency between decks
to remove: just change frequencyTable[card_info["name"]] += card[1] * deck["total_games"]
                    to frequencyTable[card_info["name"]] += card[1]
"""
def computeCardFreqs(class_name):
    frequencyTable = defaultdict(int)
    totalCards = 0
    for deck in hsreplay_data["series"]["data"][class_name]:
        for card in decode_deck_list(deck["deck_list"]):
            card_info = get_card_info(card[0])
            frequencyTable[card_info["name"]] += card[1] * deck["total_games"]
            totalCards += card[1] * deck["total_games"]

    return (frequencyTable, totalCards)

    """
    THIS CODE PRINTS THE FREQUENCIES IN CORRECT ORDER
    card_tuples = []
    for card_name in frequencyTable:
        card_tuples.append((frequencyTable[card_name], card_name))

    for item in reversed(sorted(card_tuples)):
        print(item[1], " has frequency ", item[0])
    """

def buildCardMatchings(class_name):
    """
    Want to have e.g. key = "Flame Imp", value = {"cardname": relativeFreq}
    """
    matchings = defaultdict(lambda: defaultdict(int))
    for deck in hsreplay_data["series"]["data"][class_name]:
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

def kNearestDecks(observed_cards, opponent_class):
    """
    To make this frequency thing even better, something I thought of:
    If they have a card that's pretty rare in their deck but appears in other decks,
    they should be prioritised somehow.
    e.g. if a Golakka crawler appears, that's much more significant than if a Voidwalker appears!
    How do we fix this?
    Maybe we should have a similarity score based on the relative INfrequency of cards,
    rather than the current distance based on the relative frequency of cards.
    """
    frequencyTable, totalCards = computeCardFreqs(opponent_class)
    def relativeFreq(card_name):
        if card_name not in frequencyTable:
            return 1e-6
        else:
            return frequencyTable[card_name] / totalCards
    allDecks = []
    for deck in hsreplay_data["series"]["data"][opponent_class]:
        # observed_cards_copy will eventually be modified so that
        # we only have the cards that the opponent played that don't
        # appear in this prospective deck at the end
        observed_cards_copy = copy.deepcopy(observed_cards)
        distance = 0.
        for card in decode_deck_list(deck["deck_list"]):
            card_info = get_card_info(card[0])
            if card_info["name"] not in observed_cards_copy:
                # This card hasn't been played - increases distance
                distance += card[1] * 1./relativeFreq(card_info["name"])
            else:
                # This card has been played - decreases distance
                observed_cards_copy.remove(card_info["name"])
                # If there was only one instance of that card in the deck...
                # and there are no more of that card, great!
                # Otherwise, if there are two instances of that card in the deck
                # and two instances in the observed cards, great!
                if card[1] == 1:
                    # only one copy of that card in the deck
                    if card_info["name"] not in observed_cards_copy:
                        # good, this matches!
                        distance -= card[1] * 1./relativeFreq(card_info["name"])
                    else:
                        distance -= 1 * 1./relativeFreq(card_info["name"])
                        # Doesn't match.
                        # net result - remove distance since card matches,
                        # then add distance since card doesn't match.
                else:
                    # two copies of that card in the deck
                    if card_info["name"] not in observed_cards_copy:
                        # only one copy of that card has been played
                        # net result - zero
                        # (see the code below for the negation to this distance removal)
                        distance -= 1 * 1./relativeFreq(card_info["name"])
                    else:
                        # This is great! 2 copies in the deck AND
                        # the opponent has played two copies!
                        observed_cards_copy.remove(card_info["name"])
                        distance -= card[1] * 1./relativeFreq(card_info["name"])
        # now observed_cards_copy only has cards that didn't appear in this deck
        for unseen_card in observed_cards_copy:
            distance += 1 * 1./relativeFreq(unseen_card)

        allDecks.append((distance, decode_deck_list(deck["deck_list"])))
    return sorted(allDecks)

if __name__ == "__main__":
    #print(get_card_info(42743)) # prints info for Despicable Dreadlord

    """
    This code computes a frequency table for how often pairs of cards are seen
    in decks for a specific class
    matchings = buildCardMatchings("WARLOCK")
    for card in matchings["Flame Imp"]:
        print(card, " has relative frequency with Flame Imp of ", matchings["Flame Imp"][card])
    """

    """
    This code computes a frequency table of all the cards that
    appear in decks containing EVERY card in the list that is
    passed in to this method
    matchings = getCardsThatAppearAlongside(["Flame Imp", "Despicable Dreadlord", "Patches the Pirate"])
    #del(matchings["Flame Imp"])
    for thing in matchings:
        print(thing + ",", matchings[thing])
    """

    seenCards = ["Flame Imp", "Despicable Dreadlord", "Patches the Pirate", "Prince Keleseth", "Bloodreaver Gul'dan"]
    print("Given the cards", seenCards)
    print("The opponent's most likely decks are:")
    print("")
    count = 0
    for distance, deck in kNearestDecks(seenCards, opponent_class="WARLOCK"):
        print("The following deck has distance", distance)
        for card in deck:
            card_info = get_card_info(card[0])
            print("-", card_info["name"], "x" + str(card[1]))
        count += 1
        if count == 5:
            break
