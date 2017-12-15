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

#used to set the features of the game.
currFeatures = list()
def setFeatures(featuresToUse):
	global currFeatures
	currFeatures= featuresToUse

#feature extraction v2
def featureExtractor2(player, game:".game.Game") -> ".game.Game":

	features = collections.defaultdict(int)
	our_hp = player.hero.health + player.hero.armor
	opp_hp = player.opponent.hero.health + player.opponent.hero.armor
	# features['our_hp'] = our_hp
	# features['opponent_hp'] = opp_hp
	features['bias'] = 1
	# features["our_hand"] = len(player.hand)
	# features['their_hand'] = len(player.opponent.hand)
    #
	# features['mana_left'] = player.mana

	our_total_power = 0
	for card in player.field:
		our_total_power += card.atk
	# features["our_power"] = our_total_power
	opp_total_power = 0
	for card in player.opponent.field:
		opp_total_power += card.atk
	# features["their_power"] = opp_total_power

	# features["our_minion"] = len(player.field)
	# features["their_minions"] = len(player.opponent.field)

	board_mana = sum([minion.cost for minion in player.field])
	opp_board_mana = sum([minion.cost for minion in player.opponent.field])
	features["board_mana_advantage"] = board_mana - opp_board_mana

	features["mana_efficiency"] = player.total_mana_spent - player.opponent.total_mana_spent
	features["hand_advantage"] = len(player.hand) - len(player.opponent.hand)
	features["minion_advantage"] = len(player.field) - len(player.opponent.field)
	features["minion_power_advantage"] = our_total_power - opp_total_power
	features["hp_advantage"] = our_hp - opp_hp
	# print("mana_efficiency: ", features["mana_efficiency"])

	# for feature in features:
	# 	if feature not in currFeatures:
	# 		features[feature] = 0
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
#baseline, weights all 0
# premade_weights = {'their_hand': 0, 'our_hand': 0, 'our_power': 0, 'bias': 0, 'their_power': 0, 'opponent_hp': 0, 'our_hp': 0, 'our_minion': 0, 'mana_left': 0, 'their_minions': 0}
#premade_weights = {'our_hp': 1.8673489184303163, 'opponent_hp': -3.037539913253422, 'bias': 10.412656424974298, 'our_hand': 2.153127765674754, 'their_hand': 0.9804111235739774, 'mana_left': -0.2590213226410433, 'our_power': 2.451094822043288, 'their_power': -1.3346142482372798, 'our_minion': -0.004790280977330176, 'their_minions': -2.4850411791904015}
#100 iterations
# premade_weights = {'their_hand': 1.0646307772800043, 'our_hand': 1.4327237475494323, 'our_power': 1.0369101111840149, 'bias': 10.341823820463755, 'their_power': -0.6086494868042713, 'opponent_hp': -1.5532639423923134, 'our_hp': 1.4071730601372168, 'our_minion': -0.04624718876929695, 'mana_left': 0.6679475550062922, 'their_minions': -1.9432952708163345}
#these are weights after running td-learning with epsilon .75 and 200 iterations.
# premade_weights =  {'their_hand': 0.36995550582041914, 'our_hand': 0.9631924650032906, 'our_power': 2.5618985848510722, 'bias': 10.391136076838388, 'their_power': -0.6684936230427211, 'opponent_hp': -1.662752205387238, 'our_hp': 1.4978564673209003, 'our_minion': 0.5465476389621604, 'mana_left': 1.309791771696138, 'their_minions': -1.5804438382538541}
#300 iterations
# premade_weights = {'their_hand': 0.212426211768464, 'our_hand': 0.302072884763938, 'our_power': 0.2911624605284303, 'bias': 10.209268300485258, 'their_power': -0.3721761071162327, 'opponent_hp': -1.3134321405409255, 'our_hp': 1.6175992273146158, 'our_minion': 0.08821251558653698, 'mana_left': -0.3499741916863078, 'their_minions': -1.1405777692166605}
#400 iterations
# premade_weights = {'their_hand': 0.41802993693023266, 'our_hand': 0.3124753209370982, 'our_power': 0.11116826859056192, 'bias': 10.138501188678141, 'their_power': 0.778331007381161, 'opponent_hp': -0.5338714610707936, 'our_hp': 0.3235654348530477, 'our_minion': 0.2096401091254182, 'mana_left': -0.41537467405371387, 'their_minions': -0.8217223885734551}
#500:
# premade_weights = {'their_hand': 0.22458278816613944, 'our_hand': 0.45456663350945825, 'our_power': -0.5799190705958176, 'bias': 9.978792932842978, 'their_power': -0.4207673657087993, 'opponent_hp': -0.09869359518798886, 'our_hp': 0.1711667371866392, 'our_minion': 0.08902883753474322, 'mana_left': -0.5658920102805077, 'their_minions': -0.9276363211936061}
#20:
# premade_weights = {'our_minion': -0.12185503856857878, 'their_hand': 0.05445471549172044, 'their_power': 0.016551441981040936, 'opponent_hp': -1.1414067047346732, 'mana_left': -0.03466587767254341, 'our_power': 1.3478995609309878, 'our_hp': 0.7655818635207267, 'their_minions': -1.5316447444870125, 'bias': 10.230574958070411, 'our_hand': 1.5232876754976714}
#40
# premade_weights = {'our_minion': -0.12185503856857878, 'their_hand': 0.05445471549172044, 'their_power': 0.016551441981040936, 'opponent_hp': -1.1414067047346732, 'mana_left': -0.03466587767254341, 'our_power': 1.3478995609309878, 'our_hp': 0.7655818635207267, 'their_minions': -1.5316447444870125, 'bias': 10.230574958070411, 'our_hand': 1.5232876754976714}
#60
# premade_weights = {'our_minion': -0.12185503856857878, 'their_hand': 0.05445471549172044, 'their_power': 0.016551441981040936, 'opponent_hp': -1.1414067047346732, 'mana_left': -0.03466587767254341, 'our_power': 1.3478995609309878, 'our_hp': 0.7655818635207267, 'their_minions': -1.5316447444870125, 'bias': 10.230574958070411, 'our_hand': 1.5232876754976714}
#80
# premade_weights = {'our_minion': -0.12185503856857878, 'their_hand': 0.05445471549172044, 'their_power': 0.016551441981040936, 'opponent_hp': -1.1414067047346732, 'mana_left': -0.03466587767254341, 'our_power': 1.3478995609309878, 'our_hp': 0.7655818635207267, 'their_minions': -1.5316447444870125, 'bias': 10.230574958070411, 'our_hand': 1.5232876754976714}
#200 w/board-mana-advantage only
# premade_weights = {'our_hp': 2.0258296975654964, 'opponent_hp': -0.786233614047869, 'bias': -0.027235727508457677, 'our_hand': -0.6132569197522117, 'their_hand': 0.10952017087858268, 'mana_left': -0.6176642541592727, 'our_power': 0.5624496532327938, 'their_power': 0.04829666299926383, 'our_minion': 0.7096041741106176, 'their_minions': -0.14681510537123388, 'board_mana_advantage': -0.5789632029105242}
#200 w/ mana-efficiency only
# premade_weights = {'our_hp': 1.9094939844911247, 'opponent_hp': -0.6084501223763931, 'bias': -0.065081860476852, 'our_hand': 0.8589199625133825, 'their_hand': -0.013114520886652326, 'mana_left': 2.2458353839090566, 'our_power': 1.1491238395431829, 'their_power': -0.056254806650156364, 'our_minion': 0.5613719009936117, 'their_minions': 0.6214773440275192, 'mana_efficiency': 0.06605307904672975}
#200 w/ both
# premade_weights = {'our_hp': 1.9151354328361043, 'opponent_hp': -1.6075679128499454, 'bias': -0.07802881939217356, 'our_hand': 0.9099921149042629, 'their_hand': -0.17375162139897005, 'mana_left': 1.15076070140721, 'our_power': 0.379311892296743, 'their_power': -0.7341619493430168, 'our_minion': 0.22292275114902624, 'their_minions': 0.20418176040099065, 'board_mana_advantage': 0.18522614599905135, 'mana_efficiency': 0.8654447096826992}
#200 w/ truncated features
premade_weights = {'bias': 1.4829512976964385, 'board_mana_advantage': 0.2987328257289936, 'mana_efficiency': 0.10609448036514402, 'hand_advantage': 1.3235807484387507, 'minion_advantage': 0.5496890531814512, 'minion_power_advantage': 2.450495646630526, 'hp_advantage': 0.2631808186797604}

