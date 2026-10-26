import json,re
D="C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/label_v21/practice/"
P={p["id"]:p["text"] for p in json.load(open(D+"team_a/chunk_01.json",encoding="utf-8"))}
def S(pid,r):
    s=re.split(r'(?<=[.?!])\s+',P[pid].strip())
    if "-" in r: a,b=r.split("-")
    else: a=b=r
    return " ".join(s[int(a)-1:int(b)])
R=[]
def rec(pid,entries,nei=None,none=False):
    es=[]
    for e in entries:
        n,lab,sup,mind,rel,say=e[:6]
        d={"noetic":n,"label":lab,"support":S(pid,sup),"mind":mind,"relative_to":rel,"certainty":"clear","saying":say}
        for x in e[6:]:
            if x=="amb":
                d["certainty"]="ambiguous";d["other_candidate"]="reasoning"
            if x=="reason": d["reached_by"]="reasoning"
        assert lab in d["support"],(pid,lab)
        assert not rel or rel in P[pid],(pid,rel)
        es.append(d)
    R.append({"passage_id":pid,"none_of_these":none,"entries":es,"not_enough_information":nei or []})
def M(l,s): return ("^1",l,s,l,"","")
rec("R01",[M("Sophie","1"),("^8","The soft, incessant clicking sound","2-3","Sophie","herself curled up on a rainy Saturday morning","Made me think of..."),("^9","herself curled up on a rainy Saturday morning","2-3","Sophie","The soft, incessant clicking sound","The thought came to me.")])
rec("R02",[M("Liam","1"),M("the young rider","1"),("^5","decades on ramps and rails","3","Liam","","We are the sum of our experiences."),("^7","decades","3","Liam","ramps and rails","Practice makes perfect.")])
rec("R03",[M("Carol","1"),M("the new club member","1"),("^5","decades of flying and building","4","Carol","","We are the sum of our experiences."),("^7","decades","4","Carol","flying and building","Practice makes perfect."),
 ("^8","a barely perceptible shimmy in its left wing during a turn","2-4","Carol","a slightly warped aileron","That reminds me...","amb"),("^9","a slightly warped aileron","2-4","Carol","a barely perceptible shimmy in its left wing during a turn","It just clicked.","amb")])
rec("R04",[M("Susan","1"),("^5","Decades of sailing","3","Susan","","We are the sum of our experiences."),("^7","Decades","3","Susan","sailing","Practice makes perfect."),
 ("^8","The way the clouds piled up, dark and low","2-4","Susan","a squall was brewing","That reminds me...","amb"),("^9","a squall was brewing","2-4","Susan","The way the clouds piled up, dark and low","It just clicked.","amb")])
rec("R05",[M("Kevin","1"),
 ("^6","the large script font for the name 'The Daily Loaf'","2-3","","The layout","Breaking it down."),
 ("^6","a smaller, block font","2-4","","The layout","Breaking it down."),
 ("^6","a simple graphic of a wheat stalk","2-5","","The layout","Breaking it down.")])
rec("R06",[M("George","1"),("^2","the plump tomatoes ripening on the vine","1","George","","Drawn to it like a moth to a flame."),("^3","a slug trail across a young lettuce leaf","2","George","","Rubs me the wrong way."),("^4","he did not hear it","4","George","A distant church bell","It made no impression on him.")])
rec("R07",[M("Catherine","1"),("^7","Every evening, just before closing","2","Catherine","a specific bell chimed from the nearby church tower","Getting into a groove.")])
rec("R08",[M("David","1"),
 ("^6","the hydraulic piston","2-3","","three components","Breaking it down."),
 ("^6","the sensor that detected the button's presence","2-4","","three components","Breaking it down."),
 ("^6","the feeder arm","2-5","","three components","Breaking it down.")])
rec("R09",[M("Ben","1"),("^7","for years","1","Ben","the button production line","Muscle memory."),("^7","Every morning, after the ten o’clock break","2","Ben","walk to the stamping machine","Muscle memory.")])
rec("R10",[M("Paul","1")],["Nothing settles any Noetic beyond the one Mind."])
rec("R11",[M("Elena","1"),M("her grandmother","3"),("^8","The steady rustle and pour of the grain","2-3","Elena","a summer afternoon, years ago, when she sat on her grandmother's porch","Triggered a memory."),("^9","a summer afternoon, years ago, when she sat on her grandmother's porch","2-3","Elena","The steady rustle and pour of the grain","It just popped into my head.")])
rec("R12",[M("Daniel","1")],["Nothing settles any Noetic beyond the one Mind."])
rec("R13",[M("Laura","1"),M("a customer","1"),("^6","warm, slightly sweet","1","","a spice","Breaking it down."),("^6","an orange-brown colour","1","","a spice","Breaking it down."),("^6","often used in baking","1","","a spice","Breaking it down."),
 ("^9","cinnamon, though perhaps a less common variety","4","Laura","","It just clicked.","reason")])
