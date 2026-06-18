### 1. Context-Motivation:

- Expliquer LLE
- Mechanique de coopération
- C'est la target a atteindre

### 2. Verification

- Define a decidability problem for solvability and cooperation required
- make a tool to verify solvability
- reuse it to detect cooperation

### 3. Bounded-horizon solvability

- define the problem and T_max
- the steps to answer the problem
- sat is well know problem, solver are extremly good
- LLE generelized I think is NP-Hard, comparison to chess with the size of grid and pieces

### 4. Cooperation detection

- we remove the cooperation mechanic
- define the strict method
- the steps to flag cooperation / solvability

### 5. Horizon matters

- 3 different T_max 3 different output
- tradeoff

### 6. Cooperation profile

- present them
- explain order
- only one output (the higher one)

### 7. Part 2

- how to use verification tool in generator
- target the coop profile in generators

### 8. Random generator

- everything random
- we don't want that
- constrained random solve that

### 9. Constructive

- step by step how to make a level

### 10. Level 6 style

- what changes with the constructive

### 11. Generator efficiency

- 3x3 2a 1l / 5x5 3a 2l / 8x8 4a 3l
- Random is the higher
- constructive is really good
- level 6 style struggle with small grid

### 12. Output diversity

- 8x8 3n 2l
- random is mostly assymmetric because easyier
- Constructive most mutual - built for that
- Level 6 style less mutual then Constructive

### 13. Part 3

- talk about now using MARL algo on generated levels
- IQL/VDN/QMIX because well know for LLE and famous
- can generator help in training
- curriculum learning

### 14. Learnability

- proof agents can learn on generated levels
- gap between train and test

### 15. Scaling Data

- what happen when we increase training set size
- overfitting becomes generalization
- with unlimited levels, all tests are covered

### 16. Curriculum ordering

- what types of levels.
- direct is better
- mixed is close but better then forward
- reverse is bad (unlearn)

### 17. Curriculum targets

- mutual is hard to learn
- curriculum can not help there

### 18. Contribution LLE repo

- my work is available for all LLE users

### 19. Conclusion

- everything has been done and anwsered positively except for the curriculum on mutual levels

### 20. Future work

- proof LLE is NP-Hard
- add gems
- richer dependency graph
- more experiments on curriculum learning
- more experiments on cooperation profile
- more experiments on different algorithms
