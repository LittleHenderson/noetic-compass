# Parameter arithmetic from the constructor lines (pointer_learner.py:739-822 current; learner_q4_neural.py:47-51). No model is built.
W=64; LN=2*W
def head(i,o): return i*W + LN + (W*o+o)
h2 = {
 "core ^6 (left,right,merge)": W*W + W*W + W*2*W,
 "node_encode 18->64": 18*W,
 "state_encode (F1)": W*W,
 "match_key (F2b)": W*W,
 "round_mix+round_rate": 3+1,
 "query_projection+query_norm": 21*W + LN,
 "attention_key": W,
 "world_projection 196->64": (3*W+4)*W,
 "declaration_table 1024x64": 1024*W,
 "declaration_projection": W*32,
 "directed_pair_embedding": 2*8,
 "node_head": head(2*W,2),
 "edge_head": head(2*W+8,2),
 "role_head+role_embedding": head(3*W+6,2) + 6*W,
 "pointer_key": W*W,
 "reach_option_head (F2a, 260 in)": head(4*W+4,2),
 "mode_option_head": head(3*W,2),
 "world_head": head(2+4+32,1),
}
t2=sum(h2.values())
t1 = t2 - W*W - W*W - (head(4*W+4,2)-head(2*W+4,2))
print("Helm 2.0 total", t2, "Helm 1.0 total", t1)
for k,v in h2.items(): print("  %-34s %6d  %.4f of 2.0" % (k, v, v/t2))
msg = h2["core ^6 (left,right,merge)"]+h2["node_encode 18->64"]+h2["state_encode (F1)"]+h2["round_mix+round_rate"]
print("message-passing path (core+node_encode+state_encode+mix/rate): 2.0 %d = %.4f ; 1.0 %d = %.4f" % (msg, msg/t2, msg-W*W, (msg-W*W)/t1))
print("declaration_table share: 2.0 %.4f ; 1.0 %.4f" % (1024*W/t2, 1024*W/t1))
# R1 width 64
g = 3*(W*W + W*W + W + W)
r1 = {"input_embedding 257x64": 257*W, "encoder GRU": g, "output_embedding 35x64": 35*W, "decoder GRU": g, "output_head 64->34": W*34+34}
print("R1 total", sum(r1.values()), r1)
