import random
import os.path
from bisect import bisect
from importlib import import_module
from pkgutil import iter_modules
from typing import List
from xml.etree import ElementTree
from hearthstone.enums import CardClass, CardType, Rarity
import collections, copy

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

#defines a feature extractor that generate a feature vector
def featureExtractor(player, game:".game.Game") -> ".game.Game":
	features = collections.defaultdict(int)
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
	if player.hero.power.is_usable():
		features["can use hero power"] = 1
	return features

#feature extraction v2
def featureExtractor2(player, game:".game.Game") -> ".game.Game":
	features = collections.defaultdict(int)
	features['our_hp'] = player.hero.health + player.hero.armor
	features['opponent_hp'] = player.opponent.hero.health + player.opponent.hero.armor
	features['bias'] = 1
	features["our_hand"] = len(player.hand)
	features['their_hand'] = len(player.opponent.hand)
	features['mana_left'] = player.mana

	total_power = 0
	for card in player.field:
		total_power += card.atk
	features["our_power"] = total_power
	total_power = 0
	for card in player.opponent.field:
		total_power += card.atk
	features["their_power"] = total_power
	features["our_minion"] = len(player.field)
	features["their_minions"] = len(player.opponent.field)
	return features
<<<<<<< HEAD
	
=======

def featureExtractor3(player, game:".game.Game") -> ".game.Game":
	features = collections.defaultdict(int)
	features["bias"] = 1
	if len([card for card in player.field]) > len([card for card in player.opponent.field]):
		features["board advantage"] = 1
	else:
		features["no board advantage"] = 1

	if len(player.hand) > len(player.opponent.hand):
		features["hand advantage"] = 1
	else:
		features["no hand advantage"] = 1
	if sum(card.atk for card in player.field) > sum(card.atk for card in player.opponent.field):
		features["power advantage"] = 1
	else:
		features["no power advantage"] = 1
	return features

>>>>>>> d2f77e4fd824f2fa13c56378a322b97262d64c49
_weights = collections.defaultdict(float)
def approximateV(player, game):
	phi = featureExtractor3(player, game)
	return sum(phi[x] * _weights[x] for x in phi)

def incorporateFeedback(phi, vpi, vprimepi, reward):
	for feature in phi:
		#print("IncorporateFeedback:", "phi is", phi, "vpi is", vpi, "vprimepi is", vprimepi, "reward is", reward, "new weight is", _weights[feature] - 0.05 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature])
		_weights[feature] = _weights[feature] - 0.05 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature]
		# try doing this after every sequence of actions

def TDLearningPlayer(player, game):
	actions_taken = 0
	while True:
		if game.ended:
			break
		phi = featureExtractor3(player, game)
		vpi = approximateV(player, game)
		print("TD learning estimate of V(s) is", vpi)
		print(_weights)
		# make a simple list of all the available actions at a given point
		available_actions = []
		for card in player.hand:
			if card.is_playable():
				available_actions.append(("CARD", card))
		if player.hero.power.is_usable():
			available_actions.append(("HEROPOWER", None))
		for character in player.characters:
			if character.can_attack():
				available_actions.append(("ATTACK", character))

		if not available_actions:
			break
		else:
			"""
			if 3 * len(available_actions) < actions_taken:
				for action_type, entity in available_actions:
					if action_type != "CARD":
						break
				else:
					# This happens if we've already taken a shit-tonne of actions
					# and the only thing left to do is play all our cards
					break
			"""
			action_type, entity = random.choice(available_actions)
			if action_type == "CARD":
				target = None
				card = entity
				if card.must_choose_one:
					card = random.choice(card.choose_cards)
				if card.requires_target():
					target = random.choice(card.targets)
				card.play(target=target)
			elif action_type == "HEROPOWER":
				heropower = player.hero.power
				if heropower.requires_target():
					heropower.use(target=random.choice(heropower.targets))
				else:
					heropower.use()
			else:
				entity.attack(random.choice(entity.targets))
			actions_taken += 1

			#if sum(phi[feature] for feature in phi) > 0:
			#	input()

		# reward = 0, discount = 0.9
		vprimepi = approximateV(player, game)
		incorporateFeedback(phi, vpi, vprimepi, 0)
		vpi = vprimepi

	if game.ended:
		if player == game.loser:
			incorporateFeedback(phi, vpi, 0, -100)
		else: # ASSUME TIES ARE IMPOSSIBLE FOR NOW
			incorporateFeedback(phi, vpi, 0, 100)

	game.end_turn()
	return game
	"""
			# Play the biggest minion
			available_cards = []
			for card in player.hand:
				if card.is_playable():
					available_cards.append(card)
			if available_cards:
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
				# TOOK ACTION
			# Use the hero power
			heropower = player.hero.power
			if heropower.is_usable():
				if heropower.requires_target():
					heropower.use(target=random.choice(heropower.targets))
					# TOOK ACTION
				else:
					heropower.use()
					# TOOK ACTION
				continue
			# Attack with a minion
			for character in player.characters:
				if character.can_attack():
					if character.can_attack(target=player.opponent.hero):
						character.attack(player.opponent.hero)
					else:
						character.attack(character.targets[0])
					if game.ended:
						break
			break
	"""

		# This is what the TA said:
		# we have to estimate the reward somehow
		# depth limited search
		# evaluation function (how similar is this to value function?)


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
	#return faceFirstLegalMovePlayer(player, game)

	if player == game.players[0]:
		return TDLearningPlayer(player, game)

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
	#weights = {'OG_113': -69.59999999999991, 'UNG_809': -41.999999999999915, 'CS2_065': 60.39999999999985, 'NEW1_025': -35.59999999999994, 'ICC_466': -25.99999999999997, 'EX1_310': 34.79999999999994, 'UNG_075': 38.39999999999993, 'ICC_075': -61.599999999999845, 'ICC_092': 10.400000000000004, 'ICC_851': -4.799999999999999, 'EX1_048': -14.000000000000005, 'ICC_831': -29.59999999999996, 'EX1_319': 112.80000000000052, 'CFM_637': -12.400000000000006, 'ICC_705': -61.19999999999985, 'GAME_005': -146.800000000001, 'EX1_308': -76.80000000000001, 'KAR_089': 29.999999999999957}
	toMulligan = []
	for card in hand:
		if weights[card.id] < 0:
			toMulligan.append(card)
	return toMulligan

def play_full_game(weights) -> ".game.Game":
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
	print("TD learning weights are now", _weights)
	return game
