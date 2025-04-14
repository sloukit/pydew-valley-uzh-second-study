# Experiment Utilities

This file holds some useful info for sickness probability and statistics for the experiment.

## Definition of adherence and non-adherence

This is a list of criteria used to determine when the player is considered as following the health 
measures. All durations shown here are in real time.

- A player is assumed to adhere to the bath health measure **when they take a bath within the first three minutes of each level**. If they do not take a bath in that period of time, they will be locked out of taking a bath for the duration of the round.
- A player is considered to adhere to the goggles measure **if over the past three minutes, the player has worn the goggles for at least 2mn30**. This check will be run every three minutes, so a player can stop adhering to the goggles measure after a while or adhere again, and the probabilities should be affected accordingly.


## Player's probability to get sick

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

| Condition     | Ingroup NPC behaviour            |
|---------------|----------------------------------|
| Adherence     | 80% adhering to goggles and bath |
| Non-adherence | 80% non-adhering                 |


## Sick/dead NPC proportions in the various conditions

**NOTE:** if playing in the control condition, the ingroup will randomly select one of two adherence behaviours in the first round (adherence or not).

### Condition: Adherence
This table shows how many NPCS will get sick and potentially die when the player is in the "Adherence" scenario 
(i.e. when most of the ingroup NPCs adhere to the health measures).

- In ingroup: 9 adhering NPCs, 3 non-adhering NPCs
- Outgroup: 6 NPCs adhering, and 6 NPCs not adhering.

| Sick NPCs in ingroup       | Sick NPCs in outgroup      | Dying NPCs in ingroup | Dying NPCs in outgroup | During rounds |
|----------------------------|----------------------------|-----------------------|------------------------|---------------|
| 2 non-adhering, 1 adhering | 5 non-adhering, 1 adhering | 1 non-adhering        | 1 non-adhering         | 7, 8 and 9    |
| 2 non-adhering, 1 adhering | 4 non-adhering, 1 adhering | 0                     | 1 non-adhering         | 10, 11 and 12 |

### Condition: Non-adherence

The following table shows how many NPCs will get sick and potentially die when the player is in the "Non-adherence" scenario
(i.e. when most of the ingroup NPCs refuse to follow the health measures).

- Ingroup: 3 adhering NPCs, 6 non-adhering NPCS
- Outgroup: 6 NPCs adhering, 6 not adhering.

| Sick NPCs in ingroup       | Sick NPCs in outgroup      | Dying NPCs in ingroup | Dying NPCs in outgroup | During rounds |
|----------------------------|----------------------------|-----------------------|------------------------|---------------|
| 8 non-adhering, 1 adhering | 5 non-adhering, 1 adhering | 2 non-adhering        | 1 non-adhering         | 7, 8 and 9    |
| 6 non-adhering, 1 adhering | 4 non-adhering, 1 adhering | 1 non-adhering        | 1 non-adhering         | 10, 11 and 12 |


