# Diplomatic Debate Simulation

A multi-agent, LLM-driven simulation for orchestrating diplomatic debates among different countries. Each `CountryAgent` responds with official statements, while a `JudgeAgent` evaluates each round and delivers a final verdict. The system is orchestrated end-to-end by a `DebateOrchestrator`, using **AgentScope** to manage messaging among agents.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Installation & Setup](#installation--setup)
5. [Usage](#usage)
6. [Detailed Example Flow](#detailed-example-flow)
7. [Design Rationale](#design-rationale)
8. [Code Documentation Guidelines](#code-documentation-guidelines)
   1. [Comments & Docstrings](#comments--docstrings)
   2. [Time Complexity](#time-complexity)
9. [Key Modules & Classes](#key-modules--classes)
10. [Troubleshooting & FAQs](#troubleshooting--faqs)
11. [Contributing](#contributing)
12. [License](#license)
13. [Architecture & Flow](#architecture--flow)

---

## 1. Overview

The **Diplomatic Debate Simulation** provides an end-to-end solution for simulating a multi-round, multi-country debate over a specified geopolitical issue. Each country:

- Has a **profile** describing its background, foreign policy, etc.
- Implements a **CountryAgent** that uses a Large Language Model (LLM) to generate official statements.
- Maintains short-term and long-term **memory** of the conversation, strategic considerations, and overall historical context.

A **JudgeAgent** observes these statements every round, compiles them, scores each country, and eventually produces a **final verdict**. The entire conversation is orchestrated via `DebateOrchestrator`, which also logs every message to a transcript for later review.

**Key Purposes**:

- Demonstrate how separate AI agents can coordinate in a shared environment.
- Show how to parse LLM outputs to keep data structured, consistent, and robust.
- Provide an example of an interactive scenario where memory and profiles significantly affect agent responses.

---

## 2. Features

1. **Modular Agent Design**

   - **CountryAgent**: Focuses on generating official statements, validated by a diplomatic protocol check.
   - **JudgeAgent**: Evaluates each round, sets scores, and summarizes.

2. **Multi-Round Debate**

   - N configurable rounds; each country speaks in turn, the judge scores them, then final verdict.

3. **Strict JSON Parsing**

   - Output from each agent is forced into JSON with a parser.
   - This ensures structured data, easy introspection, and consistent updates.

4. **Profile Builder**

   - If a country’s profile doesn’t exist, we can build it automatically using search queries and LLM calls.
   - Fallbacks for incomplete data (backup prompts).

5. **Transcript Logging**

   - A textual `debate_log.txt` is produced, capturing all messages in a time-stamped format.

6. **AgentScope Integration**
   - We leverage `agentscope.msghub(...)` to broadcast messages among participants, simplifying multi-agent communication.

---

## 3. Project Structure

```
.
├── run.py                 # Entry point script to initiate the debate
├── pyproject.toml         # Build system / project metadata
├── requirements.txt       # Python dependencies
├── data/
│   ├── country_profiles/
│   │   ├── united_states.json
│   │   ├── china.json
│   │   └── france.json
│   └── ...
├── src/
│   ├── agents/
│   │   ├── country_agent.py
│   │   ├── judge_agent.py
│   │   └── orchestrator.py
│   ├── builder/
│   │   └── builder.py
│   ├── memory/
│   │   └── streams.py
│   ├── models/
│   │   └── country_profile.py
│   ├── prompts/
│   │   └── ... # All the prompt templates for LLM
│   ├── parsers/
│   │   └── parsers.py
│   ├── utils/
│   │   └── utils.py
│   └── validator/
│       └── validator.py
└── ...
```

- **`run.py`**: Main entry point to run the entire simulation.
- **`src/agents/`**: Country, Judge, and Orchestrator logic.
- **`src/builder/`**: Tools for building or loading country profiles.
- **`src/memory/`**: Classes for memory management.
- **`src/models/`**: Data models (Pydantic) for typed profile structures.
- **`src/parsers/`**: JSON parsing logic to handle LLM responses.
- **`src/prompts/`**: Prompt templates specifying how the LLM should respond.
- **`src/validator/`**: Classes for validating (and applying changes to) profiles.

---

## 4. Installation & Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/YourUserName/DebateSimulation.git
   cd DebateSimulation
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # or for Windows:
   venv\Scripts\activate.bat
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set your environment variables**:

   - Typically, you need an `OPENAI_API_KEY` set for the LLM calls.
   - Optionally, create a `.env` file in the project root with:
     ```
     OPENAI_API_KEY=<your_key>
     ```

5. **(Optional) Build profiles**:
   - The first time you run it, any missing country profiles are built automatically. This might require internet access for DuckDuckGo search + LLM calls.

---

## 5. Usage

Once installed:

```bash
python run.py
```

By default, `run.py`:

- Initializes `agentscope` with a chosen model config.
- Defines a set of countries, e.g. `["United States", "China", "France"]`.
- Sets a problem statement: `"Disputed trade routes in international waters..."`.
- Runs `DebateOrchestrator(...)` for 3 rounds.
- Logs the entire conversation to `debate_log.txt`.

**Customizing**:

- **Number of Rounds**: In `run.py`, adjust `num_rounds=3` to your desired integer.
- **Countries**: Add or remove countries in the `countries = [...]` list. If no profile JSON exists, it builds it.
- **Log File**: Change `log_file_path` if you want a different name or location for the transcript.

---

## 6. Detailed Example Flow

1. **Initialization**:  
   The orchestrator imports country profiles, or if they don’t exist, runs the `CountryProfileBuilder` to build them.

2. **Round 1**:

   - The `Host` announces the problem statement.
   - Each `CountryAgent` speaks once, referencing its memory to produce a validated JSON response.
   - The `JudgeAgent` sees all these statements, calls the LLM to generate a round summary in JSON, and logs it.

3. **Round 2..N**:

   - The orchestrator repeatedly signals the next round.
   - Each country again produces a statement, referencing the newly updated debate memory.
   - The judge evaluates them again, storing the new round data.

4. **Final Verdict**:

   - When the orchestrator triggers the judge after the last round, the `JudgeAgent` compiles final scores, ranks each country, and produces a concluding summary.

5. **Logging**:
   - Each message is appended to `debate_log.txt` with a timestamp, role, and the message content.

---

## 7. Design Rationale

This project uses a multi-agent approach, where each agent has distinct responsibilities and memory. Below is the rationale behind each design choice:

1. **Strict JSON for LLM Output**

   - We require each LLM-based agent to produce JSON, parsed by classes in `src/parsers/parsers.py`.
   - This ensures we can reliably extract fields like `score`, `analysis`, etc., without string mismatch or ad hoc regex.

2. **Modular Memory**

   - Each `CountryAgent` has a `DiplomaticMemoryStream` that keeps track of past statements (debate history), strategic analysis, and general knowledge.
   - This promotes **longer-term consistency** in multi-round dialogues.

3. **Separation of Roles**

   - **CountryAgent**: Focuses solely on generating a new official statement.
   - **JudgeAgent**: Aggregates statements each round and uses a different prompt to produce a JSON-based score summary.

4. **Orchestrator**

   - A single orchestrator (`DebateOrchestrator`) handles the flow from round to round.
   - This centralizes logic for announcements, round ordering, final verdict, etc.

5. **Why This Layout**
   - We wanted each piece of logic (country building, memory, agenting, judging, orchestrating) to remain loosely coupled.
   - **Easy Debugging**: If the judge sees no messages, it’s simpler to diagnose that the orchestrator might not be broadcasting or that a country has the wrong name.

---

## 8. Code Documentation Guidelines

### 8.1 Comments & Docstrings

- **Docstrings**: All public classes and methods should have a docstring describing purpose, parameters, and returns. Example:

  ```python
  def reply(self, incoming_msg: Optional[Msg] = None) -> Msg:
      """
      Generates a diplomatic response based on internal memory and the incoming message.

      :param incoming_msg: The last message observed (can be None if first call).
      :return: A structured Msg with "diplomatic_response" text.
      """
  ```

- **Inline Comments**: For logic that’s not straightforward, add short comments. For example:
  ```python
  # Filter out only country messages from memory
  country_messages = [m for m in raw_memory if m.name in self._country_list]
  ```

### 8.2 Time Complexity

- **Round Execution**: Each round calls `C` `CountryAgent`s, then 1 `JudgeAgent`. For `R` rounds, total calls = `O(R*C)`.
- **JSON Parsing**: Typically `O(M)` on the size of the LLM text, though overshadowed by network calls to the LLM.
- **Profile Building**: Each country profile is built once with multiple search queries + LLM calls. The overhead is mostly external API calls (I/O bound).

---

## 9. Key Modules & Classes

1. **`DebateOrchestrator`** (in `src/agents/orchestrator.py`)

   - Orchestrates the entire debate.
   - Methods:
     - `run_debate()`: Announces rounds, collects messages, triggers the judge, logs everything.

2. **`CountryAgent`** (in `src/agents/country_agent.py`)

   - Subclass of `DialogAgent`.
   - Maintains a `DiplomaticMemoryStream` for each country.
   - `reply(...)`: Build prompt from memory, call LLM, parse JSON, validate the statement.

3. **`JudgeAgent`** (in `src/agents/judge_agent.py`)

   - Evaluates each round by reading all relevant country statements.
   - `_evaluate_round(...)` ensures each country spoke once, calls the LLM to produce a JSON-based round summary.
   - `_final_verdict(...)` compiles a final ranking and summary.

4. **`DiplomaticMemoryStream`** (in `src/memory/streams.py`)

   - Manages general, debate, and strategy memories for a single country.
   - Adds new statements to the debate memory, triggers “strategic analysis” calls for foreign statements.

5. **`CountryProfileBuilder`** (in `src/builder/builder.py`)

   - Either loads a JSON file if the profile exists or builds it by using search queries + LLM calls.
   - Validates the final profile with `ProfileValidator`.

6. **Parsers** (in `src/parsers/parsers.py`)
   - A set of `MarkdownJsonDictParser` objects for different tasks, e.g. parsing round output, final verdict, or country statements.

---

## 10. Troubleshooting & FAQs

1. **The judge raises “Expected X but got 0”**

   - This usually means the judge didn’t receive the countries’ messages. Ensure you’re using `with msghub(self.all_agents)` and that each agent’s name matches exactly the strings in `judge_agent._country_list`.

2. **JSON Parsing Errors (“invalid control character”)**

   - Sometimes LLMs produce curly quotes or incomplete JSON.
   - Add a sanitize step (e.g. replacing `“` with `"` before parse) or instruct the LLM to strictly use ASCII quotes.

3. **Profile Fails to Build**

   - Check your network connection or your API keys for DuckDuckGoSearchAPIWrapper. Also ensure your `OPENAI_API_KEY` is set.

4. **LLM Repeats the Same Statement**
   - Increase `temperature` in the model config or add more context changes from round to round. Ensure no caching is interfering.

---

## 11. Contributing

1. **Fork & Clone**: If you want to propose changes, fork the repo and clone locally.
2. **Create a Branch**: For a new feature or bugfix, `git checkout -b feature/your-feature`.
3. **Code Standards**:
   - Add docstrings where missing.
   - Ensure `pylint` or `flake8` passes if you have style checks.
4. **Pull Request**: Submit a PR describing the change or fix. We’ll review it ASAP.

---

## 12. License

This repository is distributed under the **MIT License**. See `LICENSE` for more details.

---

## Thank You!

We hope the Diplomatic Debate Simulation helps you explore advanced usage of multi-agent systems and structured LLM interactions. If you have any questions, feel free to open an issue or reach out!

_Enjoy simulating diplomatic negotiations!_

---

## 13. Architecture & Flow

This section visually explains how the system’s components interact and how a single debate round unfolds.

### 13.1 Architecture Diagram

```mermaid
flowchart LR
    subgraph "Orchestrator"
        O[DebateOrchestrator<br/>- Orchestrates Rounds<br/>- Maintains Problem Statement<br/>- Logs Transcript]
    end

    subgraph "Agents"
    A1[CountryAgent<br/>- One instance per country<br/>- Maintains DiplomaticMemoryStream]
    A2[JudgeAgent<br/>- Observes all statements<br/>- Produces round scores & final verdict]
    end

    subgraph "Memory"
    M1[General Memory]
    M2[Debate Memory]
    M3[Strategy Memory]
    end

    O --> A1
    O --> A2

    A1 -->|Build official statement| LLM[(OpenAI Model)]
    A2 -->|Evaluate statements| LLM
    A1 --> M1
    A1 --> M2
    A1 --> M3

    O -->|Logs| LOGFILE[debate_log.txt]
```

**Explanation**:

1. **DebateOrchestrator** (O) controls the debate flow and logging.
2. **CountryAgent** (A1) uses a `DiplomaticMemoryStream` (M1, M2, M3) and calls the LLM to build official statements.
3. **JudgeAgent** (A2) evaluates statements each round using the LLM.
4. The final transcript is written to `debate_log.txt`.

### 13.2 Sequence Diagram (Round Flow)

```mermaid
sequenceDiagram
    participant Host
    participant Orchestrator
    participant Country1
    participant Country2
    participant Judge

    Host->>Orchestrator: Start Debate (Round 1)
    Orchestrator->>Country1: Request opening statement
    Country1->>Country1: Access DiplomaticMemoryStream
    Country1->>LLM: Generate official statement (JSON)
    LLM-->>Country1: Return structured response
    Country1-->>Orchestrator: Diplomatic statement (in JSON)

    Orchestrator->>Country2: Request opening statement
    Country2->>Country2: Access DiplomaticMemoryStream
    Country2->>LLM: Generate official statement (JSON)
    LLM-->>Country2: Return structured response
    Country2-->>Orchestrator: Diplomatic statement (in JSON)

    note over Country1,Country2: (Repeat for all participating countries...)

    Orchestrator->>Judge: Summon round evaluation
    Judge->>Judge: Summarize all country statements
    Judge->>LLM: Evaluate & produce round scores
    LLM-->>Judge: JSON round summary
    Judge-->>Orchestrator: Round results & summary
    note over Orchestrator,Judge: Round complete – proceed to next round or final verdict
```

**Explanation**:

1. The **Host** (system or user) triggers the round start.
2. The **Orchestrator** requests each **CountryAgent**’s statement sequentially.
3. Each **CountryAgent** calls the **LLM** to craft a JSON-based diplomatic response, referencing their memory.
4. After all countries speak, the **JudgeAgent** evaluates them, also using the **LLM**.
5. The result is compiled, and the Orchestrator either proceeds to the next round or obtains the final verdict if all rounds are complete.

---
