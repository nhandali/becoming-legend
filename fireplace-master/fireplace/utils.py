import random
import os.path
from bisect import bisect
from importlib import import_module
from pkgutil import iter_modules
from typing import List
from xml.etree import ElementTree
from hearthstone.enums import CardClass, CardType, Rarity


# Autogenerate the list of cardset modules
_cards_module = os.path.join(os.path.dirname(__file__), "cards")
CARD_SETS = [cs for _, cs, ispkg in iter_modules([_cards_module]) if ispkg]


class CardList(list):
	def __contains__(self, x):
		for item in self:
			if x is item:
				return True
		return False

	def __getitem__(self, key):
		ret = super().__getitem__(key)
		if isinstance(key, slice):
			return self.__class__(ret)
		return ret

	def __int__(self):
		# Used in Kettle to easily serialize CardList to json
		return len(self)

	def contains(self, x):
		"True if list contains any instance of x"
		for item in self:
			if x == item:
				return True
		return False

	def index(self, x):
		for i, item in enumerate(self):
			if x is item:
				return i
		raise ValueError

	def remove(self, x):
		for i, item in enumerate(self):
			if x is item:
				del self[i]
				return
		raise ValueError

	def exclude(self, *args, **kwargs):
		if args:
			return self.__class__(e for e in self for arg in args if e is not arg)
		else:
			return self.__class__(e for k, v in kwargs.items() for e in self if getattr(e, k) != v)

	def filter(self, **kwargs):
		return self.__class__(e for k, v in kwargs.items() for e in self if getattr(e, k, 0) == v)


def random_draft(card_class: CardClass, exclude=[]):
	"""
	Return a deck of 30 random cards for the \a card_class
	"""
	from . import cards
	from .deck import Deck 

	deck = []
	collection = []
	hero = card_class.default_hero

	for card in cards.db.keys():
		if card in exclude:
			continue
		cls = cards.db[card]
		if not cls.collectible:
			continue
		if cls.type == CardType.HERO:
			# Heroes are collectible...
			if cls.rarity != Rarity.LEGENDARY:
				continue
		if cls.card_class and cls.card_class != card_class:
			continue
		collection.append(cls)

	while len(deck) < Deck.MAX_CARDS:
		card = random.choice(collection)
		if deck.count(card.id) < card.max_count_in_deck:
			deck.append(card.id)

	return deck


def random_class():
	return CardClass(random.randint(2, 10))


def get_script_definition(id):
	"""
	Find and return the script definition for card \a id
	"""
	for cardset in CARD_SETS:
		module = import_module("fireplace.cards.%s" % (cardset))
		if hasattr(module, id):
			return getattr(module, id)


def entity_to_xml(entity):
	e = ElementTree.Element("Entity")
	for tag, value in entity.tags.items():
		if value and not isinstance(value, str):
			te = ElementTree.Element("Tag")
			te.attrib["enumID"] = str(int(tag))
			te.attrib["value"] = str(int(value))
			e.append(te)
	return e


def game_state_to_xml(game):
	tree = ElementTree.Element("HSGameState")
	tree.append(entity_to_xml(game))
	for player in game.players:
		tree.append(entity_to_xml(player))
	for entity in game:
		if entity.type in (CardType.GAME, CardType.PLAYER):
			# Serialized those above
			continue
		e = entity_to_xml(entity)
		e.attrib["CardID"] = entity.id
		tree.append(e)

	return ElementTree.tostring(tree)


def weighted_card_choice(source, weights: List[int], card_sets: List[str], count: int):
	"""
	Take a list of weights and a list of card pools and produce
	a random weighted sample without replacement.
	len(weights) == len(card_sets) (one weight per card set)
	"""

	chosen_cards = []

	# sum all the weights
	cum_weights = []
	totalweight = 0
	for i, w in enumerate(weights):
		totalweight += w * len(card_sets[i])
		cum_weights.append(totalweight)

	# for each card
	for i in range(count):
		# choose a set according to weighting
		chosen_set = bisect(cum_weights, random.random() * totalweight)

		# choose a random card from that set
		chosen_card_index = random.randint(0, len(card_sets[chosen_set]) - 1)

		chosen_cards.append(card_sets[chosen_set].pop(chosen_card_index))
		totalweight -= weights[chosen_set]
		cum_weights[chosen_set:] = [x - weights[chosen_set] for x in cum_weights[chosen_set:]]

	return [source.controller.card(card, source=source) for card in chosen_cards]


def setup_game() -> ".game.Game":
	from .game import Game
	from .player import Player
	from fireplace.card import princeWarlock
	deck1 = princeWarlock()
	deck2 = princeWarlock()
	#deck2 = random_draft(CardClass.WARRIOR)
	player1 = Player("Player1", deck1, CardClass.WARLOCK.default_hero)
	player2 = Player("Player2", deck2, CardClass.WARLOCK.default_hero)

	game = Game(players=(player1, player2))
	game.start()

	return game

