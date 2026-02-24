# ARES COMMAND — Mars Colony Simulation

Static classroom dashboard for Lesson 7.

## Run locally

Open `index.html` in a browser.

## GitHub Pages

1. Push this folder to a GitHub repository.
2. In GitHub: `Settings` -> `Pages`.
3. Under `Build and deployment`, choose:
   - `Source`: `Deploy from a branch`
   - `Branch`: `main` and folder `/ (root)`
4. Save and wait for deployment.
5. Your public URL will be:
   - `https://<github-username>.github.io/<repo-name>/`

## MU workflow (manual mode)

- Teacher enters each team's MU budget manually and broadcasts.
- Team budget in Proposal is numeric.
- Each team's budget is its own effective spacecraft capacity for that team.

## Access token workflow

- Students cannot access the app until they pass the access gate.
- Teacher enters as teacher with PIN, then configures `TEAM ID + MU + TOKEN`.
- Teacher clicks `GENERATE PACKAGE` and shares the package string with students.
- Student pastes package + team token in the gate.
- Students using the same token are assigned the same team and MU setup.

## Realtime sync (Firebase RTDB)

- Session data syncs under `sessions/<session-id>`.
- Teacher actions (`broadcast`, `generate package`, `clear team`, `clear all`) propagate to all connected instances.
- Team submissions sync live across devices.

## Security note

- Current DB rules are open read/write. This is convenient for testing but not secure for production.
