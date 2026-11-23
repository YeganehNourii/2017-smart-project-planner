# Class diagram

```mermaid
classDiagram
    direction LR

    class Task {
        +str id
        +str name
        +int duration
        +str owner
        +int priority
        +date|None deadline
        +tuple~str~ depends_on
        +bool done
        +is_milestone() bool
    }

    class Project {
        +str name
        +date start
        +dict~str, Task~ tasks
        +add(task)
        +remove(task_id)
        +get(task_id) Task
        +dependents_of(task_id) list~str~
        +validate()
    }

    class BinaryHeap~T~ {
        -list _items
        -int _counter
        +push(item, key)
        +pop() T
        +peek() T
        +from_items(pairs)$ BinaryHeap
        -_sift_up(i)
        -_sift_down(i)
    }

    class TaskSchedule {
        +str task_id
        +int es
        +int ef
        +int ls
        +int lf
        +int slack
        +bool critical
        +date start_date
        +date finish_date
        +bool late
    }

    class CPMResult {
        +list~str~ order
        +dict~str, TaskSchedule~ schedule
        +list~str~ critical_path
        +int duration
        +date end_date
    }

    class Recommendation {
        +Task task
        +TaskSchedule schedule
        +list~str~ reasons
    }

    class Repository {
        -Connection conn
        +save_project(project)
        +load_project(name) Project
        +list_projects() list~str~
        +delete_project(name)
        +add_task(project_name, task)
        +set_done(project_name, task_id, done)
        +delete_task(project_name, task_id)
    }

    class CycleError {
        +list~str~ cycle
    }
    class MissingDependencyError
    class ValidationError

    Project "1" *-- "0..*" Task : contains
    Task "0..*" --> "0..*" Task : depends on
    CPMResult "1" *-- "1..*" TaskSchedule
    Recommendation --> Task
    Recommendation --> TaskSchedule
    Repository ..> Project : saves / loads
    ValidationError <|-- CycleError
    ValidationError <|-- MissingDependencyError

    note for BinaryHeap "used by topological_sort() and next_tasks()"
```

Module functions (not classes) that tie these together:

| Function | Module | Returns |
|---|---|---|
| `topological_sort(tasks)` | `planner.graph` | `list[str]`, or raises `CycleError` / `MissingDependencyError` |
| `critical_path(project)` | `planner.cpm` | `CPMResult` |
| `next_tasks(project, result, limit)` | `planner.scheduler` | `list[Recommendation]` |
| `gantt_figure(project, result)` | `planner.gantt` | Plotly figure as a plain `dict` |
| `analyse(project_json)` | `planner.web` | JSON string for the web demo |