rec("R14",[M("Frank","1"),("^8","The sharp scent of balsa cement","2-3","Frank","his childhood kitchen table, covered in newspaper","Triggered a memory."),("^9","his childhood kitchen table, covered in newspaper","2-3","Frank","The sharp scent of balsa cement","The thought came to me.")])
rec("R15",[M("Peter","1"),("^6","The weight felt slightly off","1-2","","the wristwatch","Breaking it down."),("^6","the minute hand stuttered instead of sweeping smoothly","1-3","","the wristwatch","Breaking it down."),("^6","a slight blur in the printed logo on the face","1-4","","the wristwatch","Breaking it down."),
 ("^9","it was a counterfeit","6","Peter","","It just clicked.","reason")])
rec("R16",[M("Jessica","1"),M("the older skater","1"),("^6","the ollie for height","2-3","","distinct movements","Breaking it down."),("^6","the board spun beneath their feet","2-4","","distinct movements","Breaking it down."),("^6","the perfect landing","2-5","","distinct movements","Breaking it down.")])
rec("R17",[M("Mark","1"),("^6","the heat felt lower than usual","1","","the sauna","Breaking it down."),("^6","the bucket of water was completely empty","1-2","","the sauna","Breaking it down."),("^6","The thermometer also read a few degrees below its typical setting","1-3","","the sauna","Breaking it down."),
 ("^9","someone had forgotten to add water and adjust the temperature earlier","4","Mark","","It just clicked.","reason")])
rec("R18",[],none=True)
rec("R19",[M("Henry","1"),M("a new customer","1"),("^5","Years of dealing with instruments","3","Henry","","We are the sum of our experiences."),("^7","Years","3","Henry","dealing with instruments","Practice makes perfect."),
 ("^8","The way the wood aged","2-3","Henry","its craftsmanship and likely value","That reminds me...","amb"),("^9","its craftsmanship and likely value","2-3","Henry","The way the wood aged","It just clicked.","amb")])
rec("R20",[],none=True)
rec("R21",[M("Clara","1")],["Nothing settles any Noetic beyond the one Mind."])
rec("R22",[M("Emily","1"),("^2","the vibrant bed of zinnias","1","Emily","","Speaks to me."),("^3","a patch of stubborn bindweed","3","Emily","","Rubs me the wrong way."),("^4","she barely noticed its presence","4","Emily","a small ladybug","It made no impression on her.")])
rec("R23",[M("Robert","1"),("^6","The frame itself was sturdy aluminum","2-3","","several factors","Breaking it down."),("^6","the tires were bald","2-4","","several factors","Breaking it down."),("^6","the brake cables were frayed","2-4","","several factors","Breaking it down."),("^6","the derailleur housing was cracked","2-4","","several factors","Breaking it down."),("^6","several scratches on the paintwork","2-5","","several factors","Breaking it down.")])
rec("R24",[M("Arthur","1"),("^7","Every afternoon at three","2","Arthur","the deep blast","Muscle memory.")])
rec("R25",[M("Olivia","1"),M("her grandmother","3"),("^8","The constant gentle clanking of halyards against masts","2-3","Olivia","her grandmother's garden, filled with tinkling bamboo chimes","Made me think of..."),("^9","her grandmother's garden, filled with tinkling bamboo chimes","2-3","Olivia","The constant gentle clanking of halyards against masts","The thought came to me.")])
rec("R26",[M("Gary","1"),("^5","worked in the silo for thirty years","1","Gary","","We are the sum of our experiences."),("^7","for thirty years","1","Gary","worked in the silo","Practice makes perfect."),
 ("^8","the faint, irregular clinking sound","2-4","Gary","a bearing was beginning to seize up","That reminds me...","amb"),("^9","a bearing was beginning to seize up","2-4","Gary","the faint, irregular clinking sound","It just clicked.","amb")])
rec("R27",[],none=True)
rec("R28",[M("Nora","1"),("^2","the sweet, earthy smell of the freshly harvested wheat","1","Nora","","Speaks to me."),("^3","The fine, airborne dust","3","Nora","","Can't stomach it."),("^4","she barely flinched","4","Nora","the large overhead fan","It made no impression on her.")])
rec("R29",[M("Margaret","1"),("^5","forty years with a brush","4","Margaret","","We are the sum of our experiences."),("^7","forty years","4","Margaret","a brush","Practice makes perfect."),
 ("^8","A faint smudge near the corner of the 'G'","2-4","Margaret","the paint was drying too fast for the humidity","That reminds me...","amb"),("^9","the paint was drying too fast for the humidity","2-4","Margaret","A faint smudge near the corner of the 'G'","It just clicked.","amb")])
rec("R30",[M("Leo","1"),("^2","the smooth, even consistency of the pigment","1","Leo","","Speaks to me."),("^2","the clean lines that flowed from his brush","2","Leo","","Speaks to me."),("^3","a tiny paint drip","3","Leo","","Rubs me the wrong way."),("^4","he paid it no attention","4","Leo","a distant train whistle","It made no impression on him.")])
json.dump(R,open(D+"labels_team_a.json.chunk_01.work.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(len(R))
