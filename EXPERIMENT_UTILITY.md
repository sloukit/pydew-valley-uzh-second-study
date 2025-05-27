# Experiment Utilities

This file holds some useful info for sickness probability and statistics for the experiment.

## Sickness symptoms

Sickness is decided every five minutes after the first five minutes have passed.
If the player gets sick, they first suffer severe symptoms for three minutes, then they gradually recover (players cannot die, unlike NPCs).

| Symptom               | Severe                                  | Recovery                                |
|-----------------------|-----------------------------------------|-----------------------------------------|
| Reduced walking speed | 50% of normal speed                     | 75% of normal speed                     |
| Ability to use tools  | 30% chance to fail using any given tool | 10% chance to fail using any given tool |

NPCs will also suffer from these same symptoms, but unlike the player, their recovery/death is determined in advance.
If, for a given condition, enough NPCs died, NPCs cannot die anymore if they fulfill that condition.
For example, in an adhering setting, only one non-adhering NPC can die in the first three rounds.

For each potentially dying NPC, the death moment shall be selected in advance (round number and timestamp).
This could potentially be saved in the database so everything can be computed when starting a new game at once.


## Definition of adherence and non-adherence

This is a list of criteria used to determine when the player is considered as following the health 
measures. All durations shown here are in real time.

- A player is assumed to adhere to the bath health measure **when they take a bath within the first three minutes of each level**. If they do not take a bath in that period of time, they will be locked out of taking a bath for the duration of the round.
- A player is considered to adhere to the goggles measure **if over the past five minutes, the player has worn the goggles for at least 4mn**. This check will be run twice per round, after five minutes have passed, and then after 10 minutes have passed.


## Player's probability to get sick

**Players cannot get sick during the first five minutes of each round.**

**NOTE:** An adhering player can only get sick once during the entire six rounds, as long they adhere to the health measures
for all rounds.

### Rounds 7 to 9

| Wears goggles for long enough? | Takes a bath early enough? | Likelihood of getting sick |
|--------------------------------|----------------------------|----------------------------|
| No                             | No                         | 90%                        |
| No                             | Yes                        | 50%                        |
| Yes                            | No                         | 70%                        |
| Yes                            | Yes                        | 10%                        |


### Rounds 10 to 12

| Wears goggles for long enough? | Takes a bath early enough? | Likelihood of getting sick |
|--------------------------------|----------------------------|----------------------------|
| No                             | No                         | 70%                        |
| No                             | Yes                        | 30%                        |
| Yes                            | No                         | 50%                        |
| Yes                            | Yes                        | 10%                        |


## NPC behaviours in experiment conditions
**NOTE:** Regardless of the experiment condition, the outgroup will always have half of its members adhering to both measures (a given NPC can either adhere to both measures or to none).

| Condition     | Ingroup NPC behaviour                    |
|---------------|------------------------------------------|
| Adherence     | 80% of NPCs adhering to goggles and bath |
| Non-adherence | 80% non-adhering                         |


## Sick/dead NPC proportions in the various conditions

**NOTE:** if playing in the control condition, the ingroup will randomly select one of two adherence behaviours in the first round (adherence or not).

### Condition: Adherence
This table shows how many NPCS will get sick and potentially die when the player is in the "Adherence" scenario 
(i.e. when most of the ingroup NPCs adhere to the health measures).

| Sick NPCs in ingroup       | Sick NPCs in outgroup      | Dying NPCs in ingroup | Dying NPCs in outgroup | During rounds |
|----------------------------|----------------------------|-----------------------|------------------------|---------------|
| 2 non-adhering, 1 adhering | 5 non-adhering, 1 adhering | 1 non-adhering        | 1 non-adhering         | 7, 8 and 9    |
| 2 non-adhering, 1 adhering | 4 non-adhering, 1 adhering | 0                     | 1 non-adhering         | 10, 11 and 12 |

### Condition: Non-adherence

The following table shows how many NPCs will get sick and potentially die when the player is in the "Non-adherence" scenario
(i.e. when most of the ingroup NPCs refuse to follow the health measures).

| Sick NPCs in ingroup       | Sick NPCs in outgroup      | Dying NPCs in ingroup | Dying NPCs in outgroup | During rounds |
|----------------------------|----------------------------|-----------------------|------------------------|---------------|
| 8 non-adhering, 1 adhering | 5 non-adhering, 1 adhering | 2 non-adhering        | 1 non-adhering         | 7, 8 and 9    |
| 6 non-adhering, 1 adhering | 4 non-adhering, 1 adhering | 1 non-adhering        | 1 non-adhering         | 10, 11 and 12 |


