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

# initialise the weights to previously calculated optimal values
_weights = collections.defaultdict(float)
#premade_weights = {'our_hp': 1.8673489184303163, 'opponent_hp': -3.037539913253422, 'bias': 10.412656424974298, 'our_hand': 2.153127765674754, 'their_hand': 0.9804111235739774, 'mana_left': -0.2590213226410433, 'our_power': 2.451094822043288, 'their_power': -1.3346142482372798, 'our_minion': -0.004790280977330176, 'their_minions': -2.4850411791904015}
premade_weights =  {'their_hand': 0.36995550582041914, 'our_hand': 0.9631924650032906, 'our_power': 2.5618985848510722, 'bias': 10.391136076838388, 'their_power': -0.6684936230427211, 'opponent_hp': -1.662752205387238, 'our_hp': 1.4978564673209003, 'our_minion': 0.5465476389621604, 'mana_left': 1.309791771696138, 'their_minions': -1.5804438382538541}
for w in premade_weights:
	_weights[w] = premade_weights[w]

def approximateV(player, game):
	phi = featureExtractor2(player, game)
	return sum(phi[x] * _weights[x] for x in phi)

def incorporateFeedback(phi, vpi, vprimepi, reward):
	for feature in set().union(_weights, phi):
		#print("IncorporateFeedback:", "phi is", phi, "vpi is", vpi, "vprimepi is", vprimepi, "reward is", reward, "new weight is", _weights[feature] - 0.05 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature])
		_weights[feature] = _weights[feature] - 0.001 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature]
		# try doing this after every sequence of actions

def get_all_available_actions(player):
	available_actions = []
	for card in player.hand:
		if card.is_playable():
			available_actions.append(("CARD", card))
	if player.hero.power.is_usable():
		available_actions.append(("HEROPOWER", None))
	for character in player.characters:
		if character.can_attack():
			available_actions.append(("ATTACK", character))
	available_actions.append(("END_TURN", None)) # player can always end their turn
	return available_actions

# slightly more efficient!
def get_action_by_index(game, actionIndex, playerIndex=0):
	playable_cards = [card for card in game.players[playerIndex].hand if card.is_playable()]
	#print("get_action_by_index: there are", len(playable_cards), "playable cards.")
	if actionIndex < len(playable_cards):
		return ("CARD", playable_cards[actionIndex])
	actionIndex -= len(playable_cards)
	#print("get_action_by_index: hero power usable:", game.players[playerIndex].hero.power.is_usable())
	if game.players[playerIndex].hero.power.is_usable():
		if actionIndex == 0:
			return ("HEROPOWER", None)
		actionIndex -= 1
	ready_characters = [character for character in game.players[playerIndex].characters if character.can_attack()]
	#print("get_action_by_index: there are", len(ready_characters), "ready characters.")
	if actionIndex < len(ready_characters):
		return ("ATTACK", ready_characters[actionIndex])
	actionIndex -= len(ready_characters)
	if actionIndex == 0:
		return ("END_TURN", None)
	else:
		#print("get_action_by_index: ERROR! should end turn but could not, actionIndex was", actionIndex)
		return None

def get_num_targets(game, moveIndex, playerIndex=0):
	action_type, action_entity = get_action_by_index(game, moveIndex, playerIndex)
	if action_type == "CARD":
		card = action_entity
		if card.must_choose_one:
			return len(card.choose_cards)
		if card.requires_target():
			return len(card.targets)
		return -1
	elif action_type == "HEROPOWER":
		heropower = game.players[playerIndex].hero.power
		if heropower.requires_target():
			return len(heropower.targets)
		return -1
	elif action_type == "ATTACK":
		return len(action_entity.targets)
	else:
		return -1

def get_value_of_move(game, moveIndex, moveTarget=-1, playerIndex=0):
	game_copy = copy.deepcopy(game)
	action_type, action_entity = get_action_by_index(game_copy, moveIndex, playerIndex)
	if action_type == "CARD":
		target = None
		card = action_entity
		if card.must_choose_one:
			card = card.choose_cards[moveTarget]
		if card.requires_target():
			target = card.targets[moveTarget]
		card.play(target=target)
	elif action_type == "HEROPOWER":
		heropower = game_copy.players[playerIndex].hero.power
		if heropower.requires_target():
			heropower.use(target=heropower.targets[moveTarget])
		else:
			heropower.use()
	elif action_type == "ATTACK":
		action_entity.attack(action_entity.targets[moveTarget])
	else:
		pass
	return approximateV(game_copy.players[playerIndex], game_copy)

def stringify_target_info(player, action_type, action_entity, targetIndex):
	if action_type == "CARD":
		if action_entity.must_choose_one:
			return str(action_entity.choose_cards[targetIndex])
		if action_entity.requires_target():
			return str(action_entity.targets[targetIndex])
	if action_type == "HEROPOWER":
		if player.hero.power.requires_target():
			return str(player.hero.power.targets[targetIndex])
	if action_type == "ATTACK":
		return str(action_entity.targets[targetIndex])
	return "(none)"