def featureExtractor(player, game:".game.Game") -> ".game.Game":
	features = collections.defualtdict(int)
	features['our_hp'] = player.hero.health + player.hero.armor
	features['opponent_hp'] = player.opponent.hero.health + player.opponent.hero.armor
	features['bias'] = 1
	for card in player.hand:
		features["our_card" + str(card)] = 1
	for card in player.opponent.hand:
		features["opp_card" + str(card)] = 1
	our_board_mana = 0
	for card in player.field:
		features["our_board" + str(card)] = 1
		our_board_mana += card.cost
	features["our_board_cost"] = our_board_mana
	their_board_mana = 0
	for card in player.opponent.field:
		features["our_board" + str(card)] = 1
		their_board_mana += card.cost
	features["their_board_cost"] = their_board_mana
	features["our_hand"] = len(player.hand)
	features["their_hand"] = len(player.opponent.hand)
	features["mana_left"] = player.mana
	features["num_minions"] = len(player.field)
	features["their_minions"] = len(player.opponent.field)


def minimaxPlayer(player, game: ".game.Game") -> ".game.Game":
	pass
"""
	This player tries to play cards before hero powering, it also plays
	the first card that's playable, and keeps playing cards until it can't anymore.
	It also always goes face, unless there are taunts in the way.
"""
def faceFirstLegalMovePlayer(player, game: ".game.Game") -> ".game.Game":
	while True:
		if game.ended:
			break
		# iterate over our hand and play whatever is playable
		for card in player.hand:

			if card.is_playable():
				target = None
				if card.must_choose_one:
					card = random.choice(card.choose_cards)
				if card.requires_target():
					if player.opponent.hero in card.targets:
						target = player.opponent.hero
					else:
						target = card.targets[0]
				#print("Playing %r on %r" % (card, target))
				card.play(target=target)
				
				if game.ended:
					game.end_turn()
					return game
				if player.choice:
					choice = random.choice(player.choice.cards)
					#print("Choosing card %r" % (choice))
					player.choice.choose(choice)

				continue

		heropower = player.hero.power
		if heropower.is_usable():
			if heropower.requires_target():
				if player.opponent.hero in heropower.targets:
					heropower.use(target=player.opponent.hero)
				else:
					heropower.use(target=heropower.targets[0])
			else:
				heropower.use()
			continue

		# For all characters, try to attack hero if possible
		for character in player.characters:
			if character.can_attack():
				if character.can_attack(target=player.opponent.hero):
					character.attack(player.opponent.hero)
				else:
					character.attack(character.targets[0])
				if game.ended:
					break
		break

	game.end_turn()
	return game


# Seems like this is where players actually play some sort of strategy
def play_turn(game: ".game.Game") -> ".game.Game":
	player = game.current_player
	#if player == game.players[0]:
	return faceFirstLegalMovePlayer(player, game)

	while True:
		if game.ended:
			break
		heropower = player.hero.power
		if heropower.is_usable() and random.random() < 0.1:
			if heropower.requires_target():
				heropower.use(target=random.choice(heropower.targets))
			else:
				heropower.use()
			continue

		# iterate over our hand and play whatever is playable
		for card in player.hand:
			if card.is_playable() and random.random() < 0.5:
				target = None
				if card.must_choose_one:
					card = random.choice(card.choose_cards)
				if card.requires_target():
					target = random.choice(card.targets)
				#print("Playing %r on %r" % (card, target))
				card.play(target=target)

				if player.choice:
					choice = random.choice(player.choice.cards)
					#print("Choosing card %r" % (choice))
					player.choice.choose(choice)

				continue

		# Randomly attack with whatever can attack
		for character in player.characters:
			if character.can_attack():
				character.attack(random.choice(character.targets))
				if game.ended:
					break

		break

	game.end_turn()
	return game

#our mulligan strategy
def mulligan(hand, weights):

	toMulligan = []
	for card in hand:
		if weights[card.id] < 0:
			toMulligan.append(card)
	return toMulligan
def play_full_game(weights) -> ".game.Game":
	import copy
	game = setup_game()

	for player in game.players:
		#print("Can mulligan %r" % (player.choice.cards))
		if player == game.players[0]:
			player.choice.choose(*mulligan(player.choice.cards, weights))
		else:
			mull_count = random.randint(0, len(player.choice.cards))
			cards_to_mulligan = random.sample(player.choice.cards, mull_count)
			player.choice.choose(*cards_to_mulligan)
		if player == game.players[0]:
			game.startCards = copy.deepcopy(player.hand)
		else:
			game.oppCards = copy.deepcopy(player.hand)

	while True:
		play_turn(game)
		if game.ended:
			print("loser:" ,game.loser)
			break
	return game
