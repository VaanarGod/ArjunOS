# Crew: several workers, long files split between them

**Pick the models.** In the Crew sidebar, Workers opens a list of installed models with a switch for each (up to 8). Switch on any number: every one of them is put to work. Leave it on Automatic to let the crew choose the smallest capable model. A model you force on a single file still wins for that file.

**Long files are measured and cut.** Before the boss plans anything, each file is measured (PDF page markers, characters, page images for scans):

* a file that fits comfortably in one worker stays whole (about 24,000 characters per worker by default, tied to your attachment budget);
* a longer one is cut into balanced parts at page boundaries (PDF) or paragraph boundaries (other text), never into pieces smaller than about 4,000 characters, and never more than 8 parts per file or `max_subtasks` workers in total;
* with several models switched on, the file is cut into at least as many parts as each model can get a real share of;
* scanned PDFs are cut into page ranges of about 6 pages, for vision models only.

**Every part gets its own worker.** The boss still writes the instructions and the shared conventions, but if it lumps parts together or names the whole file, each part is still read by its own worker, told exactly which pages it covers and that others read the rest. The boss then reviews and combines the reports, as before.

**Which model reads which part.** Every switched-on model gets real work before any gets a second part; after that each part goes where it would finish soonest, so small fast models read more and big slow ones less. Scanned parts go only to vision models. A switched-on model with nothing to read is announced, not silently ignored.

**Preview = run.** The sidebar shows the split (file, pages, parts, model per part) before you start, from the same function the run uses. Memory planning counts every distinct model that will run; the Memory setting decides how many are awake at once, so with little RAM the workers take turns.

Code: `orchestration/split.py` (pure functions), `CrewEngine.layout` in `orchestration/crew.py`. Tests: `tests/test_crew_split.py`, `CrewSplitTests.swift`.
