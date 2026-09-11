# One cross-cube teaching episode per face

Compiled from the declared corpus; the input shown is what the
numerical path receives.

## Face 1 - name_definition_function (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:02, family:grammatical:00, family:procedural:00

```
CUBE_FACE_1
node Clock kind=idea
node Gear kind=idea
node Spring kind=idea
node Seal kind=idea
rel Clock --contains--> Gear
rel Clock --contains--> Spring
rel Spring --contains--> Seal
rel Gear --contains--> Seal
Requested view: CUBE_FACE_1 state what the whole is and what it is for, as declared -> Object under inspection: Clock, a timekeeping mechanism. Function: transmits force between Clock and Gear.
CUBE_FACE_1
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_1 state what the whole is and what it is for, as declared -> Sentence is a grammatical unit. Declared function: it carries the relation between Sentence and Phrase.
CUBE_FACE_1
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_1 state what the whole is and what it is for, as declared -> Recipe is a cooking procedure. Declared function: it produces Step as part of Recipe.
CUBE_FACE_1
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_1 state what the whole is and what it is for, as declared
Choose one of the three supplied options.
```

Delivered choices (public order): `["Clause - a clause pattern. Its declared function is to carries the relation between Clause and Subject.", "Sentence is a grammatical unit. Declared function: it carries the relation between Sentence and Phrase.", "Bicycle is a wheeled vehicle. Declared function: it transmits force between Bicycle and Wheel."]`; correct slot 2.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
declaration: Bicycle is a wheeled vehicle. Declared purpose: it transmits force between Bicycle and Wheel.
```

Recognition choices: `["5: parts and structural relationships", "4: explicit correspondence", "1: technical name, definition and function"]`; correct slot 2.

## Face 2 - context_environment (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:03, family:grammatical:00, family:procedural:00

```
CUBE_FACE_2
node Pump kind=idea
node Piston kind=idea
node Valve kind=idea
node Gasket kind=idea
rel Pump --contains--> Piston
rel Piston --contains--> Valve
rel Valve --contains--> Gasket
Requested view: CUBE_FACE_2 state the setting and the interactions that hold here -> In a workshop the participants are Pump and Piston, Valve.
CUBE_FACE_2
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_2 state the setting and the interactions that hold here -> Setting: in an edited sentence. Participants: Sentence, Phrase, Word.
CUBE_FACE_2
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_2 state the setting and the interactions that hold here -> Setting: during a recorded run. Participants: Recipe, Step, Ingredient.
CUBE_FACE_2
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_2 state the setting and the interactions that hold here
Choose one of the three supplied options.
```

Delivered choices (public order): `["Setting: in a workshop. Participants: Bicycle, Wheel, Rim.", "Setting: in a workshop. Participants: Bicycle, and Wheel is contained by Wheel.", "This holds elsewhere, with Bicycle and Wheel, Rim present."]`; correct slot 0.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
surroundings: Surroundings: in a workshop. Participants: Bicycle, Wheel, Rim.
```

Recognition choices: `["2: context, environment and interactions", "6: recomposition, story or bounded process", "5: parts and structural relationships"]`; correct slot 0.

## Face 3 - analogy_metaphor (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:04, family:grammatical:00, family:procedural:00

```
CUBE_FACE_3
node Loom kind=idea
node Shuttle kind=idea
node Thread kind=idea
node Bearing kind=idea
rel Loom --contains--> Thread
rel Shuttle --contains--> Thread
rel Loom --contains--> Bearing
Requested view: CUBE_FACE_3 choose the example whose declared relationships match -> node List kind=idea
node Item kind=idea
node Marker kind=idea
node Determiner kind=idea
rel List --contains--> Marker
rel Item --contains--> Marker
rel List --contains--> Determiner
CUBE_FACE_3
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_3 choose the example whose declared relationships match -> node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
CUBE_FACE_3
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_3 choose the example whose declared relationships match -> node Kit kind=idea
node Rope kind=idea
node Strand kind=idea
rel Kit --contains--> Rope
rel Rope --contains--> Strand
CUBE_FACE_3
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_3 choose the example whose declared relationships match
Choose one of the three supplied options.
```