for w in premade_weights:
	_weights[w] = premade_weights[w]

def setTDWeights(tdweights):
	global _weights
	for w in tdweights:
		if w in currFeatures:
			_weights[w] = tdweights[w]


def approximateV(player, game):
	phi = featureExtractor2(player, game)
	return sum(phi[x] * _weights[x] for x in phi)

def incorporateFeedback(phi, vpi, vprimepi, reward):
	for feature in set().union(_weights, phi):
		#print("IncorporateFeedback:", "phi is", phi, "vpi is", vpi, "vprimepi is", vprimepi, "reward is", reward, "new weight is", _weights[feature] - 0.05 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature])
		_weights[feature] = _weights[feature] - 0.001 * (vpi - (reward + 0.9 * vprimepi)) * phi[feature]

def get_all_available_actions(player):
	"""
	Returns a list of (action_type, action_entity) tuples
	representing all the actions a given player can take
	during the current turn in the game
	"""
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
	"""
	Returns the i-th (action_type, action_entity) tuple from
	get_all_available_actions. This method is slightly more efficient since
	it only generates the relevant tuple.
	"""
	playable_cards = [card for card in game.players[playerIndex].hand if card.is_playable()]
	if actionIndex < len(playable_cards):
		return ("CARD", playable_cards[actionIndex])
	actionIndex -= len(playable_cards)
	if game.players[playerIndex].hero.power.is_usable():
		if actionIndex == 0:
			return ("HEROPOWER", None)
		actionIndex -= 1
	ready_characters = [character for character in game.players[playerIndex].characters if character.can_attack()]
	if actionIndex < len(ready_characters):
		return ("ATTACK", ready_characters[actionIndex])
	actionIndex -= len(ready_characters)
	if actionIndex == 0:
		return ("END_TURN", None)
	else:
		return None

