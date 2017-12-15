# becoming-legend
Our Hearthstone AI project for CS221 and CS 229
By: Nolan Handali, Aleksander Dash, Franklin Jia

Due to the large codebase, we will highlight where the most important sections are
that contain the relevant code written by the members of this CS229 and CS221 project team. All
paths are relative to the current working directory, which should be /becoming-legend.
We will indicate where and which file to look at. Then we will indicate the functions
to pay attention to, and then we will describe why it's relevant. 

Testing:
To set up the environment, run pip3 install -r requirements.txt from /fireplace-master
Then, to see some output, navigate to /fireplace-master/tests.
Currently, the test we wrote is set up to do td-learning, but you can change that at line 874 in /fireplace-master/fireplace/utils.py
by returning which player to return. Then, to see output, go to /fireplace-master/fireplace/logging.py and change debug level to DEBUG.
Then, simply run python3 full_game.py [num_games] where the optional parameter is the number of games to run. At the end, the program
will output the winrate over those number of games.

Navigating the Framework:
1. Look inside of /fireplace-master/tests/full_game.py. 
	- test_full_game()
		- shows how we modified the testing to work for multiple simulations at a time.
		- shows the method for updating mulligan weights

	- backwardSearch()
		- shows the algorithm for backward search

2. Look inside of /fireplace-master/fireplace/utils.py
	- mulligan()
		- shows the optimal mulligan weights found from running mini-batch gradient descent
		until convergence

	- play_turn()
		- calls minimaxPlayer for our minimax player, or TDLearning Player to learn the 
		weights for our minimax evaluation function, or faceFirstLegalMovePlayer for 
		the opponent to play against for training and testing
		- it also shows the codebase's random player, we used this to train against prior
		to implementing the aggressive agent

	- faceFirstLegalMovePlayer()
		- shows our implementation for the aggressive agent

	- TDLearningPlayer()
		- shows our implementation for the TD Learning Player that is used to determine
		best weighting for our features

	- minimaxPlayer()
		- shows our implementation for the minimax player that is our primary AI for playing
		Hearthstone
		
	- minimaxGetBestAction()
		- shows our implementation for determining the best sequence of actions to take in
		a given turn for our AI
		- this is the bulk of the code for the logic of the minimax player
	
	- perform_action()
		- shows our implementation for how to perform an action within a turn
	
	- setEpsilon()
		- sets the epsilon for our TD Learning player

	- stringify_target_info()
		- shows how to convert target info into string

	- get_value_of_move()
		- shows how we play a move and then evaluate the value of being in that new state
	
	- get_num_targets()
		- gets the number of targets that an action can target (minion on field attacking
		opponent Hero, spell targeting an opposing minion, etc.)
	
	- get_action_by_index()
		- shows how to determine which action we should be taking, this is a helper that is 
		necessary since we are forced by the framework to deepcopy every time we want to
		explore an action in minimax
		- allows us to keep pick the right optimal action from a deepcopy
	
	- get_all_available_actions()
		- Find all available actions in a game state for a given player

	- incorporateFeedback()
		- shows the process of updating weights from TDLearning
	
	- approximateV()
		- shows how to find the value of being in a state

	- setTDWeights()
		- shows how we would set the TD-learned weights
		- this is for testing purposes, when we don't want to explore state space anymore,
		(so epsilon=0) and just want to test how good our minimax player is with these weights

	- setFeatures()
		- shows how we set the features upon completion of backward search

	- featureExtractor(), featureExtractor2(), featureExtractor3()
		- shows a couple of early attempts of hard-coding a feature extractor
		- no longer used once backwardSearch() was implemented for finding the best features

3. Look in /hsreplay-scraper/devtest.py
	- The documentation or function name should be enough for the majority of these functions

	- kNearestDecks()
		- shows how we determine the distance of decks given the cards we've already seen
		during the course of a game
		- this is the main function to pay attention to in this file
		- this is used by the minimax player to make good predictions on the opposing player's
		deck so we can better evaluate potential moves by the opponent

Final Note: 
While this is a pretty exhaustive list of functions that we implemented, there
are many changes that we made throughout the codebase that we failed to mention here, simply
because they aren't directly relevant to CS229 but were absolutely necessary in order for any
of this to be possible.
