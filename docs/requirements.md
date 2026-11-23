# Requirements

## 1. Purpose

A small planner for **student and small-team projects**. It stores tasks with
durations, deadlines, owners, priorities and "depends on" links. It then
answers two questions: *what should we work on next?* and *when will we
finish?* It draws the answer as a Gantt chart.

## 2. Actors

| Actor | Description |
|---|---|
| **Team member** | Adds tasks, marks them done, asks what to do next. |
| **Project manager** | Creates the project, sets deadlines, checks the critical path and the timeline. Can do everything a team member can. |
| **Visitor** (web demo) | Tries the planner in the browser with a sample project. Nothing is stored on a server. |

## 3. Functional requirements

| ID | Requirement |
|---|---|
| FR1 | Create a project with a name and a start date. |
| FR2 | Add a task with: short id, name, duration in days (0 = milestone), owner, priority 1 (highest) to 5, optional deadline, and a list of tasks it depends on. |
| FR3 | Mark a task done / not done; delete a task (refused while other tasks depend on it). |
| FR4 | Reject invalid data: unknown dependencies, duplicate ids, negative durations, priorities outside 1–5, and **dependency cycles**. Error messages name the problem (for example the cycle `a → b → c → a`). |
| FR5 | Order tasks so that every task comes after the tasks it depends on (topological sort). |
| FR6 | Compute the **critical path** (CPM): earliest/latest start and finish, and slack, for every task, plus the project duration and end date. |
| FR7 | Recommend the **next tasks**. Candidates are tasks that are not done and whose dependencies are all done. They are ranked by urgency: least slack first, then earliest latest-start, then earliest deadline, then priority. Each recommendation explains *why* it ranks where it does. |
| FR8 | Warn when the planned finish of a task is **after its deadline**. |
| FR9 | Draw a **Gantt chart**: one bar per task, critical tasks highlighted, done tasks greyed out, milestones and deadlines marked. |
| FR10 | Store projects in **SQLite** and load them again. Import and export them as JSON. |
| FR11 | Provide a command-line interface and a static web demo that runs the same Python core in the browser. |

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR1 | The scheduling core uses only the Python standard library (≥ 3.10). The heap, topological sort and CPM are implemented by hand, not imported. |
| NFR2 | Scheduling is O((V + E) log V) for V tasks and E dependencies. |
| NFR3 | Results are deterministic: the same input always gives the same order. |
| NFR4 | Scheduling logic is covered by automated pytest tests, including cycles and edge cases. GitHub Actions runs them on every push. |
| NFR5 | The web demo is static (GitHub Pages) and needs no server. Data stays in the visitor's browser. |

## 5. Simplifications (out of scope)

- Durations are whole **calendar days**; weekends and holidays are not skipped.
- Resource levelling is not done. If one owner has two parallel tasks, the plan
  still runs them in parallel. The next-task list is what helps a person
  choose between them.
- One user at a time per database file; there is no login.

## 6. Glossary

- **ES / EF**: earliest start / finish, in days from the project start.
- **LS / LF**: latest start / finish that does not delay the whole project.
- **Slack** (float): `LS − ES`, how many days a task can slip for free.
- **Critical path**: the chain of tasks with zero slack. Any delay there
  delays the project.
