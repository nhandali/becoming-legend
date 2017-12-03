from ..util import *

#minions

class ICC_092:
	"Acherus Veteran"
	play = Buff(TARGET, "ICC_092e")
ICC_092e = buff(+1, +0)

class UNG_809:
	"Fire Fly"
	play = Give(CONTROLLER, "UNG_809t1")

class ICC_851:
	"Prince Keleseth"
	play = Buff(FRIENDLY_DECK, "ICC_851e")
ICC_851e = buff(+1, +1)

class OG_113:
	"Darkshire Councilman"
	events = Summon(CONTROLLER, MINION).after(
		Buff(SELF, "OG_113e")
	)
OG_113e = buff(+1, 0)

class ICC_466:
	"Saronite Chain Gang"
	play = Summon(CONTROLLER, ExactCopy(SELF))

class ICC_075:
	"Despicable Dreadlord"
	play = OWN_TURN_END.on(Hit(ENEMY_MINIONS, 1))
class ICC_705:
	"Bonemare"
	play = Buff(Target, "ICC_705e")
ICC_705e = buff(+4, +4, taunt=True)