def get_num_targets(game, moveIndex, playerIndex=0):
	"""
	Given an action, returns the number of targets of that action
	(e.g. the number of valid targets for a minion to attack) or -1
	if there are no valid targets.
	"""
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
	"""
	Returns the V(s') of performing a given action on the current game state.
	Does not modify the game state passed into the method.
	"""
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
		game_copy.current_player.total_mana_spent += card.cost
	elif action_type == "HEROPOWER":
		heropower = game_copy.players[playerIndex].hero.power
		if heropower.requires_target():
			heropower.use(target=heropower.targets[moveTarget])
		else:
			heropower.use()
		game_copy.current_player.total_mana_spent += 2
	elif action_type == "ATTACK":
		action_entity.attack(action_entity.targets[moveTarget])
	else:
		pass
	return approximateV(game_copy.players[playerIndex], game_copy)

def stringify_target_info(player, action_type, action_entity, targetIndex):
	"""
	Debug helper method to print the target of an action as a string.
	"""
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

epsilon = 0
def setEpsilon(eVal):
	global epsilon
	epsilon = eVal


def perform_action(game, player_index, action_index, target_index):
	"""
	Performs the given action on the current game state and modifies it.
	Returns True if the action caused the game to end or the player's turn to finish.
	Returns False otherwise.
	"""
	action_type, action_entity = get_action_by_index(game, action_index, player_index)
	if action_type == "CARD":
		target = None
		card = action_entity
		if card.must_choose_one:
			card = card.choose_cards[target_index]
		if card.requires_target():
			target = card.targets[target_index]
		card.play(target=target)
	elif action_type == "HEROPOWER":
		heropower = game.players[player_index].hero.power
		if heropower.requires_target():
			heropower.use(target=heropower.targets[target_index])
		else:
			heropower.use()
	elif action_type == "ATTACK":
		action_entity.attack(action_entity.targets[target_index])
	else:
		game.end_turn() # END TURN
		return True

	if game.ended:
		return True
	else:
		return False

