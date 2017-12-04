#!/usr/bin/env python
import sys; sys.path.append("..")
from fireplace import cards
from fireplace.exceptions import GameOver
from fireplace.utils import play_full_game
import collections

def test_full_game(numgames = 1):
	try:
		alpha = .4
		weights = collections.defaultdict(int)
		winrates = []
		numIterations = 0
		winrate = 0
		while True:
			numIterations += 1
			count = 0
			total = 0
			for _ in range(numgames):
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
				total += 1
			print("Winrate: ", count/float(total))
			print("Card Weights", weights)
			
			winrates.append((numIterations, count/float(total)))
			if abs(count/float(total) - winrate) < .02:
				break
			winrate = count/float(total)
		print(winrates)
	except GameOver:
		print("Game completed normally.")



def main():
	cards.db.initialize()
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
