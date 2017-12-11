#!/usr/bin/env python
import sys; sys.path.append("..")
from fireplace import cards
from fireplace.exceptions import GameOver
from fireplace.utils import play_full_game, setEpsilon, setFeatures, setTDWeights
import collections,copy

'''
Performs backward search. First it trains with epsilon-greedy algo, and uses those weights to then test with epsilon 0(deterministic policy)
We then take the best subset of features each time and continue our search. At the end, we print out the best overall features
'''
def backwardSearch():
	overallBestFeatures = list()
	overallBestWinrate = 0.0
	featureVec = ['our_hp', 'opponent_hp', 'bias', "our_hand", 'their_hand', 'mana_left', "our_power", "their_power", "our_minion", "their_minions", "board_mana_advantage", "mana_efficiency", "hand_advantage", "minion_advantage", "minion_power_advantage", "hp_advantage"]
	for i in range(1,10):
		iterationBestWinrate = 0
		iterationBestIndex = 0

		for index in range(len(featureVec)):
			currFeatures = copy.deepcopy(featureVec)
			currFeatures.pop(index)
			print("Training with curr features", currFeatures)
			setEpsilon(.75)
			setFeatures(currFeatures)
			weights,winrate = test_full_game(5)

			#now test
			setEpsilon(0)
			setTDWeights(weights)
			print("Testing with curr features,", currFeatures)
			print("current WEights are", weights)
			weights, winrate = test_full_game(5)

			if winrate > iterationBestWinrate:
				iterationBestWinrate = winrate
				iterationBestIndex = index

		featureVec.pop(iterationBestIndex)
		if iterationBestWinrate > overallBestWinrate:
			overallBestWinrate = iterationBestWinrate
			overallBestFeatures= featureVec
		print("current features size", len(featureVec))
		print('current best winrate is ', iterationBestWinrate)
		print('current best features', featureVec)
	print("Best winrate was ", overallBestWinrate)
	print("Those features were", overallBestFeatures)



def test_full_game(numgames = 1):
	try:
		alpha = .4
		weights = collections.defaultdict(int)
		winrates = []
		numIterations = 0
		winrate = 0
		td_weights = []
		while True:
			numIterations += 1
			count = 0
			for i in range(numgames):
				game = play_full_game(weights)
				if game.loser != game.players[0] :
					count += 1
					for card in game.startCards:
						weights[card.id] +=alpha
					# for card in game.oppCards:
					# 	weights[card.id] -= alpha
				else:
					for card in game.startCards:
						weights[card.id] -= alpha
					# for card in game.oppCards:
					# 	weights[card.id] += alpha
				# if i % 25 == 0: 
				# if i % 100 == 0:
				if i % 20 == 0 or i == 199:
					print("iteration", i)
					print("td-weights", game.weights)
					td_weights.append((i,game.weights))
			print("Winrate: ", count/float(numgames))
			#print("Card Weights", weights)
			return (game.weights,count/float(numgames) )
			break
			winrates.append((numIterations, count/float(numgames)))
			if abs(count/float(numgames) - winrate) < .02:
				break
			winrate = count/float(numgames)
		print(winrates)
		print("td-weights", td_weights)
	except GameOver:
		print("Game completed normally.")



def main():
	cards.db.initialize()
	# backwardSearch()
	if len(sys.argv) > 1:
		numgames = sys.argv[1]
		if not numgames.isdigit():
			sys.stderr.write("Usage: %s [NUMGAMES]\n" % (sys.argv[0]))
			exit(1)
		test_full_game(int(numgames))
	else:
		test_full_game()


if __name__ == "__main__":
	main()
