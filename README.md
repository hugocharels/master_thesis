# Procedural Generation of Solvable Levels in LLE

### Master Thesis – Hugo Charels (ULB, 2025–2026)

This repository contains the code and experiments for my Master Thesis:

> **Procedural Generation of Solvable Levels in a Multi-Agent Reinforcement Learning Environment using Curriculum Learning**

The project focuses on generating **solvable, cooperative, and learnable levels** for the **Laser Learning Environment (LLE)**, a benchmark designed for studying coordination in Multi-Agent Reinforcement Learning (MARL).

---

## 📌 Project Overview

The goal of this work is to design and evaluate a framework capable of generating levels that satisfy three core properties:

- ✅ **Solvability** – Every generated level must admit at least one valid joint solution.
- 🤝 **Cooperation** – Levels must require inter-agent coordination.
- 📈 **Learnability** – Generated levels should be suitable for training MARL agents, potentially through curriculum learning.

Rather than manually designing levels, this project explores **procedural generation techniques** combined with theoretical guarantees and validation mechanisms.

---

## 🎮 Laser Learning Environment (LLE)

<p align="center">
  <img src="lvl6-annotated.png" alt="Example LLE Level" width="500"/>
</p>

The Laser Learning Environment (LLE) is a 2D grid-based cooperative puzzle game where:

- Agents must navigate through walls and colored laser beams.
- Each laser can only be blocked by an agent of the matching color.
- All agents must reach their exits **simultaneously**.
- Intermediate cooperative steps provide **no reward**, making exploration difficult.

This environment is particularly suited for studying:

- Coordination under sparse rewards
- State-space bottlenecks
- Temporal synchronization
- Inter-agent dependencies

🔗 Official LLE implementation:  
https://github.com/yamoling/lle

---

## 🧠 What This Repository Will Contain

This repository will include:

### 1 Level Generation Framework

- Implementation of procedural generation techniques
- Modular generator architecture

### 2 Solvability & Validation Tools

- Reachability and structural validation
- Cooperation constraint verification

---

## 🎯 Research Questions

This project aims to investigate:

- How to embed **solvability directly into generation**
- How to enforce **structural cooperation**
- How level structure impacts **MARL learnability**
- How to balance **diversity vs. controllability**
- (How to integrate **curriculum learning into PCG**)

---

## ⚙️ Current Status

🚧 Work in progress — this repository is under active development as part of the Master Thesis.

---

## 📄 License

This project is developed for academic research purposes.
License details will be added upon completion.