epsilon = .05
def TDLearningPlayer(player, game):
	actions_taken = 0
	while True:
		if game.ended:
			break
		phi = featureExtractor2(player, game)
		vpi = approximateV(player, game)
		#print("TD learning estimate of V(s) is", vpi)
		#print(_weights)
		# make a simple list of all the available actions at a given point
		available_actions = get_all_available_actions(player)
		#print("====== CURRENT PLAYER MANA:", player.mana)

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
			if random.random() < epsilon:
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
				elif action_type == "ATTACK":
					entity.attack(random.choice(entity.targets))
				else: # end turn
					break
				actions_taken += 1
			else:
				# Go through every action and see which one is the best one
				best_action_index = -1
				best_action_target = -1
				best_value = float("-inf")
				for _ in range(1):
					for i in range(len(available_actions)):
						num_targets = get_num_targets(game, i)
						if num_targets == -1:
							vpi = get_value_of_move(game, i)
							action_type, action_entity = get_action_by_index(game, i)
							#print("Action", action_type, "with", action_entity, "has value", vpi)
							if vpi > best_value:
								best_value = vpi
								best_action_index = i
								best_action_target = -1
						else:
							for t in range(num_targets):
								vpi = get_value_of_move(game, i, moveTarget=t)
								action_type, action_entity = get_action_by_index(game, i)
								#print("Action", action_type, "with", action_entity, "on target", stringify_target_info(player, action_type, action_entity, t), "has value", vpi)
								if vpi > best_value:
									best_value = vpi
									best_action_index = i
									best_action_target = t
						"""
						game_copy = copy.deepcopy(game)
						current_action_type, current_entity = get_all_available_actions(game_copy.players[0])[i]
						if current_action_type == "CARD":
							card = current_entity
							target = None
							if card.must_choose_one:
								card = random.choice(card.choose_cards)
							if card.requires_target():
								target = random.choice(card.targets)
							card.play(target=target)
							vpi = approximateV(game_copy.players[0], game_copy)
							print("Playing", card, "has value", vpi)
						elif current_action_type == "HEROPOWER":
							heropower = game_copy.players[0].hero.power
							if heropower.requires_target():
								heropower.use(target=random.choice(heropower.targets))
							else:
								heropower.use()
							vpi = approximateV(game_copy.players[0], game_copy)
							print("Hero power has value", vpi)
						elif current_action_type == "ATTACK":
							new_attacker = current_entity
							new_attacker.attack(random.choice(new_attacker.targets))
							vpi = approximateV(game_copy.players[0], game_copy)
							print("Attacking with", new_attacker, "has value", vpi)
						else:
							# END TURN
							vpi = approximateV(player, game)
							print("Ending turn has value", vpi)

						if vpi > best_value:
							best_value = vpi
							best_action_index = i
						"""
				# NOW perform the action
				best_action_type, best_entity = available_actions[best_action_index]
				#print("============ BEST ACTION IS", best_action_type, "with", best_entity, "and target", stringify_target_info(player, best_action_type, best_entity, best_action_target), "(value " + str(best_value) + " )")
				if best_action_type == "CARD":
					target = None
					card = best_entity
					if card.must_choose_one:
						card = card.choose_cards[best_action_target]
					if card.requires_target():
						target = card.targets[best_action_target]
					card.play(target=target)
				elif best_action_type == "HEROPOWER":
					heropower = player.hero.power
					if heropower.requires_target():
						heropower.use(target=heropower.targets[best_action_target])
					else:
						heropower.use()
				elif best_action_type == "ATTACK":
					best_entity.attack(best_entity.targets[best_action_target])
				else:
					break # END TURN
				actions_taken += 1

		#if sum(_weights[feature] for feature in phi) > 0:
		#	input()

		# reward = 0, discount = 0.9
		vprimepi = approximateV(player, game)
		#print("vpi is", vpi, " vprimepi is ", vprimepi)
		#incorporateFeedback(phi, vpi, vprimepi, 0)
		vpi = vprimepi

	# if game.ended:
	# 	if player == game.loser:
	# 		#incorporateFeedback(phi, vpi, 0, -100)
	# 	else: # ASSUME TIES ARE IMPOSSIBLE FOR NOW
	# 		#incorporateFeedback(phi, vpi, 0, 100)
	#print("=========================== TURN OVER")

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

"""
		# This is what the TA said:
		# we have to estimate the reward somehow
		# depth limited search
		# evaluation function (how similar is this to value function?)
# def minimax(player, game: ".game.Game") -> ".game.Game":

# 	def getMaxAction(player, game,depth):
# 		if game.ended:
# 			if game.players[0] == game.loser:
# 				return -100,None
# 			else return 100,None
# 		elif depth == 0:
# 			return approximateV(player, game),None
# 		elif player == game.players[0]:
# 			#call getMaxAction on all possible actions
# 			return max(values)
# 		else:
# 			#call get Max Action on all possible
# 			return min(values)
# 	value, actions = getMaxAction(player, game, 2)
# 	for action in actions:
# 		do action
"""
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


# Reflex agent to test against.
def play_turn(game: ".game.Game") -> ".game.Game":
	player = game.current_player
	if player == game.players[0]:
		#return faceFirstLegalMovePlayer(player, game)
		return TDLearningPlayer(player, game)
	else:
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
	weights = {'OG_113': -69.59999999999991, 'UNG_809': -41.999999999999915, 'CS2_065': 60.39999999999985, 'NEW1_025': -35.59999999999994, 'ICC_466': -25.99999999999997, 'EX1_310': 34.79999999999994, 'UNG_075': 38.39999999999993, 'ICC_075': -61.599999999999845, 'ICC_092': 10.400000000000004, 'ICC_851': -4.799999999999999, 'EX1_048': -14.000000000000005, 'ICC_831': -29.59999999999996, 'EX1_319': 112.80000000000052, 'CFM_637': -12.400000000000006, 'ICC_705': -61.19999999999985, 'GAME_005': -146.800000000001, 'EX1_308': -76.80000000000001, 'KAR_089': 29.999999999999957}
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
			game.weights =_weights
			print("loser:" ,game.loser)
			break
	#print("TD learning weights are now", _weights)
	return game
