#!/usr/bin/env python
import sys; sys.path.append("..")
from fireplace import cards
from fireplace.exceptions import GameOver
from fireplace.utils import play_full_game


def test_full_game():
	try:
		count = 0
		total = 0
		for _ in range(500):
			game = play_full_game()
			if game.loser != game.players[0] :
				count += 1
			total += 1
		print("Winrate: ", count/float(total))
	except GameOver:
		print("Game completed normally.")


def main():
	cards.db.initialize()
	if len(sys.argv) > 1:
		numgames = sys.argv[1]
		if not numgames.isdigit():
			sys.stderr.write("Usage: %s [NUMGAMES]\n" % (sys.argv[0]))
			exit(1)
		for i in range(int(numgames)):
			test_full_game()
	else:
		test_full_game()


if __name__ == "__main__":
	main()