def minimaxGetBestAction(player_index, game_orig, depth, indent):
	"""
	Performs a beam search with K = 3 over the current game state with the given
	depth. The indent parameter should initially be "" and makes it easier for debug
	purposes to visualise the call stack.
	Returns a (predicted_V, action_list) tuple to the caller.
	"""
	print(indent + "Entering minimax for player_index " + str(player_index) + " and depth " + str(depth))
	if game_orig.ended:
		if game_orig.loser == game_orig.players[1]:
			return (200., None)
		else:
			return (-200., None)
	elif depth == 0:
		return (approximateV(game_orig.players[player_index], game_orig), None)

	# Make a deep copy since we do not want to modify the original game state
	# nor the game state from the previous recursive call
	game = copy.deepcopy(game_orig)

	# List of (approximateV, action_chain, game_state) tuples
	completed_action_chains = []
	partial_action_chains = [(approximateV(game.players[0], game), [], game)]

	print(indent + "Exploring all action chains for player_index " + str(player_index) + " and depth " + str(depth))
	while partial_action_chains:
		current_value, prev_actions, chain_game = partial_action_chains.pop(0)
		available_actions = get_all_available_actions(chain_game.players[player_index])
		for i in range(len(available_actions)):
			num_targets = get_num_targets(chain_game, i, player_index)
			if num_targets == -1:
				chain_game_copy = copy.deepcopy(chain_game)
				game_or_turn_just_ended = perform_action(chain_game_copy, player_index, i, -1)
				if game_or_turn_just_ended:
					if chain_game_copy.ended and chain_game_copy.loser == chain_game_copy.players[1]:
						predicted_value = 200.
					elif chain_game_copy.ended and chain_game_copy.loser == chain_game_copy.players[0]:
						predicted_value = -200.
					else:
						predicted_value = approximateV(chain_game_copy.players[0], chain_game_copy)
					new_actions = copy.deepcopy(prev_actions)
					new_actions.append((i, -1))
					completed_action_chains.append((predicted_value, new_actions, chain_game_copy))
				else:
					predicted_value = approximateV(chain_game_copy.players[0], chain_game_copy)
					new_actions = copy.deepcopy(prev_actions)
					new_actions.append((i, -1))
					partial_action_chains.append((predicted_value, new_actions, chain_game_copy))

			else:
				for t in range(num_targets):
					chain_game_copy = copy.deepcopy(chain_game)
					game_or_turn_just_ended = perform_action(chain_game_copy, player_index, i, t)
					if game_or_turn_just_ended:
						if chain_game_copy.ended and chain_game_copy.loser == chain_game_copy.players[1]:
							predicted_value = 200.
						elif chain_game_copy.ended and chain_game_copy.loser == chain_game_copy.players[0]:
							predicted_value = -200.
						else:
							predicted_value = approximateV(chain_game_copy.players[0], chain_game_copy)
						new_actions = copy.deepcopy(prev_actions)
						new_actions.append((i, t))
						completed_action_chains.append((predicted_value, new_actions, chain_game_copy))
					else:
						predicted_value = approximateV(chain_game_copy.players[0], chain_game_copy)
						new_actions = copy.deepcopy(prev_actions)
						new_actions.append((i, t))
						partial_action_chains.append((predicted_value, new_actions, chain_game_copy))

	print(indent + "completed_action_chains has length " + str(len(completed_action_chains)))

	# Explore best/worst 3 paths from completed_action_chains
	if player_index == 0:
		best_paths = sorted(completed_action_chains)[:3]
		best_chain = None
		max_value = float("-inf")
		for chain in best_paths:
			print(indent + "Player " + str(player_index) + " at depth " + str(depth) + " - current estimate " + str(chain[0]) + " (actions " + str(chain[1]) + ")")
			est_value, _ = minimaxGetBestAction(1, chain[2], depth, indent + "  ")
			if est_value > max_value:
				max_value = est_value
				best_chain = chain[1]
		return (max_value, best_chain)
	else:
		worst_paths = sorted(completed_action_chains)[-1:-4:-1]
		print(indent + "Minimising player worst action chains have predicted value:")
		worst_chain = None
		min_value = float("+inf")
		for chain in worst_paths:
			print(indent + "Player " + str(player_index) + " at depth " + str(depth) + " - current estimate " + str(chain[0]) + " (actions " + str(chain[1]) + ")")
			est_value, _ = minimaxGetBestAction(0, chain[2], depth - 1, indent + "  ")
			if est_value < min_value:
				min_value = est_value
				worst_chain = chain[1]
		return (min_value, worst_chain)

def minimaxPlayer(player, game):
	"""
	Wrapper that makes use of minimaxGetBestAction to play the game.
	"""
	if game.ended:
		return game
	available_actions = get_all_available_actions(player)
	if not available_actions:
		return game

	stuff = minimaxGetBestAction(0, game, 2, "")
	print("Minimax says our best actions to take right now have value " + str(stuff[0]))
	print("The action sequence is " + str(stuff[1]))
	print("Returned stuff is " + str(stuff))
	print("============================================================================")

	for action in stuff[1]:
		perform_action(game, 0, action[0], action[1])
	return game