Delivered choices (public order): `["node Sentence kind=idea\nnode Phrase kind=idea\nnode Word kind=idea\nrel Sentence --contains--> Phrase\nrel Phrase --contains--> Word\n", "node Sentence kind=idea\nnode Phrase kind=idea\nnode Word kind=idea\nrel Sentence --contains--> Phrase\nrel Word --contains--> Phrase\n", "node Clause kind=idea\nnode Subject kind=idea\nnode Predicate kind=idea\nnode Object kind=idea\nrel Clause --contains--> Subject\nrel Clause --contains--> Predicate\nrel Clause --contains--> Object\n"]`; correct slot 0.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
relation to keep: a whole contains a direct constituent, and that constituent contains a further constituent (Bicycle -> Wheel -> Rim)
candidate: node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
```

Recognition choices: `["6: recomposition, story or bounded process", "1: technical name, definition and function", "3: analogy or metaphor within a declared scope"]`; correct slot 2.

## Face 4 - explicit_correspondence (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:05, family:grammatical:00, family:procedural:00

```
CUBE_FACE_4
node Lathe kind=idea
node Chuck kind=idea
node Tool kind=idea
node Bolt kind=idea
rel Lathe --contains--> Chuck
rel Lathe --contains--> Tool
rel Tool --contains--> Bolt
Requested view: CUBE_FACE_4 choose the mapping that preserves the declared relations -> Lathe=Compound ; Chuck=ClauseA ; Tool=Conjunction ; Bolt=Particle
CUBE_FACE_4
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_4 choose the mapping that preserves the declared relations -> Sentence=Recipe ; Phrase=Step ; Word=Ingredient
CUBE_FACE_4
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_4 choose the mapping that preserves the declared relations -> Recipe=Kit ; Step=Rope ; Ingredient=Strand
CUBE_FACE_4
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_4 choose the mapping that preserves the declared relations
Choose one of the three supplied options.
```

Delivered choices (public order): `["Bicycle=Phrase ; Wheel=Sentence ; Rim=Word", "Bicycle=Sentence ; Wheel=Phrase", "Bicycle=Sentence ; Wheel=Phrase ; Rim=Word"]`; correct slot 2.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
candidate table: Bicycle=Sentence ; Wheel=Phrase ; Rim=Word
```

Recognition choices: `["1: technical name, definition and function", "4: explicit correspondence", "2: context, environment and interactions"]`; correct slot 1.

## Face 5 - parts_structure (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:06, family:grammatical:00, family:procedural:00

```
CUBE_FACE_5
node Turbine kind=idea
node Blade kind=idea
node Rotor kind=idea
rel Turbine --contains--> Blade
rel Blade --contains--> Rotor
Requested view: CUBE_FACE_5 state whether Rotor is directly inside, reached through another constituent, or absent (Turbine) -> via:Blade
CUBE_FACE_5
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_5 state whether Word is directly inside, reached through another constituent, or absent (Sentence) -> via:Phrase
CUBE_FACE_5
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_5 state whether Ingredient is directly inside, reached through another constituent, or absent (Recipe) -> via:Step
CUBE_FACE_5
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_5 state whether Rim is directly inside, reached through another constituent, or absent (Bicycle)
Choose one of the three supplied options.
```

Delivered choices (public order): `["via:Wheel", "absent", "direct"]`; correct slot 0.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
inventory: via:Wheel
```

Recognition choices: `["5: parts and structural relationships", "2: context, environment and interactions", "3: analogy or metaphor within a declared scope"]`; correct slot 0.

## Face 6 - recomposition_process (family family:mechanical:00, mechanical/chain2)

Worked supports from: family:mechanical:07, family:grammatical:00, family:procedural:00

```
CUBE_FACE_6
node Boiler kind=idea
node Drum kind=idea
node Tube kind=idea
node Sprocket kind=idea
rel Boiler --contains--> Drum
rel Boiler --contains--> Tube
rel Boiler --contains--> Sprocket
Requested view: CUBE_FACE_6 choose the complete account of how these parts make the whole -> Boiler contains Drum ; Boiler contains Sprocket ; Boiler contains Tube
CUBE_FACE_6
node Sentence kind=idea
node Phrase kind=idea
node Word kind=idea
rel Sentence --contains--> Phrase
rel Phrase --contains--> Word
Requested view: CUBE_FACE_6 choose the complete account of how these parts make the whole -> Phrase contains Word ; Sentence contains Phrase
CUBE_FACE_6
node Recipe kind=idea
node Step kind=idea
node Ingredient kind=idea
rel Recipe --contains--> Step
rel Step --contains--> Ingredient
Requested view: CUBE_FACE_6 choose the complete account of how these parts make the whole -> Recipe contains Step ; Step contains Ingredient
CUBE_FACE_6
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
Requested view: CUBE_FACE_6 choose the complete account of how these parts make the whole
Choose one of the three supplied options.
```

Delivered choices (public order): `["Bicycle contains Wheel ; Wheel contains Rim", "Bicycle contains Wheel", "Bicycle contains Outsider ; Bicycle contains Wheel ; Wheel contains Rim"]`; correct slot 0.

Unlabelled recognition excerpt:

```
node Bicycle kind=idea
node Wheel kind=idea
node Rim kind=idea
rel Bicycle --contains--> Wheel
rel Wheel --contains--> Rim
account: Bicycle contains Wheel ; Wheel contains Rim
```

Recognition choices: `["6: recomposition, story or bounded process", "4: explicit correspondence", "3: analogy or metaphor within a declared scope"]`; correct slot 0.