def TDLearningPlayer(player, game):
	"""
	Implements a TD-learning player with an epsilon-greedy algorithm
	and Monte Carlo bootstrapping to learn how to play a specific deck
	against a given opponent.
	"""
	actions_taken = 0
	while True:
		if game.ended:
			break
		phi = featureExtractor2(player, game)
		vpi = approximateV(player, game)

		# make a simple list of all the available actions at a given point
		available_actions = get_all_available_actions(player)
		#print("====== CURRENT PLAYER MANA:", player.mana)

		if not available_actions:
			break
		else:
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
					player.total_mana_spent += card.cost

				elif action_type == "HEROPOWER":
					heropower = player.hero.power
					if heropower.requires_target():
						heropower.use(target=random.choice(heropower.targets))
					else:
						heropower.use()
					player.total_mana_spent += 2
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
							if vpi > best_value:
								best_value = vpi
								best_action_index = i
								best_action_target = -1
						else:
							for t in range(num_targets):
								vpi = get_value_of_move(game, i, moveTarget=t)
								action_type, action_entity = get_action_by_index(game, i)
								if vpi > best_value:
									best_value = vpi
									best_action_index = i
									best_action_target = t

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
					player.total_mana_spent += card.cost
				elif best_action_type == "HEROPOWER":
					heropower = player.hero.power
					if heropower.requires_target():
						heropower.use(target=heropower.targets[best_action_target])
					else:
						heropower.use()
					player.total_mana_spent += 2
				elif best_action_type == "ATTACK":
					best_entity.attack(best_entity.targets[best_action_target])
				else:
					break # END TURN
				actions_taken += 1

		# uncomment this if you want to see how the weight vector changes
		#if sum(_weights[feature] for feature in phi) > 0:
		#	input()

		# reward = 0, discount = 0.9
		vprimepi = approximateV(player, game)
		#print("vpi is", vpi, " vprimepi is ", vprimepi)
		if epsilon != 0:
			incorporateFeedback(phi, vpi, vprimepi, 0)
		vpi = vprimepi

	if game.ended and epsilon != 0:
		if player == game.loser:
			incorporateFeedback(phi, vpi, 0, -100)
		else: # Ties are impossible with our deck
			incorporateFeedback(phi, vpi, 0, 100)
	#print("=========================== TURN OVER")

	game.end_turn()
	return game


cardsPlayed = list()
def faceFirstLegalMovePlayer(player, game: ".game.Game") -> ".game.Game":
	"""
	This player tries to play cards before hero powering, it also plays
	the first card that's playable, and keeps playing cards until it can't anymore.
	It also always goes face, unless there are taunts in the way.
	"""
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
				print("Playing %r on %r" % (card, target))
				card.play(target=target)
				cardsPlayed.append(str(card))
				player.total_mana_spent += card.cost

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
			player.total_mana_spent += 2
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
	"""
	This method essentially decides which player to use for the game.
	Everything after the return statements at the beginning of this
	method is not important.
	"""
	player = game.current_player
	if player == game.players[0]:
		# Change these lines of code to change which player we use.
		#return faceFirstLegalMovePlayer(player, game)
		return TDLearningPlayer(player, game)
		#return minimaxPlayer(player, game)
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

def mulligan(hand, weights):
	"""
	Method that decides which cards to keep at the beginning of the game
	will lead to the highest probability of winning.
	Weights learned through batch gradient descent.
	"""
	weights = {'OG_113': -69.59999999999991, 'UNG_809': -41.999999999999915, 'CS2_065': 60.39999999999985, 'NEW1_025': -35.59999999999994, 'ICC_466': -25.99999999999997, 'EX1_310': 34.79999999999994, 'UNG_075': 38.39999999999993, 'ICC_075': -61.599999999999845, 'ICC_092': 10.400000000000004, 'ICC_851': -4.799999999999999, 'EX1_048': -14.000000000000005, 'ICC_831': -29.59999999999996, 'EX1_319': 112.80000000000052, 'CFM_637': -12.400000000000006, 'ICC_705': -61.19999999999985, 'GAME_005': -146.800000000001, 'EX1_308': -76.80000000000001, 'KAR_089': 29.999999999999957}
	toMulligan = []
	for card in hand:
		if weights[card.id] < 0:
			toMulligan.append(card)
	return toMulligan

def play_full_game(weights) -> ".game.Game":
	"""
	This method is the entry point of this code file.
	It in turn calls mulligan for both players, and then
	proceeds to play the game, which is a sequence of calls to
	the play_turn() method, which in turn calls the
	appropriate player (random, aggressive, TD-learning, minimax).
	"""
	game = setup_game()
	global cardsPlayed
	cardsPlayed = list()
	for player in game.players:
		#print("Can mulligan %r" % (player.choice.cards))
		player.total_mana_spent = 0
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
			print(cardsPlayed)
			#print("1 iteration ended")
			print("Loser: ", game.loser)
			game.weights =_weights
			break
	#print("TD learning weights are now", _weights)
	return game
